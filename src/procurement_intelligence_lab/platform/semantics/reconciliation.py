"""Reusable reconciliation policy contracts."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class SourceObservation(Protocol):
    @property
    def source_artifact(self) -> str: ...


class ReconciliationPolicyError(ValueError):
    """Raised when no explicit policy can select a governing observation."""


@dataclass(frozen=True)
class SourcePrecedencePolicy:
    """Select the first available source in explicit precedence order."""

    source_precedence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_precedence:
            raise ValueError("source_precedence must not be empty")
        if len(set(self.source_precedence)) != len(self.source_precedence):
            raise ValueError("source_precedence must not contain duplicates")

    def governing_source(self, observations: Sequence[SourceObservation]) -> str:
        available = {line.source_artifact for line in observations}
        for source in self.source_precedence:
            if source in available:
                return source
        raise ReconciliationPolicyError(
            f"no source-precedence rule covers observations from {sorted(available)!r}"
        )
