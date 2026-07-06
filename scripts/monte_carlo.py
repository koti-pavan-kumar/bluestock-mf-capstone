"""
scripts/monte_carlo.py
-----------------------
Bonus B3 — Bluestock Fintech Mutual Fund Analytics Capstone

Monte Carlo simulation projecting NAV growth over 5 years (1,260 trading
days) with uncertainty bands for 5 selected mutual fund schemes.

Method: Geometric Brownian Motion (GBM)
  NAV_t = NAV_0 * exp((mu - 0.5*sigma^2)*t + sigma*sqrt(t)*Z)
  where Z ~ N(0,1), mu and sigma estimated from historical daily returns.

Outputs:
  - reports/monte_carlo_simulation.png  — fan chart with 10th/50th/90th
    percentile bands for each fund
  - reports/monte_carlo_summary.csv     — summary statistics per fund

Usage (run from project root):
    python scripts/monte_carlo.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"
RAW = BASE_DIR / "data" / "raw"
REPORTS = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

np.random.seed(42)

# Simulation parameters
N_SIMULATIONS = 1000
N_TRADING_DAYS = 1260        # ~5 years
TRADING_DAYS_PER_YEAR = 252
CONFIDENCE_BANDS = [10, 50, 90]   # percentiles to plot

# Selected funds: diverse across risk categories
SELECTED_CODES = [119551, 119598, 119120, 120503, 100016]

COLORS = ["#0077B6", "#E63946", "#2DC653", "#F4A261", "#9B5DE5"]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    nav = pd.read_csv(PROCESSED / "clean_nav.csv", parse_dates=["date"])
    nav = nav.sort_values(["amfi_code", "date"]).copy()
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    fm = pd.read_csv(RAW / "01_fund_master.csv")
    return nav, fm


def estimate_gbm_params(returns: pd.Series) -> tuple[float, float]:
    """
    Estimate drift (mu) and volatility (sigma) for GBM from historical
    daily log returns.
    """
    log_returns = np.log(1 + returns.dropna())
    mu = log_returns.mean()
    sigma = log_returns.std()
    return mu, sigma


def simulate_paths(nav_0: float, mu: float, sigma: float,
                   n_days: int, n_sims: int) -> np.ndarray:
    """
    Simulate n_sims price paths over n_days using GBM.
    Returns array of shape (n_days+1, n_sims).
    """
    dt = 1.0
    drift = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)

    Z = np.random.standard_normal((n_days, n_sims))
    daily_changes = np.exp(drift + diffusion * Z)

    paths = np.ones((n_days + 1, n_sims))
    paths[0] = nav_0
    for t in range(1, n_days + 1):
        paths[t] = paths[t - 1] * daily_changes[t - 1]

    return paths


def run_monte_carlo() -> pd.DataFrame:
    nav_df, fm = load_data()
    summary_rows = []

    fig, axes = plt.subplots(1, len(SELECTED_CODES), figsize=(18, 7), sharey=False)
    fig.suptitle(
        "Monte Carlo NAV Projection — 5 Years (1,260 Trading Days)\n"
        f"{N_SIMULATIONS:,} Simulations per Fund | GBM Model | 10th/50th/90th Percentile",
        fontsize=13, fontweight="bold", y=1.02
    )

    for idx, (code, ax, color) in enumerate(
            zip(SELECTED_CODES, axes, COLORS)):

        fund_nav = nav_df[nav_df["amfi_code"] == code].copy()
        returns = fund_nav["daily_return"].dropna()
        nav_0 = fund_nav["nav"].iloc[-1]   # start from last known NAV
        fund_name = fm[fm["amfi_code"] == code]["scheme_name"].values[0]
        short_name = fund_name.split(" - ")[0].replace("Fund", "").strip()

        mu, sigma = estimate_gbm_params(returns)
        paths = simulate_paths(nav_0, mu, sigma, N_TRADING_DAYS, N_SIMULATIONS)

        t = np.arange(N_TRADING_DAYS + 1) / TRADING_DAYS_PER_YEAR
        p10 = np.percentile(paths, 10, axis=1)
        p50 = np.percentile(paths, 50, axis=1)
        p90 = np.percentile(paths, 90, axis=1)

        ax.fill_between(t, p10, p90, alpha=0.2, color=color, label="10th-90th pct")
        ax.fill_between(t, np.percentile(paths, 25, axis=1),
                         np.percentile(paths, 75, axis=1),
                         alpha=0.35, color=color, label="25th-75th pct")
        ax.plot(t, p50, color=color, linewidth=2, label="Median")
        ax.plot(t, p10, color=color, linewidth=0.8, linestyle="--", alpha=0.6)
        ax.plot(t, p90, color=color, linewidth=0.8, linestyle="--", alpha=0.6)
        ax.axhline(nav_0, color="black", linewidth=0.8, linestyle=":", alpha=0.5,
                    label=f"Start NAV: Rs.{nav_0:.0f}")

        ax.set_title(short_name[:22], fontsize=10, fontweight="bold", pad=8)
        ax.set_xlabel("Years", fontsize=9)
        ax.set_ylabel("NAV (Rs.)" if idx == 0 else "", fontsize=9)
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3)

        # Expected CAGR from simulation
        median_5yr = p50[-1]
        expected_cagr = (median_5yr / nav_0) ** (1 / 5) - 1

        summary_rows.append({
            "amfi_code": code,
            "scheme_name": fund_name,
            "nav_start": round(nav_0, 2),
            "mu_daily": round(mu, 6),
            "sigma_daily": round(sigma, 6),
            "ann_volatility_pct": round(sigma * np.sqrt(252) * 100, 2),
            "p10_5yr_nav": round(p10[-1], 2),
            "p50_5yr_nav": round(p50[-1], 2),
            "p90_5yr_nav": round(p90[-1], 2),
            "expected_cagr_pct": round(expected_cagr * 100, 2),
            "prob_positive_5yr_pct": round((paths[-1] > nav_0).mean() * 100, 1),
        })

    plt.tight_layout()
    out_path = REPORTS / "monte_carlo_simulation.png"
    fig.savefig(out_path, bbox_inches="tight", dpi=110)
    plt.close()
    print(f"Chart saved: {out_path.relative_to(BASE_DIR)}")

    summary_df = pd.DataFrame(summary_rows)
    csv_path = REPORTS / "monte_carlo_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"Summary saved: {csv_path.relative_to(BASE_DIR)}")
    print()
    print(summary_df[["scheme_name", "expected_cagr_pct",
                        "prob_positive_5yr_pct", "p50_5yr_nav"]].to_string(index=False))
    return summary_df


if __name__ == "__main__":
    print("=" * 65)
    print("MONTE CARLO SIMULATION — 5-Year NAV Projection")
    print("=" * 65)
    run_monte_carlo()
