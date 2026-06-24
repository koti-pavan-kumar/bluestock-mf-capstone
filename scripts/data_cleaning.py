"""
scripts/data_cleaning.py
--------------------------
Day 2 — Bluestock Fintech Mutual Fund Analytics Capstone

Cleans the three datasets flagged in the Day 2 task and writes the
cleaned versions to data/processed/:

1. 02_nav_history.csv -> clean_nav.csv
   - parse dates to datetime
   - sort by amfi_code + date
   - forward-fill missing NAV (reindexed to a full business-day calendar
     per fund, so weekends/holidays that simply don't appear in the
     source data are filled rather than silently absent)
   - remove duplicates
   - validate NAV > 0

2. 08_investor_transactions.csv -> clean_transactions.csv
   - standardise transaction_type values
   - validate amount_inr > 0
   - check kyc_status against expected enum
   - fix/parse transaction_date

3. 07_scheme_performance.csv -> clean_performance.csv
   - validate return columns are numeric
   - flag negative Sharpe ratios
   - check expense_ratio_pct is within the expected 0.1%-2.5% range

Each step prints a short before/after summary so cleaning decisions are
auditable, and writes a consolidated cleaning log to reports/.

Usage (run from project root):
    python scripts/data_cleaning.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"

for d in (PROCESSED_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

EXPENSE_RATIO_MIN = 0.1
EXPENSE_RATIO_MAX = 2.5
VALID_TRANSACTION_TYPES = {"SIP", "Lumpsum", "Redemption"}
VALID_KYC_STATUS = {"Verified", "Pending"}

log_lines: list[str] = []


def log(msg: str) -> None:
    print(msg)
    log_lines.append(msg)


# ---------------------------------------------------------------------------
# 1. Clean NAV history
# ---------------------------------------------------------------------------

def clean_nav_history() -> pd.DataFrame:
    log("\n" + "=" * 70)
    log("CLEANING: 02_nav_history.csv")
    log("=" * 70)

    df = pd.read_csv(RAW_DIR / "02_nav_history.csv")
    rows_before = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        log(f"  Dropping {bad_dates} rows with unparseable dates")
        df = df.dropna(subset=["date"])

    dup_count = df.duplicated(subset=["amfi_code", "date"]).sum()
    if dup_count:
        log(f"  Removing {dup_count} duplicate (amfi_code, date) rows")
        df = df.drop_duplicates(subset=["amfi_code", "date"], keep="first")

    invalid_nav = (df["nav"] <= 0).sum()
    if invalid_nav:
        log(f"  Dropping {invalid_nav} rows with NAV <= 0")
        df = df[df["nav"] > 0]

    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # Reindex each fund to a full business-day calendar and forward-fill,
    # so holidays/weekends not present in the source data get a carried-
    # forward NAV instead of being silently missing from the time series.
    filled_frames = []
    total_filled = 0
    for code, group in df.groupby("amfi_code"):
        group = group.set_index("date")
        full_range = pd.bdate_range(group.index.min(), group.index.max())
        reindexed = group.reindex(full_range)
        filled_count = reindexed["nav"].isna().sum()
        total_filled += filled_count
        reindexed["nav"] = reindexed["nav"].ffill()
        reindexed["amfi_code"] = code
        reindexed = reindexed.reset_index().rename(columns={"index": "date"})
        filled_frames.append(reindexed)

    df = pd.concat(filled_frames, ignore_index=True)
    log(f"  Forward-filled {total_filled} missing business-day NAV values "
        f"(holidays/weekends not present in source)")

    df = df[["amfi_code", "date", "nav"]].sort_values(["amfi_code", "date"]).reset_index(drop=True)

    rows_after = len(df)
    log(f"  Rows before: {rows_before:,} | Rows after: {rows_after:,}")

    out_path = PROCESSED_DIR / "clean_nav.csv"
    df.to_csv(out_path, index=False)
    log(f"  Saved -> {out_path.relative_to(BASE_DIR)}")

    return df


# ---------------------------------------------------------------------------
# 2. Clean investor transactions
# ---------------------------------------------------------------------------

def clean_transactions() -> pd.DataFrame:
    log("\n" + "=" * 70)
    log("CLEANING: 08_investor_transactions.csv")
    log("=" * 70)

    df = pd.read_csv(RAW_DIR / "08_investor_transactions.csv")
    rows_before = len(df)

    # Standardise transaction_type: strip whitespace, fix casing
    df["transaction_type"] = df["transaction_type"].str.strip().str.title()
    # Normalise common variants to the canonical 3 values
    df["transaction_type"] = df["transaction_type"].replace({
        "Sip": "SIP", "Lump Sum": "Lumpsum", "Lump-Sum": "Lumpsum",
    })
    bad_types = df[~df["transaction_type"].isin(VALID_TRANSACTION_TYPES)]
    if len(bad_types):
        log(f"  Flagging {len(bad_types)} rows with unrecognised transaction_type: "
            f"{bad_types['transaction_type'].unique().tolist()}")
        df = df[df["transaction_type"].isin(VALID_TRANSACTION_TYPES)]
    else:
        log(f"  transaction_type values all valid: {sorted(VALID_TRANSACTION_TYPES)}")

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad_dates = df["transaction_date"].isna().sum()
    if bad_dates:
        log(f"  Dropping {bad_dates} rows with unparseable transaction_date")
        df = df.dropna(subset=["transaction_date"])

    invalid_amount = (df["amount_inr"] <= 0).sum()
    if invalid_amount:
        log(f"  Dropping {invalid_amount} rows with amount_inr <= 0")
        df = df[df["amount_inr"] > 0]
    else:
        log(f"  All amount_inr values > 0 (min: {df['amount_inr'].min()})")

    df["kyc_status"] = df["kyc_status"].str.strip().str.title()
    bad_kyc = df[~df["kyc_status"].isin(VALID_KYC_STATUS)]
    if len(bad_kyc):
        log(f"  Flagging {len(bad_kyc)} rows with unexpected kyc_status: "
            f"{bad_kyc['kyc_status'].unique().tolist()}")
    else:
        log(f"  kyc_status values all valid: {sorted(VALID_KYC_STATUS)}")

    dup_count = df.duplicated().sum()
    if dup_count:
        log(f"  Removing {dup_count} fully duplicated rows")
        df = df.drop_duplicates()

    rows_after = len(df)
    log(f"  Rows before: {rows_before:,} | Rows after: {rows_after:,}")

    out_path = PROCESSED_DIR / "clean_transactions.csv"
    df.to_csv(out_path, index=False)
    log(f"  Saved -> {out_path.relative_to(BASE_DIR)}")

    return df


# ---------------------------------------------------------------------------
# 3. Clean scheme performance
# ---------------------------------------------------------------------------

def clean_performance() -> pd.DataFrame:
    log("\n" + "=" * 70)
    log("CLEANING: 07_scheme_performance.csv")
    log("=" * 70)

    df = pd.read_csv(RAW_DIR / "07_scheme_performance.csv")
    rows_before = len(df)

    numeric_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
                     "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
                     "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
                     "expense_ratio_pct"]
    non_numeric_total = 0
    for col in numeric_cols:
        before_na = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        after_na = df[col].isna().sum()
        non_numeric_total += (after_na - before_na)
    if non_numeric_total:
        log(f"  Found {non_numeric_total} non-numeric values across return/risk columns")
    else:
        log(f"  All return/risk columns ({len(numeric_cols)}) are valid numeric")

    neg_sharpe = df[df["sharpe_ratio"] < 0]
    if len(neg_sharpe):
        log(f"  FLAGGED: {len(neg_sharpe)} funds with negative Sharpe ratio: "
            f"{neg_sharpe['scheme_name'].tolist()}")
    else:
        log("  No funds with negative Sharpe ratio")

    out_of_range = df[(df["expense_ratio_pct"] < EXPENSE_RATIO_MIN) |
                       (df["expense_ratio_pct"] > EXPENSE_RATIO_MAX)]
    if len(out_of_range):
        log(f"  FLAGGED: {len(out_of_range)} funds with expense_ratio_pct outside "
            f"{EXPENSE_RATIO_MIN}-{EXPENSE_RATIO_MAX}% range: "
            f"{out_of_range['scheme_name'].tolist()}")
    else:
        log(f"  All expense_ratio_pct values within {EXPENSE_RATIO_MIN}-{EXPENSE_RATIO_MAX}% range")

    rows_after = len(df)
    log(f"  Rows before: {rows_before:,} | Rows after: {rows_after:,}")

    out_path = PROCESSED_DIR / "clean_performance.csv"
    df.to_csv(out_path, index=False)
    log(f"  Saved -> {out_path.relative_to(BASE_DIR)}")

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log("=" * 70)
    log("DAY 2 — DATA CLEANING")
    log("Bluestock Fintech Mutual Fund Analytics Capstone")
    log("=" * 70)

    clean_nav_history()
    clean_transactions()
    clean_performance()

    log_path = REPORTS_DIR / "day2_cleaning_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    log(f"\n[OK] Cleaning log written to {log_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
