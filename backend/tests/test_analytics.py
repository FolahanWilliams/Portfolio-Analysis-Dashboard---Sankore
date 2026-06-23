"""Validate the analytics layer against independent references.

The PRD requires every metric within +/-0.1% of an independent calculation.
These tests recompute key figures with plain numpy/pandas (a different code
path) and assert they match, plus check the Brinson reconciliation identity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.config import RISK_FREE_RATE, TRADING_DAYS_PER_YEAR
from app.data.loader import load_market_data, clear_cache
from app.analytics.windows import resolve_window, returns_in_window
from app.analytics.summary import compute_summary
from app.analytics.exposure import compute_exposure
from app.analytics.risk import compute_risk
from app.analytics.attribution import compute_attribution

REL = 1e-3  # +/-0.1%


@pytest.fixture(scope="module")
def md():
    clear_cache()
    return load_market_data()


def _w(md, code="YTD"):
    return resolve_window(code, md.dates)


def test_data_loads_clean(md):
    assert len(md.dates) > 100
    assert len(md.holdings) == 14
    assert md.report.ok, md.report.issues


def test_aum_matches_manual(md):
    w = _w(md)
    out = compute_summary(md, w)
    shares = md.holdings.set_index("ticker")["shares"]
    px = md.usd_prices.loc[md.dates[-1]]
    manual = float((shares * px.reindex(shares.index)).sum())
    assert out["aum"] == pytest.approx(manual, rel=REL)


def test_total_return_matches_value_series(md):
    w = _w(md)
    out = compute_summary(md, w)
    pv = md.portfolio_value_series()
    manual = float(pv.loc[w.end_date]) / float(pv.loc[w.base_date]) - 1.0
    assert out["total_return"] == pytest.approx(manual, rel=REL)
    assert out["active_return"] == pytest.approx(
        out["total_return"] - out["benchmark_return"], rel=REL)


def test_weights_sum_to_one(md):
    out = compute_exposure(md, _w(md))
    assert sum(r["portfolio"] for r in out["sector"]) == pytest.approx(1.0, rel=REL)
    assert sum(r["benchmark"] for r in out["sector"]) == pytest.approx(1.0, rel=REL)
    assert sum(r["portfolio"] for r in out["region"]) == pytest.approx(1.0, rel=REL)


def test_hhi_and_effective_n(md):
    out = compute_exposure(md, _w(md))
    # effective N must be between 1 and the number of holdings.
    assert 1.0 <= out["concentration"]["effective_n"] <= len(md.holdings)
    assert out["concentration"]["hhi"] == pytest.approx(
        1.0 / out["concentration"]["effective_n"], rel=REL)


def test_volatility_matches_numpy(md):
    w = _w(md)
    out = compute_risk(md, w)
    pv = md.portfolio_value_series().pct_change().iloc[1:]
    r = returns_in_window(pv, w)
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


def test_var_ordering(md):
    out = compute_risk(md, _w(md))
    # 99% VaR should be at least as large a loss as 95%.
    assert out["var"]["99"]["historical"] >= out["var"]["95"]["historical"] - 1e-9
    assert out["var"]["99"]["parametric"] >= out["var"]["95"]["parametric"] - 1e-9


def test_max_drawdown_nonnegative(md):
    out = compute_risk(md, _w(md))
    assert 0.0 <= out["max_drawdown"] <= 1.0


def test_brinson_reconciles_to_active_return(md):
    """alloc + select + interaction (summed) == r_p,total - r_b,total."""
    w = _w(md)
    attr = compute_attribution(md, w)
    summ = compute_summary(md, w)
    active = summ["total_return"] - attr["benchmark_return"]
    assert attr["brinson_totals"]["total"] == pytest.approx(active, abs=5e-4)


def test_security_contribution_sums_to_portfolio_return(md):
    w = _w(md)
    attr = compute_attribution(md, w)
    total_contrib = sum(r["contribution"] for r in attr["security_contribution"])
    summ = compute_summary(md, w)
    # contribution uses base weights -> approximates the period return closely.
    assert total_contrib == pytest.approx(summ["total_return"], abs=2e-3)


def test_all_windows_resolve(md):
    for code in ("MTD", "QTD", "YTD", "1Y", "ALL"):
        w = resolve_window(code, md.dates)
        assert w.base_date <= w.end_date
        compute_summary(md, w)
        compute_risk(md, w)
        compute_attribution(md, w)
