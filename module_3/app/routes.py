# module_3/app/routes.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, render_template, redirect, url_for, flash
import threading

from application.services import analysis_to_files, pull_data as svc_pull

bp = Blueprint("main", __name__)
_pull_lock = threading.Lock()

APP_DIR: Path = Path(__file__).resolve().parent
APP_DATA_DIR: Path = APP_DIR / "data"


def _load_card_files() -> Dict[str, Dict[str, Any]]:
    """
    Load app/data/q_*.json and adapt keys
    """
    results: Dict[str, Dict[str, Any]] = {}
    if not APP_DATA_DIR.exists():
        return results
    for p in sorted(APP_DATA_DIR.glob("q*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        results[p.name] = {
            "sql": payload.get("query", p.stem),
            "result": payload.get("answer"),
        }
    return results


@bp.get("/")
def index():
    # Render from precomputed JSON cards
    results = _load_card_files()
    return render_template("query_page.html", results=results)


@bp.post("/pull-data")
def pull_data():
    if _pull_lock.locked():
        flash("A pull is already running. Try again shortly.", "info")
        return redirect(url_for("main.index"))
    with _pull_lock:
        try:
            stats = svc_pull()
            flash(
                f"Pull complete: attempted {stats['attempted']}, inserted {stats['inserted']}, skipped {stats['skipped']}.",
                "success",
            )
        except Exception as e:
            flash(f"Pull failed: {e}", "error")
    return redirect(url_for("main.index"))


@bp.post("/update-analysis")
def update_analysis():
    if _pull_lock.locked():
        flash("Busy pulling data; update skipped.", "warning")
        return redirect(url_for("main.index"))
    try:
        out = analysis_to_files()
        flash(f"Analysis updated: wrote {out['written']} cards.", "success")
    except Exception as e:
        flash(f"Update failed: {e}", "error")
    return redirect(url_for("main.index"))