""" Unit and integration tests for src.scripts.load_db """
from __future__ import annotations

import builtins
from pathlib import Path
import pytest
# Mark module as integration suite
pytestmark = pytest.mark.integration


def test_scripts_load_db_main_happy_path(  # pylint: disable=too-many-locals
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Happy path: CLI returns files/rows; script copies and prints summary."""
    # Import target or skip if module not present
    load_db = pytest.importorskip(
        "src.scripts.load_db", reason="load_db script module not present"
    )

    # Source files to be copied by the script
    p_raw = tmp_path / "raw.jsonl"
    p_cleaned = tmp_path / "cleaned.jsonl"
    p_extended = tmp_path / "extended.jsonl"
    p_raw.write_text("raw\n", encoding="utf-8")
    p_cleaned.write_text("cleaned\n", encoding="utf-8")
    p_extended.write_text("extended\n", encoding="utf-8")

    class _RunObj:  # pylint: disable=too-few-public-methods
        """Minimal run object matching attributes expected by main()."""
        def __init__(self) -> None:
            self.raw_path = p_raw
            self.cleaned_path = p_cleaned
            self.extended_path = p_extended
            self.final_records = [{"url": "https://x/1"}, {"url": "https://x/2"}]
            self.raw_count = 5
            self.cleaned_count = 4
            self.final_count = len(self.final_records)

    run_obj = _RunObj()
    called = {"cli": 0, "load": 0}

    def _fake_run_module2_cli(*_args, **_kwargs):
        called["cli"] += 1
        return run_obj

    def _fake_load_applicants(rows, *_args, **_kwargs):
        called["load"] += 1
        assert rows == run_obj.final_records
        n = len(rows)
        return {"attempted": n, "inserted": n, "skipped": 0}

    # Patch collaborators used by the script
    monkeypatch.setattr(load_db, "run_module2_cli", _fake_run_module2_cli, raising=False)
    monkeypatch.setattr(load_db, "load_applicants", _fake_load_applicants, raising=False)

    # Redirect copy target to a temp dir
    target_dir = tmp_path / "m3_data"
    target_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(load_db, "M3_DATA", target_dir, raising=False)
    monkeypatch.setattr(load_db, "COPY_TO_MODULE3", True, raising=False)

    # Capture printed summary
    printed: dict[str, object] = {}
    def _fake_print(obj, *_args, **_kwargs):
        printed["obj"] = obj
    monkeypatch.setattr(builtins, "print", _fake_print)

    # Run entrypoint
    load_db.main()

    # Verify collaborators called
    assert called["cli"] == 1
    assert called["load"] == 1

    # Files copied to target dir
    assert (target_dir / p_raw.name).exists()
    assert (target_dir / p_cleaned.name).exists()
    assert (target_dir / p_extended.name).exists()

    # Printed summary has expected keys
    assert isinstance(printed.get("obj"), dict)
    out = printed["obj"]  # type: ignore[assignment]
    for key in (
        "scraped", "cleaned", "to_load",
        "raw_path", "cleaned_path", "extended_path",
        "attempted", "inserted", "skipped",
    ):
        assert key in out, f"missing key in printed summary: {key}"

    # Sanity checks on values
    assert out["scraped"] == run_obj.raw_count
    assert out["cleaned"] == run_obj.cleaned_count
    assert out["to_load"] == run_obj.final_count
    assert out["raw_path"] == str(p_raw)
    assert out["cleaned_path"] == str(p_cleaned)
    assert out["extended_path"] == str(p_extended)
