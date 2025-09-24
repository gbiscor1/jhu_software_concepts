"""Application orchestration services."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .scrapper_cli_caller import run_module2_cli

from ..data.loader import load_applicants
from ..data.query_runner import run_and_dump_all


ROOT: Path = Path(__file__).resolve().parents[1]
QUERIES_DIR: Path = ROOT / "sql" / "queries"
APP_DATA_DIR: Path = ROOT / "app" / "data"


def pull_data(*, pages: int = 12, delay: float = 0.8, use_llm: bool = True) -> Dict[str, Any]:
    """Run scrape/clean/extend and load rows into Postgres.

    :param pages: Number of pages to scrape.
    :param delay: Delay between HTTP requests in seconds.
    :param use_llm: Whether to run LLM extension on cleaned data.
    :returns: Mapping with source info, record counts, and loader stats.
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
    """Execute saved queries and write analysis JSON files.

    Runs all ``q*.sql`` in ``sql/queries`` and writes ``app/data/q*.json``.

    :returns: Mapping with ``written`` count and list of filenames in ``files``.
    """
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    written_paths = run_and_dump_all(QUERIES_DIR, APP_DATA_DIR)
    return {"written": len(written_paths), "files": [p.name for p in written_paths]}
