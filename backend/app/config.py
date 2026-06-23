"""Central configuration for the analytics backend.

Kept tiny and import-only so both the API layer and the (presentation-free)
analytics layer can read the same constants without circular deps.
"""
from __future__ import annotations

import os

# Base reporting currency. Every cross-holding total is normalised to this
# before aggregation (see data.loader).
BASE_CURRENCY = "USD"

# Annualisation + risk constants.
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.04  # annual, used for Sharpe

# VaR confidence -> normal z-scores for the parametric method.
VAR_Z = {95: 1.645, 99: 2.326}

# Where the mock CSVs live. Overridable for tests.
MOCK_DATA_DIR = os.environ.get(
    "MOCK_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "mock_data"),
)

# Supported selectable windows for the dashboard (label -> meaning).
SUPPORTED_WINDOWS = ["MTD", "QTD", "YTD", "1Y", "ALL"]
DEFAULT_WINDOW = "YTD"
