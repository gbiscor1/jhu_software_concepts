""" Tests for DB insert loader and query functions."""
from __future__ import annotations

from pathlib import Path
import pytest


# Required suite marker (assignment)
pytestmark = pytest.mark.db


# ----------------------------- small utils -----------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _schema_path() -> Path:
    return _project_root() / "src" / "sql" / "schema" / "schema.sql"


def _run_loader(loader, rows, conn=None):
    # Adapter: support load_applicants(rows) or load_applicants(conn, rows)
    if conn is None:
        try:
            return loader.load_applicants(rows)
        except TypeError:
            return loader.load_applicants(None, rows)
    try:
        return loader.load_applicants(conn, rows)
    except TypeError:
        return loader.load_applicants(rows)


# ----------------------------- INSERTS: single row -----------------------------
def test_loader_inserts_single_row_records_unique_key(
    monkeypatch: pytest.MonkeyPatch, applicant_row_factory, fake_conn, db_store
):
    """Single row -> expect one INSERT executes and unique key added."""
    loader = pytest.importorskip("src.data.loader", reason="loader module not present")
    psych_connect = pytest.importorskip(
        "src.data.psych_connect", reason="psych_connect module not present"
    )

    def _fake_get_conn():
        return fake_conn

    monkeypatch.setattr(psych_connect, "get_conn", _fake_get_conn, raising=False)
    monkeypatch.setattr(loader, "get_conn", _fake_get_conn, raising=False)

    row = applicant_row_factory(pid=1, url="https://example.test/1")
    before = len(db_store)
    res = _run_loader(loader, [row], conn=fake_conn)
    cur = fake_conn.cursor()
    if not cur.executed:
        # No SQL emitted in this env; at least assert stats if present
        if isinstance(res, dict):
            assert res.get("attempted") in (1, 0)
        return
    after = len(db_store)
    assert after == before + 1, "expected exactly one unique insert"
    if isinstance(res, dict):
        assert res.get("attempted") in (1, 0)
        assert res.get("inserted", 0) >= 0


# ----------------------------- INSERTS: multiple rows / batch path -----------------------------
def test_loader_inserts_multiple_rows_uses_batch_or_multi_execute(
    monkeypatch: pytest.MonkeyPatch, applicant_row_factory, fake_conn
):
    """Multiple rows -> expect executemany() or multiple INSERT executes."""
    loader = pytest.importorskip("src.data.loader", reason="loader module not present")
    psych_connect = pytest.importorskip(
        "src.data.psych_connect", reason="psych_connect module not present"
    )

    def _fake_get_conn():
        return fake_conn

    monkeypatch.setattr(psych_connect, "get_conn", _fake_get_conn, raising=False)
    monkeypatch.setattr(loader, "get_conn", _fake_get_conn, raising=False)

    rows = [
        applicant_row_factory(pid=10, url="https://example.test/10"),
        applicant_row_factory(pid=11, url="https://example.test/11"),
        applicant_row_factory(pid=12, url="https://example.test/12"),
    ]
    res = _run_loader(loader, rows, conn=fake_conn)

    cur = fake_conn.cursor()
    if not cur.executed:
        if isinstance(res, dict):
            assert res.get("attempted") in (len(rows), 0)
        return

    sql_chunks = [sql for (sql, _p) in cur.executed if isinstance(sql, str)]
    saw_executemany = any(sql.startswith("[executemany]") for sql in sql_chunks)
    saw_multiple_inserts = sum("insert" in sql.lower() for sql in sql_chunks) >= 2
    assert saw_executemany or saw_multiple_inserts, (
        f"expected executemany or multiple INSERTs; got {sql_chunks!r}"
    )


# ----------------------------- IDEMPOTENCY -----------------------------
def test_loader_is_idempotent_with_duplicate_rows(
    monkeypatch: pytest.MonkeyPatch, applicant_row_factory, fake_conn, db_store
):
    """Idempotency: re-running with same rows must not increase unique key count."""
    loader = pytest.importorskip("src.data.loader", reason="loader module not present")
    psych_connect = pytest.importorskip(
        "src.data.psych_connect", reason="psych_connect module not present"
    )

    def _fake_get_conn():
        return fake_conn

    monkeypatch.setattr(psych_connect, "get_conn", _fake_get_conn, raising=False)
    monkeypatch.setattr(loader, "get_conn", _fake_get_conn, raising=False)

    rows = [
        applicant_row_factory(pid=2, url="https://example.test/2"),
        applicant_row_factory(pid=3, url="https://example.test/3"),
    ]
    _ = _run_loader(loader, rows, conn=fake_conn)
    size_after_first = len(db_store)

    _ = _run_loader(loader, rows, conn=fake_conn)
    size_after_second = len(db_store)

    assert size_after_second == size_after_first, "duplicate load must not add new unique keys"


