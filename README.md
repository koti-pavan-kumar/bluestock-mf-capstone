# Bluestock Fintech — Mutual Fund Analytics Capstone

**Company:** Bluestock Fintech Pvt. Ltd.
**Domain:** Mutual Fund / Fintech
**Project Type:** Individual Capstone (7 working days, ~50–55 hours)
**Author:** Pavan Kumar Koti

End-to-end data engineering, ETL pipeline, risk analytics, and interactive
dashboard built on real AMFI-anchored mutual fund data: 40 schemes, ~46K NAV
rows (4.5 yrs history), ~32K investor transactions, 10 fund houses.

## Folder Structure

```
mutual-fund-analytics/
├── data/
│   ├── raw/          # 10 provided source CSVs + live mfapi.in pulls
│   ├── processed/     # Cleaned, merged CSVs (Day 2+)
│   └── db/             # bluestock_mf.db (SQLite) — gitignored, see below
├── notebooks/           # 01_data_ingestion ... 05_advanced_analytics
├── scripts/              # data_ingestion.py, live_nav_fetch.py, etc.
├── sql/                   # schema.sql, queries.sql
├── dashboard/              # Power BI / Tableau files + exported PDFs
├── reports/                 # Data quality summaries, Final_Report.pdf
├── requirements.txt
└── README.md
```

## How to Run (Day 1 + Day 2)

```bash
pip install -r requirements.txt

# Day 1: fetch live NAV history for 6 schemes from mfapi.in
python scripts/live_nav_fetch.py

# Day 1: inspect all 10 provided datasets + AMFI code validation
python scripts/data_ingestion.py

# Day 2: clean nav_history, investor_transactions, scheme_performance
python scripts/data_cleaning.py

# Day 2: build the SQLite star schema and load cleaned data
python scripts/load_to_sqlite.py
```

## Day 1 — Project Setup + Data Ingestion (ETL) — ✅ Complete

**Due:** 24 Jun 2026 | **Time estimate:** 6–8 hours

| # | Task | Status |
|---|------|--------|
| 1 | Project folder structure created, committed to GitHub | ✅ |
| 2 | `requirements.txt` (pandas, numpy, matplotlib, seaborn, plotly, sqlalchemy, requests, jupyter) | ✅ |
| 3 | `scripts/data_ingestion.py` — loads all 10 CSVs, prints shape/dtypes/head | ✅ |
| 4 | `scripts/live_nav_fetch.py` — fetches HDFC Top 100 (125497) from mfapi.in | ✅ (run locally — see note) |
| 5 | Fetch NAV for SBI Bluechip, ICICI Bluechip, Nippon Large Cap, Axis Bluechip, Kotak Bluechip | ✅ (run locally — see note) |
| 6 | Fund master domain summary: unique fund houses, categories, sub-categories, risk grades | ✅ |
| 7 | AMFI code validation: fund_master vs nav_history | ✅ — 40/40 codes match, zero discrepancies |
| 8 | Git commit: `"Day 1: Data ingestion complete"` | ✅ |

### Data quality findings (real data, not simulated test data)

- **All 10 datasets load cleanly.** Row counts match spec: 40 funds, 46,000
  NAV rows, 32,778 transactions, 8,050 benchmark rows, 322 portfolio holdings.
- **AMFI code validation passed**: all 40 `amfi_code` values in
  `01_fund_master.csv` are present in `02_nav_history.csv`, with zero
  missing or extra codes in either direction.
- Two flagged "anomalies" are expected by design, not data quality issues:
  - `min_sip_amount` in `01_fund_master.csv` is constant (₹500 across all
    40 schemes) — real-world AMFI minimum, not a data error.
  - `portfolio_date` in `09_portfolio_holdings.csv` is constant
    (single snapshot: 2025-12-31) — holdings are a point-in-time dataset.
- `04_monthly_sip_inflows.csv` has 12 nulls in `yoy_growth_pct` — expected,
  since the first 12 months in the series have no prior-year value to
  compute YoY growth against.
