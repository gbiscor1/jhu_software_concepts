"""Adapters to obtain applicant records via bulk JSON or an external CLI."""

from __future__ import annotations
import os
import json
import tempfile
import subprocess

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional


# Data locations
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_BULK_JSON = DATA_DIR / "database_bulk.json"


def _jsonl_to_list(p: Optional[Path]) -> List[Dict[str, Any]]:
    """Parse a JSONL file into a list of dicts.

    :param p: Path to JSONL file.
    :returns: List of JSON objects (dicts) parsed from lines; empty on errors.
    """
    if not p or not p.is_file():
        return []

    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # File missing/unreadable or bad encoding
        return []

    rows: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            # Skip malformed JSON line
            continue

        if isinstance(obj, dict):
            rows.append(obj)
        elif isinstance(obj, list):
            rows.extend(x for x in obj if isinstance(x, dict))

    return rows

def _read_bulk_json(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read a pre-scraped dataset from disk.

    Accepts either a JSON array or an object with a ``"records"`` array.

    :param path: Optional override path; defaults to :data:`DEFAULT_BULK_JSON`.
    :returns: List of dicts; empty on missing file or parse error.
    """
    p = path if isinstance(path, Path) else DEFAULT_BULK_JSON
    if not p or not p.is_file():
        return []

    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict) and "records" in data:
        data = data["records"]

    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


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
    env_override = os.getenv("SCRAPER_BULK_JSON")
    rows = _read_bulk_json(Path(env_override)) if env_override else _read_bulk_json()
    if rows:
        return _make_result(source="bulk-json", rows=rows)

    out_dir = Path(tempfile.mkdtemp(prefix="mod4_scrape_"))
    out_jsonl = out_dir / "out.jsonl"

    cmd = ["python", "-m", "module_3.scraper", "--pages", str(pages), "--delay", str(delay)]
    if use_llm:
        cmd.append("--use-llm")
    if force:
        cmd.append("--force")

    try:
        subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        # CLI missing/unlaunchable/invalid or hung
        return _make_result(source="cli-missing", rows=[])

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
