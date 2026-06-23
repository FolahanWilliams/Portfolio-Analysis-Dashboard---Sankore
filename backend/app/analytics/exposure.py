"""Sector & Geographic Exposure analytics.

Portfolio vs benchmark weights by sector and region, signed active weights, a
concentration measure (HHI / effective N), and a sector x region heatmap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.loader import MarketData
from app.analytics.windows import WindowSlice


def _portfolio_weights(md: MarketData, on: pd.Timestamp) -> pd.Series:
    shares = md.holdings.set_index("ticker")["shares"]
    px = md.usd_prices.loc[on]
    cols = [t for t in shares.index if t in px.index]
    values = shares.reindex(cols) * px.reindex(cols)
    return values / values.sum()


def _group_weights(weights: pd.Series, mapping: pd.Series, key: str) -> pd.DataFrame:
    df = pd.DataFrame({"weight": weights, key: mapping.reindex(weights.index)})
    return df.groupby(key)["weight"].sum()


def _active_table(port: pd.Series, bench: pd.Series, key: str) -> list[dict]:
    keys = sorted(set(port.index) | set(bench.index))
    rows = []
    for k in keys:
        wp = float(port.get(k, 0.0))
        wb = float(bench.get(k, 0.0))
        rows.append({key: k, "portfolio": wp, "benchmark": wb, "active": wp - wb})
    rows.sort(key=lambda r: r["portfolio"], reverse=True)
    return rows


def compute_exposure(md: MarketData, w: WindowSlice) -> dict:
    end = w.end_date
    port_w = _portfolio_weights(md, end)

    h = md.holdings.set_index("ticker")
    sector_of = h["sector"]
    region_of = h["region"]

    # Benchmark group weights straight from its constituent weights.
    b = md.benchmark.set_index("ticker")
    bench_w = b["weight"]

    port_sector = _group_weights(port_w, sector_of, "sector")
    port_region = _group_weights(port_w, region_of, "region")
    bench_sector = _group_weights(bench_w, b["sector"], "sector")
    bench_region = _group_weights(bench_w, b["region"], "region")

    # Concentration: HHI over individual holdings + effective number of names.
    hhi = float((port_w ** 2).sum())
    effective_n = float(1.0 / hhi) if hhi > 0 else 0.0

    # Sector x region heatmap of portfolio weights.
    grid = pd.DataFrame({
        "weight": port_w,
        "sector": sector_of.reindex(port_w.index),
        "region": region_of.reindex(port_w.index),
    })
    pivot = grid.pivot_table(index="sector", columns="region",
                             values="weight", aggfunc="sum", fill_value=0.0)
    heatmap = {
        "sectors": list(pivot.index),
        "regions": list(pivot.columns),
        "values": [[float(v) for v in row] for row in pivot.to_numpy()],
    }

    return {
        "window": w.code,
        "as_of": end.date().isoformat(),
        "sector": _active_table(port_sector, bench_sector, "sector"),
        "region": _active_table(port_region, bench_region, "region"),
        "concentration": {
            "hhi": hhi,
            "effective_n": effective_n,
            "largest_weight": float(port_w.max()),
            "top5_weight": float(port_w.sort_values(ascending=False).head(5).sum()),
        },
        "heatmap": heatmap,
    }
