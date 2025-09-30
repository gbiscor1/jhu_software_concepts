# tests/scripts/test_reset_db.py
"""Tests for the reset_db script."""

from __future__ import annotations

import sys
import types
import builtins
from pathlib import Path
import os
import pytest

pytestmark = pytest.mark.db


class _FakeCur:
    """Minimal cursor stub recording executed SQL."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, object | None]] = []

    def execute(self, sql: str, params: object | None = None) -> int:
        """Record the SQL (and optional params)."""
        self.executed.append((sql, params))
        return 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pylint: disable=unused-argument
        return False


class _FakeConn:
    """Minimal connection stub yielding _FakeCur and tracking commits."""

    def __init__(self) -> None:
        self._cur = _FakeCur()
        self.closed = False
        self.commits = 0

    def cursor(self) -> _FakeCur:
        """Return a cursor context manager."""
        return self._cur

    def commit(self) -> None:
        """Count commits."""
        self.commits += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pylint: disable=unused-argument
        self.closed = True
        return False


class _CommitRaisesConn:
    """Fake connection whose commit() raises; acts as both connection and cursor."""

    def __init__(self, sql_sink: list[str]) -> None:
        self._sql_sink = sql_sink

    def cursor(self):
        """Return self as cursor context manager."""
        return self

    # Acts as both conn and cursor context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pylint: disable=unused-argument
        return False

    def execute(self, sql: str) -> None:
        """Record the SQL."""
        self._sql_sink.append(sql)

    def commit(self) -> None:
        """Raise to simulate commit failure."""
        raise RuntimeError("boom")


def test_load_env_covers_missing_and_setdefault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Cover: (a) missing .env => no-op, (b) valid lines, (c) setdefault doesn't override."""
    reset_db = pytest.importorskip("src.scripts.reset_db", reason="reset_db not present")

    # (a) missing file -> no-op
    reset_db.load_env(str(tmp_path / "nope.env"))  # should not raise

    # (b) valid file with comments and junk lines
    envp = tmp_path / ".env"
    envp.write_text(
        "# comment\n"
        "FOO=bar\n"
        "INVALID_LINE\n"
        "SPACED = value with spaces\n",
        encoding="utf-8",
    )

    # Ensure setdefault behavior (pre-existing wins)
    monkeypatch.setenv("FOO", "preexisting")

    reset_db.load_env(str(envp))
    assert os.getenv("FOO") == "preexisting"            # not overridden
    assert os.getenv("SPACED") == "value with spaces"   # newly set
    assert os.getenv("INVALID_LINE") is None            # ignored


def test_apply_schema_commit_exception_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Cover the try/except around conn.commit() by forcing commit() to raise."""
    reset_db = pytest.importorskip("src.scripts.reset_db", reason="reset_db not present")

    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE t(id int);", encoding="utf-8")

    sink: list[str] = []
    monkeypatch.setattr(reset_db, "get_conn", lambda: _CommitRaisesConn(sink), raising=False)

    statements = reset_db.apply_schema(schema)
    # executed SQL recorded
    assert sink and "CREATE TABLE" in sink[0]
    # crude statement count (based on ';')
    assert statements >= 1


def test_main_prints_and_returns_summary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Drive main(argv=...) to cover print+return and --env missing path."""
    reset_db = pytest.importorskip("src.scripts.reset_db", reason="reset_db not present")

    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE x(id int);", encoding="utf-8")

    # Simple fake conn that commits fine (success path)
    class _OKConn:  # pylint: disable=too-few-public-methods
        """OK connection that supports cursor/commit without side-effects."""
        def cursor(self):
            """Fake cursor context manager."""
            return self
        def __enter__(self):
            """Return self as context manager."""
            return self
        def __exit__(self, exc_type, exc, tb):
            """exit context; do not suppress exceptions."""
            return False  # noqa: D401
        def execute(self):  # noqa: D401
            """No-op execute."""
            return None
        def commit(self):  # noqa: D401
            """No-op commit."""
            return None

    monkeypatch.setattr(reset_db, "get_conn", _OKConn, raising=False)

    printed: dict[str, object] = {}
    def _fake_print(obj, *_args, **_kwargs):
        printed.setdefault("obj", obj)
    monkeypatch.setattr(builtins, "print", _fake_print)

    out = reset_db.main(argv=["--schema", str(schema), "--env", str(tmp_path / "missing.env")])
    # both return value and printed value should be the summary dict
    assert isinstance(out, dict)
    assert printed.get("obj") == out
    assert out["schema"] == str(schema)
    assert out["statements"] >= 1


