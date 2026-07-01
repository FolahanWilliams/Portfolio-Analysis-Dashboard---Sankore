"""Per-holding position table: bought price vs current price, value and P&L.

Works in both snapshot and time-series mode -- it only needs the latest price
column, which exists either way. This is the plain "what do we own, what did we
pay, what's it worth now" view that sits under the portfolio summary.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.loader import MarketData


def compute_holdings(md: MarketData) -> dict:
    on = md.dates[-1]
    h = md.holdings.set_index("ticker")
    px = md.usd_prices.loc[on]
    held = [t for t in h.index if t in px.index]

    rows = []
    total_value = 0.0
    for t in held:
        shares = float(h.loc[t, "shares"])
        fx = md.fx_on(md.currency_of.get(t, "USD"), on)
        # cost_basis is the native per-share purchase price; normalise to USD so
        # bought and current price are directly comparable.
        cost_px = float(h.loc[t, "cost_basis"]) * fx if pd.notna(h.loc[t, "cost_basis"]) else float("nan")
        cur_px = float(px[t])
        value = shares * cur_px
        cost_value = shares * cost_px if np.isfinite(cost_px) else float("nan")
        gain = value - cost_value if np.isfinite(cost_value) else float("nan")
        ret = gain / cost_value if np.isfinite(cost_value) and cost_value else float("nan")
        total_value += value
        rows.append({
            "ticker": t,
            "name": str(h.loc[t, "name"]),
            "sector": str(h.loc[t, "sector"]),
            "region": str(h.loc[t, "region"]),
            "currency": str(md.currency_of.get(t, "USD")),
            "shares": shares,
            "cost_price": cost_px,
            "current_price": cur_px,
            "cost_value": cost_value,
            "market_value": value,
            "unrealised_pnl": gain,
            "unrealised_return": ret,
        })

    for r in rows:
        r["weight"] = (r["market_value"] / total_value) if total_value else 0.0
    rows.sort(key=lambda x: x["market_value"], reverse=True)

    return {
        "as_of": on.date().isoformat(),
        "base_currency": "USD",
        "aum": total_value,
        "holdings_count": len(rows),
        "holdings": rows,
    }
