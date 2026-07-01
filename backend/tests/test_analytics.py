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


def _w(md, code="1Y"):
    return resolve_window(code, md.dates)


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


def test_all_windows_resolve(md):
    for code in ("MTD", "QTD", "YTD", "1Y", "ALL"):
        w = resolve_window(code, md.dates)
        assert w.base_date <= w.end_date
        compute_summary(md, w)
        compute_risk(md, w)
        compute_attribution(md, w)
