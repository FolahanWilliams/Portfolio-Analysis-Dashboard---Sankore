"""FastAPI application: four thin REST endpoints over the analytics layer.

    GET /summary       Portfolio Summary
    GET /exposure      Sector & Geographic Exposure
    GET /risk          Risk Metrics
    GET /attribution   Performance Attribution
    GET /health        liveness + data-quality report
    GET /meta          dataset metadata (window list, as-of, holdings count)

Each endpoint accepts ?window=MTD|QTD|YTD|1Y|ALL. The route handlers do no
fund math -- they resolve the window, call a pure analytics function, and
attach the data-quality report. JSON only; the backend never formats for
display.
"""
from __future__ import annotations

import math

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import DEFAULT_WINDOW, SUPPORTED_WINDOWS
from app.data.loader import load_market_data
from app.data.live import get_live_market_data
from app.analytics.windows import resolve_window
from app.analytics.summary import compute_summary
from app.analytics.exposure import compute_exposure
from app.analytics.risk import compute_risk
from app.analytics.attribution import compute_attribution
from app.analytics.alerts import compute_alerts
from app.analytics.holdings import compute_holdings
from app.analytics.scenario import apply_scenario
from app.analytics import snapshot as snap
from app.models.schemas import Window

app = FastAPI(
    title="Portfolio Intelligence Dashboard API",
    version="0.1.0",
    description="Analytics backend for the Portfolio Intelligence Dashboard prototype.",
)

# Vite dev server + common localhost origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ScenarioRequest(BaseModel):
    market: float = Field(0.0, description="Market shock, e.g. -0.10 for -10%")
    sector_shocks: dict[str, float] = Field(default_factory=dict)
    fx_shocks: dict[str, float] = Field(default_factory=dict)


def _sanitize(obj):
    """Recursively replace NaN/Inf with None so the JSON is strictly valid."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def _respond(payload: dict, md, live_info: dict | None = None) -> JSONResponse:
    payload = dict(payload)
    payload["data_quality"] = md.report.as_dict()
    if live_info is not None:
        payload["live"] = live_info
    return JSONResponse(content=_sanitize(payload))


def _get_market_data(live: bool):
    """Return (MarketData, live_info) — refreshed from Yahoo when live=True."""
    if live:
        return get_live_market_data()
    return load_market_data(), None


def _load_and_resolve(window: str, live: bool = False):
    md, info = _get_market_data(live)
    if len(md.dates) == 0:
        return md, None, info
    return md, resolve_window(window, md.dates), info


@app.get("/health")
def health():
    md = load_market_data()
    return {
        "status": "ok",
        "has_data": len(md.dates) > 0,
        "data_quality": md.report.as_dict(),
    }


@app.get("/meta")
def meta(live: bool = Query(False, description="Refresh prices from Yahoo Finance")):
    md, info = _get_market_data(live)
    if len(md.dates) == 0:
        return {"has_data": False, "windows": SUPPORTED_WINDOWS}
    return {
        "has_data": True,
        "is_snapshot": md.is_snapshot,
        "windows": SUPPORTED_WINDOWS,
        "default_window": DEFAULT_WINDOW,
        "as_of": md.dates[-1].date().isoformat(),
        "inception": md.dates[0].date().isoformat(),
        "holdings_count": int(len(md.holdings)),
        "base_currency": "USD",
        "benchmark": "S&P 500",
        "price_source": "snapshot" if md.is_snapshot else "Yahoo Finance",
        "live": info,
        "provenance": (
            "Static snapshot — holdings, weights, exposure, concentration and "
            "P&L are computed directly from the GEF MCB monitor as of "
            f"{md.dates[-1].date().isoformat()}. With only one day of prices, "
            "statistical risk (volatility, beta, VaR, drawdown, correlation) and "
            "time-window/Brinson returns are not shown — they populate "
            "automatically once a price history is captured."
        ) if md.is_snapshot else None,
        "sectors": sorted(md.holdings["sector"].unique().tolist()),
        "regions": sorted(md.holdings["region"].unique().tolist()),
        "data_quality": md.report.as_dict(),
    }


def _empty_response():
    return JSONResponse(status_code=503,
                        content={"error": "no_data",
                                 "detail": "Mock data missing or unreadable."})


@app.get("/summary")
def summary(
    window: Window = Query(default=Window(DEFAULT_WINDOW)),
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, w, info = _load_and_resolve(window.value, live)
    if w is None:
        return _empty_response()
    out = snap.snapshot_summary(md) if md.is_snapshot else compute_summary(md, w)
    return _respond(out, md, info)


@app.get("/holdings")
def holdings(
    window: Window = Query(default=Window(DEFAULT_WINDOW)),
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, w, info = _load_and_resolve(window.value, live)
    if w is None:
        return _empty_response()
    return _respond(compute_holdings(md), md, info)


@app.get("/exposure")
def exposure(
    window: Window = Query(default=Window(DEFAULT_WINDOW)),
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, w, info = _load_and_resolve(window.value, live)
    if w is None:
        return _empty_response()
    # Exposure is time-series-free, so it works unchanged in either mode.
    return _respond(compute_exposure(md, w), md, info)


@app.get("/risk")
def risk(
    window: Window = Query(default=Window(DEFAULT_WINDOW)),
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, w, info = _load_and_resolve(window.value, live)
    if w is None:
        return _empty_response()
    out = snap.snapshot_risk(md) if md.is_snapshot else compute_risk(md, w)
    return _respond(out, md, info)


@app.get("/attribution")
def attribution(
    window: Window = Query(default=Window(DEFAULT_WINDOW)),
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, w, info = _load_and_resolve(window.value, live)
    if w is None:
        return _empty_response()
    out = snap.snapshot_attribution(md) if md.is_snapshot else compute_attribution(md, w)
    return _respond(out, md, info)


@app.get("/alerts")
def alerts(
    window: Window = Query(default=Window(DEFAULT_WINDOW)),
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, w, info = _load_and_resolve(window.value, live)
    if w is None:
        return _empty_response()
    if md.is_snapshot:
        out = snap.snapshot_alerts(md, compute_exposure(md, w))
    else:
        out = compute_alerts(md, w)
    return _respond(out, md, info)


@app.post("/scenario")
def scenario(
    req: ScenarioRequest,
    live: bool = Query(False, description="Refresh prices from Yahoo Finance"),
):
    md, info = _get_market_data(live)
    if len(md.dates) == 0:
        return _empty_response()
    if md.is_snapshot:
        result = snap.snapshot_scenario(md, req.market, req.sector_shocks, req.fx_shocks)
    else:
        result = apply_scenario(md, req.market, req.sector_shocks, req.fx_shocks)
    return _respond(result, md, info)
