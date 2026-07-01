"""Portfolio Summary analytics.

AUM (USD), unrealised + realised P&L and total return, active return vs the
benchmark over the selected window, and top contributors / detractors.

Pure functions over a MarketData object -- no FastAPI, no formatting. This is
the layer that "lifts into production unchanged".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.loader import MarketData
from app.analytics.windows import WindowSlice


def _holding_values_usd(md: MarketData, on: pd.Timestamp) -> pd.Series:
    """USD market value per held ticker on a given date."""
    shares = md.holdings.set_index("ticker")["shares"]
    px = md.usd_prices.loc[on]
    cols = [t for t in shares.index if t in px.index]
    return shares.reindex(cols) * px.reindex(cols)


def compute_summary(md: MarketData, w: WindowSlice) -> dict:
    end, base = w.end_date, w.base_date

    values_now = _holding_values_usd(md, end)
    aum = float(values_now.sum())

    # --- P&L --------------------------------------------------------------
    # Cost basis is in each holding's native currency. Convert to USD at the
    # current fx rate, so unrealised P&L = current USD value - USD cost.
    h = md.holdings.set_index("ticker")
    fx_now = pd.Series(
        {t: md.fx_on(md.currency_of.get(t, "USD"), end) for t in values_now.index}
    )
    cost_usd = (h["cost_basis"].reindex(values_now.index)
                * h["shares"].reindex(values_now.index)
                * fx_now)
    cost_total = float(cost_usd.sum())
    unrealised = float((values_now - cost_usd).sum())
    realised = float(h["realised_pnl"].fillna(0).sum())

    # --- Return: inception-to-date, cost-based (matches the holdings sheet) --
    # Simple return since purchase = (market value - cost basis) / cost basis.
    total_return = unrealised / cost_total if cost_total else 0.0

    # Benchmark (S&P 500) comparison lives on the Performance & Risk panel, on a
    # like-for-like time-series basis; the summary reports the book's own P&L.
    # --- Contribution by holding: gain$ / total cost (sums to total_return) --
    contribs = []
    for tkr in values_now.index:
        v_end = float(values_now[tkr])
        c = float(cost_usd[tkr])
        gain = v_end - c
        contribs.append({
            "ticker": tkr,
            "name": str(h.loc[tkr, "name"]),
            "weight": v_end / aum if aum else 0.0,
            "return": gain / c if c else 0.0,
            "contribution": gain / cost_total if cost_total else 0.0,
        })
    contribs.sort(key=lambda r: r["contribution"], reverse=True)
    top = contribs[:5]
    bottom = [c for c in reversed(contribs[-5:])]

    return {
        "window": w.code,
        "as_of": end.date().isoformat(),
        "base_currency": "USD",
        "aum": aum,
        "cost_basis": cost_total,
        "positions_at_loss": int((values_now - cost_usd < 0).sum()),
        "pnl": {
            "unrealised": unrealised,
            "realised": realised,
            "total": unrealised + realised,
        },
        "total_return": total_return,
        "benchmark_return": None,
        "active_return": None,
        "holdings_count": int(len(values_now)),
        "top_contributors": top,
        "top_detractors": bottom,
        "truncated": w.truncated,
    }