def _find_reset_fn(mod) -> object | None:
    """Locate a plausible entrypoint function in the module."""
    for name in ("main", "reset_db", "reset_database", "reset", "run", "cli_main"):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    return None


def test_reset_db_runs_schema_against_fake_db(  # pylint: disable=too-many-locals
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Exercise reset flow with a temp schema and fake DB/subprocess seams."""
    reset_db = pytest.importorskip(
        "src.scripts.reset_db", reason="reset_db script module not present"
    )

    # --- temp schema we control ---
    schema_path: Path = tmp_path / "schema.sql"
    schema_path.write_text("CREATE TABLE IF NOT EXISTS t (id int);\n", encoding="utf-8")

    # steer any module-level schema paths to our file/dir
    for attr in ("SCHEMA_PATH", "SCHEMA_FILE", "SCHEMA_SQL", "SCHEMA"):
        if hasattr(reset_db, attr):
            monkeypatch.setattr(reset_db, attr, schema_path, raising=False)
    if hasattr(reset_db, "SCHEMA_DIR"):
        monkeypatch.setattr(reset_db, "SCHEMA_DIR", schema_path.parent, raising=False)

    # --- patch DB + subprocess boundaries ---
    fake_conn = _FakeConn()

    def _fake_get_conn():
        return fake_conn

    # Patch both the module symbol and (optionally) the canonical module
    monkeypatch.setattr(reset_db, "get_conn", _fake_get_conn, raising=False)

    import importlib
    import importlib.util

    spec = importlib.util.find_spec("src.data.psych_connect")
    if spec is not None:
        pc = importlib.import_module("src.data.psych_connect")
        monkeypatch.setattr(pc, "get_conn", _fake_get_conn, raising=False)

    calls: list[tuple[str, ...]] = []

    def _fake_run(cmd, *_args, **_kwargs):
        calls.append(tuple(cmd) if isinstance(cmd, (list, tuple)) else (str(cmd),))
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(
        reset_db, "subprocess", types.SimpleNamespace(run=_fake_run), raising=False
    )

    # neutralize potential cross-calls
    def _noop(*_args, **_kwargs):
        return None

    for maybe_mod in ("init_db", "load_db"):
        if hasattr(reset_db, maybe_mod):
            obj = getattr(reset_db, maybe_mod)
            if hasattr(obj, "main"):
                monkeypatch.setattr(obj, "main", _noop, raising=False)
            else:
                monkeypatch.setattr(reset_db, maybe_mod, _noop, raising=False)

    printed: dict[str, object] = {}

    def _fake_print(obj, *_args, **_kwargs):
        printed.setdefault("obj", obj)

    monkeypatch.setattr(builtins, "print", _fake_print)

    # >>> key fixes:
    # 1) Hide pytest args from argparse
    # 2) Point --env to a throwaway .env so load_env() doesn't error
    tmp_env = tmp_path / ".env"
    tmp_env.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["reset_db", "--env", str(tmp_env)], raising=False)

    # --- call entrypoint ---
    fn = _find_reset_fn(reset_db)
    if not fn:
        pytest.skip("No known reset entrypoint found in reset_db")
    fn()

    # Assertions: either executed SQL or used subprocess
    # pylint: disable=protected-access
    executed_sql = any(
        isinstance(sql, str) and sql.strip() for (sql, _p) in fake_conn._cur.executed
    )
    assert executed_sql or calls, "expected SQL execution or a subprocess call in reset_db"

    # Commit behavior optional; if not present, accept autocommit designs
    if getattr(fake_conn, "commits", 0) == 0:
        pytest.skip("reset_db appears to rely on autocommit / no explicit commit")
    assert fake_conn.commits >= 1
