from typing import Any, Dict, List, Optional, Iterable
import re, html
from datetime import datetime
import json
import os

from pathlib import Path

import sys
import tempfile
import subprocess

from models.applicant import ApplicantEntry, ApplicantEntryExtended

""" 
*****************
Schemas, some validation methods and normalizations suggested by chatGPT-4
*****************
"""

# Required fields for the schema
REQUIRED_FIELDS = [
    "program",      # str 
    "university",   # str 
    "date_added",   # ISO 'YYYY-MM-DD' preferred
    "url",          # absolute http/https
    "status",       # one of STATUS_ALLOWED
]

# Optional fields for the schema
OPTIONAL_FIELDS = [
    "comments",     # str | None 
    "accept_date",  # ISO 'YYYY-MM-DD' | None 
    "reject_date",  # ISO 'YYYY-MM-DD' | None 
    "start_term",   # 'Fall' | 'Spring' | 'Summer' | None 
    "start_year",   # int | None
    "citizenship",  # 'International' | 'American' | None
    "gre_total",    # int | None (260–340)
    "gre_verbal",   # int | None (130–170)
    "gre_aw",       # float | None (0.0–6.0, 0.5 steps ok)
    "degree",       # 'Masters' | 'PhD' | 'MFA' | 'MBA' | 'JD' | 'EdD' | 'PsyD' | 'Other' | None
    "gpa",          # float | None 
]

# Full schema fields
SCHEMA_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# -------- Allowed canonical values ----------------------------
# TODO: extend if necessary

STATUS_ALLOWED = {"Accepted", "Rejected", "Interview", "Waitlisted", "Pending"}
DEGREE_ALLOWED = {"Masters", "PhD", "MFA", "MBA", "JD", "EdD", "PsyD", "Other"}
TERM_ALLOWED   = {"Fall", "Spring", "Summer"}
CIT_ALLOWED    = {"International", "American"}

