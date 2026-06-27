"""Ingest the GEF MCB portfolio monitor (a static daily snapshot) into the
app's data files.

The boss's sheet is a single-day snapshot, not a price history. Per his
instruction the data stays static (today's prices, no live pulling), so we do
NOT fabricate a price history. We emit:

    holdings.csv   the 32 real positions (ticker, name, sector, region,
                   currency, shares, cost_basis/share, realised_pnl)
    benchmark.csv  a Nasdaq-100 proxy (sector weights for active-weight vs
                   benchmark) -- weights only; no prices needed in snapshot mode
    prices.csv     ONE row per ticker, dated to the snapshot (today's price)
    fx.csv         USD = 1.0 (the whole book is USD)

Headline figures tie out exactly to the sheet (AUM $248,236, P&L -$11,008)
because cost basis per share is derived from the sheet's exact Cost Basis
column, not the rounded purchase price.
"""
from __future__ import annotations

import csv
import os
from datetime import date

SRC = os.path.join(os.path.dirname(__file__), "..", "data", "GEF_MCB_Monitor.csv")
OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "mock_data"))
SNAPSHOT_DATE = date(2026, 6, 2)

# The sheet's right-hand "clean" grouping -> tidy sector labels.
SECTOR_MAP = {
    "Semis & Equip": "Semiconductors",
    "Software": "Software",
    "IT Svcs/Distrib/Net": "IT Services & Networking",
    "Comm Svcs/Internet": "Communication Services",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Utilities/Power": "Utilities",
    "Materials": "Materials",
    "Healthcare": "Healthcare",
    "Space (Thematic)": "Space (Thematic)",
}

# Domicile of the non-US listings (everything trades in USD; this only colours
# the geographic-exposure view). Everything else defaults to US.
REGION_OVERRIDE = {"TSM": "Asia", "AZN": "Europe"}


def _money(s: str) -> float:
    s = (s or "").strip().replace("$", "").replace(",", "").replace("%", "")
    if not s or s in {"-", "—"}:
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def parse_holdings() -> list[dict]:
    with open(SRC, newline="") as f:
        rows = list(csv.reader(f))
    # Find the holdings table header, then read until TOTAL.
    start = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Ticker")
    holdings = []
    for r in rows[start + 1:]:
        ticker = (r[0] or "").strip()
        if ticker == "" or ticker.upper() == "TOTAL":
            break
        units = _money(r[5])
        cost_basis_total = _money(r[6])     # exact, so P&L ties out
        current_price = _money(r[4])
        if units <= 0:
            continue
        clean = (r[16].strip() if len(r) > 16 and r[16].strip() else r[2].strip())
        holdings.append({
            "ticker": ticker,
            "name": (r[1] or "").strip(),
            "sector": SECTOR_MAP.get(clean, clean),
            "region": REGION_OVERRIDE.get(ticker, "US"),
            "currency": "USD",
            "shares": units,
            "cost_basis": round(cost_basis_total / units, 4),  # per share
            "realised_pnl": 0.0,
            "_current": current_price,
        })
    return holdings


# Nasdaq-100 proxy: representative constituents with sector + index-style
# weight (held names + a few mega-caps the fund doesn't own, so active weights
# are meaningful). Snapshot mode uses these weights only -- no prices needed.
BENCHMARK = [
    # ticker, name, sector, region, weight
    ("AAPL", "Apple", "IT Services & Networking", "US", 0.090),
    ("MSFT", "Microsoft", "Software", "US", 0.085),
    ("NVDA", "NVIDIA", "Semiconductors", "US", 0.080),
    ("AMZN", "Amazon.com", "Communication Services", "US", 0.060),
    ("AVGO", "Broadcom", "Semiconductors", "US", 0.050),
    ("META", "Meta Platforms", "Communication Services", "US", 0.045),
    ("GOOGL", "Alphabet", "Communication Services", "US", 0.045),
    ("TSLA", "Tesla", "Industrials", "US", 0.030),
    ("COST", "Costco", "Industrials", "US", 0.025),
    ("NFLX", "Netflix", "Communication Services", "US", 0.025),
    ("AMD", "Advanced Micro Devices", "Semiconductors", "US", 0.022),
    ("PEP", "PepsiCo", "Industrials", "US", 0.020),
    ("ADBE", "Adobe", "Software", "US", 0.018),
    ("CRM", "Salesforce", "Software", "US", 0.016),
    ("AMAT", "Applied Materials", "Semiconductors", "US", 0.016),
    ("MU", "Micron Technology", "Semiconductors", "US", 0.014),
    ("LRCX", "Lam Research", "Semiconductors", "US", 0.014),
    ("INTU", "Intuit", "Software", "US", 0.016),
    ("NOW", "ServiceNow", "Software", "US", 0.014),
    ("PANW", "Palo Alto Networks", "Software", "US", 0.014),
    ("MRVL", "Marvell Technology", "Semiconductors", "US", 0.010),
    ("ANET", "Arista Networks", "IT Services & Networking", "US", 0.012),
    ("TSM", "Taiwan Semiconductor", "Semiconductors", "Asia", 0.010),
    ("AZN", "AstraZeneca", "Healthcare", "Europe", 0.010),
    ("VRTX", "Vertex Pharmaceuticals", "Healthcare", "US", 0.012),
    ("LIN", "Linde", "Materials", "US", 0.012),
    ("CEG", "Constellation Energy", "Utilities", "US", 0.010),
    ("CSCO", "Cisco", "IT Services & Networking", "US", 0.014),
]


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    holdings = parse_holdings()
    iso = SNAPSHOT_DATE.isoformat()

    # holdings.csv
    with open(os.path.join(OUT_DIR, "holdings.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "sector", "region", "currency",
                    "shares", "cost_basis", "realised_pnl"])
        for h in holdings:
            w.writerow([h["ticker"], h["name"], h["sector"], h["region"],
                        h["currency"], h["shares"], h["cost_basis"], h["realised_pnl"]])

    # prices.csv -- single snapshot date per holding
    with open(os.path.join(OUT_DIR, "prices.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "ticker", "price"])
        for h in holdings:
            w.writerow([iso, h["ticker"], round(h["_current"], 4)])

    # benchmark.csv -- renormalise weights to 1.0
    total_w = sum(b[4] for b in BENCHMARK)
    with open(os.path.join(OUT_DIR, "benchmark.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "sector", "region", "currency", "weight"])
        for ticker, name, sector, region, weight in BENCHMARK:
            w.writerow([ticker, name, sector, region, "USD", round(weight / total_w, 6)])

    # fx.csv -- all USD
    with open(os.path.join(OUT_DIR, "fx.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "currency", "rate_to_usd"])
        w.writerow([iso, "USD", 1.0])

    aum = sum(h["shares"] * h["_current"] for h in holdings)
    cost = sum(h["shares"] * h["cost_basis"] for h in holdings)
    print(f"Wrote {len(holdings)} holdings to {OUT_DIR}")
    print(f"  AUM        ${aum:,.0f}")
    print(f"  Cost basis ${cost:,.0f}")
    print(f"  P&L        ${aum - cost:,.0f}  ({(aum/cost - 1)*100:.2f}%)")
    print(f"  Benchmark  {len(BENCHMARK)} constituents (Nasdaq-100 proxy)")
    print(f"  Snapshot   {iso}")


if __name__ == "__main__":
    main()
