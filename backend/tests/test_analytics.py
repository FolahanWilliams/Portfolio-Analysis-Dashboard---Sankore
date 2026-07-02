"""Validate the analytics against independent references.

The live dataset is real Yahoo Finance daily history for the GEF MCB book, so
the app runs the full time-series analytics. These tests recompute key figures
with an independent numpy/pandas path and assert they match, and check that the
Brinson attribution reconciles to the active return.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.config import TRADING_DAYS_PER_YEAR
from app.data.loader import load_market_data, clear_cache
from app.analytics.windows import resolve_window, returns_in_window
from app.analytics.summary import compute_summary
from app.analytics.exposure import compute_exposure
from app.analytics.risk import compute_risk
from app.analytics.attribution import compute_attribution
from app.analytics.holdings import compute_holdings

REL = 1e-3


@pytest.fixture(scope="module")
def md():
    clear_cache()
    return load_market_data()


def _w(md, code="ALL"):
    return resolve_window(code, md.dates)


def test_cost_basis_ties_to_sheet_and_return_is_live(md):
    """Cost basis is the sheet's fixed starting point; market value / gain are
    computed live from Yahoo prices, so they follow the data rather than the
    sheet's static snapshot."""
    w = _w(md)
    s = compute_summary(md, w)
    h = md.holdings.set_index("ticker")
    px = md.usd_prices.loc[w.end_date]
    # Cost basis = units x sheet purchase price -> the sheet's $259,244.
    assert s["cost_basis"] == pytest.approx(259_244, abs=3)
    # AUM = units x live Yahoo price; gain and return follow from that.
    live_aum = float((h["shares"] * px.reindex(h.index)).sum())
    assert s["aum"] == pytest.approx(live_aum, rel=REL)
    assert s["pnl"]["unrealised"] == pytest.approx(s["aum"] - s["cost_basis"], abs=2)
    assert s["total_return"] == pytest.approx((s["aum"] - s["cost_basis"]) / s["cost_basis"], rel=REL)
    assert s["holdings_count"] == 32


def test_cross_panel_consistency(md):
    """AUM, cost basis and total return agree across summary / holdings /
    attribution / exposure."""
    w = _w(md)
    s = compute_summary(md, w)
    h = compute_holdings(md)
    a = compute_attribution(md, w)
    e = compute_exposure(md, w)

    assert h["aum"] == pytest.approx(s["aum"], rel=REL)
    assert sum(x["market_value"] for x in h["holdings"]) == pytest.approx(s["aum"], rel=REL)
    assert a["total_return"] == pytest.approx(s["total_return"], abs=1e-9)
    assert sum(x["contribution"] for x in a["security_contribution"]) == pytest.approx(
        a["total_return"], abs=5e-6)
    assert sum(r["portfolio"] for r in e["sector"]) == pytest.approx(1.0, rel=REL)
    assert sum(r["portfolio"] for r in e["region"]) == pytest.approx(1.0, rel=REL)
    # every holding's attribution contribution == gain$ / total cost
    hd = {x["ticker"]: x for x in h["holdings"]}
    tcost = sum(x["cost_value"] for x in h["holdings"])
    for x in a["security_contribution"]:
        assert x["contribution"] == pytest.approx(hd[x["ticker"]]["unrealised_pnl"] / tcost, abs=1e-9)


def test_data_loads_timeseries(md):
    assert not md.is_snapshot
    assert len(md.dates) > 200          # ~2y of daily history
    assert len(md.holdings) == 32


def test_aum_matches_manual(md):
    out = compute_summary(md, _w(md))
    shares = md.holdings.set_index("ticker")["shares"]
    px = md.usd_prices.loc[md.dates[-1]]
    manual = float((shares * px.reindex(shares.index)).sum())
    assert out["aum"] == pytest.approx(manual, rel=REL)


def test_holdings_prices_and_value_tie_out(md):
    h = compute_holdings(md)
    # One row per position, and the market values reconcile to summary AUM.
    assert h["holdings_count"] == len(md.holdings)
    assert h["aum"] == pytest.approx(compute_summary(md, _w(md))["aum"], rel=REL)
    for r in h["holdings"]:
        # Each row exposes a current price and a bought price, and value = shares*price.
        assert r["current_price"] > 0
        assert r["cost_price"] > 0
        assert r["market_value"] == pytest.approx(r["shares"] * r["current_price"], rel=REL)
    # Weights sum to 1.
    assert sum(r["weight"] for r in h["holdings"]) == pytest.approx(1.0, rel=REL)


