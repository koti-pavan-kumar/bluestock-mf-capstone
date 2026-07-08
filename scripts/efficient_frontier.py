"""
scripts/efficient_frontier.py
------------------------------
Bonus B4 — Bluestock Fintech Mutual Fund Analytics Capstone

Markowitz Mean-Variance Portfolio Optimisation for 5 selected mutual
fund schemes. Generates the Efficient Frontier — the set of portfolios
offering the maximum expected return for each level of risk.

Key outputs:
  - Efficient Frontier curve
  - Minimum Variance Portfolio (MVP)
  - Maximum Sharpe Ratio Portfolio (MSR)
  - 5,000 random portfolio simulations (for context)
  - reports/efficient_frontier.png
  - reports/efficient_frontier_weights.csv

Usage (run from project root):
    python scripts/efficient_frontier.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"
RAW = BASE_DIR / "data" / "raw"
REPORTS = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

RF_ANNUAL = 0.065
TRADING_DAYS = 252
N_PORTFOLIOS = 5000
np.random.seed(42)

# 5 selected funds — diverse across categories per the brief
SELECTED_CODES = [119551, 119598, 119120, 120503, 100016]


def load_returns() -> tuple[pd.DataFrame, list[str]]:
    nav = pd.read_csv(PROCESSED / "clean_nav.csv", parse_dates=["date"])
    fm = pd.read_csv(RAW / "01_fund_master.csv")

    nav = nav[nav["amfi_code"].isin(SELECTED_CODES)].sort_values(["amfi_code", "date"])
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()

    pivot = nav.pivot(index="date", columns="amfi_code", values="daily_return").dropna()
    pivot.columns = [
        fm[fm["amfi_code"] == c]["scheme_name"].values[0].split(" - ")[0].strip()[:18]
        for c in pivot.columns
    ]
    return pivot, list(pivot.columns)


def portfolio_performance(weights: np.ndarray, mean_returns: np.ndarray,
                           cov_matrix: np.ndarray) -> tuple[float, float, float]:
    ann_return = np.dot(weights, mean_returns) * TRADING_DAYS
    ann_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * TRADING_DAYS, weights)))
    sharpe = (ann_return - RF_ANNUAL) / ann_vol
    return ann_return, ann_vol, sharpe


def random_portfolios(mean_returns, cov_matrix, n=N_PORTFOLIOS):
    n_assets = len(mean_returns)
    results = np.zeros((3, n))
    weights_all = []
    for i in range(n):
        w = np.random.dirichlet(np.ones(n_assets))
        ret, vol, sharpe = portfolio_performance(w, mean_returns, cov_matrix)
        results[0, i] = ret
        results[1, i] = vol
        results[2, i] = sharpe
        weights_all.append(w)
    return results, weights_all


def min_variance_portfolio(mean_returns, cov_matrix):
    n = len(mean_returns)
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
    bounds = tuple((0, 1) for _ in range(n))
    w0 = np.ones(n) / n
    result = minimize(
        lambda w: portfolio_performance(w, mean_returns, cov_matrix)[1],
        w0, method="SLSQP", bounds=bounds, constraints=constraints
    )
    return result


def max_sharpe_portfolio(mean_returns, cov_matrix):
    n = len(mean_returns)
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
    bounds = tuple((0, 1) for _ in range(n))
    w0 = np.ones(n) / n
    result = minimize(
        lambda w: -portfolio_performance(w, mean_returns, cov_matrix)[2],
        w0, method="SLSQP", bounds=bounds, constraints=constraints
    )
    return result


def efficient_frontier_curve(mean_returns, cov_matrix, n_points=100):
    target_returns = np.linspace(
        mean_returns.min() * TRADING_DAYS * 1.05,
        mean_returns.max() * TRADING_DAYS * 0.95,
        n_points
    )
    n = len(mean_returns)
    frontier_vols = []
    for target in target_returns:
        constraints = (
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w: portfolio_performance(w, mean_returns, cov_matrix)[0] - target},
        )
        bounds = tuple((0, 1) for _ in range(n))
        result = minimize(
            lambda w: portfolio_performance(w, mean_returns, cov_matrix)[1],
            np.ones(n) / n, method="SLSQP", bounds=bounds, constraints=constraints
        )
        if result.success:
            frontier_vols.append(result.fun)
        else:
            frontier_vols.append(np.nan)
    return target_returns, np.array(frontier_vols)


def main():
    print("=" * 65)
    print("MARKOWITZ EFFICIENT FRONTIER — Portfolio Optimisation")
    print("=" * 65)

    returns_df, names = load_returns()
    mean_returns = returns_df.mean().values
    cov_matrix = returns_df.cov().values

    print(f"\nFunds: {names}")
    print(f"Date range: {returns_df.index.min().date()} to {returns_df.index.max().date()}")
    print(f"Observations: {len(returns_df)}")

    # Random portfolios
    print(f"\nSimulating {N_PORTFOLIOS:,} random portfolios...")
    results, weights_all = random_portfolios(mean_returns, cov_matrix)

    # Optimal portfolios
    mvp = min_variance_portfolio(mean_returns, cov_matrix)
    msr = max_sharpe_portfolio(mean_returns, cov_matrix)
    mvp_ret, mvp_vol, mvp_sharpe = portfolio_performance(mvp.x, mean_returns, cov_matrix)
    msr_ret, msr_vol, msr_sharpe = portfolio_performance(msr.x, mean_returns, cov_matrix)

    # Efficient frontier curve
    print("Computing efficient frontier curve...")
    ef_returns, ef_vols = efficient_frontier_curve(mean_returns, cov_matrix)

    # ── Plot ─────────────────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))

    # Left: Efficient Frontier scatter
    sc = ax1.scatter(results[1], results[0], c=results[2], cmap="viridis",
                      alpha=0.4, s=8, label="Random Portfolios")
    plt.colorbar(sc, ax=ax1, label="Sharpe Ratio")

    valid = ~np.isnan(ef_vols)
    ax1.plot(ef_vols[valid], ef_returns[valid], "b-", linewidth=2.5,
              label="Efficient Frontier", zorder=5)

    ax1.scatter(mvp_vol, mvp_ret, marker="*", color="gold", s=300, zorder=10,
                 label=f"Min Variance (Sharpe: {mvp_sharpe:.2f})")
    ax1.scatter(msr_vol, msr_ret, marker="*", color="red", s=300, zorder=10,
                 label=f"Max Sharpe (Sharpe: {msr_sharpe:.2f})")

    ax1.set_xlabel("Annualised Volatility (Risk)", fontsize=11)
    ax1.set_ylabel("Annualised Expected Return", fontsize=11)
    ax1.set_title("Markowitz Efficient Frontier\n5 Selected Mutual Funds", fontsize=12, fontweight="bold")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x*100:.0f}%"))
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x*100:.0f}%"))
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Right: Portfolio weights
    portfolio_labels = ["Equal\nWeight", "Min\nVariance", "Max\nSharpe"]
    n = len(names)
    equal_w = np.ones(n) / n
    weight_data = np.array([equal_w, mvp.x, msr.x])
    colors_p = ["#0077B6", "#00B4D8", "#0D2B55", "#F4A261", "#2DC653"]
    bottom = np.zeros(3)
    for i, (name, color) in enumerate(zip(names, colors_p)):
        ax2.bar(portfolio_labels, weight_data[:, i], bottom=bottom,
                 color=color, label=name[:18], edgecolor="white", linewidth=0.5)
        bottom += weight_data[:, i]

    ax2.set_title("Portfolio Weights — Optimal vs Equal", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Portfolio Weight", fontsize=11)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x*100:.0f}%"))
    ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    out_path = REPORTS / "efficient_frontier.png"
    fig.savefig(out_path, bbox_inches="tight", dpi=110)
    plt.close()
    print(f"\nChart saved: {out_path.relative_to(BASE_DIR)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    weight_rows = []
    for i, name in enumerate(names):
        weight_rows.append({
            "fund": name,
            "equal_weight_pct": round(equal_w[i] * 100, 1),
            "min_variance_weight_pct": round(mvp.x[i] * 100, 1),
            "max_sharpe_weight_pct": round(msr.x[i] * 100, 1),
        })
    weights_df = pd.DataFrame(weight_rows)
    weights_df.to_csv(REPORTS / "efficient_frontier_weights.csv", index=False)

    print(f"\nMinimum Variance Portfolio:")
    print(f"  Return: {mvp_ret*100:.1f}% | Vol: {mvp_vol*100:.1f}% | Sharpe: {mvp_sharpe:.3f}")
    print(f"\nMaximum Sharpe Portfolio:")
    print(f"  Return: {msr_ret*100:.1f}% | Vol: {msr_vol*100:.1f}% | Sharpe: {msr_sharpe:.3f}")
    print(f"\nPortfolio Weights:")
    print(weights_df.to_string(index=False))


if __name__ == "__main__":
    main()
