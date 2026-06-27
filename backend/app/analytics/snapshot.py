"""Snapshot-native analytics.

When the data is a single-day snapshot (no price history), the statistical
time-series metrics (volatility, beta, VaR, drawdown, correlation, window and
Brinson returns) cannot be computed from real data. Rather than fabricate a
history, these functions compute everything a snapshot *does* support, truthfully:

  - return measured since cost basis (the sheet's Gain %)
  - contribution by security and sector to that return
  - concentration & positioning risk (HHI, effective N, weights, loss count)
  - concentration / position-drawdown alerts
  - a scenario stress test using *assumed* sector sensitivities (clearly flagged)

Exposure (weights, active weights vs benchmark, sector/region, heatmap) is fully
supported by the existing time-series-free `compute_exposure`, so it is reused
as-is by the API layer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.config import ALERT_THRESHOLDS as T
from app.data.loader import MarketData

# Assumed market sensitivities for the scenario stress test (no history to
# estimate betas from). Clearly surfaced as assumptions in the UI.
SECTOR_BETA = {
    "Semiconductors": 1.40,
    "Software": 1.20,
    "IT Services & Networking": 1.10,
    "Communication Services": 1.10,
    "Energy": 0.80,
    "Industrials": 1.00,
    "Utilities": 0.50,
    "Materials": 0.90,
    "Healthcare": 0.70,
    "Space (Thematic)": 1.30,
}
LOSS_WARN = -0.20   # a position down >20% from cost -> warning
LOSS_BREACH = -0.30  # >30% -> breach


def _positions(md: MarketData) -> pd.DataFrame:
    """One row per holding with value, cost, gain and weight (all USD)."""
    on = md.dates[-1]
    h = md.holdings.set_index("ticker")
    px = md.usd_prices.loc[on]
    held = [t for t in h.index if t in px.index]
    df = pd.DataFrame(index=held)
    df["name"] = h["name"].reindex(held)
    df["sector"] = h["sector"].reindex(held)
    df["region"] = h["region"].reindex(held)
    df["shares"] = h["shares"].reindex(held).astype(float)
    df["price"] = px.reindex(held).astype(float)
    fx = pd.Series({t: md.fx_on(md.currency_of.get(t, "USD"), on) for t in held})
    df["cost"] = h["cost_basis"].reindex(held).astype(float) * df["shares"] * fx
    df["value"] = df["shares"] * df["price"]
    df["gain"] = df["value"] - df["cost"]
    df["ret"] = np.where(df["cost"] != 0, df["gain"] / df["cost"], 0.0)
    df["assumed_beta"] = [_assumed_beta(t, str(h.loc[t, "name"]), str(h.loc[t, "sector"]))
                          for t in held]
    aum = df["value"].sum()
    df["weight"] = df["value"] / aum if aum else 0.0
    return df


def _assumed_beta(ticker: str, name: str, sector: str) -> float:
    beta = SECTOR_BETA.get(sector, 1.0)
    if "2X" in name.upper() or "BULL" in name.upper():
        beta *= 2.0
    return round(beta, 2)


def snapshot_summary(md: MarketData) -> dict:
    df = _positions(md)
    aum = float(df["value"].sum())
    cost = float(df["cost"].sum())
    realised = float(md.holdings["realised_pnl"].fillna(0).sum())
    unrealised = aum - cost
    total_cost = cost if cost else 1.0

    rows = []
    for t, r in df.iterrows():
        rows.append({
            "ticker": t,
            "name": str(r["name"]),
            "weight": float(r["weight"]),
            "return": float(r["ret"]),
            "contribution": float(r["gain"] / total_cost),
        })
    rows.sort(key=lambda x: x["contribution"], reverse=True)

    return {
        "mode": "snapshot",
        "window": "SNAPSHOT",
        "as_of": md.dates[-1].date().isoformat(),
        "base_currency": "USD",
        "aum": aum,
        "cost_basis": cost,
        "pnl": {"unrealised": unrealised, "realised": realised,
                "total": unrealised + realised},
        "total_return": unrealised / total_cost,
        "benchmark_return": None,
        "active_return": None,
        "holdings_count": int(len(df)),
        "positions_at_loss": int((df["gain"] < 0).sum()),
        "top_contributors": rows[:5],
        "top_detractors": list(reversed(rows[-5:])),
        "truncated": False,
    }


def snapshot_risk(md: MarketData) -> dict:
    df = _positions(md).sort_values("weight", ascending=False)
    w = df["weight"]
    hhi = float((w ** 2).sum())
    sector_w = df.groupby("sector")["weight"].sum().sort_values(ascending=False)
    best = df.sort_values("ret", ascending=False).iloc[0]
    worst = df.sort_values("ret").iloc[0]
    return {
        "mode": "snapshot",
        "as_of": md.dates[-1].date().isoformat(),
        "positions": int(len(df)),
        "positions_at_loss": int((df["gain"] < 0).sum()),
        "hhi": hhi,
        "effective_n": float(1.0 / hhi) if hhi else 0.0,
        "largest_weight": {"ticker": str(w.index[0]), "weight": float(w.iloc[0])},
        "top5_weight": float(w.head(5).sum()),
        "top10_weight": float(w.head(10).sum()),
        "largest_sector": {"sector": str(sector_w.index[0]), "weight": float(sector_w.iloc[0])},
        "assumed_beta": float((df["weight"] * df["assumed_beta"]).sum()),
        "unrealised_return": float(df["gain"].sum() / df["cost"].sum()) if df["cost"].sum() else 0.0,
        "best": {"ticker": str(best.name), "return": float(best["ret"])},
        "worst": {"ticker": str(worst.name), "return": float(worst["ret"])},
        "loss_makers": [
            {"ticker": str(t), "return": float(r["ret"]), "value_change": float(r["gain"])}
            for t, r in df.sort_values("ret").head(5).iterrows()
        ],
    }


def snapshot_attribution(md: MarketData) -> dict:
    df = _positions(md)
    total_cost = float(df["cost"].sum()) or 1.0
    sec = []
    for t, r in df.iterrows():
        sec.append({
            "ticker": t,
            "name": str(r["name"]),
            "sector": str(r["sector"]),
            "weight": float(r["weight"]),
            "return": float(r["ret"]),
            "contribution": float(r["gain"] / total_cost),
        })
    sec.sort(key=lambda x: x["contribution"], reverse=True)

    by_sector: dict[str, float] = {}
    for row in sec:
        by_sector[row["sector"]] = by_sector.get(row["sector"], 0.0) + row["contribution"]
    sector_contrib = [{"sector": s, "contribution": v}
                      for s, v in sorted(by_sector.items(), key=lambda kv: kv[1], reverse=True)]

    return {
        "mode": "snapshot",
        "as_of": md.dates[-1].date().isoformat(),
        "total_return": float(df["gain"].sum() / total_cost),
        "security_contribution": sec,
        "sector_contribution": sector_contrib,
    }


def snapshot_alerts(md: MarketData, exposure: dict) -> dict:
    df = _positions(md)
    alerts: list[dict] = []

    def add(level, category, title, detail, value, threshold):
        if level:
            alerts.append({
                "id": f"{category}:{title}".lower().replace(" ", "_"),
                "severity": level, "category": category, "title": title,
                "detail": detail, "value": value, "threshold": threshold,
            })

    def lvl(v, limit):
        if v >= limit:
            return "breach"
        if v >= 0.8 * limit:
            return "warning"
        return None

    # Single-name concentration
    for t, r in df.sort_values("weight", ascending=False).iterrows():
        wt = float(r["weight"])
        level = lvl(wt, T["single_name_weight"])
        if level:
            add(level, "Concentration", f"Single-name weight — {t}",
                f"{r['name']} ({t}) is {wt*100:.1f}% of AUM (limit {T['single_name_weight']*100:.0f}%).",
                wt, T["single_name_weight"])

    # Sector active weight vs benchmark (from exposure)
    for row in exposure["sector"]:
        active = abs(row["active"])
        level = lvl(active, T["sector_active_weight"])
        if level:
            direction = "overweight" if row["active"] > 0 else "underweight"
            add(level, "Concentration", f"Sector active weight — {row['sector']}",
                f"{row['sector']} is {active*100:.1f}% {direction} vs benchmark "
                f"(limit {T['sector_active_weight']*100:.0f}%).",
                active, T["sector_active_weight"])

    # HHI
    hhi = exposure["concentration"]["hhi"]
    add(lvl(hhi, T["hhi"]), "Concentration", "Portfolio concentration (HHI)",
        f"HHI is {hhi:.3f} (effective {exposure['concentration']['effective_n']:.1f} names; "
        f"limit {T['hhi']:.2f}).", hhi, T["hhi"])

    # Position drawdown from cost
    for t, r in df.sort_values("ret").iterrows():
        ret = float(r["ret"])
        if ret <= LOSS_BREACH:
            add("breach", "Position", f"Position drawdown — {t}",
                f"{r['name']} ({t}) is {ret*100:.1f}% below cost.", -ret, -LOSS_BREACH)
        elif ret <= LOSS_WARN:
            add("warning", "Position", f"Position drawdown — {t}",
                f"{r['name']} ({t}) is {ret*100:.1f}% below cost.", -ret, -LOSS_WARN)

    order = {"breach": 0, "warning": 1}
    alerts.sort(key=lambda a: (order.get(a["severity"], 2), -a["value"]))
    return {
        "mode": "snapshot",
        "as_of": md.dates[-1].date().isoformat(),
        "counts": {
            "breach": sum(1 for a in alerts if a["severity"] == "breach"),
            "warning": sum(1 for a in alerts if a["severity"] == "warning"),
        },
        "alerts": alerts,
    }


def snapshot_scenario(md: MarketData, market: float = 0.0,
                      sector_shocks: dict[str, float] | None = None,
                      fx_shocks: dict[str, float] | None = None) -> dict:
    sector_shocks = sector_shocks or {}
    df = _positions(md)
    base_aum = float(df["value"].sum())

    rows = []
    for t, r in df.iterrows():
        shock = float(r["assumed_beta"]) * market + float(sector_shocks.get(str(r["sector"]), 0.0))
        v0 = float(r["value"])
        v1 = v0 * (1.0 + shock)
        rows.append({
            "ticker": t, "name": str(r["name"]), "sector": str(r["sector"]),
            "currency": "USD", "beta": float(r["assumed_beta"]),
            "weight": float(r["weight"]), "shock_return": shock,
            "value_before": v0, "value_after": v1, "value_change": v1 - v0,
        })

    new_aum = sum(r["value_after"] for r in rows)
    movers = sorted(rows, key=lambda r: r["value_change"])
    return {
        "mode": "snapshot",
        "assumed": True,
        "as_of": md.dates[-1].date().isoformat(),
        "inputs": {"market": market, "sector_shocks": sector_shocks, "fx_shocks": fx_shocks or {}},
        "base_aum": base_aum,
        "new_aum": new_aum,
        "pnl_change": new_aum - base_aum,
        "portfolio_return": (new_aum - base_aum) / base_aum if base_aum else 0.0,
        "top_gainers": [r for r in reversed(movers[-3:])],
        "top_losers": movers[:3],
        "by_holding": sorted(rows, key=lambda r: r["weight"], reverse=True),
    }
