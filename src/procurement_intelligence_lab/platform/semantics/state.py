"""Shared state-projection lifecycle vocabulary."""

from enum import StrEnum


class StateFreshness(StrEnum):
    CURRENT = "current"
    PARTIAL = "partial"
    STALE = "stale"
    UNKNOWN = "unknown"
