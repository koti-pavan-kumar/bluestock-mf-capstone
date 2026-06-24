# Data Dictionary — Bluestock Fintech Mutual Fund Analytics Capstone

Documents every column across the 10 raw provided datasets, the 3 cleaned
datasets produced on Day 2, and the 6-table SQLite star schema. Business
definitions are included for any field that isn't self-explanatory from
its name alone.

---

## 1. Raw Source Datasets (`data/raw/`)

### 01_fund_master.csv (40 rows)
| Column | Type | Business Definition |
|---|---|---|
| amfi_code | int | AMFI's unique scheme identifier. Primary key for fund-level data. |
| fund_house | text | Name of the Asset Management Company (AMC) that manages the fund. |
| scheme_name | text | Full official AMFI scheme name, including plan variant. |
| category | text | Top-level fund category: Equity or Debt. |
| sub_category | text | Fund's specific mandate, e.g. Large Cap, Small Cap, Gilt, Liquid. |
| plan | text | Regular (sold via distributor, higher expense ratio) or Direct (bought directly from AMC, lower expense ratio). |
| launch_date | date | Date the scheme was first launched. |
| benchmark | text | The index this fund is measured against (e.g. NIFTY 100 TRI). |
| expense_ratio_pct | float | Annual fee charged by the AMC, as % of assets. |
| exit_load_pct | float | Penalty % charged if units are redeemed before a minimum holding period. |
| min_sip_amount | int | Minimum monthly SIP investment allowed (₹). |
| min_lumpsum_amount | int | Minimum one-time investment allowed (₹). |
| fund_manager | text | Name of the fund's primary portfolio manager. |
| risk_category | text | SEBI-mandated risk label: Low / Moderate / High / Very High. |
| sebi_category_code | text | SEBI's internal scheme classification code (e.g. EC01 = Large Cap Equity). |

### 02_nav_history.csv (46,000 rows)
| Column | Type | Business Definition |
|---|---|---|
| amfi_code | int | Foreign key to fund_master. |
| date | date | NAV date (business day). |
| nav | float | Net Asset Value in ₹ per unit on that date — the fund's "price". |

### 03_aum_by_fund_house.csv (90 rows)
| Column | Type | Business Definition |
|---|---|---|
| date | date | Quarter-end reporting date. |
| fund_house | text | Asset Management Company name. |
| aum_lakh_crore | float | Total Assets Under Management, in ₹ lakh crore (1 lakh crore = ₹1,000,000,000,000). |
| aum_crore | int | Same AUM figure, expressed in ₹ crore for finer granularity. |
| num_schemes | int | Number of distinct schemes the AMC offers as of that date. |

### 04_monthly_sip_inflows.csv (48 rows)
| Column | Type | Business Definition |
|---|---|---|
| month | text (YYYY-MM) | Reporting month. |
| sip_inflow_crore | float | Total SIP money invested industry-wide that month, in ₹ crore. |
| active_sip_accounts_crore | float | Number of SIP accounts with at least one contribution that month, in crore. |
| new_sip_accounts_lakh | float | Newly registered SIP accounts that month, in lakh. |
| sip_aum_lakh_crore | float | Total assets held via SIP investments, in ₹ lakh crore. |
| yoy_growth_pct | float | Year-over-year % growth in SIP inflow vs. the same month last year. Null for the first 12 months (no prior year to compare). |

### 05_category_inflows.csv (144 rows)
| Column | Type | Business Definition |
|---|---|---|
| month | text (YYYY-MM) | Reporting month. |
| category | text | Fund category (Large Cap, Mid Cap, Small Cap, Flexi Cap, etc.). |
| net_inflow_crore | float | Net money flowing into that category that month (inflows minus outflows), in ₹ crore. |

### 06_industry_folio_count.csv (21 rows)
| Column | Type | Business Definition |
|---|---|---|
| month | text (YYYY-MM) | Reporting month (quarterly cadence). |
| total_folios_crore | float | Total investor folios (accounts) industry-wide, in crore. |
| equity_folios_crore | float | Folios specifically in equity schemes, in crore. |
| debt_folios_crore | float | Folios in debt schemes, in crore. |
| hybrid_folios_crore | float | Folios in hybrid schemes, in crore. |
| others_folios_crore | float | Folios in all other scheme types, in crore. |