def test_total_return_is_cost_based_gain(md):
    # Summary return is now inception-to-date, cost-based: (value - cost) / cost,
    # matching the holdings sheet's Gain %.
    w = _w(md)
    out = compute_summary(md, w)
    h = md.holdings.set_index("ticker")
    px = md.usd_prices.loc[w.end_date]
    value = float((h["shares"] * px.reindex(h.index)).sum())
    cost = float((h["shares"] * h["cost_basis"]).sum())
    assert out["aum"] == pytest.approx(value, rel=REL)
    assert out["cost_basis"] == pytest.approx(cost, rel=REL)
    assert out["total_return"] == pytest.approx((value - cost) / cost, rel=REL)
    assert out["active_return"] is None  # S&P 500 comparison lives on the risk panel


def test_weights_sum_to_one(md):
    out = compute_exposure(md, _w(md))
    assert sum(r["portfolio"] for r in out["sector"]) == pytest.approx(1.0, rel=REL)


def test_volatility_matches_numpy(md):
    w = _w(md)
    out = compute_risk(md, w)
    r = returns_in_window(md.portfolio_value_series().pct_change().iloc[1:], w)
    manual = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    assert out["volatility"] == pytest.approx(manual, rel=REL)


def test_beta_matches_numpy(md):
    w = _w(md)
    out = compute_risk(md, w)
    p = returns_in_window(md.portfolio_value_series().pct_change().iloc[1:], w)
    b = returns_in_window(md.benchmark_index_series().pct_change().iloc[1:], w)
    aligned = pd.concat([p, b], axis=1, keys=["p", "b"]).dropna()
    manual = np.cov(aligned["p"], aligned["b"], ddof=1)[0, 1] / aligned["b"].var(ddof=1)
    assert out["beta"] == pytest.approx(float(manual), rel=REL)


def test_var_ordering_and_drawdown(md):
    out = compute_risk(md, _w(md))
    assert out["var"]["99"]["historical"] >= out["var"]["95"]["historical"] - 1e-9
    assert out["var"]["99"]["parametric"] >= out["var"]["95"]["parametric"] - 1e-9
    assert 0.0 <= out["max_drawdown"] <= 1.0


def test_attribution_contributions_sum_to_total_return(md):
    # Security contributions (gain$ / total cost) sum to the book's total return,
    # which equals the summary's cost-based total return.
    w = _w(md)
    attr = compute_attribution(md, w)
    summ = compute_summary(md, w)
    csum = sum(r["contribution"] for r in attr["security_contribution"])
    assert csum == pytest.approx(attr["total_return"], abs=5e-4)
    assert attr["total_return"] == pytest.approx(summ["total_return"], abs=5e-4)


def test_risk_benchmark_is_sp500(md):
    # Beta/alpha/excess are measured against the S&P 500, inception-to-date.
    out = compute_risk(md, _w(md))
    assert out["benchmark_name"] == "S&P 500"
    assert out["excess_return"] == pytest.approx(
        out["portfolio_return"] - out["benchmark_return"], rel=REL)
    assert out["alpha"] is not None and out["beta"] is not None


def test_chat_context_is_grounded_and_formatted(md):
    """The AI context pack is built from the same audited analytics, with numbers
    pre-formatted so the model never does arithmetic."""
    from app.ai.chat import build_context, answer
    ctx = build_context(md)
    # Cost basis ties to the sheet; percentages are pre-formatted strings.
    assert ctx["portfolio_summary"]["cost_basis"] == "$259,244"
    assert ctx["portfolio_summary"]["return_since_purchase"].endswith("%")
    assert len(ctx["holdings"]) == 32
    assert ctx["benchmark"] == "S&P 500"
    # Superlatives are pre-computed (no model sorting needed).
    assert "at" in ctx["key_facts"]["largest_position"]
    # Without a key, the endpoint degrades gracefully rather than erroring.
    import os
    if not os.environ.get("GEMINI_API_KEY"):
        r = answer("How are we doing?")
        assert r["configured"] is False and r["grounded_as_of"] == ctx["as_of"]


def test_all_windows_resolve(md):
    for code in ("MTD", "QTD", "YTD", "1Y", "ALL"):
        w = resolve_window(code, md.dates)
        assert w.base_date <= w.end_date
        compute_summary(md, w)
        compute_risk(md, w)
        compute_attribution(md, w)
