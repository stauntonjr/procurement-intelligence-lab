"""Procurement evidence-chain assembly over shared platform records."""

from procurement_intelligence_lab.domains.procurement.state import OperationalBomLine
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.evidence_graph import (
    EvidenceChain,
    EvidenceNode,
    EvidenceNodeKind,
    source_chain,
)
from procurement_intelligence_lab.platform.semantics.resolution import ResolutionDecision

__all__ = (
    "EvidenceChain",
    "EvidenceNode",
    "EvidenceNodeKind",
    "pipeline_chain",
    "source_chain",
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
            EvidenceNode(
                EvidenceNodeKind.SOURCE_ASSERTION, "source assertions", evidence, "observed"
            ),
            EvidenceNode(
                EvidenceNodeKind.RESOLUTION,
                "entity resolution",
                evidence,
                resolution_status,
            ),
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
