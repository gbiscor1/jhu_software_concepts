# module_3/application/scrapper_cli_caller.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
import json, subprocess, sys, tempfile

REPO_ROOT   = Path(__file__).resolve().parents[2]
MODULE2_DIR = REPO_ROOT / "module_2"
M2_DATA     = MODULE2_DIR / "data"
HOST_DIR    = MODULE2_DIR / "llm_hosting"

RAW_PATH      = M2_DATA / "applicant_data.json"
CLEANED_PATH  = M2_DATA / "applicant_data.cleaned.json"
EXTENDED_PATH = M2_DATA / "llm_extend_applicant_data.json"

@dataclass
class Module2RunResult:
    pages: int
    delay: float
    use_llm: bool
    raw_path: Path
    cleaned_path: Path
    extended_path: Path
    raw_count: int
    cleaned_count: int
    final_count: int
    final_records: list[dict]
    source: str

def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

def _run(cmd: list[str], cwd: Path):
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cwd.name}: failed ({proc.returncode}).\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc

def run_module2_cli(*, pages: int = 12, delay: float = 0.8, use_llm: bool = True, force: bool = True) -> Module2RunResult:
    if not MODULE2_DIR.exists():
        raise RuntimeError(f"Module 2 folder not found at {MODULE2_DIR}")

    # force fresh scrape by removing previous artifacts
    if force:
        for p in (RAW_PATH, CLEANED_PATH, EXTENDED_PATH):
            try: p.unlink()
            except FileNotFoundError: pass

    py = sys.executable

    # Run module_2/app.py with LLM OFF to avoid starting the server
    _run([py, "app.py", str(pages), f"{delay:.2f}", "false"], cwd=MODULE2_DIR)

    raw     = _load_json(RAW_PATH)
    cleaned = _load_json(CLEANED_PATH)

    # If use_llm=True, call the host in CLI mode on the cleaned rows
    final = cleaned
    if use_llm:
        HOST_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "in.json"
            out = td / "out.jsonl"

            inp.write_text(json.dumps({"rows": cleaned}, ensure_ascii=False), encoding="utf-8")

            # Run: python llm_hosting/app.py --file in.json --out out.jsonl
            _run([py, "app.py", "--file", str(inp), "--out", str(out)], cwd=HOST_DIR)

            # Parse JSONL - list of dicts
            ext = []
            with out.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        ext.append(json.loads(line))

        # Merge canonical fields into the cleaned rows
        merged: list[dict] = []
        for i, base in enumerate(cleaned):
            row = dict(base)
            if i < len(ext):
                e = ext[i]
                # accept either your canonical keys or the hyphenated ones we saw in the smoke test
                row["program_canon"]   = e.get("program_canon")   or e.get("llm-generated-program")
                row["university_canon"]= e.get("university_canon") or e.get("llm-generated-university")
            merged.append(row)

        final = merged

        EXTENDED_PATH.write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")

    return Module2RunResult(
        pages=pages, delay=delay, use_llm=use_llm,
        raw_path=RAW_PATH, cleaned_path=CLEANED_PATH, extended_path=EXTENDED_PATH,
        raw_count=len(raw), cleaned_count=len(cleaned), final_count=len(final),
        final_records=final, source="live+cli-llm" if use_llm else "live",
    )
