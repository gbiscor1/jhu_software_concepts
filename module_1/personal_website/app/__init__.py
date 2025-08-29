# __init__.py
# Initializes the Flask application.
# Sets template and static folders, and registers the routes blueprint.

from flask import Flask
from .routes import bp

def create_app():
    # Initialize Flask app
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # Register blueprint
    app.register_blueprint(bp)
    return app