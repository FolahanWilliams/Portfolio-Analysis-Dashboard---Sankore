"""Reconcile the committed data to the boss's GEF holdings sheet, and switch the
benchmark to the S&P 500.

1. Overwrite the latest price row for each holding with the sheet's exact
   "Current Price" (GoogleFinance-derived), so AUM, market value and gain$/gain%
   tie out to the sheet to the cent ($252,672 / -$6,571 / -2.53%).
2. Fetch the S&P 500 index (^GSPC) daily history over the same window and add it
   to prices.csv, so beta / alpha / volatility can be measured against it.
3. Rewrite benchmark.csv to a single S&P 500 row (the market index), replacing
   the old Nasdaq-100 proxy basket.

Cost basis is unchanged -- it already matches the sheet (Cost Basis / Units).
"""
from __future__ import annotations

import csv
import datetime as dt
import os

import pandas as pd
import requests

DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "mock_data"))
UA = {"User-Agent": "Mozilla/5.0"}

# Ticker -> current price, verbatim from the boss's sheet ("Current Price").
CURRENT = {
    "SNX": 262.38, "EWW": 75.01, "ZM": 90.39, "MRVL": 279.11, "MUU": 904.36,
    "ADBE": 211.28, "MU": 1065.32, "MRVU": 201.16, "ANET": 169.51, "TSM": 451.46,
    "LNG": 237.60, "G": 28.59, "AMAT": 668.14, "LRCX": 400.50, "AVGO": 372.40,
    "GOOGL": 361.40, "DAL": 94.20, "META": 625.16, "VST": 152.63, "NOW": 105.17,
    "PANW": 355.23, "FNV": 212.26, "CRM": 164.35, "AMZN": 242.85, "CDW": 142.74,
    "INTU": 270.68, "MSFT": 384.69, "AZN": 184.67, "CPRT": 28.88, "CRDO": 266.75,
    "PEG": 80.51, "NASA": 30.52,
}
SP500 = "^GSPC"


def _fetch_chart(symbol: str, rng: str = "2y") -> dict[str, float]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = requests.get(url, params={"range": rng, "interval": "1d", "events": "div,splits"},
                     headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = res.get("timestamp") or []
    ind = res["indicators"]
    adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
    close = adj if adj else ind["quote"][0].get("close")
    out = {}
    for t, c in zip(ts, close or []):
        if c is None:
            continue
        out[dt.datetime.utcfromtimestamp(t).date().isoformat()] = round(float(c), 4)
    return out


def main() -> None:
    prices = pd.read_csv(os.path.join(DATA, "prices.csv"))
    prices["date"] = pd.to_datetime(prices["date"]).dt.date.astype(str)
    # Anchor to the holdings' latest date (not the matrix max, which may include
    # a benchmark series that trades an extra day) so re-runs don't drift.
    last = prices[prices["ticker"].isin(CURRENT)]["date"].max()
    prices = prices[prices["date"] <= last]

    # 1. Override the latest holding prices with the sheet's current prices.
    updated = 0
    for tkr, px in CURRENT.items():
        mask = (prices["ticker"] == tkr) & (prices["date"] == last)
        if mask.any():
            prices.loc[mask, "price"] = px
        else:
            prices = pd.concat([prices, pd.DataFrame([{"date": last, "ticker": tkr, "price": px}])],
                               ignore_index=True)
        updated += 1

    # 2. Fetch the S&P 500 index and add it to the price matrix.
    sp = {d: p for d, p in _fetch_chart(SP500).items() if d <= last}
    sp_rows = pd.DataFrame([{"date": d, "ticker": SP500, "price": p} for d, p in sp.items()])
    prices = prices[prices["ticker"] != SP500]  # idempotent re-run
    prices = pd.concat([prices, sp_rows], ignore_index=True)
    prices = prices.sort_values(["date", "ticker"]).reset_index(drop=True)
    prices.to_csv(os.path.join(DATA, "prices.csv"), index=False)

    # 3. Benchmark = S&P 500 (single market index).
    with open(os.path.join(DATA, "benchmark.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "sector", "region", "currency", "weight"])
        w.writerow([SP500, "S&P 500", "Index", "US", "USD", 1.0])

    # Report AUM tie-out.
    h = pd.read_csv(os.path.join(DATA, "holdings.csv"))
    px_last = prices[prices["date"] == last].set_index("ticker")["price"]
    aum = float((h.set_index("ticker")["shares"] * px_last.reindex(h["ticker"]).values).sum())
    cost = float((h["shares"] * h["cost_basis"]).sum())
    print(f"Updated {updated} holding prices at {last}")
    print(f"S&P 500 rows: {len(sp_rows)}  ({min(sp)} -> {max(sp)})")
    print(f"AUM = ${aum:,.0f}  cost basis = ${cost:,.0f}  gain = ${aum-cost:,.0f} ({(aum-cost)/cost*100:.2f}%)")


if __name__ == "__main__":
    main()
