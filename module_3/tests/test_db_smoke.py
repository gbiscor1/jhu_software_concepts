# tests/test_db_smoke.py
from data.psych_connect import get_conn

def test_can_query_current_db(db_cursor):
    db_cursor.execute("SELECT current_user, current_database();")
    user, db = db_cursor.fetchone()
    assert user == "app_user"
    assert db == "gradcafe_db"

def test_applicants_table_exists_and_columns(db_cursor):
    db_cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='applicants'
        ORDER BY ordinal_position;
    """)
    cols = [r[0] for r in db_cursor.fetchall()]
    expected = [
        "p_id","program","comments","date_added","url","status","term",
        "us_or_international","gpa","gre","gre_v","gre_aw","degree",
        "llm_generated_program","llm_generated_university"
    ]
    assert cols == expected

def test_applicants_count_is_nonnegative(db_cursor):
    db_cursor.execute("SELECT COUNT(*) FROM applicants;")
    (count,) = db_cursor.fetchone()
    assert count >= 0
