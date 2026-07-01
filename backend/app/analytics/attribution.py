"""Performance Attribution analytics (inception-to-date, cost-based).

Every position's contribution to the book's total return since purchase:

    contribution_i = gain$_i / total_cost_basis
    total_return   = sum_i contribution_i = (mkt_value - cost_basis) / cost_basis

Aggregated by security and by sector. This ties out exactly to the holdings
sheet's Gain % and to the Portfolio Summary. (Brinson allocation/selection is
not shown: the benchmark is now the S&P 500 index, which has no per-sector
constituent basket to attribute against.)
"""
from __future__ import annotations

import pandas as pd

from app.data.loader import MarketData
from app.analytics.windows import WindowSlice


def compute_attribution(md: MarketData, w: WindowSlice) -> dict:
    end = w.end_date
    h = md.holdings.set_index("ticker")
    px_e = md.usd_prices.loc[end]
    held = [t for t in h.index if t in px_e.index]

    fx = pd.Series({t: md.fx_on(md.currency_of.get(t, "USD"), end) for t in held})
    cost = (h["cost_basis"].reindex(held).astype(float) * h["shares"].reindex(held).astype(float) * fx)
    value = h["shares"].reindex(held).astype(float) * px_e.reindex(held).astype(float)
    gain = value - cost
    total_cost = float(cost.sum())
    total_value = float(value.sum())

    sec_contrib = []
    for t in held:
        sec_contrib.append({
            "ticker": t,
            "name": str(h.loc[t, "name"]),
            "sector": str(h.loc[t, "sector"]),
            "weight": float(value[t] / total_value) if total_value else 0.0,
            "return": float(gain[t] / cost[t]) if cost[t] else 0.0,
            "contribution": float(gain[t] / total_cost) if total_cost else 0.0,
        })
    sec_contrib.sort(key=lambda r: r["contribution"], reverse=True)

    by_sector: dict[str, float] = {}
    for row in sec_contrib:
        by_sector[row["sector"]] = by_sector.get(row["sector"], 0.0) + row["contribution"]
    sector_contrib = [{"sector": s, "contribution": v} for s, v in
                      sorted(by_sector.items(), key=lambda kv: kv[1], reverse=True)]

    return {
        "window": w.code,
        "as_of": end.date().isoformat(),
        "total_return": (total_value - total_cost) / total_cost if total_cost else 0.0,
        "security_contribution": sec_contrib,
        "sector_contribution": sector_contrib,
        "truncated": w.truncated,
    }
