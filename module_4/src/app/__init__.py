"""Flask application factory and environment configuration."""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import os
from flask import Flask
from pathlib import Path


# Paths
APP_DIR = Path(__file__).resolve().parent          # .../MODULE_4/src/app
PROJECT_ROOT = APP_DIR.parent.parent               # .../MODULE_4

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

MIN_KEY_LEN = 32  # 32+ chars gets 64 hex chars

def _get_secret_key_from_env() -> str:
    """Return ``SECRET_KEY`` from environment.

    :returns: Secret key string.
    :raises RuntimeError: If key is missing or shorter than ``MIN_KEY_LEN``.
    """
    key = os.environ.get("SECRET_KEY", "")
    if len(key) < MIN_KEY_LEN:
        raise RuntimeError(
            "SECRET_KEY is missing or too short. "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))" '
            "and place it in MODULE_4/.env"
        )
    return key

def create_app() -> Flask:
    """Create and configure the Flask application.

    :returns: Configured Flask application.
    :rtype: Flask
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Read env
    app.config["SECRET_KEY"] = _get_secret_key_from_env()

    # Ensure app-local data dir exists
    (APP_DIR / "data").mkdir(parents=True, exist_ok=True)

    # Register routes
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    return app
