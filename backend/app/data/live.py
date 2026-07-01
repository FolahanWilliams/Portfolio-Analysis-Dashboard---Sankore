"""On-demand live price refresh from Yahoo Finance.

Powers the dashboard's "Refresh prices" button. Rather than auto-updating, the
frontend calls the endpoints with `?live=1` when the user clicks refresh; this
module fetches the most recent prices from Yahoo, splices them onto the bundled
historical series (so the latest point becomes "now"), and returns a fresh
MarketData for that request. Result is cached briefly so one button press
(which fans out to several endpoints) triggers a single fetch.

Transport is stdlib urllib against Yahoo's public chart API — no extra runtime
dependency, and it respects HTTPS_PROXY. If Yahoo throttles the request (cloud
IPs can be rate-limited), we fall back to the bundled data and flag it, so the
dashboard never breaks.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import time
import urllib.parse
import urllib.request

import pandas as pd

from app.data.loader import MarketData, load_market_data

_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
_TTL_SECONDS = 60
_cache: dict[str, object] = {"md": None, "info": None, "ts": 0.0}


def _fetch_recent(ticker: str, rng: str = "5d") -> dict[str, float]:
    url = _CHART + urllib.parse.quote(ticker) + "?" + urllib.parse.urlencode(
        {"range": rng, "interval": "1d", "events": "div,splits"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    res = payload["chart"]["result"][0]
    ts = res.get("timestamp") or []
    ind = res["indicators"]
    adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
    close = adj if adj else ind["quote"][0].get("close")
    out: dict[str, float] = {}
    for t, c in zip(ts, close or []):
        if c is None:
            continue
        d = dt.datetime.utcfromtimestamp(t).date().isoformat()
        out[d] = round(float(c), 4)
    return out


def _refresh(base: MarketData) -> tuple[MarketData, dict]:
    tickers = list(base.usd_prices.columns)
    recent: dict[str, dict[str, float]] = {}
    failed: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_recent, t): t for t in tickers}
        for fut in concurrent.futures.as_completed(futures):
            t = futures[fut]
            try:
                s = fut.result()
                if s:
                    recent[t] = s
                else:
                    failed.append(t)
            except Exception:
                failed.append(t)

    updated = len(recent)
    # If Yahoo throttled most of the book, don't corrupt the series -- fall back.
    if updated < max(1, len(tickers) // 2):
        return base, {
            "ok": False,
            "error": "Yahoo refresh throttled/unavailable — showing last committed prices.",
            "updated": updated,
            "failed": failed,
            "refreshed_at": dt.datetime.now().isoformat(timespec="seconds"),
            "as_of": base.dates[-1].date().isoformat(),
        }

    # Splice recent prices onto the bundled history.
    new_dates = set()
    for s in recent.values():
        new_dates.update(s.keys())
    full_index = base.usd_prices.index.union(
        pd.to_datetime(sorted(new_dates))
    ).sort_values()
    usd = base.usd_prices.reindex(full_index)
    for t, s in recent.items():
        for d, px in s.items():
            usd.loc[pd.Timestamp(d), t] = px
    usd = usd.ffill().bfill()

    fx = base.fx_rates.reindex(full_index).ffill().bfill() if not base.fx_rates.empty else base.fx_rates

    md = MarketData(
        holdings=base.holdings,
        benchmark=base.benchmark,
        usd_prices=usd,
        fx_rates=fx,
        currency_of=base.currency_of,
        dates=full_index,
        report=base.report,
    )
    info = {
        "ok": True,
        "updated": updated,
        "failed": failed,
        "refreshed_at": dt.datetime.now().isoformat(timespec="seconds"),
        "as_of": full_index[-1].date().isoformat(),
    }
    return md, info


def get_live_market_data() -> tuple[MarketData, dict]:
    """Return live-refreshed MarketData (cached ~60s across the fan-out calls)."""
    now = time.time()
    if _cache["md"] is not None and now - float(_cache["ts"]) < _TTL_SECONDS:
        return _cache["md"], _cache["info"]  # type: ignore[return-value]
    md, info = _refresh(load_market_data())
    _cache["md"], _cache["info"], _cache["ts"] = md, info, now
    return md, info
