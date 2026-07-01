"""Risk Metrics analytics.

Annualised volatility, beta, Sharpe, VaR (95/99, historical & parametric),
holdings correlation matrix, and max drawdown -- all over the selected window,
on USD daily returns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.config import RISK_FREE_RATE, TRADING_DAYS_PER_YEAR, VAR_Z
from app.data.loader import MarketData
from app.analytics.windows import WindowSlice, returns_in_window


def _max_drawdown(value: pd.Series) -> float:
    """Largest peak-to-trough decline as a positive fraction."""
    running_peak = value.cummax()
    drawdown = (value - running_peak) / running_peak
    return float(-drawdown.min()) if len(drawdown) else 0.0


def compute_risk(md: MarketData, w: WindowSlice) -> dict:
    pv = md.portfolio_value_series()
    port_ret_all = pv.pct_change().iloc[1:]
    port_ret = returns_in_window(port_ret_all, w)

    bench = md.benchmark_index_series()
    bench_ret_all = bench.pct_change().iloc[1:]
    bench_ret = returns_in_window(bench_ret_all, w)

    n = len(port_ret)
    ann = np.sqrt(TRADING_DAYS_PER_YEAR)

    mu_daily = float(port_ret.mean()) if n else 0.0
    sigma_daily = float(port_ret.std(ddof=1)) if n > 1 else 0.0
    volatility = sigma_daily * ann
    ann_return = mu_daily * TRADING_DAYS_PER_YEAR

    # Benchmark (S&P 500) stats over the same window.
    bench_mu = float(bench_ret.mean()) if len(bench_ret) else 0.0
    bench_sigma = float(bench_ret.std(ddof=1)) if len(bench_ret) > 1 else 0.0
    bench_vol = bench_sigma * ann
    bench_ann_return = bench_mu * TRADING_DAYS_PER_YEAR

    # Cumulative (inception-to-date) returns, portfolio vs S&P 500.
    port_cum = float(pv.loc[w.end_date] / pv.loc[w.base_date] - 1.0)
    bench_cum = float(bench.loc[w.end_date] / bench.loc[w.base_date] - 1.0)
    excess_return = port_cum - bench_cum  # "extra above the market"

    # Beta vs benchmark (aligned daily returns within the window).
    aligned = pd.concat([port_ret, bench_ret], axis=1, keys=["p", "b"]).dropna()
    if len(aligned) > 1 and aligned["b"].var(ddof=1) > 0:
        cov = float(np.cov(aligned["p"], aligned["b"], ddof=1)[0, 1])
        beta = cov / float(aligned["b"].var(ddof=1))
    else:
        beta = float("nan")

    # Jensen's alpha (annualised, CAPM): the return earned above what beta-times-
    # market exposure alone would predict, net of the risk-free rate.
    if np.isfinite(beta):
        alpha = ann_return - (RISK_FREE_RATE + beta * (bench_ann_return - RISK_FREE_RATE))
    else:
        alpha = float("nan")

    sharpe = (ann_return - RISK_FREE_RATE) / volatility if volatility > 0 else float("nan")

    # VaR (1-day), reported as positive loss fractions.
    var = {}
    if n:
        for conf in (95, 99):
            hist = -float(np.percentile(port_ret, 100 - conf))
            param = -(mu_daily - VAR_Z[conf] * sigma_daily)
            var[str(conf)] = {"historical": hist, "parametric": param}
    else:
        var = {"95": {"historical": 0.0, "parametric": 0.0},
               "99": {"historical": 0.0, "parametric": 0.0}}

    # Correlation matrix across held tickers (USD daily returns in window).
    held = [t for t in md.held_tickers() if t in md.usd_prices.columns]
    rets = md.usd_prices[held].pct_change().iloc[1:]
    rets = returns_in_window(rets, w)
    corr = rets.corr()
    correlation = {
        "tickers": list(corr.columns),
        "matrix": [[round(float(v), 4) for v in row] for row in corr.to_numpy()],
    }

    pv_window = pv[(pv.index >= w.base_date) & (pv.index <= w.end_date)]

    return {
        "window": w.code,
        "as_of": w.end_date.date().isoformat(),
        "observations": int(n),
        "volatility": volatility,
        "annualised_return": ann_return,
        "beta": beta,
        "alpha": alpha,
        "sharpe": sharpe,
        "max_drawdown": _max_drawdown(pv_window),
        "var": var,
        "risk_free_rate": RISK_FREE_RATE,
        "correlation": correlation,
        "benchmark_name": "S&P 500",
        "portfolio_return": port_cum,
        "benchmark_return": bench_cum,
        "excess_return": excess_return,
        "benchmark_volatility": bench_vol,
        "benchmark_annualised_return": bench_ann_return,
        "inception": w.base_date.date().isoformat(),
        "truncated": w.truncated,
    }