### 07_scheme_performance.csv (40 rows)
| Column | Type | Business Definition |
|---|---|---|
| amfi_code | int | Foreign key to fund_master. |
| scheme_name, fund_house, category, plan | text | Denormalised copies from fund_master for convenience. |
| return_1yr_pct | float | Absolute return over the trailing 1 year. |
| return_3yr_pct | float | Annualised (CAGR) return over the trailing 3 years. |
| return_5yr_pct | float | Annualised (CAGR) return over the trailing 5 years. |
| benchmark_3yr_pct | float | The fund's benchmark index's 3yr CAGR, for comparison. |
| alpha | float | Excess return vs. benchmark, after adjusting for risk (return_3yr - benchmark_3yr, risk-adjusted). |
| beta | float | Fund's sensitivity to overall market movements (1.0 = moves with the market). |
| sharpe_ratio | float | Risk-adjusted return per unit of total volatility. Higher is better; >1 is considered good. |
| sortino_ratio | float | Like Sharpe, but only penalises downside volatility (ignores upside swings). |
| std_dev_ann_pct | float | Annualised standard deviation of daily returns — a volatility measure. |
| max_drawdown_pct | float | The worst peak-to-trough decline the fund has experienced (negative value). |
| aum_crore | int | Fund's own AUM (scheme-level, not fund-house level), in ₹ crore. |
| expense_ratio_pct | float | Same as in fund_master — included here for convenience in performance analysis. |
| morningstar_rating | int | 1-5 star rating (this dataset's version is simulated, based on Sharpe ratio). |
| risk_grade | text | SEBI risk category, duplicated from fund_master. |

### 08_investor_transactions.csv (32,778 rows)
| Column | Type | Business Definition |
|---|---|---|
| investor_id | text | Unique synthetic investor identifier. |
| transaction_date | date | Date the transaction occurred. |
| amfi_code | int | Which fund the transaction was made in. Foreign key to fund_master. |
| transaction_type | text | SIP (recurring), Lumpsum (one-time investment), or Redemption (withdrawal). |
| amount_inr | int | Transaction amount in ₹. |
| state, city | text | Investor's location. |
| city_tier | text | T30 = Top 30 cities by AMFI definition (more developed MF penetration); B30 = Beyond Top 30 (smaller towns/cities). |
| age_group | text | Investor's age bracket. |
| gender | text | Investor's gender. |
| annual_income_lakh | float | Investor's self-reported annual income, in ₹ lakh. |
| payment_mode | text | How the transaction was funded (UPI, Net Banking, Mandate, Cheque). |
| kyc_status | text | Verified or Pending — whether the investor's Know Your Customer compliance check is complete. |

### 09_portfolio_holdings.csv (322 rows)
| Column | Type | Business Definition |
|---|---|---|
| amfi_code | int | Which equity fund holds this stock. Foreign key to fund_master. |
| stock_symbol | text | NSE/BSE ticker symbol of the held stock. |
| stock_name | text | Full company name. |
| sector | text | Industry sector the stock belongs to. |
| weight_pct | float | What % of the fund's portfolio this single stock represents. |
| market_value_cr | float | ₹ value of the fund's holding in this stock, in crore. |
| current_price_inr | float | Stock's market price per share at the snapshot date. |
| portfolio_date | date | Snapshot date for this holdings disclosure (single date across the dataset — point-in-time, not a time series). |

### 10_benchmark_indices.csv (8,050 rows)
| Column | Type | Business Definition |
|---|---|---|
| date | date | Trading date. |
| index_name | text | Name of the benchmark index (NIFTY50, NIFTY100, etc.). |
| close_value | float | Index's closing value on that date. |

---

## 2. Cleaned Datasets (`data/processed/`) — produced Day 2

| File | Source | Cleaning applied |
|---|---|---|
| clean_nav.csv | 02_nav_history.csv | Parsed dates, deduplicated on (amfi_code, date), dropped NAV ≤ 0, reindexed each fund to a full business-day calendar with forward-fill for any gaps, sorted by amfi_code + date. |
| clean_transactions.csv | 08_investor_transactions.csv | Standardised transaction_type casing, validated against {SIP, Lumpsum, Redemption}, dropped amount_inr ≤ 0, validated kyc_status against {Verified, Pending}, parsed transaction_date, deduplicated. |
| clean_performance.csv | 07_scheme_performance.csv | Coerced all return/risk columns to numeric, flagged (did not find any) negative Sharpe ratios, validated expense_ratio_pct within the expected 0.1%-2.5% range. |

**Result:** all three source datasets passed validation with zero rows requiring removal — the provided data was already clean. See `reports/day2_cleaning_log.txt` for the full audit trail.

---

## 3. SQLite Star Schema (`data/db/bluestock_mf.db`)

| Table | Type | Grain | Source |
|---|---|---|---|
| dim_fund | Dimension | One row per amfi_code | 01_fund_master.csv |
| dim_date | Dimension | One row per calendar date | Generated from clean_nav.csv date range |
| fact_nav | Fact | One row per (amfi_code, date) | clean_nav.csv + computed daily_return_pct |
| fact_transactions | Fact | One row per transaction | clean_transactions.csv |
| fact_performance | Fact | One row per amfi_code | clean_performance.csv |
| fact_aum | Fact | One row per (report_date, fund_house) | 03_aum_by_fund_house.csv |

Full DDL with primary keys, foreign keys, and indexes: see `sql/schema.sql`.

**Note on fact_aum:** this table is at the fund-house aggregate level (e.g.
"SBI Mutual Fund" as a whole), not the individual-scheme level that
dim_fund uses (keyed by amfi_code). It is joined by `fund_house` name
rather than a foreign key to dim_fund, since AUM at this granularity
doesn't map 1:1 to a single scheme.

**Not yet loaded into the database:** `04_monthly_sip_inflows.csv`,
`05_category_inflows.csv`, `06_industry_folio_count.csv`,
`09_portfolio_holdings.csv`, and `10_benchmark_indices.csv` are
industry-level or supplementary datasets not required by the Day 2 star
schema. They remain available as raw CSVs in `data/raw/` for the EDA and
benchmark-comparison work planned in Days 3-4.
