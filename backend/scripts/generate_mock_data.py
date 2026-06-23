"""Generate deterministic mock data for the Portfolio Intelligence Dashboard.

Produces four CSVs that mirror what a real custodian / market-data export
would provide, in the shape the workflow map advertised:

    holdings.csv    portfolio positions (ticker, name, sector, region,
                    currency, shares, cost_basis, realised_pnl)
    benchmark.csv   benchmark constituents and weights (a superset of holdings)
    prices.csv      daily native-currency close per ticker (Nov 2025 -> Jun 2026)
    fx.csv          daily rate to USD per currency

The universe is an S&P-tech-style basket. A few non-USD listings (EUR, HKD)
exercise the currency-normalisation path. Prices are generated with a shared
market factor plus idiosyncratic noise so betas and correlations are realistic.

Everything is seeded, so the data is identical on every run -- the prototype
must be reproducible.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

# Seed chosen so the mock market shows a healthy up-period (~+19%) with a
# realistic mid-period correction (~-12% drawdown) and dispersion between
# winners and losers -- a representative demo, not a one-way line.
SEED = 31
RNG = np.random.default_rng(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "mock_data")
OUT_DIR = os.path.abspath(OUT_DIR)

START = date(2025, 11, 3)   # "November last year +"
END = date(2026, 6, 19)     # last business day before the 23rd
TRADING_DAYS_PER_YEAR = 252

# --- Universe ---------------------------------------------------------------
# ticker, name, sector (tech sub-sector), region, currency,
# annual_drift, annual_vol, beta_to_market, start_price (native)
UNIVERSE = [
    ("AAPL",  "Apple Inc.",            "Hardware",      "US",     "USD", 0.18, 0.26, 1.05, 225.0),
    ("MSFT",  "Microsoft Corp.",       "Software",      "US",     "USD", 0.20, 0.24, 1.00, 415.0),
    ("NVDA",  "NVIDIA Corp.",          "Semiconductors","US",     "USD", 0.35, 0.45, 1.55, 120.0),
    ("GOOGL", "Alphabet Inc.",         "Internet",      "US",     "USD", 0.16, 0.27, 1.05, 165.0),
    ("AMZN",  "Amazon.com Inc.",       "Internet",      "US",     "USD", 0.17, 0.30, 1.15, 185.0),
    ("META",  "Meta Platforms Inc.",   "Internet",      "US",     "USD", 0.22, 0.33, 1.20, 560.0),
    ("AVGO",  "Broadcom Inc.",         "Semiconductors","US",     "USD", 0.28, 0.36, 1.30, 165.0),
    ("AMD",   "Advanced Micro Devices","Semiconductors","US",     "USD", 0.20, 0.48, 1.60, 150.0),
    ("CRM",   "Salesforce Inc.",       "Software",      "US",     "USD", 0.12, 0.30, 1.10, 280.0),
    ("ADBE",  "Adobe Inc.",            "Software",      "US",     "USD", 0.10, 0.29, 1.05, 520.0),
    ("ORCL",  "Oracle Corp.",          "Software",      "US",     "USD", 0.19, 0.28, 0.95, 175.0),
    ("QCOM",  "Qualcomm Inc.",         "Semiconductors","US",     "USD", 0.14, 0.34, 1.25, 170.0),
    ("ASML",  "ASML Holding NV",       "Semiconductors","Europe", "EUR", 0.16, 0.32, 1.20, 680.0),
    ("SAP",   "SAP SE",                "Software",      "Europe", "EUR", 0.13, 0.25, 0.90, 200.0),
    ("0700",  "Tencent Holdings",      "Internet",      "Asia",   "HKD", 0.15, 0.34, 1.05, 400.0),
    ("TSM",   "Taiwan Semiconductor",  "Semiconductors","Asia",   "USD", 0.24, 0.35, 1.25, 190.0),
]

# Portfolio: which names we hold, and how many shares (active vs the benchmark).
# Some benchmark names are deliberately not held (QCOM) and weights differ, so
# active weights and Brinson attribution are non-trivial.
HOLDINGS = {
    # ticker: (shares, cost_basis_native, realised_pnl_usd)
    "AAPL":  (4200,  198.0,  12000.0),
    "MSFT":  (1600,  380.0,   8000.0),
    "NVDA":  (9000,   98.0,  -4000.0),
    "GOOGL": (3800,  150.0,   3000.0),
    "AMZN":  (2600,  170.0,   0.0),
    "META":  (1100,  500.0,   6500.0),
    "AVGO":  (5200,  140.0,   2000.0),
    "AMD":   (3400,  165.0,  -7500.0),
    "CRM":   (1500,  295.0,   0.0),
    "ADBE":  (700,   540.0,  -1500.0),
    "ORCL":  (2900,  150.0,   4200.0),
    "ASML":  (450,   640.0,   0.0),
    "SAP":   (2300,  185.0,   1800.0),
    "0700":  (3500,  360.0,   0.0),
}

# Benchmark weights (S&P-tech-style). Superset of holdings; sums to 1.0.
BENCHMARK_WEIGHTS = {
    "AAPL": 0.16, "MSFT": 0.16, "NVDA": 0.15, "GOOGL": 0.09, "AMZN": 0.09,
    "META": 0.08, "AVGO": 0.06, "AMD": 0.03, "CRM": 0.03, "ADBE": 0.03,
    "ORCL": 0.03, "QCOM": 0.02, "ASML": 0.03, "SAP": 0.02, "0700": 0.01,
    "TSM": 0.01,
}

FX_BASE = {"USD": 1.0, "EUR": 1.08, "HKD": 0.1282}
FX_ANNUAL_VOL = {"USD": 0.0, "EUR": 0.07, "HKD": 0.02}


def business_days(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d += timedelta(days=1)
    return days


# Market factor: positive drift with a realistic mid-period pullback so the
# demo shows an up-market that still has drawdown, dispersion, and risk to see.
MARKET_DRIFT = 0.16   # annual
MARKET_VOL = 0.15     # annual


def gbm_path(start_price: float, drift: float, vol: float, shocks: np.ndarray) -> np.ndarray:
    """Daily GBM close path given a vector of standard-normal shocks."""
    dt = 1.0 / TRADING_DAYS_PER_YEAR
    daily = (drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * shocks
    log_path = np.cumsum(daily)
    return start_price * np.exp(log_path)


def factor_price_path(p0: float, beta: float, total_vol: float, stock_drift: float,
                      market_log_ret: np.ndarray, idio_shocks: np.ndarray) -> np.ndarray:
    """Single-factor price path: r_i = alpha + beta * r_market + idiosyncratic.

    Alpha is sized so the stock's expected annual return matches its target
    (`stock_drift`), and idiosyncratic vol so its *total* annualised vol matches
    its target given market exposure -- a faithful one-factor model that yields
    realistic dispersion between names.
    """
    dt = 1.0 / TRADING_DAYS_PER_YEAR
    idio_var = max(total_vol**2 - (beta * MARKET_VOL) ** 2, (0.10) ** 2)
    idio_vol = np.sqrt(idio_var)
    alpha = stock_drift - beta * MARKET_DRIFT
    idio = idio_vol * np.sqrt(dt) * idio_shocks - 0.5 * idio_var * dt
    daily_log = alpha * dt + beta * market_log_ret + idio
    return p0 * np.exp(np.cumsum(daily_log))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    days = business_days(START, END)
    n = len(days)
    iso = [d.isoformat() for d in days]

    # Shared market factor (with drift) -> realistic correlations / betas.
    dt = 1.0 / TRADING_DAYS_PER_YEAR
    market_shocks = RNG.standard_normal(n)
    market_log_ret = ((MARKET_DRIFT - 0.5 * MARKET_VOL**2) * dt
                      + MARKET_VOL * np.sqrt(dt) * market_shocks)

    # --- prices.csv (native currency) --------------------------------------
    price_rows = []
    for ticker, name, sector, region, ccy, drift, vol, beta, p0 in UNIVERSE:
        idio = RNG.standard_normal(n)
        path = factor_price_path(p0, beta, vol, drift, market_log_ret, idio)
        for d, px in zip(iso, path):
            price_rows.append((d, ticker, round(float(px), 4)))
    prices = pd.DataFrame(price_rows, columns=["date", "ticker", "price"])
    prices.to_csv(os.path.join(OUT_DIR, "prices.csv"), index=False)

    # --- fx.csv ------------------------------------------------------------
    fx_rows = []
    for ccy, base in FX_BASE.items():
        vol = FX_ANNUAL_VOL[ccy]
        if vol == 0:
            path = np.full(n, base)
        else:
            shocks = RNG.standard_normal(n)
            path = gbm_path(base, 0.0, vol, shocks)
        for d, rate in zip(iso, path):
            fx_rows.append((d, ccy, round(float(rate), 6)))
    fx = pd.DataFrame(fx_rows, columns=["date", "currency", "rate_to_usd"])
    fx.to_csv(os.path.join(OUT_DIR, "fx.csv"), index=False)

    # --- holdings.csv ------------------------------------------------------
    meta = {u[0]: u for u in UNIVERSE}
    hold_rows = []
    for ticker, (shares, cost, realised) in HOLDINGS.items():
        _, name, sector, region, ccy = meta[ticker][:5]
        hold_rows.append((ticker, name, sector, region, ccy, shares, cost, realised))
    holdings = pd.DataFrame(
        hold_rows,
        columns=["ticker", "name", "sector", "region", "currency",
                 "shares", "cost_basis", "realised_pnl"],
    )
    holdings.to_csv(os.path.join(OUT_DIR, "holdings.csv"), index=False)

    # --- benchmark.csv -----------------------------------------------------
    bench_rows = []
    for ticker, weight in BENCHMARK_WEIGHTS.items():
        _, name, sector, region, ccy = meta[ticker][:5]
        bench_rows.append((ticker, name, sector, region, ccy, round(weight, 6)))
    benchmark = pd.DataFrame(
        bench_rows,
        columns=["ticker", "name", "sector", "region", "currency", "weight"],
    )
    benchmark.to_csv(os.path.join(OUT_DIR, "benchmark.csv"), index=False)

    print(f"Wrote mock data to {OUT_DIR}")
    print(f"  prices.csv    {len(prices):>6} rows  ({n} days x {len(UNIVERSE)} tickers)")
    print(f"  fx.csv        {len(fx):>6} rows")
    print(f"  holdings.csv  {len(holdings):>6} rows")
    print(f"  benchmark.csv {len(benchmark):>6} rows")
    print(f"  window: {iso[0]} -> {iso[-1]}")


if __name__ == "__main__":
    main()
