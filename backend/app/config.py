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

# The dashboard reports a single period: inception-to-date (ALL). The multi-
# window selector was removed at the boss's request -- every figure is measured
# from the start of the price history to the latest date.
SUPPORTED_WINDOWS = ["ALL"]
DEFAULT_WINDOW = "ALL"

# --- P1: rule-based alert thresholds ---------------------------------------
# Each limit drives one rule in analytics/alerts.py. Tuned for the mock book so
# the demo trips a representative mix of warnings and breaches. In production
# these would come from the risk mandate / IPS.
ALERT_THRESHOLDS = {
    "single_name_weight": 0.10,     # any holding above 10% of AUM
    "sector_active_weight": 0.05,   # |sector active weight| above 5%
    "hhi": 0.15,                    # concentration (HHI) above 0.15
    "volatility": 0.20,             # annualised vol above 20%
    "beta_high": 1.20,              # portfolio beta above 1.20
    "beta_low": 0.80,               # portfolio beta below 0.80
    "var99": 0.035,                 # 1-day 99% historical VaR worse than 3.5%
    "max_drawdown": 0.12,           # peak-to-trough beyond 12%
}
