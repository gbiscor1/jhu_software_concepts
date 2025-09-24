# Module 4: Buttons & Busy-State Behavior
# Focus: JSON vs HTML responses and mutual-exclusion lock paths.

import pytest

pytestmark = pytest.mark.buttons


def test_pull_data_not_busy_returns_200_json(monkeypatch, client, json_headers):
    # Not busy: expect JSON 200/202 and ok=True
    import src.app.routes as routes
    monkeypatch.setattr(routes, "_pull_lock", routes._pull_lock)  # default unlocked
    stats = {"scraped": 5, "cleaned": 5, "to_load": 5}
    from tests.conftest import CallCounter
    monkeypatch.setattr(routes, "svc_pull", CallCounter(result=stats))

    r = client.post("/pull-data", headers=json_headers)
    assert r.status_code in (200, 202)
    assert r.is_json and r.get_json()["ok"] is True


def test_pull_data_busy_returns_409_json(monkeypatch, client, json_headers):
    # Busy: expect 409 JSON and no service call
    import src.app.routes as routes
    from tests.conftest import FakeLock
    monkeypatch.setattr(routes, "_pull_lock", FakeLock(locked=True))
    called = {"hit": False}

    def _svc():
        called["hit"] = True

    monkeypatch.setattr(routes, "svc_pull", _svc)

    r = client.post("/pull-data", headers=json_headers)
    assert r.status_code == 409
    assert r.is_json and r.get_json().get("busy") is True
    assert called["hit"] is False  # nothing executed while busy


def test_update_analysis_not_busy_returns_200_json(monkeypatch, client, json_headers):
    # Not busy: expect 200 JSON and ok=True
    import src.app.routes as routes
    from tests.conftest import FakeLock, CallCounter
    monkeypatch.setattr(routes, "_pull_lock", FakeLock(locked=False))
    monkeypatch.setattr(routes, "analysis_to_files", CallCounter(result={"written": 3}))

    r = client.post("/update-analysis", headers=json_headers)
    assert r.status_code == 200
    assert r.is_json and r.get_json()["ok"] is True


def test_update_analysis_error_returns_500_json(monkeypatch, client, json_headers):
    # Error path: analysis raises -> 500 JSON with ok=False
    import src.app.routes as routes
    from tests.conftest import FakeLock, CallCounter
    monkeypatch.setattr(routes, "_pull_lock", FakeLock(locked=False))
    monkeypatch.setattr(routes, "analysis_to_files", CallCounter(exc=RuntimeError("boom")))
    r = client.post("/update-analysis", headers=json_headers)
    assert r.status_code == 500
    assert r.is_json and r.get_json().get("ok") is False


# HTML branch coverage
def test_pull_data_html_redirects(monkeypatch, client):
    # No Accept header -> allow redirect branch or JSON depending on app behavior
    import src.app.routes as routes
    from tests.conftest import FakeLock, CallCounter
    monkeypatch.setattr(routes, "_pull_lock", FakeLock(locked=False))
    monkeypatch.setattr(
        routes, "svc_pull", CallCounter(result={"scraped": 1, "cleaned": 1, "to_load": 1})
    )
    r = client.post("/pull-data")  # no explicit Accept -> server decides
    if r.is_json:
        assert r.status_code in (200, 202)
        assert r.get_json().get("ok") in (True, None)
    else:
        assert r.status_code in (302, 303)


def test_update_analysis_html_redirects(monkeypatch, client):
    # No Accept header -> allow redirect branch or JSON 200
    import src.app.routes as routes
    from tests.conftest import FakeLock, CallCounter
    monkeypatch.setattr(routes, "_pull_lock", FakeLock(locked=False))
    monkeypatch.setattr(routes, "analysis_to_files", CallCounter(result={"written": 1}))
    r = client.post("/update-analysis")
    if r.is_json:
        assert r.status_code == 200
    else:
        assert r.status_code in (302, 303)
