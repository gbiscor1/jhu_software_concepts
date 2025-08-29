# routes.py
# ----------
# Defines the main Flask blueprint for the personal website.
# Includes routes for Home (/), Contact (/contact), and Projects (/projects).
# The helper function load_projects() loads project data from JSON files.

from flask import Blueprint, render_template, current_app, url_for
import os
import json


bp = Blueprint("pages", __name__)


def load_projects():
    """
    Helper function:
    ----------------
    Reads all JSON files inside app/data/projects/ and returns them
    as a list of project dictionaries.
    """
    projects_dir = os.path.join(current_app.root_path, "data", "projects")
    projects = []
    if os.path.isdir(projects_dir):
        for fname in os.listdir(projects_dir):
            if fname.endswith(".json"):
                with open(os.path.join(projects_dir, fname), "r", encoding="utf-8") as f:
                    projects.append(json.load(f))
    # sort by "order"
    projects.sort(key=lambda x: x.get("order", 999))
    return projects

@bp.route("/")
def home():
    return render_template("home.html")

@bp.route("/contact")
def contact():
    return render_template("contact.html")

@bp.route("/projects")
def projects():
    return render_template("projects.html", projects=load_projects())