"""Shared epistemic vocabulary for evidence-backed values."""

from enum import StrEnum


class EpistemicStatus(StrEnum):
    """How directly a value is supported by available evidence."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"
