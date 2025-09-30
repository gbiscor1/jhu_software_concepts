"""Integration tests for scraper CLI adapter."""

from __future__ import annotations
import json
import types
from typing import Any
import pytest

# Mark test module as part of the integration suite
pytestmark = pytest.mark.integration


def _call_entrypoint(scc: types.ModuleType) -> Any:
    # Try common entrypoints; tolerate positional/keyword variants
    for name in ("run_module2_cli", "call_scraper", "scrape_cli"):
        fn = getattr(scc, name, None)
        if callable(fn):
            try:
                return fn()  # zero-arg variant
            except TypeError:
                # Some shims accept positional args; pass inert placeholders
                return fn("echo", ["--version"])
    raise pytest.skip("No known CLI entrypoint found")


def test_scrapper_cli_bulk_json_env_jsonl(monkeypatch):
    """Validate the bulk-JSON fast path by stubbing the internal reader.
    Monkeypatches `_read_bulk_json` to return two rows, invokes `run_module2_cli`,
    and asserts a two-item list is produced with a source label indicating bulk/json.
    """
    # Skip cleanly if module isn’t available (no broad exceptions)
    scc = pytest.importorskip(
        "src.application.scrapper_cli_caller",
        reason="scrapper_cli_caller module not present"
    )

    rows = [{"url": "https://x/1"}, {"url": "https://x/2"}]
    monkeypatch.setattr(scc, "_read_bulk_json", lambda *a, **k: rows, raising=True)

    run = scc.run_module2_cli(pages=99, delay=0.01, use_llm=False, force=True)
    assert hasattr(run, "final_records")
    assert isinstance(run.final_records, list)
    assert len(run.final_records) == 2
    assert getattr(run, "source", "bulk").startswith(("bulk", "json"))

def test_read_bulk_json_missing_file_returns_empty(tmp_path):
    """If the file doesn't exist, return an empty list."""
    scc = pytest.importorskip(
        "src.application.scrapper_cli_caller",
        reason="scrapper_cli_caller module not present",
    )

    missing = tmp_path / "nope.json"
    # pylint: disable=protected-access
    assert scc._read_bulk_json(missing) == []


def test_read_bulk_json_bad_json_returns_empty(tmp_path):
    """Malformed JSON should be caught and return empty."""
    scc = pytest.importorskip(
        "src.application.scrapper_cli_caller",
        reason="scrapper_cli_caller module not present",
    )

    p = tmp_path / "bad.json"
    p.write_text("{not: valid", encoding="utf-8")
    # pylint: disable=protected-access
    assert scc._read_bulk_json(p) == []

def test_read_bulk_json_parses_array(tmp_path):
    """JSON array should be returned as-is (list of dicts)."""
    scc = pytest.importorskip(
        "src.application.scrapper_cli_caller",
        reason="scrapper_cli_caller module not present",
    )

    p = tmp_path / "arr.json"
    rows = [{"url": "https://x/1"}, {"url": "https://x/2"}]
    p.write_text(json.dumps(rows), encoding="utf-8")
    # pylint: disable=protected-access
    out = scc._read_bulk_json(p)
    assert isinstance(out, list)
    assert out == rows


def test_scrapper_cli_happy_path_reads_outfile(monkeypatch, tmp_path):  # pylint: disable=too-many-locals
    """Verify CLI fallback reads the generated JSONL and returns records.

Disables the bulk-JSON fast path, stubs subprocess/tempfile to a fixed
directory with an `out.jsonl`, then asserts the file was opened and a
subprocess call occurred, and that at least one record is returned
(dict or namespace result accepted).
"""
    # Skip cleanly if the module isn't available
    scc = pytest.importorskip(
        "src.application.scrapper_cli_caller",
        reason="scrapper_cli_caller module not present",
    )

    # Force CLI fallback path by disabling bulk-json shortcut
    monkeypatch.setenv("SCRAPER_BULK_JSON", str(tmp_path / "nope.json"))

    # Stub subprocess to capture commands but avoid real execution
    calls: list[tuple[str, ...]] = []

    class _DummyProc:  # pylint: disable=too-few-public-methods
        # Minimal CompletedProcess-like object
        def __init__(self, returncode=0, out=b"ok", err=b""):
            self.returncode = returncode
            self.stdout = out
            self.stderr = err

    def _fake_run(cmd, * _args, ** _kwargs):
        calls.append(tuple(cmd) if isinstance(cmd, (list, tuple)) else (str(cmd),))
        return _DummyProc()

    def _fake_check_output(cmd, * _args, ** _kwargs):
        calls.append(tuple(cmd) if isinstance(cmd, (list, tuple)) else (str(cmd),))
        return b"ok"

    monkeypatch.setattr(
        scc,
        "subprocess",
        types.SimpleNamespace(run=_fake_run, check_output=_fake_check_output),
        raising=True,
    )

    # Pin temporary directory used by the CLI and pre-create expected output
    fixed_dir = tmp_path / "cli_tmp"
    fixed_dir.mkdir(parents=True, exist_ok=True)
    out_path = fixed_dir / "out.jsonl"
    out_path.write_text(json.dumps({"url": "https://example.com/1"}) + "\n", encoding="utf-8")

    class _FakeTD:  # pylint: disable=too-few-public-methods
        # Minimal context manager for tempfile.TemporaryDirectory
        def __enter__(self):
            return str(fixed_dir)
        def __exit__(self, exc_type, exc, tb):
            return False

    # Provide both TemporaryDirectory and mkdtemp since either path may be used
    monkeypatch.setattr(
        scc,
        "tempfile",
        types.SimpleNamespace(TemporaryDirectory=_FakeTD, mkdtemp=lambda prefix="": str(fixed_dir)),
        raising=True,
    )

    # Spy on Path.open to confirm that out.jsonl is read by the code
    touched = {"count": 0}
    real_open = scc.Path.open

    def _spy_open(self, * _args, ** _kwargs):
        if str(self) == str(out_path):
            touched["count"] += 1
        return real_open(self, *_args, **_kwargs)

    monkeypatch.setattr(scc.Path, "open", _spy_open, raising=True)

    # Act
    result = _call_entrypoint(scc)

    # Assert: file was opened at least once and a subprocess call was attempted
    assert touched["count"] >= 1, "expected code to open out.jsonl at least once"
    assert calls, "expected a subprocess call to be attempted"

    # Accept either namespace-like or dict results; keep condition flexible
    items = (
        result.get("final_records") or result.get("rows") or []
        if isinstance(result, dict)
        else getattr(result, "final_records", [])
    )
    assert isinstance(items, list) and len(items) >= 1
