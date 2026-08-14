"""Framework-independent evidence nodes for drill-down interfaces."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.domain.bom import EvidenceRef


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
