"""Framework-independent evidence-chain records."""

from dataclasses import dataclass
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id


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

    @property
    def node_id(self) -> str:
        return stable_id(
            "evidence-node",
            self.kind.value,
            self.label,
            self.status,
            tuple(ref.evidence_id for ref in self.evidence),
        )


@dataclass(frozen=True)
class EvidenceChain:
    claim: str
    nodes: tuple[EvidenceNode, ...]

    @property
    def chain_id(self) -> str:
        return stable_id("evidence-chain", self.claim, tuple(node.node_id for node in self.nodes))

    @property
    def claim_id(self) -> str:
        return stable_id("claim", self.claim, self.chain_id)


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
