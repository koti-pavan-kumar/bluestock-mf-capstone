"""
streamlit_app.py
-----------------
Bonus B2 — Bluestock Fintech Mutual Fund Analytics Capstone

Streamlit web app — alternative to Power BI dashboard.
Covers all 4 dashboard pages with interactive filters.

Usage (run from project root):
    streamlit run streamlit_app.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bluestock Fintech — MF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent

# ── Load data (cached) ────────────────────────────────────────────────────────
@st.cache_data
def load_all():
    raw = BASE_DIR / "data" / "raw"
    processed = BASE_DIR / "data" / "processed"

    fm = pd.read_csv(raw / "01_fund_master.csv")
    nav = pd.read_csv(processed / "clean_nav.csv", parse_dates=["date"])
    aum = pd.read_csv(raw / "03_aum_by_fund_house.csv", parse_dates=["date"])
    sip = pd.read_csv(raw / "04_monthly_sip_inflows.csv")
    sip["month_dt"] = pd.to_datetime(sip["month"], format="%Y-%m")
    cat = pd.read_csv(raw / "05_category_inflows.csv")
    folio = pd.read_csv(raw / "06_industry_folio_count.csv")
    folio["month_dt"] = pd.to_datetime(folio["month"], format="%Y-%m")
    tx = pd.read_csv(processed / "clean_transactions.csv",
                      parse_dates=["transaction_date"])
    perf = pd.read_csv(processed / "clean_performance.csv")
    holdings = pd.read_csv(raw / "09_portfolio_holdings.csv")
    bench = pd.read_csv(raw / "10_benchmark_indices.csv", parse_dates=["date"])
    sc = pd.read_csv(BASE_DIR / "fund_scorecard.csv")
    var_df = pd.read_csv(BASE_DIR / "var_cvar_report.csv")

    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    return fm, nav, aum, sip, cat, folio, tx, perf, holdings, bench, sc, var_df

fm, nav, aum, sip, cat, folio, tx, perf, holdings, bench, sc, var_df = load_all()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.shields.io/badge/Bluestock-Fintech-0077B6?style=for-the-badge",
                  use_column_width=True)
st.sidebar.title("📊 MF Analytics Platform")
st.sidebar.markdown("**Bluestock Fintech | Capstone 2026**")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["🏭 Industry Overview",
     "📈 Fund Performance",
     "👥 Investor Analytics",
     "💹 SIP & Market Trends"],
    index=0
)

st.sidebar.divider()
st.sidebar.caption("Data: AMFI India | mfapi.in | Jan 2022 – May 2026")
st.sidebar.caption("Built by Pavan Kumar Koti | Intern Cohort 2025")

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
NAVY   = "#0D2B55"
TEAL   = "#0077B6"
ACCENT = "#00B4D8"


# ============================================================================
# PAGE 1 — INDUSTRY OVERVIEW
# ============================================================================
if page == "🏭 Industry Overview":
    st.title("🏭 Industry Overview")
    st.caption("Indian Mutual Fund Industry — Key Metrics & Trends (2022-2025)")

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total AUM",       f"Rs. {aum['aum_crore'].sum()/1e5:.1f}L Cr",  "from all fund houses")
    c2.metric("Latest SIP Inflow", f"Rs. {sip['sip_inflow_crore'].iloc[-1]:,.0f} Cr", f"Month: {sip['month'].iloc[-1]}")
    c3.metric("Total Folios",    f"{folio['total_folios_crore'].iloc[-1]:.2f} Cr", "crore investor accounts")
    c4.metric("Active SIP Accounts", f"{sip['active_sip_accounts_crore'].iloc[-1]:.2f} Cr", "crore accounts")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Industry AUM Trend")
        aum_trend = aum.groupby("date", as_index=False)["aum_crore"].sum()
        fig = px.line(aum_trend, x="date", y="aum_crore",
                       labels={"aum_crore": "Total AUM (Rs. crore)", "date": "Date"},
                       color_discrete_sequence=[TEAL])
        fig.update_layout(height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏦 AUM by Fund House (Latest)")
        latest_date = aum["date"].max()
        aum_latest = aum[aum["date"] == latest_date].sort_values("aum_crore", ascending=True)
        fig = px.bar(aum_latest, x="aum_crore", y="fund_house", orientation="h",
                      labels={"aum_crore": "AUM (Rs. crore)", "fund_house": ""},
                      color="aum_crore", color_continuous_scale="Blues")
        fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("💰 Monthly SIP Inflows")
        fig = px.line(sip, x="month_dt", y="sip_inflow_crore",
                       labels={"sip_inflow_crore": "SIP Inflow (Rs. crore)", "month_dt": "Month"},
                       color_discrete_sequence=[ACCENT])
        peak = sip.loc[sip["sip_inflow_crore"].idxmax()]
        fig.add_annotation(x=peak["month_dt"], y=peak["sip_inflow_crore"],
                            text=f"ATH: Rs.{peak['sip_inflow_crore']:,} Cr",
                            showarrow=True, arrowhead=2, ay=-30)
        fig.update_layout(height=320, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("📊 Total Folio Count Growth")
        fig = px.line(folio, x="month_dt", y="total_folios_crore",
                       labels={"total_folios_crore": "Folios (crore)", "month_dt": "Month"},
                       color_discrete_sequence=["#2DC653"])
        fig.update_layout(height=320, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# PAGE 2 — FUND PERFORMANCE
# ============================================================================
elif page == "📈 Fund Performance":
    st.title("📈 Fund Performance Analytics")

    # Slicers
    col1, col2, col3 = st.columns(3)
    with col1:
        sel_house = st.multiselect("Fund House", sorted(fm["fund_house"].unique()),
                                    default=sorted(fm["fund_house"].unique()))
    with col2:
        sel_cat = st.multiselect("Category", sorted(fm["category"].unique()),
                                  default=sorted(fm["category"].unique()))
    with col3:
        sel_plan = st.multiselect("Plan", sorted(fm["plan"].unique()),
                                   default=sorted(fm["plan"].unique()))

    filtered_fm = fm[
        fm["fund_house"].isin(sel_house) &
        fm["category"].isin(sel_cat) &
        fm["plan"].isin(sel_plan)
    ]
    filtered_sc = sc[sc["amfi_code"].isin(filtered_fm["amfi_code"])]

    st.divider()
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("🎯 Return vs Risk Scatter")
        fig = px.scatter(filtered_sc, x="cagr_3yr_pct", y="sharpe_ratio",
                          size="fund_score", color="fund_score",
                          hover_name="scheme_name",
                          labels={"cagr_3yr_pct": "3yr CAGR (%)",
                                   "sharpe_ratio": "Sharpe Ratio",
                                   "fund_score": "Score"},
                          color_continuous_scale="Blues", size_max=25)
        fig.update_layout(height=380, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏆 Fund Scorecard")
        display_cols = ["scheme_name", "fund_score", "cagr_3yr_pct", "sharpe_ratio", "max_drawdown_pct"]
        st.dataframe(
            filtered_sc[display_cols].rename(columns={
                "scheme_name": "Fund", "fund_score": "Score",
                "cagr_3yr_pct": "3yr CAGR%", "sharpe_ratio": "Sharpe",
                "max_drawdown_pct": "Max DD%"
            }).round(2),
            use_container_width=True, height=380
        )

    st.subheader("📉 NAV History — Fund vs Benchmark")
    sel_fund_name = st.selectbox("Select Fund",
                                   sorted(filtered_fm["scheme_name"].tolist()), index=0)
    sel_fund_code = filtered_fm[filtered_fm["scheme_name"] == sel_fund_name]["amfi_code"].values[0]
    sel_bench = st.selectbox("Select Benchmark",
                               sorted(bench["index_name"].unique()), index=1)

    fund_nav_filtered = nav[nav["amfi_code"] == sel_fund_code].sort_values("date")
    bench_filtered = bench[bench["index_name"] == sel_bench].sort_values("date")

    if not fund_nav_filtered.empty and not bench_filtered.empty:
        nav_norm = fund_nav_filtered["nav"] / fund_nav_filtered["nav"].iloc[0] * 100
        bench_norm = bench_filtered["close_value"] / bench_filtered["close_value"].iloc[0] * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fund_nav_filtered["date"], y=nav_norm,
                                  name=sel_fund_name[:35], line=dict(color=TEAL, width=2)))
        fig.add_trace(go.Scatter(x=bench_filtered["date"], y=bench_norm,
                                  name=sel_bench, line=dict(color="gray", width=1.5, dash="dash")))
        fig.update_layout(height=320, margin=dict(t=20, b=20),
                           yaxis_title="Normalized Value (Start=100)",
                           xaxis_title="Date")
        st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# PAGE 3 — INVESTOR ANALYTICS
# ============================================================================
elif page == "👥 Investor Analytics":
    st.title("👥 Investor Analytics")

    # Slicers
    col1, col2, col3 = st.columns(3)
    with col1:
        sel_state = st.multiselect("State", sorted(tx["state"].unique()),
                                    default=sorted(tx["state"].unique()))
    with col2:
        sel_age = st.multiselect("Age Group", sorted(tx["age_group"].unique()),
                                  default=sorted(tx["age_group"].unique()))
    with col3:
        sel_tier = st.multiselect("City Tier", sorted(tx["city_tier"].unique()),
                                   default=sorted(tx["city_tier"].unique()))

    filtered_tx = tx[
        tx["state"].isin(sel_state) &
        tx["age_group"].isin(sel_age) &
        tx["city_tier"].isin(sel_tier)
    ]

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🗺️ SIP Amount by State")
        sip_state = (filtered_tx[filtered_tx["transaction_type"] == "SIP"]
                      .groupby("state", as_index=False)["amount_inr"].sum()
                      .sort_values("amount_inr"))
        fig = px.bar(sip_state, x="amount_inr", y="state", orientation="h",
                      labels={"amount_inr": "Total SIP Amount (Rs.)", "state": ""},
                      color="amount_inr", color_continuous_scale="Blues")
        fig.update_layout(height=370, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🍩 Transaction Type Split")
        tx_split = filtered_tx.groupby("transaction_type")["amount_inr"].sum().reset_index()
        fig = px.pie(tx_split, values="amount_inr", names="transaction_type",
                      hole=0.45, color_discrete_sequence=[NAVY, TEAL, ACCENT])
        fig.update_layout(height=370, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("👤 Avg SIP by Age Group")
        age_sip = (filtered_tx[filtered_tx["transaction_type"] == "SIP"]
                    .groupby("age_group", as_index=False)["amount_inr"].mean()
                    .sort_values("age_group"))
        fig = px.bar(age_sip, x="age_group", y="amount_inr",
                      labels={"amount_inr": "Avg SIP Amount (Rs.)", "age_group": "Age Group"},
                      color="amount_inr", color_continuous_scale="Blues")
        fig.update_layout(height=320, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("📅 Monthly Transaction Volume")
        tx_monthly = (filtered_tx.groupby(
            filtered_tx["transaction_date"].dt.to_period("M"))
            .size().reset_index(name="count"))
        tx_monthly["month"] = tx_monthly["transaction_date"].astype(str)
        fig = px.line(tx_monthly, x="month", y="count",
                       labels={"count": "Transaction Count", "month": "Month"},
                       color_discrete_sequence=[ACCENT])
        fig.update_layout(height=320, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# PAGE 4 — SIP & MARKET TRENDS
# ============================================================================
elif page == "💹 SIP & Market Trends":
    st.title("💹 SIP & Market Trends")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 SIP Inflow vs Nifty 50")
        nifty50 = bench[bench["index_name"] == "NIFTY50"].sort_values("date")
        sip_plot = sip.sort_values("month_dt")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=sip_plot["month_dt"], y=sip_plot["sip_inflow_crore"],
                              name="SIP Inflow (Cr)", marker_color=TEAL, opacity=0.8))
        fig.add_trace(go.Scatter(x=nifty50["date"], y=nifty50["close_value"],
                                  name="Nifty 50", yaxis="y2",
                                  line=dict(color="orange", width=2)))
        fig.update_layout(
            yaxis=dict(title="SIP Inflow (Rs. crore)"),
            yaxis2=dict(title="Nifty 50", overlaying="y", side="right"),
            height=370, margin=dict(t=20, b=20),
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🌡️ Category Inflow Heatmap")
        pivot = cat.pivot(index="category", columns="month", values="net_inflow_crore").fillna(0)
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="RdYlGn",
                         labels={"color": "Net Inflow (Cr)"})
        fig.update_layout(height=370, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("🏆 Top 5 Categories by Net Inflow FY25")
        top_cat = cat.groupby("category", as_index=False)["net_inflow_crore"].sum()
        top_cat = top_cat.nlargest(5, "net_inflow_crore").sort_values("net_inflow_crore")
        fig = px.bar(top_cat, x="net_inflow_crore", y="category", orientation="h",
                      labels={"net_inflow_crore": "Net Inflow (Rs. crore)", "category": ""},
                      color="net_inflow_crore", color_continuous_scale="Blues")
        fig.update_layout(height=320, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("📈 Active SIP Accounts Growth")
        fig = px.line(sip, x="month_dt", y="active_sip_accounts_crore",
                       labels={"active_sip_accounts_crore": "Active SIP Accounts (crore)",
                                "month_dt": "Month"},
                       color_discrete_sequence=["#2DC653"])
        fig.update_layout(height=320, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
