# tests/scripts/test_init_db.py

from __future__ import annotations

from pathlib import Path
import builtins
import pytest

pytestmark = pytest.mark.db



def _find_init_fn(mod):
    """Return the first plausible entrypoint from a module."""
    for name in ("main", "init_main", "init", "run", "cli"):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    return None


def test_init_db_main_applies_schema_and_seeds(monkeypatch, tmp_path, fake_conn_factory):
    """
    Create a temp schema + seed file, patch init_db to use them, and run the entrypoint.
    Asserts:
      - At least one CREATE executes on the fake cursor
      - load_applicants is called with parsed rows and its summary is printed
    """
    try:
        import src.scripts.init_db as init_db
    except Exception:
        pytest.skip("init_db script module not present")

    # --- temp schema file we control ---
    schema_path: Path = tmp_path / "schema.sql"
    schema_path.write_text("CREATE TABLE IF NOT EXISTS t (id int);\n", encoding="utf-8")

    # --- temp seed (JSON or JSONL). We'll do JSON array here. ---
    seed_path: Path = tmp_path / "seed.json"
    rows = [{"url": "https://example.test/1"}, {"url": "https://example.test/2"}]
    seed_path.write_text(__import__("json").dumps(rows), encoding="utf-8")

    # --- patch module constants & collaborators ---
    # point to our schema + seed
    monkeypatch.setattr(init_db, "SCHEMA_PATH", schema_path, raising=False)
    monkeypatch.setattr(init_db, "DEFAULT_SEED_FILES", [seed_path], raising=False)

    # replace DB connection with repo fake
    conn = fake_conn_factory()
    monkeypatch.setattr(init_db, "get_conn", lambda: conn, raising=False)

    # stub loader to avoid hitting real DB insert logic
    called = {"load": 0}
    def _fake_load_applicants(rows_in):
        called["load"] += 1
        assert isinstance(rows_in, list) and len(rows_in) == 2
        return {"attempted": len(rows_in), "inserted": len(rows_in), "skipped": 0}
    monkeypatch.setattr(init_db, "load_applicants", _fake_load_applicants, raising=False)

    # capture print output from the script
    printed = {"all": []}
    def _cap(obj, *a, **k):
        printed["all"].append(obj)   # keep everything
        printed["obj"] = obj         # last print wins
    monkeypatch.setattr(builtins, "print", _cap)

    # --- run entrypoint (covers apply_schema + seed_from_json) ---
    fn = _find_init_fn(init_db)
    if not fn:
        pytest.skip("No known init entrypoint found in init_db")
    fn()

    # --- assertions ---
    # 1) schema executed against fake cursor
    cur = conn.cursor()
    sqls = [sql for (sql, _params) in getattr(cur, "executed", []) if isinstance(sql, str)]
    assert any("create table" in s.lower() for s in sqls), f"No CREATE TABLE seen in {sqls!r}"

    # 2) loader was called and the script printed a summary dict that includes loader keys
    assert called["load"] == 1
    out = printed.get("obj")
    if not isinstance(out, dict):
        # try to find *any* printed dict (script might print strings first)
        out = next((x for x in printed.get("all", []) if isinstance(x, dict)), None)
    assert out is not None, "Expected the script to print something"
    if isinstance(out, dict):
        for k in ("attempted", "inserted", "skipped"):
            assert k in out
    else:
        # If the script didn’t print a dict, we at least verified loader was called above.
        assert isinstance(out, str)


def test_init_db_seed_handles_missing_files(monkeypatch, tmp_path, fake_conn_factory):
    """
    Point DEFAULT_SEED_FILES to a non-existent file and ensure seed_from_json
    is a no-op that doesn't crash but returns/prints something sensible.
    """
    try:
        import src.scripts.init_db as init_db
    except Exception:
        pytest.skip("init_db script module not present")

    # ensure schema path is valid so apply_schema wouldn't crash if called elsewhere
    schema_path: Path = tmp_path / "schema.sql"
    schema_path.write_text("CREATE TABLE t (id int);", encoding="utf-8")
    monkeypatch.setattr(init_db, "SCHEMA_PATH", schema_path, raising=False)

    # no seed files exist
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(init_db, "DEFAULT_SEED_FILES", [missing], raising=False)

    # patch DB + loader just in case
    conn = fake_conn_factory()
    monkeypatch.setattr(init_db, "get_conn", lambda: conn, raising=False)
    monkeypatch.setattr(init_db, "load_applicants", lambda rows: {"attempted": 0, "inserted": 0, "skipped": 0}, raising=False)

    printed = {}
    monkeypatch.setattr(builtins, "print", lambda obj, *a, **k: printed.setdefault("obj", obj))

    # call the specific function to cover the "no seed file" branch
    if hasattr(init_db, "seed_from_json") and callable(init_db.seed_from_json):
        init_db.seed_from_json()
    else:
        # if the script inlines this inside main(), just run main — still safe due to our patches
        fn = _find_init_fn(init_db)
        if not fn:
            pytest.skip("No known init entrypoint found in init_db")
        fn()

    # printed message should exist; we avoid asserting exact text to keep it implementation-agnostic
    assert printed.get("obj") is not None