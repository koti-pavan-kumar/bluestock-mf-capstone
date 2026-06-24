-- ============================================================================
-- sql/schema.sql
-- Day 2 — Bluestock Fintech Mutual Fund Analytics Capstone
--
-- 6-table star schema: 2 dimension tables, 4 fact tables.
-- Designed for SQLite (development); column types chosen to be portable
-- to PostgreSQL for production if needed.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- DIMENSION: dim_fund
-- One row per mutual fund scheme. Source: 01_fund_master.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code            INTEGER PRIMARY KEY,
    fund_house           TEXT NOT NULL,
    scheme_name          TEXT NOT NULL,
    category             TEXT NOT NULL,        -- Equity / Debt
    sub_category         TEXT,                 -- Large Cap / Small Cap / Gilt / etc.
    plan                 TEXT,                 -- Regular / Direct
    launch_date          TEXT,                 -- ISO date (YYYY-MM-DD)
    benchmark            TEXT,
    expense_ratio_pct    REAL,
    exit_load_pct        REAL,
    min_sip_amount       INTEGER,
    min_lumpsum_amount   INTEGER,
    fund_manager         TEXT,
    risk_category        TEXT,
    sebi_category_code   TEXT
);

-- ----------------------------------------------------------------------------
-- DIMENSION: dim_date
-- One row per calendar date spanned by the NAV history / transactions.
-- Pre-populated by scripts/load_to_sqlite.py from the min/max dates found
-- in the cleaned NAV history.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_id        TEXT PRIMARY KEY,      -- ISO date string, e.g. '2022-01-03'
    year           INTEGER NOT NULL,
    month          INTEGER NOT NULL,
    quarter        INTEGER NOT NULL,
    day_of_week    INTEGER NOT NULL,      -- 0=Monday ... 6=Sunday
    is_weekday     INTEGER NOT NULL       -- 1 = Mon-Fri, 0 = Sat/Sun
);

-- ----------------------------------------------------------------------------
-- FACT: fact_nav
-- Daily NAV per fund. Source: cleaned 02_nav_history.csv
-- Grain: one row per (amfi_code, date)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_nav (
    amfi_code          INTEGER NOT NULL,
    nav_date           TEXT NOT NULL,
    nav                REAL NOT NULL,
    daily_return_pct   REAL,              -- computed: (nav_t / nav_t-1 - 1) * 100
    PRIMARY KEY (amfi_code, nav_date),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (nav_date) REFERENCES dim_date(date_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_nav_amfi_code ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_fact_nav_date ON fact_nav(nav_date);

-- ----------------------------------------------------------------------------
-- FACT: fact_transactions
-- Investor-level SIP / Lumpsum / Redemption transactions.
-- Source: cleaned 08_investor_transactions.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_transactions (
    tx_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id          TEXT NOT NULL,
    transaction_date     TEXT NOT NULL,
    amfi_code            INTEGER NOT NULL,
    transaction_type     TEXT NOT NULL CHECK (transaction_type IN ('SIP', 'Lumpsum', 'Redemption')),
    amount_inr           INTEGER NOT NULL CHECK (amount_inr > 0),
    state                TEXT,
    city                 TEXT,
    city_tier            TEXT CHECK (city_tier IN ('T30', 'B30')),
    age_group            TEXT,
    gender               TEXT,
    annual_income_lakh   REAL,
    payment_mode         TEXT,
    kyc_status           TEXT CHECK (kyc_status IN ('Verified', 'Pending')),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (transaction_date) REFERENCES dim_date(date_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_tx_amfi_code ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_fact_tx_date ON fact_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_fact_tx_investor ON fact_transactions(investor_id);

-- ----------------------------------------------------------------------------
-- FACT: fact_performance
-- One row per fund: pre-computed return & risk metrics as of latest data.
-- Source: cleaned 07_scheme_performance.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_performance (
    amfi_code            INTEGER PRIMARY KEY,
    return_1yr_pct       REAL,
    return_3yr_pct       REAL,
    return_5yr_pct       REAL,
    benchmark_3yr_pct    REAL,
    alpha                REAL,
    beta                 REAL,
    sharpe_ratio         REAL,
    sortino_ratio        REAL,
    std_dev_ann_pct      REAL,
    max_drawdown_pct     REAL,
    aum_crore            INTEGER,
    expense_ratio_pct    REAL,
    morningstar_rating   INTEGER CHECK (morningstar_rating BETWEEN 1 AND 5),
    risk_grade           TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- ----------------------------------------------------------------------------
-- FACT: fact_aum
-- Quarterly AUM per fund house. Source: 03_aum_by_fund_house.csv
-- Note: fund_house here is not a FK to dim_fund (which is keyed by
-- amfi_code, scheme-level) — this fact is at the fund-house aggregate
-- level, one level up. Kept as a free-text column joined by name.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_aum (
    aum_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date      TEXT NOT NULL,
    fund_house       TEXT NOT NULL,
    aum_lakh_crore   REAL,
    aum_crore        INTEGER,
    num_schemes      INTEGER,
    UNIQUE (report_date, fund_house)
);

CREATE INDEX IF NOT EXISTS idx_fact_aum_date ON fact_aum(report_date);
CREATE INDEX IF NOT EXISTS idx_fact_aum_house ON fact_aum(fund_house);
