"""
scripts/data_ingestion.py
--------------------------
Day 1 — Bluestock Fintech Mutual Fund Analytics Capstone

Loads all 10 provided datasets from data/raw/, and for each one:
  - prints .shape, .dtypes, .head()
  - runs anomaly checks (nulls, duplicates, constant columns,
    out-of-range values, bad dates)

Also performs the AMFI code validation step required by Day 1:
  - confirms every amfi_code in 01_fund_master.csv exists in the
    live-fetched NAV history (02_nav_history.csv AND the 6 schemes
    pulled fresh from mfapi.in by live_nav_fetch.py)

Writes a short data quality summary to reports/day1_data_quality_summary.txt

Usage (run from project root):
    python scripts/data_ingestion.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent  # project root
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"

for d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# The 10 official provided datasets, in spec order
PROVIDED_DATASETS = [
    "01_fund_master.csv",
    "02_nav_history.csv",
    "03_aum_by_fund_house.csv",
    "04_monthly_sip_inflows.csv",
    "05_category_inflows.csv",
    "06_industry_folio_count.csv",
    "07_scheme_performance.csv",
    "08_investor_transactions.csv",
    "09_portfolio_holdings.csv",
    "10_benchmark_indices.csv",
]

# Columns (by substring match) that should never be negative
NON_NEGATIVE_HINTS = ("nav", "price", "amount", "aum", "value", "volume",
                       "units", "weight_pct", "expense_ratio", "inflow")

# mfapi.in live-fetch outputs land in the same data/raw/ folder but are
# excluded from the "10 provided datasets" loop (handled separately).
NAV_FETCH_SUFFIX = "_nav.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def inspect_dataframe(df: pd.DataFrame, name: str) -> dict:
    print("\n" + "-" * 70)
    print(f"DATASET: {name}")
    print("-" * 70)

    print(f"\nShape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    print("\nDtypes:")
    print(df.dtypes.to_string())

    print("\nHead:")
    print(df.head().to_string())

    anomalies = []

    null_counts = df.isnull().sum()
    nulls = null_counts[null_counts > 0]
    if not nulls.empty:
        pct = (nulls / len(df) * 100).round(2)
        for col in nulls.index:
            anomalies.append(
                f"Column '{col}' has {nulls[col]:,} nulls ({pct[col]}% of rows)"
            )

    dup_count = df.duplicated().sum()
    if dup_count > 0:
        anomalies.append(f"{dup_count:,} fully duplicated rows found")

    for col in df.columns:
        if df[col].nunique(dropna=False) == 1:
            anomalies.append(f"Column '{col}' is constant (only 1 unique value)")

    for col in df.select_dtypes(include=[np.number]).columns:
        col_lower = col.lower()
        if any(k in col_lower for k in NON_NEGATIVE_HINTS):
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                anomalies.append(
                    f"Column '{col}' has {neg_count:,} negative values "
                    f"(unexpected for a value/price field)"
                )

    for col in df.columns:
        if "date" in col.lower() or col.lower() == "month":
            parsed_iso = pd.to_datetime(df[col], errors="coerce")
            bad_iso = parsed_iso.isna().sum() - df[col].isna().sum()
            if bad_iso == 0:
                bad = 0
            else:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parsed_dayfirst = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                bad_dayfirst = parsed_dayfirst.isna().sum() - df[col].isna().sum()
                bad = min(bad_iso, bad_dayfirst)
            if bad > 0:
                anomalies.append(
                    f"Column '{col}' has {bad:,} values that don't parse as dates"
                )

    if anomalies:
        print("\nAnomalies detected:")
        for a in anomalies:
            print(f"  - {a}")
    else:
        print("\nNo anomalies detected.")

    return {
        "dataset": name,
        "rows": df.shape[0],
        "columns": df.shape[1],
        "null_columns": len(nulls) if not nulls.empty else 0,
        "duplicate_rows": int(dup_count),
        "anomaly_count": len(anomalies),
        "anomalies": "; ".join(anomalies) if anomalies else "None",
    }


def validate_amfi_codes() -> str:
    """
    Cross-check every amfi_code in 01_fund_master.csv against:
      (a) 02_nav_history.csv (the provided historical dataset)
      (b) the live NAV CSVs fetched fresh from mfapi.in (if present)
    """
    master_path = RAW_DIR / "01_fund_master.csv"
    nav_path = RAW_DIR / "02_nav_history.csv"

    if not master_path.exists() or not nav_path.exists():
        msg = "Could not run AMFI validation — 01_fund_master.csv or 02_nav_history.csv missing."
        print(f"\n[WARN] {msg}")
        return msg

    fund_master = pd.read_csv(master_path)
    nav_history = pd.read_csv(nav_path)

    master_codes = set(pd.to_numeric(fund_master["amfi_code"], errors="coerce").dropna().astype(int))
    nav_codes = set(pd.to_numeric(nav_history["amfi_code"], errors="coerce").dropna().astype(int))

    missing_in_nav = master_codes - nav_codes
    extra_in_nav = nav_codes - master_codes

    lines = [
        "Cross-check: 01_fund_master.csv vs 02_nav_history.csv (provided dataset)",
        f"  Total amfi_codes in fund_master: {len(master_codes)}",
        f"  Total amfi_codes in nav_history:  {len(nav_codes)}",
        f"  Codes in fund_master MISSING from nav_history: {len(missing_in_nav)}"
        + (f" -> {sorted(missing_in_nav)}" if missing_in_nav else ""),
        f"  Codes in nav_history not in fund_master: {len(extra_in_nav)}"
        + (f" -> {sorted(extra_in_nav)}" if extra_in_nav else ""),
    ]

    # Also cross-check against the 6 live-fetched schemes, if available
    live_nav_files = sorted(RAW_DIR.glob(f"*{NAV_FETCH_SUFFIX}"))
    if live_nav_files:
        live_df = pd.concat([pd.read_csv(f) for f in live_nav_files], ignore_index=True)
        live_codes = set(pd.to_numeric(live_df["scheme_code"], errors="coerce").dropna().astype(int))
        missing_live = live_codes - master_codes

        lines.append("")
        lines.append("Cross-check: live mfapi.in fetch (6 schemes) vs fund_master")
        lines.append(f"  Live-fetched scheme codes: {sorted(live_codes)}")
        lines.append(
            f"  Live codes NOT found in fund_master: {len(missing_live)}"
            + (f" -> {sorted(missing_live)}" if missing_live else "")
        )
    else:
        lines.append("")
        lines.append("[INFO] No live mfapi.in fetch files found yet "
                      "(run scripts/live_nav_fetch.py first to include this check).")

    summary = "\n".join(lines)
    print("\n" + "=" * 70)
    print("AMFI CODE VALIDATION")
    print("=" * 70)
    print(summary)
    return summary


def domain_summary(fund_master: pd.DataFrame) -> str:
    """Task 6: print unique fund houses, categories, sub-categories, risk grades."""
    lines = []
    lines.append(f"Unique fund houses ({fund_master['fund_house'].nunique()}): "
                  f"{sorted(fund_master['fund_house'].unique())}")
    lines.append(f"Unique categories ({fund_master['category'].nunique()}): "
                  f"{sorted(fund_master['category'].unique())}")
    lines.append(f"Unique sub-categories ({fund_master['sub_category'].nunique()}): "
                  f"{sorted(fund_master['sub_category'].unique())}")
    lines.append(f"Unique risk categories ({fund_master['risk_category'].nunique()}): "
                  f"{sorted(fund_master['risk_category'].unique())}")
    summary = "\n".join(lines)
    print("\n" + "=" * 70)
    print("FUND MASTER — DOMAIN SUMMARY (Task 6)")
    print("=" * 70)
    print(summary)
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("DATA INGESTION — Bluestock Fintech Mutual Fund Analytics Capstone")
    print("=" * 70)

    quality_rows = []
    fund_master_df = None

    for filename in PROVIDED_DATASETS:
        csv_path = RAW_DIR / filename
        if not csv_path.exists():
            print(f"\n[MISSING] {filename} not found in {RAW_DIR}")
            quality_rows.append({
                "dataset": filename, "rows": 0, "columns": 0,
                "null_columns": 0, "duplicate_rows": 0,
                "anomaly_count": 1, "anomalies": "FILE MISSING",
            })
            continue

        df = pd.read_csv(csv_path)
        if filename == "01_fund_master.csv":
            fund_master_df = df

        report = inspect_dataframe(df, filename)
        quality_rows.append(report)

    domain_summary_text = ""
    if fund_master_df is not None:
        domain_summary_text = domain_summary(fund_master_df)

    amfi_summary = validate_amfi_codes()

    # ---- Write data quality summary report -------------------------------
    summary_path = REPORTS_DIR / "day1_data_quality_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("DAY 1 — DATA QUALITY SUMMARY\n")
        f.write("Bluestock Fintech Mutual Fund Analytics Capstone\n")
        f.write("=" * 70 + "\n\n")

        f.write("PROVIDED DATASETS (10)\n")
        f.write("-" * 70 + "\n")
        quality_df = pd.DataFrame(quality_rows)
        f.write(quality_df.to_string(index=False))
        f.write("\n\n")

        f.write("FUND MASTER — DOMAIN SUMMARY\n")
        f.write("-" * 70 + "\n")
        f.write(domain_summary_text if domain_summary_text else "Not available.\n")
        f.write("\n\n")

        f.write("AMFI CODE VALIDATION\n")
        f.write("-" * 70 + "\n")
        f.write(amfi_summary)
        f.write("\n")

    print(f"\n[OK] Data quality summary written to {summary_path}")


if __name__ == "__main__":
    main()
