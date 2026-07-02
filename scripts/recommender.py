"""
recommender.py
--------------
Day 6 - Bluestock Fintech Mutual Fund Analytics Capstone

Simple fund recommender: given a risk appetite level, returns the
top 3 funds by Sharpe ratio within the matching SEBI risk category.

Valid risk appetite values:
  Low / Moderate / Moderately High / High / Very High

Usage:
    python recommender.py
    python recommender.py --risk High
    python recommender.py --risk "Very High"
"""

import argparse
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROCESSED = BASE_DIR / "data" / "processed"
RAW = BASE_DIR / "data" / "raw"


def load_data() -> pd.DataFrame:
    perf = pd.read_csv(PROCESSED / "clean_performance.csv")
    fm = pd.read_csv(RAW / "01_fund_master.csv")
    return perf.merge(fm[["amfi_code", "risk_category"]], on="amfi_code")


def recommend(risk_appetite: str, n: int = 3) -> pd.DataFrame:
    df = load_data()
    valid = sorted(df["risk_category"].unique().tolist())
    if risk_appetite not in valid:
        print(f"Invalid risk appetite '{risk_appetite}'.")
        print(f"Choose from: {valid}")
        return pd.DataFrame()

    result = (
        df[df["risk_category"] == risk_appetite]
        .nlargest(n, "sharpe_ratio")
        [["scheme_name", "risk_category", "sharpe_ratio",
          "return_3yr_pct", "max_drawdown_pct"]]
        .reset_index(drop=True)
    )
    result.index += 1
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mutual Fund Recommender")
    parser.add_argument(
        "--risk", default=None,
        help="Risk appetite level: Low / Moderate / Moderately High / High / Very High"
    )
    args = parser.parse_args()

    if args.risk:
        print(f"\nTop 3 funds for '{args.risk}' risk appetite:")
        result = recommend(args.risk)
        if not result.empty:
            print(result.to_string())
    else:
        for appetite in ["Low", "Moderate", "Moderately High", "High", "Very High"]:
            print(f"\n{'='*60}")
            print(f"Top 3 funds for {appetite.upper()} risk appetite:")
            result = recommend(appetite)
            if not result.empty:
                print(result.to_string())
