# scrape.py
import time
import json
import os
import re
from typing import List, Dict
from pathlib import Path
from bs4 import BeautifulSoup
from urllib3 import PoolManager
from urllib3.util.retry import Retry
from urllib3.util import Timeout
from urllib.parse import urljoin


class Scraper:
    def __init__(self, base_url: str, delay: float = 1.0):
        self.base_url = base_url
        self.delay = delay
        self.http = self._build_http_client()

    # ---------- HTTP client ----------

    def _build_http_client(self):
        """PoolManager with retries, timeouts, and a polite UA."""
        user_agent = "jhu-module2-scraper/1.0 (+https://github.com/gbiscor1/jhu_software_concepts)"
        retries = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
        )
        timeout = Timeout(connect=5.0, read=15.0)
        http = PoolManager(
            retries=retries,
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )
        return http

    # ---------- URL building ----------

    def _build_page_url(self, page_num: int) -> str:
        """
        If ?page= is present, replace it; otherwise append it.
        """
        base = self.base_url
        updated = re.sub(r'([?&]page=)\d+', r'\g<1>' + str(page_num), base)
        if updated != base:
            return updated
        sep = '&' if '?' in base else '?'
        return f"{base}{sep}page={page_num}"

    # ---------- Fetching ----------

    def _fetch_page(self, url: str) -> str:
        """GET a page; return unicode HTML or '' on soft-fail."""
        try:
            resp = self.http.request("GET", url)
            if resp.status >= 400:
                print(f"[WARN][Scraper:_fetch_page] Failed {url} (status {resp.status})")
                return ""
            return resp.data.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[ERROR][Scraper:_fetch_page] Exception fetching {url}: {e}")
            return ""

    # ---------- Saving ----------

    def _save_json(self, out_path: str, rows: List[Dict]) -> None:
        """
        Atomic write: write to tmp file then os.replace into place.
        """
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        tmp = out.with_suffix(out.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out)

    # ---------- Parsing ----------

    def _parse_page(self, html: str, page_url: str) -> List[Dict]:
        """
        Parse one GradCafe listings page into a list of dict rows.
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        rows_out: List[Dict] = []

        # Degree detection
        DEGREE_RE = re.compile(r"\b(Masters|Master'?s|MS|PhD|PHD|MFA|MBA|JD|EdD|PsyD|Other)\b", re.I)
        DEG_CANON = {
            "masters": "Masters", "master's": "Masters", "ms": "Masters",
            "phd": "PhD", "mfa": "MFA", "mba": "MBA", "jd": "JD",
            "edd": "EdD", "psyd": "PsyD", "other": "Other",
        }

        # Status
        STATUS_RE = re.compile(
            r"\b(Accepted|Rejected|Interview|Wait\s*listed|Waitlisted)\b"
            r"(?:\s+on\s+(.*?))?"                                   
            r"(?=\s*(?:Total comments|Open options|See More|Report|$))",
            re.I,
        )

        TERM_YEAR_RE = re.compile(r"\b(Fall|Spring|Summer)\s+(\d{4})\b", re.I)

        def _to_int(s):
            try:
                return int(s)
            except Exception:
                return None

        for tr in table.select("tbody > tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 4:
                continue

            # --- University (col 0)
            university = tds[0].get_text(" ", strip=True)

            # --- Program
            pd_text = tds[1].get_text(" ", strip=True).replace("·", " ").strip()
            degree = None
            mdeg = DEGREE_RE.search(pd_text)
            if mdeg:
                key = mdeg.group(1).lower().replace("’", "'").replace(".", "")
                degree = DEG_CANON.get(key, DEG_CANON.get(key.replace("'", ""), None))
                program = pd_text[:mdeg.start()].strip(" .·-")
            else:
                program = pd_text

            # --- Publish date (col 2)
            date_added = tds[2].get_text(" ", strip=True)

            # --- Collect row 
            embedded_texts = []
            for embedded in tr.find_all(True, class_=re.compile(r"(tw-inline-flex|badge|rounded|tw-ring)")):
                t = embedded.get_text(" ", strip=True)
                if t:
                    embedded_texts.append(t)

            # Whole row text
            embedded_texts.append(tr.get_text(" ", strip=True))

            # Detail row if present
            next_tr = tr.find_next_sibling("tr")
            if next_tr and next_tr.find("td", colspan=True):
                embedded_texts.append(next_tr.get_text(" ", strip=True))

            # Flatten for regexes
            full_text = " ".join(embedded_texts)
            low = full_text.lower()

            # --- Decision
            # search in full_text
            status = None
            accept_date = None
            reject_date = None
            m = STATUS_RE.search(full_text)
            if m:
                tok = m.group(1).lower().replace(" ", "")
                when = (m.group(2) or "").strip() or None
                if "wait" in tok:
                    status = "Waitlisted"
                elif tok == "accepted":
                    status = "Accepted"
                    accept_date = when
                elif tok == "rejected":
                    status = "Rejected"
                    reject_date = when
                elif tok == "interview":
                    status = "Interview"

            # --- Embedded values
            start_term = start_year = citizenship = gpa = None
            gre_total = gre_verbal = gre_aw = None

            # Term/year
            mt = TERM_YEAR_RE.search(full_text)
            if mt:
                start_term = mt.group(1).title()
                start_year = _to_int(mt.group(2))

            # Citizenship (simple contains)
            if "international" in low:
                citizenship = "International"
            elif "american" in low:
                citizenship = "American"

            # GPA (first number after 'GPA')
            mgpa = re.search(r"gpa[^0-9]*([0-9]+(?:[.,][0-9]+)?)", full_text, re.I)
            if mgpa:
                try:
                    gpa = float(mgpa.group(1).replace(",", "."))
                except ValueError:
                    pass

            # GRE Verbal (V)
            mv = re.search(r"\bGRE\s*V[:\s]+(\d{2,3})\b", full_text, re.I)
            if mv:
                gre_verbal = _to_int(mv.group(1))

            # GRE AW (first number after 'GRE AW' or 'GRE AWA')
            maw = re.search(r"gre\s*aw[a]?\s*([0-9]+(?:\.[0-9]+)?)", full_text, re.I)
            if maw:
                try:
                    gre_aw = float(maw.group(1))
                except ValueError:
                    pass

            # GRE Total (plain 'GRE' not followed by V/AW)
            mtot = re.search(r"\bGRE(?!\s*(?:V|AW))[:\s]+(\d{2,3})\b", full_text, re.I)
            if mtot:
                gre_total = _to_int(mtot.group(1))

            # --- Per-entry URL (prefer "See More"; fallback to any /survey|/result)
            link = tr.find("a", string=re.compile(r"^\s*See More\s*$", re.I))
            if not link:
                link = tr.find("a", href=re.compile(r"/(survey|result)/"))
            url = urljoin(self.base_url, link["href"]) if link and link.has_attr("href") else page_url

            # --- Build record
            rows_out.append({
                "program": program,
                "university": university,
                "date_added": date_added,
                "url": url,
                "status": status,
                "comments": None,
                "accept_date": accept_date,
                "reject_date": reject_date,
                "start_term": start_term,
                "start_year": start_year,
                "citizenship": citizenship,
                "gre_total": gre_total,
                "gre_verbal": gre_verbal,
                "gre_aw": gre_aw,
                "degree": degree,
                "gpa": gpa,
            })

        return rows_out


    # ---------- Orchestration ----------

    def scrape(self, start_page: int = 1, max_pages: int = 500, out_path: str = "data/applicant_data.json"):
        """
        Orchestrate scrapping: build URL -> fetch -> parse -> aggregate -> save.
        Stops on empty/failed page or when max_pages reached.
        """
        results: List[Dict] = []
        row_count = 0

        # Main loop through pages
        for page_num in range(start_page, start_page + max_pages):
            page_url = self._build_page_url(page_num)
            print(f"[INFO][Scraper:scrape] Fetching page {page_num}: {page_url}")

            html = self._fetch_page(page_url)

            # If html is empty exit
            if not html:
                print(f"[WARN][Scraper:scrape] Empty HTML for page {page_num}; stopping.")
                break

            rows = self._parse_page(html, page_url)
            # If no rows detected exit
            if not rows:
                print(f"[INFO][Scraper:scrape] No rows found on page {page_num}; stopping.")
                break

            results.extend(rows)
            row_count += len(rows)
            print(f"[INFO][Scraper:scrape] Page {page_num}: {len(rows)} rows (total {row_count})")

            # Avoid hammering site
            time.sleep(self.delay)

        # Try saving file
        try:
            self._save_json(out_path, results)
            print(f"[INFO][Scraper:scrape] Saved {len(results)} records to {out_path}")
        except FileNotFoundError:
            print(f"[WARN][Scraper:scrape] Could not save to {out_path}. Returning results only.")

        return results


def scrape_data(base_url: str, start_page: int = 1, max_pages: int = 500, delay: float = 1.0, out_path: str = "data/applicant_data.json"):
    """Wrapper for scrapping"""
    scraper = Scraper(base_url, delay=delay)
    return scraper.scrape(start_page=start_page, max_pages=max_pages, out_path=out_path)
