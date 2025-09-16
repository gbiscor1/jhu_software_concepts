from __future__ import annotations
import os, argparse, json, pathlib, sys

# ---- tiny .env loader (no extra deps) ---------------------------------
def load_env(env_path: str) -> None:
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Missing .env at {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
# -----------------------------------------------------------------------

def parse_bulk_file(path: pathlib.Path):
    """Accepts JSON list, {'records': [...]}, or JSONL."""
    text = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict) and "records" in obj:
            return obj["records"]
        # fall through to error
        raise ValueError("Unexpected JSON structure in bulk file.")
    except json.JSONDecodeError:
        # JSON Lines fallback
        return [json.loads(line) for line in text.splitlines() if line.strip()]

def main():
    here = pathlib.Path(__file__).resolve()
    module3 = here.parents[1]           # .../module_3
    repo    = module3.parent            # .../jhu_sc

    ap = argparse.ArgumentParser(description="Drop applicants, apply schema, bulk load JSON")
    ap.add_argument("--schema", default=str(module3 / "sql" / "schema" / "schema.sql"))
    ap.add_argument("--bulk",   default=str(module3 / "data" / "database_bulk.json"))
    ap.add_argument("--env",    default=str(module3 / ".env"))
    args = ap.parse_args()

    load_env(args.env)

    # Make data.* imports work
    sys.path.insert(0, str(module3))

    from data.psych_connect import get_conn
    from data.loader import load_applicants

    # 1) Drop + apply schema (run CREATE TABLE before indexes if order differs)
    schema_sql = pathlib.Path(args.schema).read_text(encoding="utf-8")
    stmts = [s.strip() for s in schema_sql.split(";") if s.strip()]
    tables = [s for s in stmts if "create table" in s.lower()]
    others = [s for s in stmts if "create table" not in s.lower()]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS applicants CASCADE;")
            for s in tables: cur.execute(s + ";")
            for s in others: cur.execute(s + ";")
        conn.commit()
    print("Schema reset complete.")

    # 2) Bulk load JSON via your loader
    bulk_path = pathlib.Path(args.bulk)
    data = parse_bulk_file(bulk_path)
    print(f"Parsed {len(data)} rows from {bulk_path.name}")

    stats = load_applicants(data)  # returns dict: attempted/inserted/skipped
    print(f"Bulk load complete: attempted={stats['attempted']}, inserted={stats['inserted']}, skipped={stats['skipped']}")

if __name__ == "__main__":
    main()