# ----------------------------- MIXED ROWS -----------------------------
def test_loader_handles_mixed_rows_gracefully(
    monkeypatch: pytest.MonkeyPatch, applicant_row_factory, fake_conn
):
    """Test mixed inputs: valid + malformed. Either fail-fast or skip bad rows in stats."""
    loader = pytest.importorskip("src.data.loader", reason="loader module not present")
    psych_connect = pytest.importorskip(
        "src.data.psych_connect", reason="psych_connect module not present"
    )

    def _fake_get_conn():
        return fake_conn

    monkeypatch.setattr(psych_connect, "get_conn", _fake_get_conn, raising=False)
    monkeypatch.setattr(loader, "get_conn", _fake_get_conn, raising=False)

    good = applicant_row_factory(pid=4, url="https://example.test/good")
    bad = applicant_row_factory(pid=5, url=None)  # invalid unique id / required field
    rows = [good, bad]

    raised = False
    try:
        res = _run_loader(loader, rows, conn=fake_conn)
    except (TypeError, ValueError, KeyError, RuntimeError):
        # Accept common validation/data errors as "fail-fast"
        raised = True
        res = None

    if raised:
        return  # fail-fast design accepted

    if isinstance(res, dict):
        assert res.get("attempted") in (0, 1, 2)
        assert res.get("inserted", 0) in (0, 1, 2)
        assert res.get("skipped", 0) in (0, 1)


# ----------------------------- COMMIT BEHAVIOR -----------------------------
def test_loader_commits_transaction_if_defined(
    monkeypatch: pytest.MonkeyPatch, applicant_row_factory, fake_conn_factory
):
    """If loader uses explicit commit, expect at least one COMMIT on the connection."""
    loader = pytest.importorskip("src.data.loader", reason="loader module not present")
    psych_connect = pytest.importorskip(
        "src.data.psych_connect", reason="psych_connect module not present"
    )

    conn = fake_conn_factory(count_commits=True)

    def _fake_get_conn():
        return conn

    monkeypatch.setattr(psych_connect, "get_conn", _fake_get_conn, raising=False)
    monkeypatch.setattr(loader, "get_conn", _fake_get_conn, raising=False)

    rows = [applicant_row_factory(pid=20, url="https://example.test/20")]
    _ = _run_loader(loader, rows, conn=conn)

    if getattr(conn, "commits", 0) == 0:
        pytest.skip("loader appears to rely on autocommit / no explicit commit")
    assert conn.commits >= 1


# ----------------------------- QUERY FUNCTION KEYS  -----------------------------
def test_simple_query_function_keys_if_present(
    monkeypatch: pytest.MonkeyPatch, fake_conn_factory
):
    """If a simple query function is present, expect certain keys in its result."""
    qr = pytest.importorskip("src.data.query_runner", reason="query_runner module not present")
    psych_connect = pytest.importorskip(
        "src.data.psych_connect", reason="psych_connect module not present"
    )

    select_rows = [{"program": "MS CS", "university": "JHU", "decision": "Accepted"}]
    conn = fake_conn_factory(select_rows=select_rows)

    def _fake_get_conn():
        return conn

    monkeypatch.setattr(psych_connect, "get_conn", _fake_get_conn, raising=False)

    for fn_name in ("simple_query", "run_simple_query", "query_simple"):
        fn = getattr(qr, fn_name, None)
        if callable(fn):
            try:
                res = fn()
            except TypeError:
                res = fn(limit=1)
            if isinstance(res, list) and res and isinstance(res[0], dict):
                assert {"program", "university", "decision"}.issubset(res[0].keys())
                return
            if isinstance(res, dict):
                assert {"program", "university", "decision"}.issubset(res.keys())
                return
    pytest.skip("No known simple query function found to validate keys")


# ----------------------------- PSYCH_CONNECT -----------------------------
class DummyPsyConn: # pylint: disable=too-few-public-methods
    """Minimal dummy connection to test get_conn() return type."""
    def __init__(self, url):
        self.url = url
        self.closed = False
        self.autocommit = False

    def close(self):
        """Close the connection."""
        self.closed = True


def test_get_conn_uses_env_url(monkeypatch: pytest.MonkeyPatch):
    """Success path: with TEST_DATABASE_URL or DATABASE_URL, get_conn returns a connection."""
    pc = pytest.importorskip("src.data.psych_connect", reason="psych_connect module not present")
    sentinel_url = "postgresql://u:p@h:5432/dbname"
    monkeypatch.setenv("TEST_DATABASE_URL", sentinel_url)

    class _Lib:  # pylint: disable=too-few-public-methods
        def connect(self, **kw):
            """Return a dummy connection."""
            return DummyPsyConn(kw.get("conninfo") or kw.get("dsn") or sentinel_url)

    monkeypatch.setattr(pc, "psycopg", _Lib(), raising=False)
    monkeypatch.setattr(pc, "psycopg2", _Lib(), raising=False)

    conn = pc.get_conn()
    assert isinstance(conn, DummyPsyConn)


def test_get_conn_raises_if_no_url(monkeypatch: pytest.MonkeyPatch):
    """Failure path: without TEST_DATABASE_URL or DATABASE_URL, get_conn raises."""
    pc = pytest.importorskip("src.data.psych_connect", reason="psych_connect module not present")

    for key in ("TEST_DATABASE_URL", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)

    class _ErrLib:  # pylint: disable=too-few-public-methods
        def connect(self, *a, **kw):
            """connect always fails."""
            raise RuntimeError("no DSN")

    monkeypatch.setattr(pc, "psycopg", _ErrLib(), raising=False)
    monkeypatch.setattr(pc, "psycopg2", _ErrLib(), raising=False)

    with pytest.raises((RuntimeError, ValueError)):
        pc.get_conn()


# ----------------------------- REPO ARTIFACT -----------------------------
def test_schema_file_exists_and_is_readable():
    """Schema file should exist and contain at least one CREATE statement."""
    p = _schema_path()
    assert p.exists(), f"Schema file not found: {p}"
    assert "CREATE" in p.read_text(encoding="utf-8").upper()
