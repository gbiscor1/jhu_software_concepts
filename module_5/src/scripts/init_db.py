"""Database initialization and optional seeding."""

from __future__ import annotations
from pathlib import Path
import json

from ..data.psych_connect import get_conn
from ..data.loader import load_applicants

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "schema" / "schema.sql"

# Default seed file search order
DEFAULT_SEED_FILES = [
    Path(__file__).resolve().parents[1] / "data" / "database_bulk.json",
    Path("data/llm_extend_applicant_data.json"),
    Path("data/applicant_data.cleaned.json"),
]


def apply_schema() -> None:
    """Apply SQL schema from :data:`SCHEMA_PATH`."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
    print("Schema applied.")


def seed_from_json() -> None:
    """Seed database from the first existing path in :data:`DEFAULT_SEED_FILES`."""
    seed_path = next((p for p in DEFAULT_SEED_FILES if p.exists()), None)
    if not seed_path:
        print("No seed JSON found; skipping initial load.")
        return
    print(f"Seeding from {seed_path} ...")
    records = json.loads(seed_path.read_text(encoding="utf-8"))
    stats = load_applicants(records)
    print({"seeded_from": str(seed_path), **stats})


def main() -> None:
    """Run schema application followed by optional seeding."""
    apply_schema()
    seed_from_json()


if __name__ == "__main__":
    main()
