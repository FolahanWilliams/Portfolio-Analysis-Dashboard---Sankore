"""Rule-based alert feed (P1).

Surfaces risk concentrations and limit breaches "before they bite" (goal G2).
Each rule compares a computed metric to a threshold from config and emits an
alert with a severity:

    breach   -- the limit is exceeded
    warning  -- within 80% of the limit (approaching)

This module reuses the validated P0 analytics rather than recomputing, so an
alert can never disagree with the number shown elsewhere on the dashboard.
"""
from __future__ import annotations

from app.config import ALERT_THRESHOLDS as T
from app.data.loader import MarketData
from app.analytics.windows import WindowSlice
from app.analytics.exposure import compute_exposure
from app.analytics.risk import compute_risk

WARN_RATIO = 0.8  # within 80% of a limit -> warning


def _level(value: float, limit: float) -> str | None:
    """breach if value >= limit, warning if within 80% of it, else None."""
    if value >= limit:
        return "breach"
    if value >= WARN_RATIO * limit:
        return "warning"
    return None


def compute_alerts(md: MarketData, w: WindowSlice) -> dict:
    exp = compute_exposure(md, w)
    risk = compute_risk(md, w)
    alerts: list[dict] = []

    def add(level, category, title, detail, value, threshold):
        if level:
            alerts.append({
                "id": f"{category}:{title}".lower().replace(" ", "_"),
                "severity": level,
                "category": category,
                "title": title,
                "detail": detail,
                "value": value,
                "threshold": threshold,
            })

    # --- Single-name concentration (every breaching holding) --------------
    end = w.end_date
    h = md.holdings.set_index("ticker")
    px = md.usd_prices.loc[end]
    held = [t for t in h.index if t in px.index]
    values = (h["shares"].reindex(held) * px.reindex(held))
    aum = float(values.sum())
    weights = (values / aum).sort_values(ascending=False) if aum else values
    for tkr, wt in weights.items():
        lvl = _level(float(wt), T["single_name_weight"])
        if lvl:
            add(lvl, "Concentration", f"Single-name weight — {tkr}",
                f"{h.loc[tkr, 'name']} ({tkr}) is {float(wt)*100:.1f}% of AUM "
                f"(limit {T['single_name_weight']*100:.0f}%).",
                float(wt), T["single_name_weight"])

    # --- Sector active weight ---------------------------------------------
    for row in exp["sector"]:
        active = abs(row["active"])
        lvl = _level(active, T["sector_active_weight"])
        if lvl:
            direction = "overweight" if row["active"] > 0 else "underweight"
            add(lvl, "Concentration", f"Sector active weight — {row['sector']}",
                f"{row['sector']} is {abs(row['active'])*100:.1f}% {direction} vs "
                f"benchmark (limit {T['sector_active_weight']*100:.0f}%).",
                active, T["sector_active_weight"])

    # --- HHI concentration -------------------------------------------------
    hhi = exp["concentration"]["hhi"]
    add(_level(hhi, T["hhi"]), "Concentration", "Portfolio concentration (HHI)",
        f"HHI is {hhi:.3f} (effective {exp['concentration']['effective_n']:.1f} "
        f"names; limit {T['hhi']:.2f}).",
        hhi, T["hhi"])

    # --- Volatility --------------------------------------------------------
    vol = risk["volatility"]
    add(_level(vol, T["volatility"]), "Risk", "Annualised volatility",
        f"Volatility is {vol*100:.1f}% (limit {T['volatility']*100:.0f}%).",
        vol, T["volatility"])

    # --- Beta band (two-sided) --------------------------------------------
    beta = risk["beta"]
    if beta is not None:
        if beta >= T["beta_high"]:
            add("breach" if beta >= T["beta_high"] else "warning", "Risk",
                "Market beta high",
                f"Beta is {beta:.2f} (upper limit {T['beta_high']:.2f}).",
                beta, T["beta_high"])
        elif beta <= T["beta_low"]:
            add("breach", "Risk", "Market beta low",
                f"Beta is {beta:.2f} (lower limit {T['beta_low']:.2f}).",
                beta, T["beta_low"])

    # --- VaR ---------------------------------------------------------------
    var99 = risk["var"]["99"]["historical"]
    add(_level(var99, T["var99"]), "Risk", "Value at Risk (99%, 1-day)",
        f"1-day 99% VaR is {var99*100:.2f}% (limit {T['var99']*100:.1f}%).",
        var99, T["var99"])

    # --- Drawdown ----------------------------------------------------------
    dd = risk["max_drawdown"]
    add(_level(dd, T["max_drawdown"]), "Risk", "Max drawdown",
        f"Max drawdown is {dd*100:.1f}% over the window "
        f"(limit {T['max_drawdown']*100:.0f}%).",
        dd, T["max_drawdown"])

    order = {"breach": 0, "warning": 1}
    alerts.sort(key=lambda a: (order.get(a["severity"], 2), -a["value"]))

    return {
        "window": w.code,
        "as_of": w.end_date.date().isoformat(),
        "counts": {
            "breach": sum(1 for a in alerts if a["severity"] == "breach"),
            "warning": sum(1 for a in alerts if a["severity"] == "warning"),
        },
        "alerts": alerts,
    }