# -------- Cleaner class -------------------------------
class Cleaner:
    """
    Cleans scraped rows into the assignment schema
    """

    def __init__(
        self,
        *,
        gpa_max: float = 5.0,  # cap GPA at this value
        year_min: int = 1950,  # earliest allowable start_year
        year_max: int = 2035,  # latest allowable start_year
        dedupe_by_url: bool = True,  # drop duplicate URLs
        validate_with_dataclass: bool = True,  # enable dataclass validation with ApplicantEntry
    ) -> None:
        """
        Parameters are tunables for cleaning and validation behavior.
        """
        # Store parameters casted to correct types
        self.gpa_max = float(gpa_max)
        self.year_min = int(year_min)
        self.year_max = int(year_max)
        self.dedupe_by_url = bool(dedupe_by_url)
        self.validate_with_dataclass = bool(validate_with_dataclass)

        # Year check 
        if self.year_min > self.year_max:
            raise ValueError(f"year_min ({self.year_min}) cannot be greater than year_max ({self.year_max}).")
        
        # optional dataclass validation
        self._ApplicantEntry = None
        self._ApplicantEntryExtended = None

    # ---------- Public API ----------

    def clean_rows(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean an iterable of raw rows produced by scrape.py.
        Returns a new list of normalized dicts containing only SCHEMA_FIELDS.
        """
        cleaned: List[Dict[str, Any]] = []

        total = 0
        print("[INFO][Clean.py:cleaner]clean_rows: start")


        for idx, raw in enumerate(rows):
            total += 1
            if not isinstance(raw, dict):
                # ignore non-dict items silently
                continue

            shaped = self._drop_to_schema(raw)
            norm = self._normalize_row(shaped)

            # Enforce non-empty strings
            must_have = ("program", "university", "date_added", "url", "status")
            missing = False
            for k in must_have:
                v = norm.get(k)
                if not isinstance(v, str) or not v.strip():
                    missing = True
                    break
            if missing:
                # Drop rows that don't satisfy requirements
                continue

            # Dataclass validation
            if self.validate_with_dataclass:
                self.validate_row_with_dataclass(norm)

            cleaned.append(norm)

        cleaned = self._dedupe_by_url(cleaned)
        print("[INFO][Clean.py:Cleaner]: done. total =", total, "kept =", len(cleaned))
        
        return cleaned
    
    def clean_file(self, in_path: str | Path, out_path: str | Path) -> List[Dict[str, Any]]:
        """
        Load JSON array from in_path, clean rows to the SCHEMA_FIELDS, and save to out_path.
        Returns the cleaned rows.
        """
        print(f"[INFO][Clean.py: Cleaner] Loading rows from {in_path}")
        rows = self._load_json(in_path)
        print(f"[INFO][Clean.py: Cleaner] Loaded {len(rows)} rows")
        cleaned = self.clean_rows(rows)
        print(f"[INFO][Clean.py: Cleaner] Wrote cleaned rows to {out_path}")
        self._save_json(cleaned, out_path)
        return cleaned

    # ---------- dataclass validation ----------

    def enable_dataclass_validation(self, applicant_cls, applicant_ext_cls=None) -> None:
        """
        Provide ApplicantEntry and ApplicantEntryExtended dataclasses to enforce types.
        When enabled, each cleaned row may be instantiated with ApplicantEntry(**row).
        """
        self._ApplicantEntry = applicant_cls
        self._ApplicantEntryExtended = applicant_ext_cls
        print("[INFO][Clean.py:cleaner]data class validation enabled and set to {applicant_cls} and {applicant_ext_cls}")

    def validate_row_with_dataclass(self, row: Dict[str, Any]) -> None:
        """
        If dataclass validation is enabled, instantiate the supplied ApplicantEntry with 'row'.
        Raise on schema/type mismatch; otherwise do nothing.
        """
        if not self.validate_with_dataclass or not self._ApplicantEntry:
            print("[WARNING][Clean.py:cleaner]validate_row_with_dataclass: skipped (validation disabled or ApplicantEntry not set)")
            return

        # Decide which dataclass to use
        use_ext = (
            self._ApplicantEntryExtended is not None and
            ("program_canon" in row or "university_canon" in row)
        )
        cls = self._ApplicantEntryExtended if use_ext else self._ApplicantEntry
        try:
            cls(**row)
        except Exception as e:
            print("[ERROR][Clean.py:cleaner]alidate_row_with_dataclass: FAILED ", repr(e))
            raise

    # ---------- LLM integration ----------

    def extend_with_llm(self, rows: List[Dict[str, Any]], llm_client: "LLMClient") -> List[Dict[str, Any]]:
        """
        Call the local LLM (llm_hosting/app.py) to produce canonical labels
        and **override** 'program' and 'university' when non-empty.
        """
        if not rows:
            print("[WARNING][clean.py: LLM_Client] extend_with_llm: no rows: skipping")
            return []

        # Build inputs for the CLI: "Program, University"
        texts = [
            f"{(r.get('program') or '').strip()}, {(r.get('university') or '').strip()}".strip(", ")
            for r in rows
        ]

        labels = llm_client.canonize_batch(texts)
        print("[INFO][clean.py:LLM_Client] extend_with_llm:", len(labels), "labels")

        if len(labels) != len(rows):
            print("[WARNING][clean.py: LLM_Client] extend_with_llm: label count mismatch (rows=", len(rows), ", labels=", len(labels), ")")

        extended: List[Dict[str, Any]] = []
        for i, (r, lab) in enumerate(zip(rows, labels), start=1):
            
            out = dict(r)

            prog_c = lab.get("program_canon")
            univ_c = lab.get("university_canon")

            # Attach canon fields for traceability
            out["program_canon"] = prog_c
            out["university_canon"] = univ_c

            # Override primary fields when LLM returns non-empty strings
            orig_prog = out.get("program")
            orig_univ = out.get("university")

            if isinstance(prog_c, str) and prog_c.strip():
                out["program"] = prog_c.strip()
            if isinstance(univ_c, str) and univ_c.strip():
                out["university"] = univ_c.strip()

            if out["program"] != orig_prog or out["university"] != orig_univ:
                print("[LLM] changed:",
                    "prog:", repr(orig_prog), "->", repr(out["program"]),
                    "| univ:", repr(orig_univ), "->", repr(out["university"]))
               

            # Optional dataclass validation for the extended record
            if self.validate_with_dataclass and (self._ApplicantEntry or self._ApplicantEntryExtended):
                try:
                    self.validate_extended_row(out)
                except Exception as e:
                    print("[INFO][clean.py: LLM_Client] dataclass fail; reverting canon for row", i, "->", repr(e))
                    # If validation fails, revert overrides and null out canon
                    out["program"] = orig_prog
                    out["university"] = orig_univ
                    out["program_canon"] = None
                    out["university_canon"] = None

            extended.append(out)

        return extended

    def validate_extended_row(self, row: Dict[str, Any]) -> None:
        """
        Validate a post-LLM row (should include 'program_canon'/'university_canon' as str|None).
        If ApplicantEntryExtended is provided, instantiate it to enforce the extended schema.
        """
        if not self.validate_with_dataclass:
            return
        if self._ApplicantEntryExtended is not None:
            self._ApplicantEntryExtended(**row)
        elif self._ApplicantEntry is not None:
            # Fallback to base dataclass if extended isn't available.
            self._ApplicantEntry(**row)

    # ---------- Internal helpers  ----------

    def _drop_to_schema(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Keep only SCHEMA_FIELDS. Add missing keys with None. Do not coerce here.
        """
        return {k: row.get(k, None) for k in SCHEMA_FIELDS}

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes row fields
        """
        out = self._drop_to_schema(row)

        # -------- helpers --------
        def _norm_str(x):
            if x is None:
                return None
            s = str(x)
            s = re.sub(r"<[^>]+>", " ", s)
            s = html.unescape(s)
            s = re.sub(r"\s+", " ", s).strip()
            return s or None

        def _to_int(x):
            try:
                return int(str(x).strip())
            except Exception:
                return None

        def _to_float(x):
            try:
                return float(str(x).strip())
            except Exception:
                return None

        def _date_iso(s):
            """Try ISO and 'Month DD, YYYY'."""
            s = _norm_str(s)
            if not s:
                return None
            for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
                try:
                    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                except Exception:
                    pass
            return s  # keep original if unknown format

        # -------- REQUIRED fields --------
        out["program"] = _norm_str(out.get("program"))
        out["university"] = _norm_str(out.get("university"))
        out["url"] = _norm_str(out.get("url"))

        # status canonicalization:
        sraw = _norm_str(out.get("status"))
        if not sraw:
            out["status"] = None
        else:
            s = sraw.lower().replace(" ", "")
            if "wait" in s:
                out["status"] = "Waitlisted"
            elif s == "accepted":
                out["status"] = "Accepted"
            elif s == "rejected":
                out["status"] = "Rejected"
            elif s == "interview":
                out["status"] = "Interview"
            elif s == "pending":
                out["status"] = "Pending"
            else:
                out["status"] = "Pending"

        out["date_added"] = _date_iso(out.get("date_added"))

        # -------- OPTIONAL fields --------
        out["comments"] = _norm_str(out.get("comments"))

        # degree
        draw = _norm_str(out.get("degree"))
        if draw:
            deg_field = draw.lower().replace(".", "").replace("’", "'")
            deg_map = {
                "masters": "Masters", "master's": "Masters", "ms": "Masters",
                "phd": "PhD", "mfa": "MFA", "mba": "MBA",
                "jd": "JD", "edd": "EdD", "psyd": "PsyD", "other": "Other",
            }
            out["degree"] = deg_map.get(deg_field, None)
        else:
            out["degree"] = None

        # start_term
        traw = _norm_str(out.get("start_term"))
        term = None
        if traw:
            t = traw.lower()
            if t in ("fall", "autumn"):
                term = "Fall"
            elif t == "spring":
                term = "Spring"
            elif t.startswith("summer"):
                term = "Summer"
            elif t == "winter":
                term = "Spring"
            elif t in ("q1", "quarter1"):
                term = "Spring"
            elif t in ("q2", "quarter2"):
                term = "Summer"
            elif t in ("q3", "quarter3"):
                term = "Fall"
            elif t in ("q4", "quarter4"):
                term = "Fall"
        out["start_term"] = term

        # start_year bounded
        sy = _to_int(out.get("start_year"))
        if sy is None or sy < self.year_min or sy > self.year_max:
            sy = None
        out["start_year"] = sy

        # citizenship
        craw = _norm_str(out.get("citizenship"))
        if craw:
            c = craw.lower()
            if c.startswith("inter"):
                out["citizenship"] = "International"
            elif c.startswith("amer"):
                out["citizenship"] = "American"
            else:
                out["citizenship"] = None
        else:
            out["citizenship"] = None

        # GPA
        gpa = _to_float(out.get("gpa"))
        if gpa is None or gpa < 0.0 or gpa > float(self.gpa_max):
            gpa = None
        out["gpa"] = gpa

        # GREs
        gt = _to_int(out.get("gre_total"))
        out["gre_total"] = gt if gt is not None and 260 <= gt <= 340 else None

        gv = _to_int(out.get("gre_verbal"))
        out["gre_verbal"] = gv if gv is not None and 130 <= gv <= 170 else None

        gaw = _to_float(out.get("gre_aw"))
        out["gre_aw"] = gaw if gaw is not None and 0.0 <= gaw <= 6.0 else None

        # Accept/Reject dates
        def _badge_date(s, default_year=None):
            s = _norm_str(s)
            if not s:
                return None

            # Trim any UI tails that may have leaked in
            s = re.split(r'(?:Total comments|Open options|See More|Report)\b', s, 1)[0].strip()

            # Try the full formats already supported
            for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
                try:
                    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                except Exception:
                    pass

            # Accept short dates w/o year like "28 Aug" or "Aug 28"
            m = re.search(r'^\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,})\s*$', s, re.I)
            flipped = False
            if not m:
                m = re.search(r'^\s*([A-Za-z]{3,})\s+(\d{1,2})(?:st|nd|rd|th)?\s*$', s, re.I)
                flipped = True

            if m and default_year:
                if not flipped:
                    day, mon = m.group(1), m.group(2)
                else:
                    mon, day = m.group(1), m.group(2)
                for fmt in ("%d %b %Y", "%d %B %Y"):
                    try:
                        return datetime.strptime(f"{day} {mon} {default_year}", fmt).strftime("%Y-%m-%d")
                    except Exception:
                        pass

            return None

        default_year = None
        try:
            if isinstance(out.get("date_added"), str) and len(out["date_added"]) >= 4:
                default_year = int(out["date_added"][:4])
        except Exception:
            default_year = None

        # Short dates to full dates
        out["accept_date"] = _badge_date(out.get("accept_date"), default_year)
        out["reject_date"] = _badge_date(out.get("reject_date"), default_year)

        return out

    def _dedupe_by_url(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        drop duplicate URLs
        """
        if not self.dedupe_by_url:
            return list(rows)

        seen: set[str] = set()
        out: List[Dict[str, Any]] = []

        for r in rows:
            u = r.get("url")
            if not u:
                out.append(r)
                continue

            key = u.strip()  # minimal normalization
            if key in seen:
                continue

            seen.add(key)
            out.append(r)

        return out

    # ---------- File handling ----------

    @staticmethod
    def _load_json(path: str | Path) -> List[Dict[str, Any]]:
        """Load a JSON array 
         return [] if file missing or not a list.
         """
        p = Path(path)
        if not p.exists():
            return []
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    
    @staticmethod
    def _save_json(rows: List[Dict[str, Any]], path: str | Path) -> None:
        """Write rows to path as pretty JSON via temp file + replace."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)

        tmp = out.with_suffix(out.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())  # ensure bytes hit disk

        os.replace(tmp, out)


# -------- LLM client ----------------------------------------------------

class LLMClient:
    """
    CLI for the local llm_hosting service.
    """

    def __init__(self, app_dir: str = "llm_hosting", timeout_s: float = 120.0) -> None:
        self.app_dir = str(app_dir)
        self.timeout_s = float(timeout_s)

    def canonize_batch(self, program_texts: List[str]) -> List[Dict[str, Optional[str]]]:
        payload = {"rows": [{"program": t} for t in program_texts]}
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = Path(tmpdir) / "in.json"
            out_path = Path(tmpdir) / "out.jsonl"
            in_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            cmd = [sys.executable, "app.py", "--file", str(in_path), "--out", str(out_path)]
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            try:
                proc = subprocess.run(
                    cmd, cwd=self.app_dir, capture_output=True, text=True,
                    timeout=self.timeout_s, check=False, env=env
                )
            except Exception:
                return [{"program_canon": None, "university_canon": None} for _ in program_texts]

            if proc.stderr:
                print("[LLMClient] child stderr (first 12 lines):\n" + "\n".join(proc.stderr.splitlines()[:12]))

            if not out_path.exists():
                print(f"[LLMClient] missing output: {out_path}")
                return [{"program_canon": None, "university_canon": None} for _ in program_texts]

            def _row_to_pair(d):
                prog = d.get("llm-generated-program") or d.get("program_canon") or d.get("standardized_program")
                univ = d.get("llm-generated-university") or d.get("university_canon") or d.get("standardized_university")
                return {"program_canon": prog, "university_canon": univ}

            results = []
            ok = fail = 0
            with out_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    s = line.strip()
                    if not s: continue
                    try:
                        m = re.search(r"\{.*\}", s)  # tolerate any chatter
                        if m: s = m.group(0)
                        d = json.loads(s)
                        results.append(_row_to_pair(d)); ok += 1
                    except Exception:
                        fail += 1

            print(f"[LLMClient] parsed JSONL ok={ok} fail={fail}")

            n = len(program_texts)
            if len(results) < n:
                results += [{"program_canon": None, "university_canon": None}] * (n - len(results))
            return results[:n]


# -------- Wrapper functions ----------------------------------------

def load_data(path: str | Path) -> List[Dict[str, Any]]:
    """
    Load JSON array from disk (delegates to Cleaner._load_json).
    """
    return Cleaner._load_json(path)

def save_data(rows: List[Dict[str, Any]], path: str | Path) -> None:
    """
    Save JSON to disk .
    """
    try:
        Cleaner._save_json(rows, path)
    except Exception:
        print("[ERROR][Clean.py:save_data] fail to save data!")

def clean_data(
    in_path: str | Path,
    out_path: str | Path,
    *,
    gpa_max: float = 5.0,
    year_min: int = 1950,
    year_max: int = 2035,
    dedupe_by_url: bool = True,
    validate_with_dataclass: bool = False,
) -> List[Dict[str, Any]]:
    cleaner = Cleaner(
        gpa_max=gpa_max,
        year_min=year_min,
        year_max=year_max,
        dedupe_by_url=dedupe_by_url,
        validate_with_dataclass=validate_with_dataclass,
    )
    return cleaner.clean_file(in_path, out_path)


def extend_with_llm(
    in_path: str | Path,
    out_path: str | Path,
    *,
    llm_app_dir: str = "llm_hosting",
    timeout_s: float = 90000,   #increase timeout for large scrapping batches
    validate_with_dataclass: bool = False,
) -> List[Dict[str, Any]]:
    print(f"[Clean] extend_with_llm: loading from {in_path}")

    try:
        rows = Cleaner._load_json(in_path)
        print(f"[Clean] extend_with_llm: loaded {len(rows)} rows")
    except Exception as e:
        print("[ERROR][Clean.py:extend_with_llm] Cleaner._load_json fail:", repr(e))
        return []

    client = LLMClient(app_dir=llm_app_dir, timeout_s=timeout_s)
    cleaner = Cleaner(validate_with_dataclass=validate_with_dataclass)

    if validate_with_dataclass:
        try:
            cleaner.enable_dataclass_validation(ApplicantEntry, ApplicantEntryExtended)
        except Exception as e:
            print("[WARNING][Clean.py:extend_with_llm] Dataclass not available:", repr(e))

    print("[Clean] extend_with_llm: calling Cleaner.extend_with_llm ...")
    extended = cleaner.extend_with_llm(rows, client)
    print(f"[Clean] extend_with_llm: got {len(extended)} extended rows")

    try:
        Cleaner._save_json(extended, out_path)
        print(f"[Clean] extend_with_llm: saved extended rows to {out_path}")
    except Exception as e:
        print("[ERROR][Clean.py:extend_with_llm] _save_json fail:", repr(e))

    return extended