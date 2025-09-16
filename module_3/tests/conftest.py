# tests/conftest.py
from __future__ import annotations
import pytest
from data.psych_connect import get_conn

@pytest.fixture(scope="function")
def db_conn():
    """Open a DB connection for a test and close it after."""
    conn = get_conn()          # uses .env
    try:
        yield conn
    finally:
        conn.close()

@pytest.fixture(scope="function")
def db_cursor(db_conn):
    """Yield a cursor tied to the test's connection."""
    with db_conn.cursor() as cur:
        yield cur
