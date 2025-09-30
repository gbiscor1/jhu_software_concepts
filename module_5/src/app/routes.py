"""HTTP routes and UI endpoints."""

# module_4/app/routes.py
from __future__ import annotations

# stdlib
import json
import threading
from pathlib import Path
from typing import Any, Dict

# third-party
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
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
    """Trigger data pull/scrape/load. Return JSON on JSON requests."""
    wants_json = "application/json" in (request.headers.get("Accept") or "")
    try:
        with _pull_lock:
            stats = svc_pull()
    except RuntimeError:
        if wants_json:
            # add busy=True here
            return jsonify(ok=False, busy=True, error="busy"), 409
        return redirect(url_for("main.index"), code=303)

    if wants_json:
        return jsonify(
            ok=True,
            scraped=stats.get("scraped"),
            cleaned=stats.get("cleaned"),
            to_load=stats.get("to_load"),
        ), 200

    return redirect(url_for("main.index"), code=302)


@bp.post("/update-analysis")
def update_analysis():
    """Re-run saved queries and refresh analysis files. Return JSON on JSON requests."""
    wants_json = "application/json" in (request.headers.get("Accept") or "")

    try:
        with _pull_lock:
            out = analysis_to_files()
    except Exception as exc:  # noqa: BLE001 (test drives error path)
        if wants_json:
            return jsonify(ok=False, error=str(exc)), 500
        # Let Flask show its error page in HTML mode.
        raise

    if wants_json:
        return jsonify(ok=True, **out), 200

    return redirect(url_for("main.index"), code=303)
