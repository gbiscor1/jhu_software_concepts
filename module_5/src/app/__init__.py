"""Flask application factory and environment configuration."""

from __future__ import annotations

# stdlib
import os
from pathlib import Path

# third-party
from dotenv import load_dotenv
from flask import Flask

# Paths
APP_DIR = Path(__file__).resolve().parent          # .../MODULE_5/src/app
PROJECT_ROOT = APP_DIR.parent.parent               # .../MODULE_5

# Load .env once at import time
load_dotenv(PROJECT_ROOT / ".env")

MIN_KEY_LEN = 32  # 32+ chars gets 64 hex chars

def _get_secret_key_from_env() -> str:
    """Return SECRET_KEY from environment or raise if too short/missing."""
    key = os.environ.get("SECRET_KEY", "")
    if len(key) < MIN_KEY_LEN:
        raise RuntimeError(
            "SECRET_KEY is missing or too short. "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))" '
            "and place it in MODULE_5/.env"
        )
    return key

def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # DO NOT load_dotenv() here; tests need to control the env per-case
    app.config["SECRET_KEY"] = _get_secret_key_from_env()

    (APP_DIR / "data").mkdir(parents=True, exist_ok=True)

    from .routes import bp as main_bp  # local import after app created
    app.register_blueprint(main_bp)
    return app
