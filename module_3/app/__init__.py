from __future__ import annotations
from flask import Flask
from pathlib import Path

def create_app() -> Flask:

    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = "dev" 
    (Path(__file__).parent / "data").mkdir(parents=True, exist_ok=True)

    # Register page routes
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
