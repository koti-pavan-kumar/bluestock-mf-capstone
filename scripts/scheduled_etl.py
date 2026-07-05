"""
scripts/scheduled_etl.py
--------------------------
Bonus B1 — Bluestock Fintech Mutual Fund Analytics Capstone

Scheduled ETL script that auto-fetches live NAV from mfapi.in and
updates the SQLite database. Designed to run every weekday at 8 PM IST
via cron (Linux/Mac) or Task Scheduler (Windows).

HOW TO SCHEDULE:
----------------
Linux / Mac (cron):
  Run: crontab -e
  Add: 0 20 * * 1-5 /usr/bin/python3 /path/to/scripts/scheduled_etl.py

Windows (Task Scheduler):
  1. Open Task Scheduler -> Create Basic Task
  2. Trigger: Daily, repeat Mon-Fri at 8:00 PM
  3. Action: Start a program -> python.exe
  4. Arguments: C:\\path\\to\\scripts\\scheduled_etl.py

The script logs every run to logs/etl_scheduler.log with timestamps,
so you always have an audit trail of when data was last updated.
"""

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "etl_scheduler.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Schemes to fetch — same 6 as Day 1 task
SCHEMES = {
    125497: "HDFC_Top_100_Direct",
    119551: "SBI_Bluechip",
    120503: "ICICI_Bluechip",
    118632: "Nippon_Large_Cap",
    119092: "Axis_Bluechip",
    120841: "Kotak_Bluechip",
}

BASE_URL = "https://api.mfapi.in/mf/{code}"


def is_weekday() -> bool:
    """Return True if today is Monday-Friday."""
    return datetime.now().weekday() < 5


def fetch_latest_nav(scheme_code: int) -> dict | None:
    """Fetch only the most recent NAV entry for a scheme."""
    url = BASE_URL.format(code=scheme_code)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        latest = data.get("data", [{}])[0]
        return {
            "scheme_code": scheme_code,
            "date": latest.get("date"),
            "nav": latest.get("nav"),
            "scheme_name": data.get("meta", {}).get("scheme_name", ""),
        }
    except Exception as exc:
        log.error(f"Failed to fetch scheme {scheme_code}: {exc}")
        return None


def update_database(nav_records: list[dict]) -> None:
    """Append fresh NAV records to the SQLite database."""
    try:
        import pandas as pd
        from sqlalchemy import create_engine, text

        db_path = BASE_DIR / "data" / "db" / "bluestock_mf.db"
        if not db_path.exists():
            log.warning("Database not found — run run_pipeline.py first to build it.")
            return

        engine = create_engine(f"sqlite:///{db_path}")

        for record in nav_records:
            if not record:
                continue
            try:
                date_parsed = pd.to_datetime(record["date"], format="%d-%m-%Y")
                nav_val = float(record["nav"])
            except Exception:
                log.warning(f"Could not parse record: {record}")
                continue

            with engine.begin() as conn:
                # Check if this date already exists for this fund (avoid duplicates)
                existing = conn.execute(
                    text("SELECT 1 FROM fact_nav WHERE amfi_code=:code AND nav_date=:dt"),
                    {"code": record["scheme_code"], "dt": date_parsed.strftime("%Y-%m-%d")}
                ).fetchone()

                if existing:
                    log.info(f"  Already in DB: {record['scheme_code']} {date_parsed.date()}")
                else:
                    conn.execute(
                        text("""INSERT INTO fact_nav (amfi_code, nav_date, nav)
                                VALUES (:code, :dt, :nav)"""),
                        {"code": record["scheme_code"],
                         "dt": date_parsed.strftime("%Y-%m-%d"),
                         "nav": nav_val}
                    )
                    log.info(f"  Inserted: {record['scheme_code']} "
                             f"{date_parsed.date()} NAV={nav_val}")

    except Exception as exc:
        log.error(f"Database update failed: {exc}")


def main() -> None:
    log.info("=" * 60)
    log.info("SCHEDULED ETL — Bluestock Fintech NAV Updater")
    log.info(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    log.info("=" * 60)

    if not is_weekday():
        log.info("Today is a weekend — skipping NAV fetch.")
        return

    log.info(f"Fetching latest NAV for {len(SCHEMES)} schemes...")
    nav_records = []
    for code, name in SCHEMES.items():
        log.info(f"  Fetching {code} ({name})...")
        record = fetch_latest_nav(code)
        if record:
            nav_records.append(record)
            log.info(f"  OK: NAV = {record['nav']} on {record['date']}")

    log.info(f"Fetched {len(nav_records)}/{len(SCHEMES)} schemes successfully.")
    update_database(nav_records)

    log.info("Scheduled ETL complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
