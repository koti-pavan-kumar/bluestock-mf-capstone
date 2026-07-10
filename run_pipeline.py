"""
run_pipeline.py
----------------
Bluestock Fintech Mutual Fund Analytics Capstone
Master ETL pipeline runner — executes all pipeline steps in order.

Steps:
  1. live_nav_fetch.py  - fetch live NAV from mfapi.in for 6 schemes
  2. data_ingestion.py  - load + validate all 10 provided datasets
  3. data_cleaning.py   - clean nav_history, transactions, performance
  4. load_to_sqlite.py  - build SQLite star schema + load all data

Usage (run from project root):
    python run_pipeline.py
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

STEPS = [
    ("Live NAV Fetch",     SCRIPTS_DIR / "live_nav_fetch.py"),
    ("Data Ingestion",     SCRIPTS_DIR / "data_ingestion.py"),
    ("Data Cleaning",      SCRIPTS_DIR / "data_cleaning.py"),
    ("Load to SQLite",     SCRIPTS_DIR / "load_to_sqlite.py"),
]


def run_step(name: str, script: Path) -> bool:
    print(f"\n{'='*65}")
    print(f"STEP: {name}")
    print(f"Script: {script.relative_to(BASE_DIR)}")
    print(f"{'='*65}")
    start = time.time()
    result = subprocess.run([sys.executable, str(script)], cwd=BASE_DIR)
    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"\n[OK] {name} completed in {elapsed:.1f}s")
        return True
    else:
        print(f"\n[FAILED] {name} exited with code {result.returncode}")
        return False


def main():
    print("=" * 65)
    print("BLUESTOCK FINTECH - MUTUAL FUND ANALYTICS ETL PIPELINE")
    print("=" * 65)
    pipeline_start = time.time()

    results = []
    for name, script in STEPS:
        if not script.exists():
            print(f"\n[SKIP] {name} - script not found: {script}")
            results.append((name, "SKIPPED"))
            continue
        success = run_step(name, script)
        results.append((name, "OK" if success else "FAILED"))
        if not success:
            print(f"\n[ABORT] Pipeline stopped at: {name}")
            break

    total = time.time() - pipeline_start
    print(f"\n{'='*65}")
    print("PIPELINE SUMMARY")
    print(f"{'='*65}")
    for name, status in results:
        icon = "OK" if status == "OK" else ("--" if status == "SKIPPED" else "!!")
        print(f"  [{icon}] {name}")
    print(f"\nTotal time: {total:.1f}s")
    all_ok = all(s in ("OK", "SKIPPED") for _, s in results)
    print("Status: ALL STEPS COMPLETE" if all_ok else "Status: PIPELINE FAILED")


if __name__ == "__main__":
    main()
