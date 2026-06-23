"""Scenario analysis (P1): shock the book and reprice it.

A first-order reprice. For each holding the instantaneous shocked return is

    r_i = beta_i * market_shock + sector_shock(sector_i) + fx_shock(ccy_i)

where beta_i is estimated vs the benchmark over the full history, and the FX
shock applies only to non-USD holdings (it moves their USD value directly).
new_value_i = value_i * (1 + r_i). We report the repriced AUM, the P&L impact,
and the holdings that move the most.

This is presentation-free: the route handler passes the shocks straight through.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.config import BASE_CURRENCY
from app.data.loader import MarketData


def _holding_betas(md: MarketData) -> pd.Series:
    """Beta of each held ticker vs the benchmark, over the full history."""
    bench_ret = md.benchmark_index_series().pct_change().iloc[1:]
    var_b = float(bench_ret.var(ddof=1))
    betas = {}
    for t in md.held_tickers():
        if t not in md.usd_prices.columns:
            betas[t] = 1.0
            continue
        r = md.usd_prices[t].pct_change().iloc[1:]
        aligned = pd.concat([r, bench_ret], axis=1, keys=["r", "b"]).dropna()
        if var_b > 0 and len(aligned) > 1:
            betas[t] = float(np.cov(aligned["r"], aligned["b"], ddof=1)[0, 1] / var_b)
        else:
            betas[t] = 1.0
    return pd.Series(betas)


def apply_scenario(
    md: MarketData,
    market: float = 0.0,
    sector_shocks: dict[str, float] | None = None,
    fx_shocks: dict[str, float] | None = None,
) -> dict:
    sector_shocks = sector_shocks or {}
    fx_shocks = fx_shocks or {}

    end = md.dates[-1]
    h = md.holdings.set_index("ticker")
    px = md.usd_prices.loc[end]
    shares = h["shares"]
    held = [t for t in shares.index if t in px.index]

    values = (shares.reindex(held) * px.reindex(held))
    base_aum = float(values.sum())
    betas = _holding_betas(md).reindex(held).fillna(1.0)

    rows = []
    for t in held:
        sector = str(h.loc[t, "sector"])
        ccy = md.currency_of.get(t, BASE_CURRENCY)
        shock = (
            float(betas[t]) * market
            + float(sector_shocks.get(sector, 0.0))
            + (float(fx_shocks.get(ccy, 0.0)) if ccy != BASE_CURRENCY else 0.0)
        )
        v0 = float(values[t])
        v1 = v0 * (1.0 + shock)
        rows.append({
            "ticker": t,
            "name": str(h.loc[t, "name"]),
            "sector": sector,
            "currency": ccy,
            "beta": float(betas[t]),
            "weight": v0 / base_aum if base_aum else 0.0,
            "shock_return": shock,
            "value_before": v0,
            "value_after": v1,
            "value_change": v1 - v0,
        })

    new_aum = sum(r["value_after"] for r in rows)
    pnl_change = new_aum - base_aum
    movers = sorted(rows, key=lambda r: r["value_change"])
    portfolio_return = pnl_change / base_aum if base_aum else 0.0

    return {
        "as_of": end.date().isoformat(),
        "inputs": {"market": market, "sector_shocks": sector_shocks, "fx_shocks": fx_shocks},
        "base_aum": base_aum,
        "new_aum": new_aum,
        "pnl_change": pnl_change,
        "portfolio_return": portfolio_return,
        "top_gainers": [r for r in reversed(movers[-3:])],
        "top_losers": movers[:3],
        "by_holding": sorted(rows, key=lambda r: r["weight"], reverse=True),
    }
