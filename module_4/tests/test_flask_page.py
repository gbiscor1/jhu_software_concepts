# Tests for the Flask web application: App Factory + GET /analysis

import pytest
from flask import Flask
from bs4 import BeautifulSoup
import importlib


VALID_32 = "a" * 32
VALID_64 = "b" * 64
VALID_100 = "c" * 100
INVALID_31 = "x" * 31
INVALID_EMPTY = ""


# ----------------------
# Secret Key validation
# ----------------------

@pytest.mark.web
@pytest.mark.parametrize(
    "key, should_fail",
    [
        (VALID_32, False),
        (VALID_64, False),
        (VALID_100, False),
        (INVALID_31, True),
        (INVALID_EMPTY, True),
        (None, True),
    ],
)
def test_secret_key_validation(monkeypatch, key, should_fail):
    # App creation should succeed only for keys with length >= 32
    monkeypatch.setenv("SECRET_KEY", VALID_64)
    import src.app as app_module
    importlib.reload(app_module)

    if key is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", key)

    if should_fail:
        with pytest.raises(RuntimeError, match="SECRET_KEY is missing or too short"):
            app_module.create_app()
    else:
        flask_app = app_module.create_app()
        assert isinstance(flask_app, Flask)
        assert flask_app.config["SECRET_KEY"] == key


# ----------------------
# App Factory
# ----------------------

@pytest.mark.web
def test_create_app_smoke_and_side_effects(monkeypatch, tmp_path):
    # Expect a Flask app with SECRET_KEY set and a local 'data' directory created
    monkeypatch.setenv("SECRET_KEY", VALID_64)
    import src.app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "APP_DIR", tmp_path, raising=True)

    flask_app = app_module.create_app()
    assert isinstance(flask_app, Flask)
    assert flask_app.config["SECRET_KEY"] == VALID_64
    assert (tmp_path / "data").is_dir()


# ----------------------
# GET /analysis content check
# ----------------------

@pytest.mark.web
def test_analysis_page_content(client, make_card_files):
    # GET /analysis should render and include required UI elements
    # Ensures presence of heading, buttons (data-testid), and "Answer:" label
    make_card_files(name="q_smoke", result="39.28%")

    response = client.get("/analysis")
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, "html.parser")
    text = soup.get_text()

    assert "Analysis" in text, "Missing 'Analysis' heading"
    assert soup.find(attrs={"data-testid": "pull-data-btn"}), "Missing Pull Data button"
    assert soup.find(attrs={"data-testid": "update-analysis-btn"}), "Missing Update Analysis button"
    assert "Answer:" in text, "Missing 'Answer:' label"
