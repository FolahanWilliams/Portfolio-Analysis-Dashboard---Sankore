"""Lightweight request/response typing.

The analytics layer is the single source of truth for response *shapes* (it
returns plain dicts), so we keep response models permissive and focus typing
where it adds safety: validating the window query parameter. The frontend
mirrors these shapes in TypeScript (see frontend/src/types).
"""
from __future__ import annotations

from enum import Enum


class Window(str, Enum):
    MTD = "MTD"
    QTD = "QTD"
    YTD = "YTD"
    ONE_YEAR = "1Y"
    ALL = "ALL"
