"""Validate the analytics against independent references.

The live dataset is the GEF MCB static snapshot, so these tests validate the
snapshot-native analytics: headline figures must tie out exactly to the sheet,
weights must sum to one, contribution must reconcile to the total return, and
concentration/alerts/scenario must behave sanely.
"""
from __future__ import annotations

import pytest

from app.data.loader import load_market_data, clear_cache
from app.analytics.windows import resolve_window
from app.analytics.exposure import compute_exposure
from app.analytics import snapshot as snap


@pytest.fixture(scope="module")
def md():
    clear_cache()
    return load_market_data()


def _w(md):
    return resolve_window("YTD", md.dates)


def test_data_loads_snapshot(md):
    assert md.is_snapshot
    assert len(md.dates) == 1
    assert len(md.holdings) == 32
    assert md.report.ok, md.report.issues


def test_summary_ties_out_to_sheet(md):
    s = snap.snapshot_summary(md)
    assert s["aum"] == pytest.approx(248236, abs=60)
    assert s["cost_basis"] == pytest.approx(259244, abs=60)
    assert s["pnl"]["unrealised"] == pytest.approx(-11008, abs=60)
    assert s["total_return"] == pytest.approx(-0.0425, abs=1e-3)
    assert s["positions_at_loss"] == 19


def test_contribution_reconciles_to_total_return(md):
    a = snap.snapshot_attribution(md)
    total = sum(r["contribution"] for r in a["security_contribution"])
    assert total == pytest.approx(a["total_return"], rel=1e-6)
    by_sector = sum(r["contribution"] for r in a["sector_contribution"])
    assert by_sector == pytest.approx(a["total_return"], rel=1e-6)


def test_exposure_weights_sum_to_one(md):
    exp = compute_exposure(md, _w(md))
    assert sum(r["portfolio"] for r in exp["sector"]) == pytest.approx(1.0, rel=1e-6)
    assert sum(r["benchmark"] for r in exp["sector"]) == pytest.approx(1.0, rel=1e-6)
    # Active weights are a zero-sum game across sectors.
    assert sum(r["active"] for r in exp["sector"]) == pytest.approx(0.0, abs=1e-6)


def test_risk_concentration(md):
    r = snap.snapshot_risk(md)
    assert r["hhi"] == pytest.approx(1.0 / r["effective_n"], rel=1e-6)
    assert 1.0 <= r["effective_n"] <= 32
    assert 0 < r["top5_weight"] <= 1.0
    assert r["positions"] == 32
    assert r["assumed_beta"] > 1.0  # tech/semis-heavy book
    assert r["worst"]["return"] < 0


def test_alerts_shape_and_order(md):
    out = snap.snapshot_alerts(md, compute_exposure(md, _w(md)))
    assert set(out["counts"]) == {"breach", "warning"}
    sev = [a["severity"] for a in out["alerts"]]
    assert sev == sorted(sev, key=lambda s: 0 if s == "breach" else 1)
    for a in out["alerts"]:
        assert a["value"] is not None and a["threshold"] is not None


def test_scenario_market_down_reprices_lower(md):
    base = snap.snapshot_scenario(md, market=0.0)
    down = snap.snapshot_scenario(md, market=-0.10)
    assert down["new_aum"] < base["new_aum"]
    assert down["pnl_change"] < 0
    assert down["portfolio_return"] == pytest.approx(
        down["pnl_change"] / down["base_aum"], rel=1e-9)
    # Leveraged 2x ETFs should fall hardest under a market drop.
    assert down["top_losers"][0]["ticker"] in {"MUU", "MRVU"}


def test_scenario_zero_shock_is_flat(md):
    flat = snap.snapshot_scenario(md, market=0.0)
    assert flat["pnl_change"] == pytest.approx(0.0, abs=1e-6)
