# module_3/scripts/ping_db.py (or wherever yours is)
from data.psych_connect import get_conn

def main():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user, current_database();")
        print(cur.fetchone())
        cur.execute("SELECT COUNT(*) FROM applicants;")
        print(cur.fetchone())

if __name__ == "__main__":
    main()
