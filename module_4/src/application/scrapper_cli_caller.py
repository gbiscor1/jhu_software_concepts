"""Adapters to obtain applicant records via bulk JSON or an external CLI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
import os
import json
import tempfile
import subprocess


# Data locations (prod points to repo file; tests can monkeypatch)
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_BULK_JSON = DATA_DIR / "database_bulk.json"


def _jsonl_to_list(p: Optional[Path]) -> List[Dict[str, Any]]:
    """Parse a JSONL file into a list of dicts.

    :param p: Path to JSONL file.
    :returns: List of JSON objects (dicts) parsed from lines; empty on errors.
    """
    if not p or not p.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            elif isinstance(obj, list):
                rows.extend([x for x in obj if isinstance(x, dict)])
    except Exception:
        return []
    return rows


def _read_bulk_json(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read a pre-scraped dataset from disk.

    Accepts either a JSON array or an object with a ``"records"`` array.

    :param path: Optional override path; defaults to :data:`DEFAULT_BULK_JSON`.
    :returns: List of dicts; empty on missing file or parse error.
    """
    p = Path(path) if path else DEFAULT_BULK_JSON
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict) and "records" in data:
        data = data.get("records")
    return [x for x in data] if isinstance(data, list) else []


def _make_result(
    *,
    source: str,
    rows: List[Dict[str, Any]],
    raw_path: Optional[Path] = None,
    cleaned_path: Optional[Path] = None,
    extended_path: Optional[Path] = None,
) -> SimpleNamespace:
    """Create a result namespace with standardized fields.

    :param source: Source identifier (e.g., ``"bulk-json"`` or ``"cli"``).
    :param rows: Final record list.
    :param raw_path: Optional path to raw artifact.
    :param cleaned_path: Optional path to cleaned artifact.
    :param extended_path: Optional path to extended artifact.
    :returns: :class:`types.SimpleNamespace` with counts and paths.
    """
    n = len(rows)
    return SimpleNamespace(
        source=source,
        raw_path=raw_path,
        cleaned_path=cleaned_path,
        extended_path=extended_path,
        final_records=rows,
        raw_count=n,
        cleaned_count=n,
        final_count=n,
    )


def run_module2_cli(*, pages: int = 12, delay: float = 0.8, use_llm: bool = True, force: bool = False):
    """Return records via bundled bulk JSON, with CLI fallback.

    Fast path reads :data:`DEFAULT_BULK_JSON` (or ``SCRAPER_BULK_JSON`` env override)
    for deterministic tests. Fallback attempts an external CLI call; on failure,
    returns an empty dataset without raising.

    :param pages: Number of pages to scrape (CLI hint).
    :param delay: Delay between HTTP requests (CLI hint).
    :param use_llm: Whether to run LLM extension (CLI hint).
    :param force: Force re-scrape if supported by the CLI.
    :returns: Result namespace from :func:`_make_result`.
    """
    # Allow tests to redirect the bulk file via env var
    env_override = os.getenv("SCRAPER_BULK_JSON")
    rows = _read_bulk_json(Path(env_override)) if env_override else _read_bulk_json()
    if rows:
        return _make_result(source="bulk-json", rows=rows)

    # Fallback path: attempt a CLI call (safe/no hard dependency)
    out_dir = Path(tempfile.mkdtemp(prefix="mod4_scrape_"))
    out_jsonl = out_dir / "out.jsonl"

    # Illustrative command; tests typically monkeypatch subprocess
    cmd = ["python", "-m", "module_3.scraper", "--pages", str(pages), "--delay", str(delay)]
    if use_llm:
        cmd.append("--use-llm")
    if force:
        cmd.append("--force")

    try:
        subprocess.run(cmd, check=False, capture_output=True, text=True)
    except Exception:
        # CLI missing or not importable
        return _make_result(source="cli-missing", rows=[])

    # Parse output if present; else empty
    rows = _jsonl_to_list(out_jsonl)
    return _make_result(source="cli", rows=rows)


def call_scraper(*_args, **kwargs):
    """Alias for :func:`run_module2_cli` with positional args ignored."""
    return run_module2_cli(**kwargs)


def scrape_cli(*_args, **kwargs):
    """Alias for :func:`run_module2_cli` with positional args ignored."""
    return run_module2_cli(**kwargs)


__all__ = [
    "run_module2_cli",
    "call_scraper",
    "scrape_cli",
    "_read_bulk_json",
    "_jsonl_to_list",
    "DEFAULT_BULK_JSON",
    "DATA_DIR",
]


