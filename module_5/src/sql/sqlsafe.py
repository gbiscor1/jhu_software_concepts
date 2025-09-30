"""
Helpers for safe SQL composition with psycopg (v3 preferred, v2 fallback).

Expose:
- sql: psycopg composables module
- ident(name): safe identifier
- col_list(cols): comma-separated identifiers
- placeholders(n): "(%s, %s, ...)"
- order_by_safe(requested, direction, allowed): validated ORDER BY
- limit_clause(limit, *, min_limit=1, max_limit=1000): clamped LIMIT
"""
from __future__ import annotations
from typing import Iterable, Optional, Set

from psycopg import sql


# --- simple helpers ---

def ident(name: str) -> sql.Identifier:
    "Return a safe SQL identifier; caller must validate name via allow-list."
    return sql.Identifier(name)

def col_list(columns: Iterable[str]) -> sql.SQL:
    "Return a comma-separated identifier list."
    idents = [ident(c) for c in columns]
    if not idents:
        return sql.SQL("")
    return sql.SQL(", ").join(idents)

def placeholders(n: int) -> sql.SQL:
    "Return a parenthesized placeholders string: (%s, %s, ...)."
    if n <= 0:
        return sql.SQL("()")
    return sql.SQL("(") + sql.SQL(", ").join([sql.SQL("%s")] * n) + sql.SQL(")")

# --- validated clauses ---

def order_by_safe(
    requested: Optional[str],
    direction: Optional[str],
    allowed: Set[str],
) -> sql.SQL:
    """
    Build a safe ORDER BY. Returns empty SQL if requested not in allow-list.
    direction in {'ASC', 'DESC'}; defaults to ASC.
    """
    if not requested or requested not in allowed:
        return sql.SQL("")
    dir_norm = (direction or "ASC").upper()
    if dir_norm not in {"ASC", "DESC"}:
        dir_norm = "ASC"
    return sql.SQL(" ORDER BY {} {}").format(ident(requested), sql.SQL(dir_norm))

def limit_clause(limit: int | str | None, *, min_limit: int = 1, max_limit: int = 1000) -> sql.SQL:
    """Build a safe LIMIT clause. Clamps to [min_limit, max_limit]."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = max_limit
    n = max(min_limit, min(n, max_limit))
    return sql.SQL(f" LIMIT {n}")