- Full breakdown: see `reports/day1_data_quality_summary.txt`

### Note on `live_nav_fetch.py`

This script calls `api.mfapi.in` directly and could not be executed inside
the sandbox used to build this repo (outbound network there is restricted
to a small allowlist that doesn't include mfapi.in). The script's logic
was verified separately; **run it on your own machine** to pull the live
NAV history — it will save raw JSON + cleaned CSVs to `data/raw/` for each
of the 6 target schemes, plus a fetch summary.

## Day 2 — Data Cleaning + SQL Database Design — ✅ Complete

**Due:** 25 Jun 2026 | **Time estimate:** 7–8 hours

| # | Task | Status |
|---|------|--------|
| 1 | Clean `nav_history.csv`: parse dates, sort, forward-fill, dedupe, validate NAV > 0 | ✅ |
| 2 | Clean `investor_transactions.csv`: standardise types, validate amounts, check KYC enum | ✅ |
| 3 | Clean `scheme_performance.csv`: validate numerics, flag anomalies, check expense ratio range | ✅ |
| 4 | Design 6-table SQLite star schema with PK/FK constraints | ✅ |
| 5 | Load all cleaned datasets into SQLite, verify row counts | ✅ — 100% match across all 5 loaded tables |
| 6 | Write 10 analytical SQL queries | ✅ — all 10 tested and returning real results |
| 7 | Data dictionary documenting all columns/types/definitions | ✅ |
| 8 | Git commit: `"Day 2: Cleaned data + SQLite DB loaded"` | ✅ |

### Data cleaning findings

All three source datasets (`nav_history`, `investor_transactions`,
`scheme_performance`) passed validation with **zero rows requiring
removal** — no negative NAVs, no invalid transaction types or amounts,
no out-of-range expense ratios, no negative Sharpe ratios. The provided
data was already clean going in. Full audit trail with before/after row
counts: `reports/day2_cleaning_log.txt`.

### Star schema

6 tables: `dim_fund`, `dim_date` (2 dimensions) + `fact_nav`,
`fact_transactions`, `fact_performance`, `fact_aum` (4 facts). Full DDL
with primary/foreign keys and indexes in `sql/schema.sql`. Built into
`data/db/bluestock_mf.db` (~9.5MB, gitignored per the project's own
guidance on `.db` file size — rebuild locally with
`python scripts/load_to_sqlite.py`, which reads `sql/schema.sql` and
verifies every table's row count against its source CSV).

### SQL queries

10 business queries in `sql/queries.sql` — top funds by AUM, monthly
average NAV, fund-house AUM YoY growth, transactions by state, funds
under 1% expense ratio, top Sharpe ratios, transaction type breakdown,
SIP amount by age group, worst drawdown by category, and KYC
verification rate by city tier. All tested against the real database.

## Upcoming Days

- **Day 3:** EDA — 15+ charts (NAV trends, AUM growth, SIP inflows, demographics)
- **Day 4:** Performance analytics — CAGR, Sharpe, Sortino, Alpha/Beta, Max Drawdown, fund scorecard
- **Day 5:** Power BI / Tableau dashboard (4 pages)
- **Day 6:** VaR/CVaR, investor cohort analysis, fund recommender, sector HHI
- **Day 7:** Final report (PDF), 12-slide deck, GitHub polish, optional dashboard publish

## Tech Stack

Python 3.10+, Pandas, NumPy, Matplotlib, Seaborn, Plotly, SQLite/SQLAlchemy,
SciPy (OLS for Alpha/Beta), Jupyter Lab, Power BI Desktop / Tableau, Git.

## Data Sources & Disclaimer

All data is sourced from publicly available AMFI India, mfapi.in, NSE/BSE
information. NAV values are anchored to real historical values; investor
transaction data is synthetically generated using realistic demographic
distributions. **Educational project — not financial advice.**
