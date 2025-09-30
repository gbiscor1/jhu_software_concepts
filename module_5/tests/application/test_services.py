""" Integration tests for application services."""

from __future__ import annotations

import importlib
import importlib.util
from types import SimpleNamespace, ModuleType
from typing import Any, Callable, Optional, cast

import pytest

# Mark module as integration suite
pytestmark = pytest.mark.integration


def _find_pull_fn(services: ModuleType) -> Optional[Callable[[], Any]]:
    """Return the first pull-like callable in the services module."""
    for name in ("svc_pull", "pull", "run_pull", "pull_data", "pull_pipeline"):
        fn = getattr(services, name, None)
        if callable(fn):
            return fn
    return None


def test_services_svc_pull_calls_collaborators(monkeypatch):
    """ Import target or skip if module not present"""
    services = pytest.importorskip(
        "src.application.services", reason="services module not present"
    )

    called = {"cli": 0, "load": 0}

    # Minimal run result object (avoid R0903 by using SimpleNamespace)
    def _run_obj(rows: list[dict[str, Any]]) -> SimpleNamespace:
        n = len(rows)
        return SimpleNamespace(
            final_records=rows,
            source="fake-source",
            raw_count=n,
            cleaned_count=n,
            final_count=n,
            raw_path=None,
            cleaned_path=None,
            extended_path=None,
        )

    def _fake_cli(*_args, **_kwargs):
        called["cli"] += 1
        return _run_obj([{"url": "https://x/1"}])

    def _fake_load(rows, *_args, **_kwargs):
        called["load"] += 1
        n = len(rows) if isinstance(rows, list) else 0
        return {"attempted": n, "inserted": n, "skipped": 0}

    # Patch collaborators at the module under test
    monkeypatch.setattr(services, "run_module2_cli", _fake_cli, raising=False)
    monkeypatch.setattr(services, "load_applicants", _fake_load, raising=False)

    # Optionally patch canonical modules if they exist (no broad except)
    spec = importlib.util.find_spec("src.application.scrapper_cli_caller")
    if spec is not None:
        scc = importlib.import_module("src.application.scrapper_cli_caller")
        monkeypatch.setattr(scc, "run_module2_cli", _fake_cli, raising=False)

    spec = importlib.util.find_spec("src.data.loader")
    if spec is not None:
        loader_mod = importlib.import_module("src.data.loader")
        monkeypatch.setattr(loader_mod, "load_applicants", _fake_load, raising=False)

    fn = _find_pull_fn(services)
    if fn is None:
        pytest.skip("svc_pull not defined")

    # Pylint: make callability explicit for dynamic attr (fixes E1102)
    out = cast(Callable[[], Any], fn)()

    # Basic behavior: collaborators called; dict returned with counts
    assert called["cli"] == 1
    assert called["load"] >= 1
    assert isinstance(out, dict)
    assert out.get("attempted", 0) >= 0
    assert out.get("inserted", 0) >= 0


def test_services_analysis_to_files_error_path(monkeypatch):
    """ Import target or skip if module not present"""
    services = pytest.importorskip(
        "src.application.services", reason="services module not present"
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("write failed")

    # Try several possible internal names to force error
    for name in ("write_cards", "analysis_to_files_impl", "analysis_pipeline"):
        if hasattr(services, name):
            monkeypatch.setattr(services, name, _boom, raising=False)
            break

    # Ensure error surfaces when analysis_to_files is called
    if hasattr(services, "analysis_to_files"):
        with pytest.raises(RuntimeError):
            services.analysis_to_files()
    else:
        pytest.skip("analysis_to_files not defined")
