"""Framework-independent evidence nodes for drill-down interfaces."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.resolution import ResolutionDecision
from procurement_intelligence_lab.domain.state import OperationalBomLine


class EvidenceNodeKind(StrEnum):
    SOURCE_ASSERTION = "source_assertion"
    RESOLUTION = "resolution"
    OPERATIONAL_STATE = "operational_state"
    RECONCILIATION = "reconciliation"


@dataclass(frozen=True)
class EvidenceNode:
    kind: EvidenceNodeKind
    label: str
    evidence: tuple[EvidenceRef, ...]
    status: str


@dataclass(frozen=True)
class EvidenceChain:
    claim: str
    nodes: tuple[EvidenceNode, ...]


def source_chain(claim: str, evidence: tuple[EvidenceRef, ...]) -> EvidenceChain:
    return EvidenceChain(
        claim,
        (
            EvidenceNode(
                EvidenceNodeKind.SOURCE_ASSERTION,
                "source assertions",
                evidence,
                "observed",
            ),
        ),
    )


def pipeline_chain(
    claim: str,
    evidence: tuple[EvidenceRef, ...],
    decisions: tuple[ResolutionDecision, ...],
    operational_lines: tuple[OperationalBomLine, ...],
    reconciliation_status: str,
) -> EvidenceChain:
    resolution_status = (
        "resolved"
        if decisions and all(decision.canonical_key is not None for decision in decisions)
        else "partially_resolved"
    )
    return EvidenceChain(
        claim,
        (
            EvidenceNode(EvidenceNodeKind.SOURCE_ASSERTION, "source assertions", evidence, "observed"),
            EvidenceNode(EvidenceNodeKind.RESOLUTION, "entity resolution", evidence, resolution_status),
            EvidenceNode(
                EvidenceNodeKind.OPERATIONAL_STATE,
                "operational state",
                evidence,
                "observed" if operational_lines else "unresolved",
            ),
            EvidenceNode(
                EvidenceNodeKind.RECONCILIATION,
                "reconciliation",
                evidence,
                reconciliation_status,
            ),
        ),
    )
