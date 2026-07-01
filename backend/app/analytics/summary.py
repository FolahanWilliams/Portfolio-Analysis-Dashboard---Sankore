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
    unrealised = float((values_now - cost_usd).sum())
    realised = float(h["realised_pnl"].fillna(0).sum())

    # --- Returns over the window -------------------------------------------
    pv = md.portfolio_value_series()
    pv_base, pv_end = float(pv.loc[base]), float(pv.loc[end])
    total_return = pv_end / pv_base - 1.0

    # Benchmark return over the window: fixed (base-weight) basket return of its
    # constituents -- the same definition attribution/Brinson uses, so active
    # return and the Brinson total reconcile exactly.
    b = md.benchmark.set_index("ticker")
    bt = [t for t in b.index if t in md.usd_prices.columns]
    bw = b["weight"].reindex(bt).to_numpy(dtype=float)
    bw = bw / bw.sum() if bw.sum() else bw
    p_b = md.usd_prices.loc[base, bt].to_numpy(dtype=float)
    p_e = md.usd_prices.loc[end, bt].to_numpy(dtype=float)
    bench_return = float((bw * (p_e / p_b - 1.0)).sum())
    active_return = total_return - bench_return

    # --- Contribution by holding over the window ---------------------------
    px_base = md.usd_prices.loc[base]
    contribs = []
    w_base_total = float((md.holdings.set_index("ticker")["shares"] * px_base).reindex(values_now.index).sum())
    for tkr in values_now.index:
        shares = float(h.loc[tkr, "shares"])
        v_base = shares * float(px_base[tkr])
        v_end = float(values_now[tkr])
        ret = v_end / v_base - 1.0 if v_base else 0.0
        weight_base = v_base / w_base_total if w_base_total else 0.0
        contribs.append({
            "ticker": tkr,
            "name": str(h.loc[tkr, "name"]),
            "weight": weight_base,
            "return": ret,
            "contribution": weight_base * ret,
        })
    contribs.sort(key=lambda r: r["contribution"], reverse=True)
    top = contribs[:5]
    bottom = [c for c in reversed(contribs[-5:])]

    return {
        "window": w.code,
        "as_of": end.date().isoformat(),
        "base_currency": "USD",
        "aum": aum,
        "pnl": {
            "unrealised": unrealised,
            "realised": realised,
            "total": unrealised + realised,
        },
        "total_return": total_return,
        "benchmark_return": bench_return,
        "active_return": active_return,
        "holdings_count": int(len(values_now)),
        "top_contributors": top,
        "top_detractors": bottom,
        "truncated": w.truncated,
    }
