"""
live_nav_fetch.py
------------------
Day 1 — Mutual Fund Analytics Capstone (Bluestock Fintech Internship)

Fetches live/historical NAV data from the mfapi.in public API for 6 mutual
fund schemes and saves each response as a raw CSV under data/raw/.

mfapi.in returns the FULL NAV history for a scheme code, not just the
latest value — so this also gives you a ready-made time series dataset
for the EDA/trend-analysis stage of the capstone.

API docs: https://www.mfapi.in/
Endpoint: GET https://api.mfapi.in/mf/<scheme_code>
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://api.mfapi.in/mf/{code}"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Scheme code -> friendly name (as specified in the Day 1 task)
SCHEMES = {
    125497: "HDFC_Top_100_Direct",
    119551: "SBI_Bluechip",
    120503: "ICICI_Bluechip",
    118632: "Nippon_Large_Cap",
    119092: "Axis_Bluechip",
    120841: "Kotak_Bluechip",
}

REQUEST_TIMEOUT = 15  # seconds
RETRY_COUNT = 3
RETRY_BACKOFF = 2  # seconds, multiplied by attempt number


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------

def fetch_scheme_data(scheme_code: int):
    """Fetch raw JSON for a single scheme code, with basic retry handling."""
    url = BASE_URL.format(code=scheme_code)

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "SUCCESS" and "data" not in data:
                print(f"  [WARN] Unexpected response shape for {scheme_code}: "
                      f"{str(data)[:120]}")

            return data

        except requests.exceptions.RequestException as exc:
            print(f"  [ATTEMPT {attempt}/{RETRY_COUNT}] Failed for "
                  f"scheme {scheme_code}: {exc}")
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_BACKOFF * attempt)

    print(f"  [ERROR] Giving up on scheme {scheme_code} after "
          f"{RETRY_COUNT} attempts.")
    return None


def save_raw_json(scheme_code: int, friendly_name: str, payload: dict) -> None:
    """Persist the untouched API response as JSON for traceability."""
    json_path = RAW_DIR / f"{scheme_code}_{friendly_name}_raw.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def nav_json_to_dataframe(payload: dict, scheme_code: int,
                           friendly_name: str) -> pd.DataFrame:
    """Convert mfapi.in's nested JSON into a clean, typed DataFrame."""
    meta = payload.get("meta", {})
    records = payload.get("data", [])

    df = pd.DataFrame(records)

    if df.empty:
        print(f"  [WARN] No NAV records returned for {scheme_code}.")
        return df

    # mfapi.in returns date as DD-MM-YYYY and nav as a string
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    df["scheme_code"] = scheme_code
    df["scheme_name"] = meta.get("scheme_name", friendly_name)
    df["fund_house"] = meta.get("fund_house", "Unknown")
    df["scheme_category"] = meta.get("scheme_category", "Unknown")
    df["scheme_type"] = meta.get("scheme_type", "Unknown")

    # Sort oldest -> newest (mfapi.in returns newest first)
    df = df.sort_values("date").reset_index(drop=True)

    # Reorder columns for readability
    cols = ["date", "nav", "scheme_code", "scheme_name",
            "fund_house", "scheme_category", "scheme_type"]
    df = df[cols]

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("LIVE NAV FETCH — mfapi.in")
    print("=" * 70)

    summary_rows = []

    for scheme_code, friendly_name in SCHEMES.items():
        print(f"\nFetching scheme {scheme_code} ({friendly_name}) ...")
        payload = fetch_scheme_data(scheme_code)

        if payload is None:
            summary_rows.append({
                "scheme_code": scheme_code,
                "scheme_name": friendly_name,
                "status": "FAILED",
                "rows_fetched": 0,
                "date_range": None,
            })
            continue

        save_raw_json(scheme_code, friendly_name, payload)

        df = nav_json_to_dataframe(payload, scheme_code, friendly_name)

        if df.empty:
            summary_rows.append({
                "scheme_code": scheme_code,
                "scheme_name": friendly_name,
                "status": "EMPTY",
                "rows_fetched": 0,
                "date_range": None,
            })
            continue

        csv_path = RAW_DIR / f"{scheme_code}_{friendly_name}_nav.csv"
        df.to_csv(csv_path, index=False)

        date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
        print(f"  -> Saved {len(df):,} rows to {csv_path.name}")
        print(f"  -> Date range: {date_range}")
        print(f"  -> Fund house: {df['fund_house'].iloc[0]}")

        summary_rows.append({
            "scheme_code": scheme_code,
            "scheme_name": df["scheme_name"].iloc[0],
            "status": "SUCCESS",
            "rows_fetched": len(df),
            "date_range": date_range,
        })

        # Be polite to the free public API between calls
        time.sleep(0.5)

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------
    summary_df = pd.DataFrame(summary_rows)
    summary_path = RAW_DIR / "nav_fetch_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\n" + "=" * 70)
    print("FETCH SUMMARY")
    print("=" * 70)
    print(summary_df.to_string(index=False))
    print(f"\nSummary saved to {summary_path}")

    failed = summary_df[summary_df["status"] != "SUCCESS"]
    if not failed.empty:
        print(f"\n[ALERT] {len(failed)} scheme(s) did not fetch successfully. "
              "Check your network/proxy access to api.mfapi.in.")
    else:
        print("\nAll 6 schemes fetched successfully.")


if __name__ == "__main__":
    main()
