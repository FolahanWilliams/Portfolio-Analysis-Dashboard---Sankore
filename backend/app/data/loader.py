"""Load and validate the mock data, and normalise everything to USD.

This is the *only* place in the system that touches raw input. Swapping mock
CSVs for a live feed is a change here and nowhere else (the production-swap
point from the workflow map).

Validation philosophy (from the PRD non-functionals): malformed or missing
rows are skipped and flagged, never allowed to crash the app. Every issue is
recorded in a `ValidationReport` that the API surfaces so the UI can show a
clear, honest "we dropped N rows" state instead of a silent wrong number.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd

from app.config import BASE_CURRENCY, MOCK_DATA_DIR


@dataclass
class ValidationReport:
    """Accumulates every row we skipped, with a human-readable reason."""

    issues: list[dict] = field(default_factory=list)

    def flag(self, source: str, reason: str, detail: str = "") -> None:
        self.issues.append({"source": source, "reason": reason, "detail": detail})

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0

    def as_dict(self) -> dict:
        return {"ok": self.ok, "count": len(self.issues), "issues": self.issues}


@dataclass
class MarketData:
    """In-memory, validated, USD-normalised dataset the analytics layer reads.

    Attributes
    ----------
    holdings   : portfolio rows (ticker, name, sector, region, currency,
                 shares, cost_basis, realised_pnl)
    benchmark  : benchmark constituents (ticker, name, sector, region,
                 currency, weight) -- weights renormalised to sum to 1.
    usd_prices : DataFrame indexed by date (datetime), columns = tickers,
                 values = price in USD (native price x fx rate). Gap-filled.
    dates      : sorted DatetimeIndex of the price history.
    report     : ValidationReport.
    """

    holdings: pd.DataFrame
    benchmark: pd.DataFrame
    usd_prices: pd.DataFrame
    fx_rates: pd.DataFrame              # date x currency -> rate to USD
    currency_of: dict[str, str]         # ticker -> currency
    dates: pd.DatetimeIndex
    report: ValidationReport

    def fx_on(self, currency: str, on: pd.Timestamp) -> float:
        if currency in self.fx_rates.columns:
            return float(self.fx_rates.loc[on, currency])
        return 1.0

    # --- convenience views the analytics modules lean on -------------------
    def held_tickers(self) -> list[str]:
        return list(self.holdings["ticker"])

    def usd_returns(self) -> pd.DataFrame:
        """Daily simple returns in USD for every ticker in the price matrix."""
        return self.usd_prices.pct_change().iloc[1:]

    def portfolio_value_series(self) -> pd.Series:
        """Total portfolio value in USD on each date = sum(shares x usd_price)."""
        shares = self.holdings.set_index("ticker")["shares"]
        cols = [t for t in shares.index if t in self.usd_prices.columns]
        return (self.usd_prices[cols] * shares.reindex(cols)).sum(axis=1)

    def benchmark_index_series(self) -> pd.Series:
        """Benchmark index level (starts at 1.0) from static constituent weights."""
        w = self.benchmark.set_index("ticker")["weight"]
        cols = [t for t in w.index if t in self.usd_prices.columns]
        prices = self.usd_prices[cols]
        normed = prices / prices.iloc[0]
        return (normed * w.reindex(cols)).sum(axis=1)


def _read_csv(path: str, source: str, report: ValidationReport) -> pd.DataFrame:
    if not os.path.exists(path):
        report.flag(source, "file_missing", path)
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive
        report.flag(source, "unreadable", str(exc))
        return pd.DataFrame()


def _clean_holdings(df: pd.DataFrame, report: ValidationReport) -> pd.DataFrame:
    required = {"ticker", "name", "sector", "region", "currency", "shares"}
    missing = required - set(df.columns)
    if missing:
        report.flag("holdings", "missing_columns", ", ".join(sorted(missing)))
        return pd.DataFrame(columns=sorted(required))
    if "cost_basis" not in df.columns:
        df["cost_basis"] = np.nan
    if "realised_pnl" not in df.columns:
        df["realised_pnl"] = 0.0

    out = []
    for _, row in df.iterrows():
        tkr = str(row["ticker"]).strip()
        if not tkr or tkr.lower() == "nan":
            report.flag("holdings", "blank_ticker")
            continue
        try:
            shares = float(row["shares"])
        except (TypeError, ValueError):
            report.flag("holdings", "bad_shares", tkr)
            continue
        if not np.isfinite(shares) or shares <= 0:
            report.flag("holdings", "non_positive_shares", tkr)
            continue
        out.append(row)
    return pd.DataFrame(out).reset_index(drop=True) if out else pd.DataFrame(columns=df.columns)


def _clean_benchmark(df: pd.DataFrame, report: ValidationReport) -> pd.DataFrame:
    required = {"ticker", "sector", "region", "weight"}
    missing = required - set(df.columns)
    if missing:
        report.flag("benchmark", "missing_columns", ", ".join(sorted(missing)))
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        tkr = str(row["ticker"]).strip()
        try:
            w = float(row["weight"])
        except (TypeError, ValueError):
            report.flag("benchmark", "bad_weight", tkr)
            continue
        if not np.isfinite(w) or w < 0:
            report.flag("benchmark", "negative_weight", tkr)
            continue
        rows.append(row)
    clean = pd.DataFrame(rows).reset_index(drop=True) if rows else pd.DataFrame(columns=df.columns)
    if not clean.empty:
        total = clean["weight"].sum()
        if total > 0 and abs(total - 1.0) > 1e-9:
            # Renormalise; flag only if materially off (data-quality signal).
            if abs(total - 1.0) > 0.01:
                report.flag("benchmark", "weights_renormalised", f"sum={total:.4f}")
            clean["weight"] = clean["weight"] / total
    return clean


def _build_usd_price_matrix(
    prices: pd.DataFrame,
    fx: pd.DataFrame,
    currency_of: dict[str, str],
    report: ValidationReport,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if prices.empty or not {"date", "ticker", "price"} <= set(prices.columns):
        report.flag("prices", "missing_columns")
        return pd.DataFrame(), pd.DataFrame()

    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices["price"] = pd.to_numeric(prices["price"], errors="coerce")
    bad = prices[prices["date"].isna() | prices["price"].isna() | (prices["price"] <= 0)]
    for _, row in bad.iterrows():
        report.flag("prices", "bad_price_row", str(row.get("ticker", "")))
    prices = prices.drop(bad.index)

    native = prices.pivot_table(index="date", columns="ticker", values="price", aggfunc="last")
    native = native.sort_index()

    # FX matrix: date x currency -> rate to USD. USD defaults to 1.0.
    if not fx.empty and {"date", "currency", "rate_to_usd"} <= set(fx.columns):
        fx = fx.copy()
        fx["date"] = pd.to_datetime(fx["date"], errors="coerce")
        fx["rate_to_usd"] = pd.to_numeric(fx["rate_to_usd"], errors="coerce")
        fx_mat = fx.pivot_table(index="date", columns="currency", values="rate_to_usd", aggfunc="last")
        fx_mat = fx_mat.reindex(native.index).ffill().bfill()
    else:
        report.flag("fx", "missing_or_empty", "defaulting all rates to 1.0")
        fx_mat = pd.DataFrame(index=native.index)
    if BASE_CURRENCY not in fx_mat.columns:
        fx_mat[BASE_CURRENCY] = 1.0

    usd = pd.DataFrame(index=native.index)
    for ticker in native.columns:
        ccy = currency_of.get(ticker, BASE_CURRENCY)
        if ccy not in fx_mat.columns:
            report.flag("fx", "missing_currency", f"{ticker}:{ccy} -> treated as 1.0")
            rate = pd.Series(1.0, index=native.index)
        else:
            rate = fx_mat[ccy]
        usd[ticker] = native[ticker] * rate

    # Gap-fill: a hole in one ticker's history shouldn't poison aggregates.
    before = usd.isna().sum().sum()
    usd = usd.ffill().bfill()
    if before:
        report.flag("prices", "gaps_filled", f"{int(before)} missing cells forward/back-filled")
    return usd, fx_mat


@lru_cache(maxsize=4)
def load_market_data(data_dir: str | None = None) -> MarketData:
    """Load, validate and USD-normalise the dataset. Cached per directory."""
    data_dir = data_dir or MOCK_DATA_DIR
    report = ValidationReport()

    holdings = _clean_holdings(_read_csv(os.path.join(data_dir, "holdings.csv"), "holdings", report), report)
    benchmark = _clean_benchmark(_read_csv(os.path.join(data_dir, "benchmark.csv"), "benchmark", report), report)
    prices_raw = _read_csv(os.path.join(data_dir, "prices.csv"), "prices", report)
    fx_raw = _read_csv(os.path.join(data_dir, "fx.csv"), "fx", report)

    # Currency master: holdings + benchmark both carry it; holdings win on conflict.
    currency_of: dict[str, str] = {}
    if not benchmark.empty and "currency" in benchmark.columns:
        currency_of.update(dict(zip(benchmark["ticker"], benchmark["currency"])))
    if not holdings.empty:
        currency_of.update(dict(zip(holdings["ticker"], holdings["currency"])))

    usd_prices, fx_rates = _build_usd_price_matrix(prices_raw, fx_raw, currency_of, report)
    dates = usd_prices.index if not usd_prices.empty else pd.DatetimeIndex([])

    return MarketData(
        holdings=holdings,
        benchmark=benchmark,
        usd_prices=usd_prices,
        fx_rates=fx_rates,
        currency_of=currency_of,
        dates=dates,
        report=report,
    )


def clear_cache() -> None:
    load_market_data.cache_clear()
