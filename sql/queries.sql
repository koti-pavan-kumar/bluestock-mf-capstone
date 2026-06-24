-- ============================================================================
-- sql/queries.sql
-- Day 2 — Bluestock Fintech Mutual Fund Analytics Capstone
-- 10 analytical business queries against bluestock_mf.db
-- Run with: sqlite3 data/db/bluestock_mf.db < sql/queries.sql
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Q1. Top 5 funds by AUM (current/latest fact_performance snapshot)
-- ----------------------------------------------------------------------------
SELECT
    f.scheme_name,
    f.fund_house,
    p.aum_crore
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.aum_crore DESC
LIMIT 5;


-- ----------------------------------------------------------------------------
-- Q2. Average NAV per month, across all funds
-- ----------------------------------------------------------------------------
SELECT
    strftime('%Y-%m', nav_date) AS month,
    ROUND(AVG(nav), 2) AS avg_nav
FROM fact_nav
GROUP BY month
ORDER BY month;


-- ----------------------------------------------------------------------------
-- Q3. SIP inflow YoY growth (top 12 most recent months with YoY data)
-- Note: sip_inflow_crore lives in 04_monthly_sip_inflows.csv, which is not
-- yet loaded into the SQLite DB as a table in this schema (it's an
-- industry-level time series, not fund/transaction level). This query
-- demonstrates the YoY calculation directly in SQL for when it is loaded;
-- for now it's run against fact_aum as a structural analogue showing the
-- same year-over-year window function pattern on fund-house AUM instead.
-- ----------------------------------------------------------------------------
SELECT
    fund_house,
    report_date,
    aum_crore,
    LAG(aum_crore, 4) OVER (PARTITION BY fund_house ORDER BY report_date) AS aum_crore_yoy_ago,
    ROUND(
        (aum_crore - LAG(aum_crore, 4) OVER (PARTITION BY fund_house ORDER BY report_date)) * 100.0
        / LAG(aum_crore, 4) OVER (PARTITION BY fund_house ORDER BY report_date),
        2
    ) AS yoy_growth_pct
FROM fact_aum
ORDER BY fund_house, report_date;


-- ----------------------------------------------------------------------------
-- Q4. Transaction volume and value by state
-- ----------------------------------------------------------------------------
SELECT
    state,
    COUNT(*) AS num_transactions,
    SUM(amount_inr) AS total_amount_inr,
    ROUND(AVG(amount_inr), 2) AS avg_amount_inr
FROM fact_transactions
GROUP BY state
ORDER BY total_amount_inr DESC;


-- ----------------------------------------------------------------------------
-- Q5. Funds with expense_ratio_pct < 1%
-- ----------------------------------------------------------------------------
SELECT
    scheme_name,
    fund_house,
    category,
    sub_category,
    expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct ASC;


-- ----------------------------------------------------------------------------
-- Q6. Top 10 funds by Sharpe ratio (best risk-adjusted return)
-- ----------------------------------------------------------------------------
SELECT
    f.scheme_name,
    f.fund_house,
    p.sharpe_ratio,
    p.return_3yr_pct,
    p.std_dev_ann_pct
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.sharpe_ratio DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- Q7. Transaction type breakdown (SIP vs Lumpsum vs Redemption) — count & value
-- ----------------------------------------------------------------------------
SELECT
    transaction_type,
    COUNT(*) AS num_transactions,
    SUM(amount_inr) AS total_amount_inr,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_transactions), 2) AS pct_of_transactions
FROM fact_transactions
GROUP BY transaction_type
ORDER BY total_amount_inr DESC;


-- ----------------------------------------------------------------------------
-- Q8. Average SIP amount by age group
-- ----------------------------------------------------------------------------
SELECT
    age_group,
    COUNT(*) AS num_sips,
    ROUND(AVG(amount_inr), 2) AS avg_sip_amount
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY age_group
ORDER BY avg_sip_amount DESC;


-- ----------------------------------------------------------------------------
-- Q9. Worst max drawdown per category (Equity vs Debt) — risk comparison
-- ----------------------------------------------------------------------------
SELECT
    f.category,
    f.sub_category,
    f.scheme_name,
    p.max_drawdown_pct
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
WHERE p.max_drawdown_pct = (
    SELECT MIN(p2.max_drawdown_pct)
    FROM fact_performance p2
    JOIN dim_fund f2 ON f2.amfi_code = p2.amfi_code
    WHERE f2.category = f.category
)
GROUP BY f.category;


-- ----------------------------------------------------------------------------
-- Q10. KYC verification rate by city tier (T30 vs B30)
-- ----------------------------------------------------------------------------
SELECT
    city_tier,
    COUNT(*) AS total_transactions,
    SUM(CASE WHEN kyc_status = 'Verified' THEN 1 ELSE 0 END) AS verified_count,
    ROUND(
        100.0 * SUM(CASE WHEN kyc_status = 'Verified' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS verified_pct
FROM fact_transactions
GROUP BY city_tier;
