"""Resolve a dashboard window code (MTD/QTD/YTD/1Y/ALL) to a date range.

Convention: a period return is measured from the *prior* close -- the base is
the last trading day strictly before the period boundary. If the boundary
predates our history (e.g. 1Y on a 7-month mock set) we fall back to inception
and flag it `truncated`, so the UI can label it honestly.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from dateutil.relativedelta import relativedelta


@dataclass
class WindowSlice:
    code: str
    base_date: pd.Timestamp      # close the period is measured FROM
    end_date: pd.Timestamp       # last available date
    start_label: pd.Timestamp    # nominal period boundary requested
    truncated: bool              # True if base fell before available history


def _period_boundary(code: str, end: pd.Timestamp) -> pd.Timestamp:
    code = code.upper()
    if code == "MTD":
        return end.normalize().replace(day=1)
    if code == "QTD":
        q_first_month = 3 * ((end.month - 1) // 3) + 1
        return end.normalize().replace(month=q_first_month, day=1)
    if code == "YTD":
        return end.normalize().replace(month=1, day=1)
    if code == "1Y":
        return (end.normalize() - relativedelta(years=1))
    if code == "ALL":
        return pd.Timestamp.min
    raise ValueError(f"unsupported window: {code}")


def resolve_window(code: str, dates: pd.DatetimeIndex) -> WindowSlice:
    code = code.upper()
    end = dates[-1]
    boundary = _period_boundary(code, end)

    # Base = last available trading day strictly before the boundary.
    prior = dates[dates < boundary]
    if len(prior) > 0:
        base = prior[-1]
        truncated = False
    else:
        # Boundary predates our history. ALL legitimately starts at inception;
        # any other window is short of its nominal length, so flag it.
        base = dates[0]
        truncated = code != "ALL" and boundary < dates[0]
    return WindowSlice(code=code, base_date=base, end_date=end,
                       start_label=boundary if boundary != pd.Timestamp.min else dates[0],
                       truncated=truncated)


def returns_in_window(daily_returns: pd.DataFrame | pd.Series, w: WindowSlice):
    """Slice daily returns to those occurring within the window (date > base)."""
    idx = daily_returns.index
    return daily_returns[(idx > w.base_date) & (idx <= w.end_date)]
