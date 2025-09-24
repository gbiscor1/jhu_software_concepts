"""HTTP routes and UI endpoints."""

# module_4/app/routes.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import threading

from ..application.services import analysis_to_files, pull_data as svc_pull

bp = Blueprint("main", __name__)
_pull_lock = threading.Lock()

APP_DIR: Path = Path(__file__).resolve().parent
APP_DATA_DIR: Path = APP_DIR / "data"


def _load_card_files() -> Dict[str, Dict[str, Any]]:
    """Load JSON cards from ``app/data/q*.json``.

    :returns: Mapping of filename to payload with keys ``sql`` and ``result``.
    :rtype: Dict[str, Dict[str, Any]]
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


@bp.get("/analysis")
def index():
    """Render analysis page from precomputed JSON cards.

    :returns: Rendered HTML page.
    """
    results = _load_card_files()
    return render_template("query_page.html", results=results)


@bp.get("/")
def root():
    """Render analysis page at root path.

    :returns: Rendered HTML page.
    """
    results = _load_card_files()
    return render_template("query_page.html", results=results)


@bp.post("/pull-data")
def pull_data():
    """Trigger scrape → load with busy-state protection.

    Honors JSON via ``Accept: application/json``.

    :returns: Flask response. Returns 409 when busy.
    """
    wants_json = "application/json" in (request.headers.get("Accept") or "")

    # Busy-state
    if _pull_lock.locked():
        if wants_json:
            return jsonify({"busy": True}), 409
        flash("A pull is already running. Try again shortly.", "info")
        return redirect(url_for("main.index"))

    # Not busy: run once
    with _pull_lock:
        try:
            stats = svc_pull()
            if wants_json:
                return jsonify({"ok": True, "stats": stats}), 200
            flash(
                f"Pull complete: attempted {stats['attempted']}, "
                f"inserted {stats['inserted']}, skipped {stats['skipped']}.",
                "success",
            )
            return redirect(url_for("main.index"))
        except Exception as e:
            if wants_json:
                return jsonify({"ok": False, "error": str(e)}), 500
            flash(f"Pull failed: {e}", "error")
            return redirect(url_for("main.index"))


@bp.post("/update-analysis")
def update_analysis():
    """Regenerate analysis card files from saved queries.

    Honors JSON via ``Accept: application/json``.

    :returns: Flask response. Returns 409 when busy.
    """
    wants_json = "application/json" in (request.headers.get("Accept") or "")

    # Busy-state
    if _pull_lock.locked():
        if wants_json:
            return jsonify({"busy": True}), 409
        flash("Busy pulling data; update skipped.", "warning")
        return redirect(url_for("main.index"))

    # Not busy: run analysis
    try:
        out = analysis_to_files()
        if wants_json:
            return jsonify({"ok": True, "written": out.get("written", 0)}), 200
        flash(f"Analysis updated: wrote {out['written']} cards.", "success")
        return redirect(url_for("main.index"))
    except Exception as e:
        if wants_json:
            return jsonify({"ok": False, "error": str(e)}), 500
        flash(f"Update failed: {e}", "error")
        return redirect(url_for("main.index"))
