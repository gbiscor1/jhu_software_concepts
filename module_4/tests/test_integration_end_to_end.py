# End-to-end (fast) integration flow: pull -> update -> render.

import json
import pytest

# Mark module as integration suite
pytestmark = pytest.mark.integration


def test_end_to_end_fast(monkeypatch, client, make_card_files):
    # Patch boundaries for predictable behavior
    import src.app.routes as routes
    from tests.conftest import FakeLock, CallCounter

    monkeypatch.setattr(routes, "_pull_lock", FakeLock(False))
    monkeypatch.setattr(routes, "svc_pull", CallCounter(result={"scraped": 2, "cleaned": 2, "to_load": 2}))
    monkeypatch.setattr(routes, "analysis_to_files", CallCounter(result={"written": 1}))

    # Flow: pull -> update -> render
    assert client.post("/pull-data", headers={"Accept": "application/json"}).status_code in (200, 202)
    assert client.post("/update-analysis", headers={"Accept": "application/json"}).status_code == 200

    # Prime at least one card so the page has an Answer section
    p = make_card_files(name="q99", answer="IGNORED")
    p.write_text(json.dumps({
        "query": "inline",
        "answer": [{"Metric": "Acceptance", "Value": "39.28%"}]
    }), encoding="utf-8")

    r = client.get("/analysis")
    s = r.get_data(as_text=True)

    # Structural assertions; formatting covered elsewhere
    assert "Answer:" in s
    assert 'data-testid="pull-data-btn"' in s
    assert 'data-testid="update-analysis-btn"' in s
    assert ("<table" in s and "</table>" in s) or ('class="big-number"' in s)
