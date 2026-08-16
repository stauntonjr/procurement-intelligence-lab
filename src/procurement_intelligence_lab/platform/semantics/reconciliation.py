"""Reusable reconciliation policy contracts."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCode,
    PolicyContractError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.resolution import CanonicalizedAssertion


class SourceObservation(Protocol):
    @property
    def source_artifact(self) -> str: ...


class ReconciliationPolicyError(PolicyContractError):
    """Raised when no explicit policy can select a governing observation."""

    code = ErrorCode.RECONCILIATION_POLICY_NO_MATCH


@dataclass(frozen=True)
class SourcePrecedencePolicy:
    """Select the first available source in explicit precedence order."""

    source_precedence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_precedence:
            raise SemanticContractError("source_precedence must not be empty")
        if len(set(self.source_precedence)) != len(self.source_precedence):
            raise SemanticContractError("source_precedence must not contain duplicates")

    def governing_source(self, observations: Sequence[SourceObservation]) -> str:
        available = {line.source_artifact for line in observations}
        for source in self.source_precedence:
            if source in available:
                return source
        raise ReconciliationPolicyError(
            f"no source-precedence rule covers observations from {sorted(available)!r}"
        )


class ReconciliationStatus(StrEnum):
    RECONCILED = "reconciled"
    CONFLICT = "conflict"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ReconciliationDecision:
    """Evidence-preserving selection of governing and losing claims."""

    subject_key: str
    status: ReconciliationStatus
    governing: tuple[CanonicalizedAssertion, ...]
    losing: tuple[CanonicalizedAssertion, ...]
    policy_id: str
    rationale: str
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        if not all((self.subject_key.strip(), self.policy_id.strip(), self.rationale.strip())):
            raise SemanticContractError(
                "reconciliation subject, policy, and rationale are required"
            )
        if self.status is not ReconciliationStatus.UNRESOLVED and not self.governing:
            raise SemanticContractError(
                "resolved reconciliation decisions require governing assertions"
            )
        if self.status is ReconciliationStatus.UNRESOLVED and self.governing:
            raise SemanticContractError(
                "unresolved reconciliation decisions cannot select governing assertions"
            )
        assertions = self.governing + self.losing
        if len({item.canonicalized_assertion_id for item in assertions}) != len(assertions):
            raise SemanticContractError("reconciliation assertions must not appear more than once")
        if any(item.canonical_key != self.subject_key for item in assertions):
            raise SemanticContractError("reconciliation assertions must share the decision subject")
        if len({item.scope for item in assertions}) > 1:
            raise SemanticContractError("reconciliation assertions must share one scope")

    @property
    def reconciliation_id(self) -> str:
        return stable_id(
            "reconciliation-decision",
            self.subject_key,
            self.status.value,
            tuple(item.canonicalized_assertion_id for item in self.governing),
            tuple(item.canonicalized_assertion_id for item in self.losing),
            self.policy_id,
            self.rationale,
            self.provenance.provenance_id,
        )
