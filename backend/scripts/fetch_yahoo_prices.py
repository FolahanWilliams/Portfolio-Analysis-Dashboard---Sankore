"""Pull real daily price history from Yahoo Finance for the portfolio universe.

Positions and cost basis come from the GEF sheet (ingest_portfolio.py); this
script replaces the single-day snapshot in prices.csv with a real ~2-year daily
history from Yahoo. Once prices.csv has more than one date the loader flips out
of snapshot mode automatically, so the full time-series analytics (volatility,
beta, VaR, drawdown, correlation, window/Brinson returns) come alive with real
data.

Transport: uses the `yfinance` module when its network stack works; falls back
to Yahoo's public chart API over plain HTTPS (via requests) when yfinance's
curl_cffi backend is blocked (e.g. behind a corporate/CI proxy). Same data
source either way. Adjusted close is used so splits/dividends don't distort
returns while the latest price still equals the live market price.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import time

import pandas as pd
import requests

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "mock_data"))
RANGE = "2y"
UA = {"User-Agent": "Mozilla/5.0"}

# A few sheet tickers don't map to their Yahoo symbol (or are mislabelled in the
# sheet); remap the ones we can, drop/flag the rest.
YAHOO_SYMBOL = {
    # sheet -> yahoo   (identity unless noted)
}


def _yfinance_works() -> bool:
    try:
        import yfinance as yf  # noqa
        df = yf.Ticker("MU").history(period="5d")
        return len(df) > 0
    except Exception:
        return False


def _fetch_yfinance(tickers: list[str]) -> dict[str, dict[str, float]]:
    import yfinance as yf
    data = yf.download(tickers, period=RANGE, interval="1d",
                       auto_adjust=True, progress=False, threads=True)
    close = data["Close"] if "Close" in data else data
    out: dict[str, dict[str, float]] = {}
    for t in tickers:
        s = close[t].dropna() if t in close else pd.Series(dtype=float)
        out[t] = {d.date().isoformat(): round(float(v), 4) for d, v in s.items()}
    return out


def _fetch_chart_api(ticker: str) -> dict[str, float]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": RANGE, "interval": "1d", "events": "div,splits"}
    r = requests.get(url, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
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


def universe() -> list[str]:
    tickers: set[str] = set()
    for fn in ("holdings.csv", "benchmark.csv"):
        path = os.path.join(OUT_DIR, fn)
        if os.path.exists(path):
            df = pd.read_csv(path)
            tickers.update(str(t).strip() for t in df["ticker"])
    return sorted(tickers)


def main() -> None:
    tickers = universe()
    yahoo = [YAHOO_SYMBOL.get(t, t) for t in tickers]
    series: dict[str, dict[str, float]] = {}
    failed: list[str] = []

    if _yfinance_works():
        print("Using yfinance transport")
        try:
            fetched = _fetch_yfinance(yahoo)
            for sheet_t, y in zip(tickers, yahoo):
                s = fetched.get(y, {})
                if s:
                    series[sheet_t] = s
                else:
                    failed.append(sheet_t)
        except Exception as exc:  # pragma: no cover
            print(f"  yfinance bulk failed ({exc}); falling back to chart API")
            series.clear()

    if not series:
        print("Using Yahoo chart API transport (requests)")
        for sheet_t, y in zip(tickers, yahoo):
            try:
                s = _fetch_chart_api(y)
            except Exception as exc:
                s = {}
                print(f"  {sheet_t}: error {str(exc)[:60]}")
            if s:
                series[sheet_t] = s
            else:
                failed.append(sheet_t)
            time.sleep(0.15)  # be polite

    # Build a long-format prices.csv over the union of dates.
    rows = []
    all_dates: set[str] = set()
    for t, s in series.items():
        for d, px in s.items():
            rows.append((d, t, px))
            all_dates.add(d)
    rows.sort()
    with open(os.path.join(OUT_DIR, "prices.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "ticker", "price"])
        w.writerows(rows)

    # fx.csv -- the whole book is USD.
    dmin, dmax = min(all_dates), max(all_dates)
    with open(os.path.join(OUT_DIR, "fx.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "currency", "rate_to_usd"])
        w.writerow([dmin, "USD", 1.0])
        w.writerow([dmax, "USD", 1.0])

    print(f"\nWrote {len(rows)} price rows for {len(series)}/{len(tickers)} tickers")
    print(f"  dates: {dmin} -> {dmax}")
    if failed:
        print(f"  UNRESOLVED (skipped, flagged by loader): {', '.join(failed)}")


if __name__ == "__main__":
    main()
