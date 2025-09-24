"""Load data into the database via the scraper pipeline."""

from __future__ import annotations
from pathlib import Path
import shutil
from ..application.scrapper_cli_caller import run_module2_cli
from ..data.loader import load_applicants

# Settings
PAGES = 12
DELAY = 0.8
USE_LLM = True

COPY_TO_MODULE3 = True
M3_DATA = Path(__file__).resolve().parents[1] / "data"
M3_DATA.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Run scraper, optionally copy artifacts, and load records.

    Uses module-level settings: ``PAGES``, ``DELAY``, ``USE_LLM``, and ``COPY_TO_MODULE3``.

    :returns: None.
    """
    run = run_module2_cli(pages=PAGES, delay=DELAY, use_llm=USE_LLM)

    if COPY_TO_MODULE3:
        for src in [run.raw_path, run.cleaned_path, run.extended_path]:
            if src and src.exists():
                shutil.copy2(src, M3_DATA / src.name)

    stats = load_applicants(run.final_records)
    print({
        "scraped": run.raw_count,
        "cleaned": run.cleaned_count,
        "to_load": run.final_count,
        **stats,
        "raw_path": str(run.raw_path),
        "cleaned_path": str(run.cleaned_path),
        "extended_path": str(run.extended_path),
    })


if __name__ == "__main__":
    main()
