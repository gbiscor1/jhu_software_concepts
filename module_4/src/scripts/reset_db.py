# src/scripts/reset_db.py
"""
Reset/initialize the database schema for Module 4.

- It exposes a `main()` entrypoint so integration tests can import and call it.
- It reads a single SQL schema file and executes it via `get_conn()`.
- It accepts `--schema` and `--env` CLI options.
- Environment loading is best-effort and **non-fatal** if the `.env` file is missing.
- All external boundaries (env, DB connection) are easy to monkeypatch in tests.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import os
from typing import Optional

# Import in a way tests can monkeypatch at the module level:
#   monkeypatch.setattr(reset_db, "get_conn", fake_conn)
from src.data.psych_connect import get_conn  # noqa: PLC0415


# ---------- Module-level paths (tests can monkeypatch these) ----------
# Example layout: <repo_root>/src/scripts/reset_db.py
# parents[0] = scripts/, parents[1] = src/, parents[2] = repo root
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# Default schema file under version control. Tests commonly override this.
DEFAULT_SCHEMA: Path = REPO_ROOT / "src" / "sql" / "schema" / "schema.sql"

# Public module attributes that tests may monkeypatch:
SCHEMA_PATH: Path = DEFAULT_SCHEMA
SCHEMA_DIR: Path = DEFAULT_SCHEMA.parent  # optional: if a dir listing is ever needed
# ---------------------------------------------------------------------


def load_env(env_path: Optional[str]) -> None:
    """
    Best-effort loader for a simple KEY=VALUE `.env` file.

    - If `env_path` is None or the file doesn’t exist, this is a no-op.
    - Lines starting with `#` or without `=` are ignored.
    - Existing environment variables are not overridden (uses `setdefault`).

    Parameters
    ----------
    env_path : Optional[str]
        Path to a `.env` file; may be None.
    """
    if not env_path:
        return
    p = Path(env_path)
    if not p.exists():
        # Silent skip by design — tests often point at a throwaway file.
        return

    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


def apply_schema(schema_file: Path) -> int:
    """
    Execute the given SQL schema file against the database connection.

    Implementation notes
    --------------------
    * Reads the file once and executes it as a single statement via `cursor.execute`.
      (Your test’s fake cursor records this call so assertions can inspect it.)
    * Attempts `conn.commit()` but tolerates fakes that don’t implement it.

    Parameters
    ----------
    schema_file : Path
        Path to the SQL file to execute.

    Returns
    -------
    int
        Crude count of statements (based on `;`) for logging/testing convenience.
    """
    sql = Path(schema_file).read_text(encoding="utf-8")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        # Commit if available; fake conns in tests may not implement commit.
        try:
            conn.commit()  # type: ignore[attr-defined]
        except Exception:
            pass

    # Not exact, but helpful for a tiny summary.
    return sql.count(";") or 1


def main(argv: Optional[list[str]] = None) -> dict:
    """
    Command-line entrypoint.

    This function is also imported and called by tests. It:
      1) Parses `--schema` and `--env`.
      2) Loads environment (best-effort).
      3) Applies the schema.
      4) Prints and returns a small summary dict.

    Parameters
    ----------
    argv : Optional[list[str]]
        Optional argv vector (used by tests). If None, argparse uses sys.argv.

    Returns
    -------
    dict
        A summary payload (useful for tests and manual runs).
    """
    ap = argparse.ArgumentParser(
        description="Drop/create DB schema and (optionally) load seed data."
    )
    ap.add_argument(
        "--schema",
        default=str(SCHEMA_PATH),
        help="Path to schema.sql (default: module SCHEMA_PATH)",
    )
    ap.add_argument(
        "--env",
        default=None,
        help="Path to a .env file (optional; best-effort load).",
    )
    args = ap.parse_args(argv)

    load_env(args.env)
    statements = apply_schema(Path(args.schema))

    out = {"schema": str(args.schema), "statements": statements}
    print(out)
    return out


if __name__ == "__main__":
    # Allow running as a script: `python -m src.scripts.reset_db --schema ...`
    main()
