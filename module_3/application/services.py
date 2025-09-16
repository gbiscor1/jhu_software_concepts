# module_3/application/services.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from application.scrapper_cli_caller import run_module2_cli
from data.loader import load_applicants
from data.query_runner import run_and_dump_all

ROOT: Path = Path(__file__).resolve().parents[1]          
QUERIES_DIR: Path = ROOT / "sql" / "queries"
APP_DATA_DIR: Path = ROOT / "app" / "data"


def pull_data(*, pages: int = 12, delay: float = 0.8, use_llm: bool = True) -> Dict[str, Any]:
    """
    Run Module 2 (scrape/clean/LLM) and upsert rows into Postgres.
    """
    run = run_module2_cli(pages=pages, delay=delay, use_llm=use_llm, force=True)
    stats = load_applicants(run.final_records)
    return {
        "source": run.source,
        "scraped": run.raw_count,
        "cleaned": run.cleaned_count,
        "to_load": run.final_count,
        **stats,
    }


def analysis_to_files() -> Dict[str, Any]:
    """
    Execute all q*.sql under sql/queries and write app/data/q_*.json
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    written_paths = run_and_dump_all(QUERIES_DIR, APP_DATA_DIR)
    return {"written": len(written_paths), "files": [p.name for p in written_paths]}
