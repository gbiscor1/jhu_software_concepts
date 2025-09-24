# Ensure src is importable; provide shared fixtures, fakes, factories.
import sys, importlib, json
from pathlib import Path
import pytest
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]  # module_4/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------- Simple headers ----------
@pytest.fixture(scope="session")
def json_headers():
    return {"Accept": "application/json"}

# ---------- Lightweight fakes ----------
class FakeLock:
    # Drop-in for routes._pull_lock; can simulate busy/not-busy
    def __init__(self, locked=False): self._locked = locked
    def locked(self): return self._locked
    def __enter__(self):
        if self._locked:  # emulate busy by refusing to acquire
            raise RuntimeError("busy")
        return self
    def __exit__(self, exc_type, exc, tb): return False

class CallCounter:
    # Callable stub that counts calls; returns value or raises
    def __init__(self, result=None, exc=None):
        self.calls = 0; self.result = result; self.exc = exc
    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.exc: raise self.exc
        return self.result

# ---------- App/client fixtures with isolated APP_DIR ----------
@pytest.fixture()
def app(monkeypatch, tmp_path):
    # Isolate secrets and app-local data dir
    monkeypatch.setenv("SECRET_KEY", "x" * 64)

    # Point modules' APP_DIR to tmp so templates/routes read/write under tmp
    import src.app as app_module
    monkeypatch.setattr(app_module, "APP_DIR", tmp_path, raising=False)
    import src.app.routes as routes
    monkeypatch.setattr(routes, "APP_DIR", tmp_path, raising=False)

    importlib.reload(app_module)  # ensure create_app sees env
    return app_module.create_app()

@pytest.fixture()
def client(app):
    return app.test_client()

# ---------- Data factories ----------
@pytest.fixture()
def applicant_row_factory():
    # Build applicant-like rows; defaults cover common fields
    def make(pid=1, url="https://gradcafe.com/p/1", **kw):
        row = {
            "post_url": url,      # many loaders accept either 'url' or 'post_url'
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
def make_card_files(tmp_path):
    # Write q_*.json files into app-local data dir used by routes/templates
    def _make(name="q01_demo", query="What is acceptance rate?", answer=None, result=None):
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
    # Normalize tuple/dict params into a stable, hashable key for uniqueness
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
    # Generic cursor:
    # - logs SQL,
    # - records unique INSERT parameter keys into shared 'store',
    # - supports executemany,
    # - returns preset rows for SELECTs.
    def __init__(self, store: set, select_rows=None, error_on_insert: Exception | None = None):
        self.store = store
        self.executed = []      # [(sql, params/list)]
        self._rows = list(select_rows or [])
        self._error_on_insert = error_on_insert

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        sql_l = str(sql).lower()
        if "insert" in sql_l:
            if self._error_on_insert:
                raise self._error_on_insert
            self.store.add(_params_to_key(params))

    def executemany(self, sql, seq_params):
        seq = list(seq_params)
        self.executed.append((f"[executemany]{sql}", seq))
        if "insert" in str(sql).lower():
            if self._error_on_insert:
                raise self._error_on_insert
            for p in seq:
                self.store.add(_params_to_key(p))

    def fetchall(self):
        return list(self._rows)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

class FakeConnBase:
    # Generic connection that returns a FakeCursorBase sharing a 'store' set
    def __init__(self, store: set | None = None, select_rows=None, error_on_insert: Exception | None = None):
        self.store = store if store is not None else set()
        self._select_rows = select_rows or []
        self._error_on_insert = error_on_insert
        self.autocommit = False
        self.closed = False
        self._cursor = FakeCursorBase(self.store, self._select_rows, self._error_on_insert)

    def cursor(self): return self._cursor
    def commit(self): pass
    def close(self): self.closed = True
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close(); return False

class CommitCountingConn(FakeConnBase):
    # Connection that counts commits
    def __init__(self, **kw):
        super().__init__(**kw)
        self.commits = 0
    def commit(self):
        self.commits += 1

# Factories/fixtures to inject into tests
@pytest.fixture()
def db_store():
    # Fresh set to track unique insert keys per test
    return set()

@pytest.fixture()
def fake_conn(db_store):
    # Default FakeConnBase with a shared store
    return FakeConnBase(store=db_store)

@pytest.fixture()
def fake_conn_factory():
    # Factory to build flexible FakeConnBase variants on demand
    def make(store=None, select_rows=None, error_on_insert=None, count_commits=False):
        if count_commits:
            return CommitCountingConn(store=store, select_rows=select_rows, error_on_insert=error_on_insert)
        return FakeConnBase(store=store, select_rows=select_rows, error_on_insert=error_on_insert)
    return make
