"""Performance Attribution analytics.

Period returns (MTD/QTD/YTD/1Y), contribution by security and sector, and
Brinson allocation vs selection by sector over the selected window.

Brinson (per sector), all over the window:
    allocation  = (w_p - w_b) x (r_b,sec - r_b,total)
    selection   = w_b x (r_p,sec - r_b,sec)
    interaction = (w_p - w_b) x (r_p,sec - r_b,sec)
Summed across sectors these reconcile to (r_p,total - r_b,total): the active
return. We report the interaction term explicitly so the identity holds exactly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.loader import MarketData
from app.analytics.windows import WindowSlice, resolve_window


def _basket_return(md: MarketData, tickers, weights, base, end) -> float:
    """Weighted return of a basket from base to end (weights need not sum to 1)."""
    w = np.array([weights[t] for t in tickers], dtype=float)
    if w.sum() == 0:
        return 0.0
    w = w / w.sum()
    px_b = md.usd_prices.loc[base, tickers].to_numpy(dtype=float)
    px_e = md.usd_prices.loc[end, tickers].to_numpy(dtype=float)
    rets = px_e / px_b - 1.0
    return float(np.dot(w, rets))


def _period_returns(md: MarketData) -> list[dict]:
    pv = md.portfolio_value_series()
    bench = md.benchmark_index_series()
    out = []
    for code in ("MTD", "QTD", "YTD", "1Y"):
        w = resolve_window(code, md.dates)
        p = float(pv.loc[w.end_date]) / float(pv.loc[w.base_date]) - 1.0
        b = float(bench.loc[w.end_date]) / float(bench.loc[w.base_date]) - 1.0
        out.append({
            "period": code,
            "portfolio": p,
            "benchmark": b,
            "active": p - b,
            "truncated": w.truncated,
        })
    return out


def compute_attribution(md: MarketData, w: WindowSlice) -> dict:
    base, end = w.base_date, w.end_date
    h = md.holdings.set_index("ticker")
    b = md.benchmark.set_index("ticker")

    # --- Base-weight portfolio & per-security contribution over window -----
    px_b = md.usd_prices.loc[base]
    px_e = md.usd_prices.loc[end]
    held = list(h.index)
    base_val = (h["shares"] * px_b.reindex(held)).rename("v")
    total_base = float(base_val.sum())

    sec_contrib = []
    for t in held:
        wb_ = float(base_val[t] / total_base) if total_base else 0.0
        r = float(px_e[t] / px_b[t] - 1.0)
        sec_contrib.append({
            "ticker": t,
            "name": str(h.loc[t, "name"]),
            "sector": str(h.loc[t, "sector"]),
            "weight": wb_,
            "return": r,
            "contribution": wb_ * r,
        })
    sec_contrib.sort(key=lambda r: r["contribution"], reverse=True)

    # --- Contribution by sector -------------------------------------------
    by_sector: dict[str, float] = {}
    for row in sec_contrib:
        by_sector[row["sector"]] = by_sector.get(row["sector"], 0.0) + row["contribution"]
    sector_contrib = [{"sector": s, "contribution": v} for s, v in
                      sorted(by_sector.items(), key=lambda kv: kv[1], reverse=True)]

    # --- Brinson by sector -------------------------------------------------
    port_sectors = h["sector"]
    bench_sectors = b["sector"]
    port_w_sector = (base_val / total_base).groupby(port_sectors).sum()
    bench_w_sector = b["weight"].groupby(bench_sectors).sum()

    r_b_total = _basket_return(md, list(b.index), b["weight"].to_dict(), base, end)

    all_sectors = sorted(set(port_w_sector.index) | set(bench_w_sector.index))
    brinson = []
    for s in all_sectors:
        wp = float(port_w_sector.get(s, 0.0))
        wb = float(bench_w_sector.get(s, 0.0))

        p_names = [t for t in held if port_sectors[t] == s]
        b_names = [t for t in b.index if bench_sectors[t] == s]
        r_p_sec = _basket_return(md, p_names, (base_val / total_base).to_dict(), base, end) if p_names else 0.0
        r_b_sec = _basket_return(md, b_names, b["weight"].to_dict(), base, end) if b_names else 0.0

        allocation = (wp - wb) * (r_b_sec - r_b_total)
        selection = wb * (r_p_sec - r_b_sec)
        interaction = (wp - wb) * (r_p_sec - r_b_sec)
        brinson.append({
            "sector": s,
            "w_portfolio": wp,
            "w_benchmark": wb,
            "r_portfolio": r_p_sec,
            "r_benchmark": r_b_sec,
            "allocation": allocation,
            "selection": selection,
            "interaction": interaction,
            "total": allocation + selection + interaction,
        })

    totals = {
        "allocation": sum(x["allocation"] for x in brinson),
        "selection": sum(x["selection"] for x in brinson),
        "interaction": sum(x["interaction"] for x in brinson),
    }
    totals["total"] = totals["allocation"] + totals["selection"] + totals["interaction"]

    return {
        "window": w.code,
        "as_of": end.date().isoformat(),
        "period_returns": _period_returns(md),
        "security_contribution": sec_contrib,
        "sector_contribution": sector_contrib,
        "brinson": brinson,
        "brinson_totals": totals,
        "benchmark_return": r_b_total,
        "truncated": w.truncated,
    }
