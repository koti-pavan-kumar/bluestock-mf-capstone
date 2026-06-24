"""
scripts/load_to_sqlite.py
---------------------------
Day 2 — Bluestock Fintech Mutual Fund Analytics Capstone

Builds bluestock_mf.db (SQLite) from the cleaned CSVs in data/processed/
and the raw dimension/fact sources in data/raw/, following the star
schema defined in sql/schema.sql.

Tables loaded:
  dim_fund          <- data/raw/01_fund_master.csv
  dim_date          <- generated from min/max dates in clean_nav.csv
  fact_nav          <- data/processed/clean_nav.csv (+ computed daily_return_pct)
  fact_transactions <- data/processed/clean_transactions.csv
  fact_performance  <- data/processed/clean_performance.csv
  fact_aum          <- data/raw/03_aum_by_fund_house.csv

After loading, verifies row counts match source CSVs and prints a summary.

Usage (run from project root):
    python scripts/load_to_sqlite.py
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_DIR = BASE_DIR / "data" / "db"
SQL_DIR = BASE_DIR / "sql"
REPORTS_DIR = BASE_DIR / "reports"

DB_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "bluestock_mf.db"

verification_rows = []


def build_dim_date(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Generate a date dimension spanning the full NAV history range."""
    dates = pd.date_range(nav_df["date"].min(), nav_df["date"].max(), freq="D")
    dim_date = pd.DataFrame({"date_id": dates.strftime("%Y-%m-%d")})
    dim_date["year"] = dates.year
    dim_date["month"] = dates.month
    dim_date["quarter"] = dates.quarter
    dim_date["day_of_week"] = dates.dayofweek
    dim_date["is_weekday"] = (dates.dayofweek < 5).astype(int)
    return dim_date


def add_daily_return(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily_return_pct per fund: (nav_t / nav_t-1 - 1) * 100."""
    nav_df = nav_df.sort_values(["amfi_code", "date"]).copy()
    nav_df["daily_return_pct"] = (
        nav_df.groupby("amfi_code")["nav"].pct_change() * 100
    ).round(4)
    return nav_df


def main() -> None:
    print("=" * 70)
    print("LOAD TO SQLITE — bluestock_mf.db")
    print("=" * 70)

    # Fresh DB each run, so this script is safely re-runnable
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[INFO] Removed existing {DB_PATH.name} for a clean rebuild")

    engine = create_engine(f"sqlite:///{DB_PATH}")

    # Apply schema.sql first (CREATE TABLE statements, indexes, constraints).
    # Use sqlite3's executescript (via the raw DBAPI connection) rather than
    # splitting on ";" ourselves, since a naive split breaks on the "--"
    # comments in schema.sql.
    schema_sql = (SQL_DIR / "schema.sql").read_text()
    raw_conn = engine.raw_connection()
    try:
        raw_conn.executescript(schema_sql)
        raw_conn.commit()
    finally:
        raw_conn.close()
    print("[OK] Schema applied from sql/schema.sql")

    # ---- dim_fund ---------------------------------------------------------
    fund_master = pd.read_csv(RAW_DIR / "01_fund_master.csv")
    fund_master.to_sql("dim_fund", engine, if_exists="append", index=False)
    verification_rows.append(("dim_fund", "01_fund_master.csv",
                               len(fund_master), len(fund_master)))
    print(f"[OK] dim_fund loaded: {len(fund_master)} rows")

    # ---- fact_nav (+ dim_date generated from its range) --------------------
    nav = pd.read_csv(PROCESSED_DIR / "clean_nav.csv", parse_dates=["date"])
    dim_date = build_dim_date(nav)
    dim_date.to_sql("dim_date", engine, if_exists="append", index=False)
    print(f"[OK] dim_date loaded: {len(dim_date)} rows "
          f"({nav['date'].min().date()} to {nav['date'].max().date()})")

    nav = add_daily_return(nav)
    nav_out = nav.copy()
    nav_out["date"] = nav_out["date"].dt.strftime("%Y-%m-%d")
    nav_out = nav_out.rename(columns={"date": "nav_date"})
    nav_out[["amfi_code", "nav_date", "nav", "daily_return_pct"]].to_sql(
        "fact_nav", engine, if_exists="append", index=False
    )
    source_nav_rows = len(pd.read_csv(PROCESSED_DIR / "clean_nav.csv"))
    verification_rows.append(("fact_nav", "clean_nav.csv",
                               source_nav_rows, len(nav_out)))
    print(f"[OK] fact_nav loaded: {len(nav_out)} rows")

    # ---- fact_transactions --------------------------------------------------
    tx = pd.read_csv(PROCESSED_DIR / "clean_transactions.csv")
    tx_out = tx.rename(columns={"transaction_date": "transaction_date"}).copy()
    tx_cols = ["investor_id", "transaction_date", "amfi_code", "transaction_type",
               "amount_inr", "state", "city", "city_tier", "age_group", "gender",
               "annual_income_lakh", "payment_mode", "kyc_status"]
    tx_out[tx_cols].to_sql("fact_transactions", engine, if_exists="append", index=False)
    verification_rows.append(("fact_transactions", "clean_transactions.csv",
                               len(tx), len(tx_out)))
    print(f"[OK] fact_transactions loaded: {len(tx_out)} rows")

    # ---- fact_performance -----------------------------------------------------
    perf = pd.read_csv(PROCESSED_DIR / "clean_performance.csv")
    perf_cols = ["amfi_code", "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
                 "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio", "sortino_ratio",
                 "std_dev_ann_pct", "max_drawdown_pct", "aum_crore", "expense_ratio_pct",
                 "morningstar_rating", "risk_grade"]
    perf[perf_cols].to_sql("fact_performance", engine, if_exists="append", index=False)
    verification_rows.append(("fact_performance", "clean_performance.csv",
                               len(perf), len(perf)))
    print(f"[OK] fact_performance loaded: {len(perf)} rows")

    # ---- fact_aum -----------------------------------------------------------
    aum = pd.read_csv(RAW_DIR / "03_aum_by_fund_house.csv")
    aum_out = aum.rename(columns={"date": "report_date"})
    aum_out.to_sql("fact_aum", engine, if_exists="append", index=False)
    verification_rows.append(("fact_aum", "03_aum_by_fund_house.csv",
                               len(aum), len(aum_out)))
    print(f"[OK] fact_aum loaded: {len(aum_out)} rows")

    # ---- Verification -------------------------------------------------------
    print("\n" + "=" * 70)
    print("ROW COUNT VERIFICATION")
    print("=" * 70)
    verification_df = pd.DataFrame(
        verification_rows,
        columns=["table", "source_file", "source_rows", "loaded_rows"]
    )
    verification_df["match"] = verification_df["source_rows"] == verification_df["loaded_rows"]
    print(verification_df.to_string(index=False))

    all_match = verification_df["match"].all()
    print(f"\n{'All row counts match source CSVs.' if all_match else '[WARNING] Row count mismatch detected!'}")

    report_path = REPORTS_DIR / "day2_load_verification.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("DAY 2 — SQLITE LOAD VERIFICATION\n")
        f.write("=" * 70 + "\n\n")
        f.write(verification_df.to_string(index=False))
        f.write(f"\n\nDatabase file: {DB_PATH.relative_to(BASE_DIR)}\n")
        f.write(f"Database size: {DB_PATH.stat().st_size / 1024:.1f} KB\n")

    print(f"\n[OK] Verification report written to {report_path.relative_to(BASE_DIR)}")
    print(f"[OK] Database created at {DB_PATH.relative_to(BASE_DIR)} "
          f"({DB_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
