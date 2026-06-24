"""
scripts/run_queries.py
-------------------------
Day 2 — runs every query in sql/queries.sql against data/db/bluestock_mf.db
and prints the results. Useful when the sqlite3 command-line tool isn't
installed (e.g. on Windows by default) — this uses Python's built-in
sqlite3 module instead, so no extra installation is needed.

Usage (run from project root):
    python scripts/run_queries.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"
QUERIES_PATH = BASE_DIR / "sql" / "queries.sql"


def load_statements() -> list[str]:
    sql = QUERIES_PATH.read_text()
    # Strip comment lines (anything starting with --) then split on ;
    code_lines = [line for line in sql.split("\n") if not line.strip().startswith("--")]
    code_only = "\n".join(code_lines)
    return [s.strip() for s in code_only.split(";") if s.strip()]


def main() -> None:
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found at {DB_PATH}")
        print("Run 'python scripts/load_to_sqlite.py' first.")
        return

    conn = sqlite3.connect(DB_PATH)
    statements = load_statements()

    print("=" * 70)
    print(f"RUNNING {len(statements)} QUERIES FROM sql/queries.sql")
    print("=" * 70)

    ok_count = 0
    for i, stmt in enumerate(statements, 1):
        print(f"\n--- Query {i} ---")
        try:
            cursor = conn.execute(stmt)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            print(" | ".join(cols))
            for row in rows[:5]:
                print(row)
            if len(rows) > 5:
                print(f"... ({len(rows)} total rows)")
            else:
                print(f"({len(rows)} total rows)")
            ok_count += 1
        except Exception as e:
            print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print(f"{ok_count}/{len(statements)} queries ran successfully")
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()
