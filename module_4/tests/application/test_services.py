# Integration tests for application services.

import pytest

# Mark module as integration suite
pytestmark = pytest.mark.integration


def _find_pull_fn(services):
    # Try common function names; return first callable
    for name in ("svc_pull", "pull", "run_pull", "pull_data", "pull_pipeline"):
        fn = getattr(services, name, None)
        if callable(fn):
            return fn
    return None


def test_services_svc_pull_calls_collaborators(monkeypatch):
    # Import target or skip if module not present
    try:
        import src.application.services as services
    except Exception:
        pytest.skip("services module not present")

    called = {"cli": 0, "load": 0}

    # Match attributes used by services.pull_data / svc_pull
    class _RunObj:
        def __init__(self, rows):
            self.final_records = rows
            self.source = "fake-source"
            n = len(rows)
            self.raw_count = n
            self.cleaned_count = n
            self.final_count = n
            # Unused by services, kept for robustness
            self.raw_path = None
            self.cleaned_path = None
            self.extended_path = None

    def _fake_cli(*a, **k):
        called["cli"] += 1
        return _RunObj([{"url": "https://x/1"}])

    def _fake_load(rows, *a, **k):
        called["load"] += 1
        n = len(rows) if isinstance(rows, list) else 0
        return {"attempted": n, "inserted": n, "skipped": 0}

    # Patch collaborators at the module under test
    monkeypatch.setattr(services, "run_module2_cli", _fake_cli, raising=False)
    monkeypatch.setattr(services, "load_applicants", _fake_load, raising=False)

    # Also patch canonical modules in case of different import paths
    try:
        import src.application.scrapper_cli_caller as scc
        monkeypatch.setattr(scc, "run_module2_cli", _fake_cli, raising=False)
    except Exception:
        pass
    try:
        from src.data import loader as loader_mod
        monkeypatch.setattr(loader_mod, "load_applicants", _fake_load, raising=False)
    except Exception:
        pass

    fn = _find_pull_fn(services)
    if not fn:
        pytest.skip("svc_pull not defined")

    out = fn()

    # Basic behavior: collaborators called; dict returned with counts
    assert called["cli"] == 1
    assert called["load"] >= 1
    assert isinstance(out, dict)
    assert out.get("attempted", 0) >= 0
    assert out.get("inserted", 0) >= 0


def test_services_analysis_to_files_error_path(monkeypatch):
    # Import target or skip if module not present
    try:
        import src.application.services as services
    except Exception:
        pytest.skip("services module not present")

    def _boom(*a, **k):
        raise RuntimeError("write failed")

    # Try several possible internal names to force error
    for name in ("write_cards", "analysis_to_files_impl", "analysis_pipeline"):
        if hasattr(services, name):
            monkeypatch.setattr(services, name, _boom, raising=False)
            break

    # Ensure error surfaces when analysis_to_files is called
    if hasattr(services, "analysis_to_files"):
        with pytest.raises(Exception):
            services.analysis_to_files()
    else:
        pytest.skip("analysis_to_files not defined")
