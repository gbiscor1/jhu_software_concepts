# module_3/tests/test_loader_dedupe.py
from __future__ import annotations
import uuid
from typing import Dict, Any

from data.loader import load_applicants
from data.psych_connect import get_conn


def _count_by_url(url: str) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants WHERE url = %s;", (url,))
        n = cur.fetchone()
        return int(n[0]) if n else 0


def _cleanup_urls(urls: list[str]) -> None:
    if not urls:
        return
    with get_conn() as conn, conn.cursor() as cur:
        for u in urls:
            cur.execute("DELETE FROM applicants WHERE url = %s;", (u,))


def _row(url: str, **overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal valid row for the loader. Adjust keys here if your JSON shape differs.
    (Loader maps these onto the DB column names internally.)
    """
    base = {
        "program": "Computer Science MS",
        "comments": "pytest insert",
        "date_added": "2025-09-01",   # ISO date string is fine
        "url": url,
        "status": "Accepted",
        "term": "Fall 2025",
        "citizenship": "American",    # maps -> us_or_international
        "gpa": 3.8,
        "gre_total": 325,             # maps -> gre
        "gre_verbal": 160,            # maps -> gre_v
        "gre_aw": 4.5,
        "degree": "MS",
        "program_canon": "Computer Science",     # maps -> llm_generated_program
        "university_canon": "Test University",   # maps -> llm_generated_university
    }
    base.update(overrides)
    return base


def test_loader_skips_exact_duplicate_url():
    url = f"https://example.com/pytest-dup-{uuid.uuid4()}"
    created = [url]

    try:
        pre = _count_by_url(url)

        # Send the same URL twice
        stats = load_applicants([_row(url), _row(url)])
        post = _count_by_url(url)

        # We attempted 2 rows; loader should insert once and skip once
        assert stats["attempted"] == 2
        assert stats["inserted"] == 1
        assert stats["skipped"] == 1

        # Table gained exactly one row for that URL
        assert post == pre + 1
    finally:
        _cleanup_urls(created)


def test_loader_inserts_new_and_skips_existing():
    url_existing = f"https://example.com/pytest-existing-{uuid.uuid4()}"
    url_new = f"https://example.com/pytest-new-{uuid.uuid4()}"
    created = [url_existing, url_new]

    try:
        # Seed one row
        first = load_applicants([_row(url_existing)])
        assert first["attempted"] == 1
        assert first["inserted"] == 1
        assert first["skipped"] == 0

        # Now send the existing (dup) + a truly new one
        stats = load_applicants([_row(url_existing), _row(url_new)])

        assert stats["attempted"] == 2
        assert stats["inserted"] == 1      # only the new URL should insert
        assert stats["skipped"] == 1

        # Sanity: both URLs present at least once
        assert _count_by_url(url_existing) >= 1
        assert _count_by_url(url_new) >= 1
    finally:
        _cleanup_urls(created)
