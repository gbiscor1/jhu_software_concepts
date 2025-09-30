"""Shared test helpers: PATH setup, lightweight fakes, and common fixtures."""

from __future__ import annotations

import sys
import importlib
import json
from pathlib import Path
from typing import Mapping

import pytest

# Ensure src is importable (prepend project root)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------- Simple headers ----------
@pytest.fixture(scope="session")
def json_headers():
    """HTTP headers requesting JSON responses."""
    return {"Accept": "application/json"}


# ---------- Lightweight fakes ----------
class FakeLock:
    """Drop-in for routes._pull_lock; can simulate busy/not-busy."""

    def __init__(self, locked: bool = False) -> None:
        self._locked = locked

    def locked(self) -> bool:
        """Return True if the fake lock is 'busy'."""
        return self._locked

    def __enter__(self):
        """Enter context; raise if configured busy (emulates lock contention)."""
        if self._locked:
            raise RuntimeError("busy")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pylint: disable=unused-argument
        """Exit context; do not suppress exceptions."""
        return False


class CallCounter: #pylint: disable=too-few-public-methods
    """Callable stub that counts calls; returns value or raises."""

    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self.calls = 0
        self.result = result
        self.exc = exc

    def __call__(self, *args, **kwargs):  # pylint: disable=unused-argument
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.result


# ---------- App/client fixtures with isolated APP_DIR ----------
@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Create Flask app with isolated APP_DIR and test SECRET_KEY."""
    monkeypatch.setenv("SECRET_KEY", "x" * 64)

    # Import modules lazily in a way Pylint won’t try to resolve statically
    app_module = pytest.importorskip("src.app", reason="src.app not importable")
    monkeypatch.setattr(app_module, "APP_DIR", tmp_path, raising=False)

    routes = pytest.importorskip("src.app.routes", reason="src.app.routes not importable")
    monkeypatch.setattr(routes, "APP_DIR", tmp_path, raising=False)

    importlib.reload(app_module)  # ensure create_app sees env
    return app_module.create_app()


@pytest.fixture()
def client(app):  # pylint: disable=redefined-outer-name
    """Return Flask test client from app fixture."""
    return app.test_client()


# ---------- Data factories ----------
@pytest.fixture()
def applicant_row_factory():
    """Factory for applicant-like rows; defaults cover common fields."""

    def make(pid: int = 1, url: str = "https://gradcafe.com/p/1", **kw):
        row = {
            # many loaders accept either 'url' or 'post_url'
            "post_url": url,
            "program": "MS CS",
            "university": "JHU",
            "decision": "Accepted",
            "p_id": pid,
            "gpa": 3.80,
        }
        row.update(kw)
        return row

    return make


@pytest.fixture()
def make_card_files(tmp_path: Path):
    """Factory to write q_*.json files into app-local data dir used by routes/templates."""

    def _make(
        name: str = "q01_demo",
        query: str = "What is acceptance rate?",
        answer=None,
        result=None,
    ) -> Path:
        """Write a q_{name}.json file with query/answer/result in app-local data dir."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        val = answer if answer is not None else result if result is not None else "39.28%"
        payload = {"query": query, "answer": val}
        p = data_dir / f"{name}.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    return _make


# ---------- DB fake infrastructure  ----------

# Canonical alias groups to build a uniqueness key from INSERT params
_DB_ALIAS_GROUPS = [
    ("url", "post_url"),
    ("university", "school", "institution", "college"),
    ("program", "degree", "major"),
    ("decision", "result", "status", "decision_result", "decision_label"),
    ("decision_date", "date", "date_added", "decision_dt"),
]


def _params_to_key(params) -> tuple:
    """Normalize tuple/dict params into a stable, hashable key for uniqueness."""
    if params is None:
        return ("<none>",)
    if isinstance(params, (list, tuple)):
        return tuple(params)
    if isinstance(params, Mapping):
        key = []
        for group in _DB_ALIAS_GROUPS:
            present = next((k for k in group if k in params), None)
            key.append((group[0], params.get(present)))
        return tuple(key)
    return (repr(params),)


class FakeCursorBase:
    """Generic cursor:
    - logs SQL,
    - records unique INSERT parameter keys into shared 'store',
    - supports executemany,
    - returns preset rows for SELECTs.
    """

    def __init__(
        self,
        store: set,
        select_rows=None,
        error_on_insert: Exception | None = None,
    ) -> None:
        self.store = store
        self.executed: list[tuple[str, object]] = []  # [(sql, params/list)]
        self._rows = list(select_rows or [])
        self._error_on_insert = error_on_insert

    def execute(self, sql, params=None) -> None:
        """Log SQL and params; record unique INSERT keys into store; return preset rows for SELECT."""
        self.executed.append((sql, params))
        sql_l = str(sql).lower()
        if "insert" in sql_l:
            if self._error_on_insert:
                raise self._error_on_insert
            self.store.add(_params_to_key(params))

    def executemany(self, sql, seq_params) -> None:
        """Log SQL and param sequence; record unique INSERT keys into store."""
        seq = list(seq_params)
        self.executed.append((f"[executemany]{sql}", seq))
        if "insert" in str(sql).lower():
            if self._error_on_insert:
                raise self._error_on_insert
            for p in seq:
                self.store.add(_params_to_key(p))

    def fetchall(self):
        """Return all preset rows (copy)."""
        return list(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pylint: disable=unused-argument
        return False


class FakeConnBase:
    """Generic connection that returns a FakeCursorBase sharing a 'store' set."""

    def __init__(
        self,
        store: set | None = None,
        select_rows=None,
        error_on_insert: Exception | None = None,
    ) -> None:
        self.store = store if store is not None else set()
        self._select_rows = select_rows or []
        self._error_on_insert = error_on_insert
        self.autocommit = False
        self.closed = False
        self._cursor = FakeCursorBase(self.store, self._select_rows, self._error_on_insert)

    def cursor(self) -> FakeCursorBase:
        """Return a cursor context manager."""
        return self._cursor

    def commit(self) -> None:
        """No-op commit."""
        return None

    def close(self) -> None:
        """Mark connection as closed."""
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pylint: disable=unused-argument
        self.close()
        return False


class CommitCountingConn(FakeConnBase):
    """Connection that increments a counter on commit()."""

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


# Factories/fixtures to inject into tests
@pytest.fixture()
def db_store():
    """Fresh set to track unique insert keys per test."""
    return set()


@pytest.fixture()
def fake_conn(db_store):  # pylint: disable=redefined-outer-name
    """Default FakeConnBase with a shared store."""
    return FakeConnBase(store=db_store)


@pytest.fixture()
def fake_conn_factory():
    """Factory to build flexible FakeConnBase variants on demand."""

    def make(
        store=None,
        select_rows=None,
        error_on_insert=None,
        count_commits: bool = False,
    ):
        if count_commits:
            return CommitCountingConn(
                store=store, select_rows=select_rows, error_on_insert=error_on_insert
            )
        return FakeConnBase(
            store=store, select_rows=select_rows, error_on_insert=error_on_insert
        )

    return make
