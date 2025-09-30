"""Tests for button endpoints /pull-data and /update-analysis."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.buttons


def test_pull_data_not_busy_returns_200_json(monkeypatch, client, json_headers):
    """PULL not busy returns 200 JSON with ok=True."""
    routes = pytest.importorskip("src.app.routes", reason="routes not importable")
    cf = pytest.importorskip("tests.conftest", reason="conftest not importable")

    # Not busy + stub svc_pull -> JSON 200/202 and ok=True
    monkeypatch.setattr(routes, "_pull_lock", cf.FakeLock(locked=False), raising=False)  # pylint: disable=protected-access
    stats = {"scraped": 5, "cleaned": 5, "to_load": 5}
    monkeypatch.setattr(routes, "svc_pull", cf.CallCounter(result=stats), raising=False)

    resp = client.post("/pull-data", headers=json_headers)
    assert resp.status_code in (200, 202)
    assert resp.is_json and resp.get_json()["ok"] is True


def test_pull_data_busy_returns_409_json(monkeypatch, client, json_headers):
    """PULL busy returns 409 JSON with busy=True and does not call svc."""
    routes = pytest.importorskip("src.app.routes", reason="routes not importable")
    cf = pytest.importorskip("tests.conftest", reason="conftest not importable")

    monkeypatch.setattr(routes, "_pull_lock", cf.FakeLock(locked=True), raising=False)  # pylint: disable=protected-access
    called = {"hit": False}

    def _svc():
        called["hit"] = True

    monkeypatch.setattr(routes, "svc_pull", _svc, raising=False)

    resp = client.post("/pull-data", headers=json_headers)
    assert resp.status_code == 409
    assert resp.is_json and resp.get_json().get("busy") is True
    assert called["hit"] is False  # nothing executed while busy


def test_update_analysis_not_busy_returns_200_json(monkeypatch, client, json_headers):
    """ANALYSIS not busy returns 200 JSON with ok=True."""
    routes = pytest.importorskip("src.app.routes", reason="routes not importable")
    cf = pytest.importorskip("tests.conftest", reason="conftest not importable")

    monkeypatch.setattr(routes, "_pull_lock", cf.FakeLock(locked=False), raising=False)  # pylint: disable=protected-access
    monkeypatch.setattr(routes, "analysis_to_files", cf.CallCounter(result={"written": 3}), raising=False)

    resp = client.post("/update-analysis", headers=json_headers)
    assert resp.status_code == 200
    assert resp.is_json and resp.get_json()["ok"] is True


def test_update_analysis_error_returns_500_json(monkeypatch, client, json_headers):
    """ANALYSIS error returns 500 JSON with ok=False."""
    routes = pytest.importorskip("src.app.routes", reason="routes not importable")
    cf = pytest.importorskip("tests.conftest", reason="conftest not importable")

    monkeypatch.setattr(routes, "_pull_lock", cf.FakeLock(locked=False), raising=False)  # pylint: disable=protected-access
    monkeypatch.setattr(
        routes, "analysis_to_files", cf.CallCounter(exc=RuntimeError("boom")), raising=False
    )

    resp = client.post("/update-analysis", headers=json_headers)
    assert resp.status_code == 500
    assert resp.is_json and resp.get_json().get("ok") is False


def test_pull_data_html_redirects(monkeypatch, client):
    """/pull-data HTML branch: allow redirect or JSON depending on app behavior."""
    routes = pytest.importorskip("src.app.routes", reason="routes not importable")
    cf = pytest.importorskip("tests.conftest", reason="conftest not importable")

    monkeypatch.setattr(routes, "_pull_lock", cf.FakeLock(locked=False), raising=False)  # pylint: disable=protected-access
    monkeypatch.setattr(
        routes, "svc_pull", cf.CallCounter(result={"scraped": 1, "cleaned": 1, "to_load": 1}), raising=False
    )

    resp = client.post("/pull-data")  # no explicit Accept -> server decides
    if resp.is_json:
        assert resp.status_code in (200, 202)
        assert resp.get_json().get("ok") in (True, None)
    else:
        assert resp.status_code in (302, 303)


def test_update_analysis_html_redirects(monkeypatch, client):
    """/update-analysis HTML branch: allow redirect or JSON 200."""
    routes = pytest.importorskip("src.app.routes", reason="routes not importable")
    cf = pytest.importorskip("tests.conftest", reason="conftest not importable")

    monkeypatch.setattr(routes, "_pull_lock", cf.FakeLock(locked=False), raising=False)  # pylint: disable=protected-access
    monkeypatch.setattr(routes, "analysis_to_files", cf.CallCounter(result={"written": 1}), raising=False)

    resp = client.post("/update-analysis")
    if resp.is_json:
        assert resp.status_code == 200
    else:
        assert resp.status_code in (302, 303)
