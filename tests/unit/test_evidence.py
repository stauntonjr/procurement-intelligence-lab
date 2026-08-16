from decimal import Decimal

from procurement_intelligence_lab.domains.procurement.bom import EvidenceRef
from procurement_intelligence_lab.domains.procurement.evidence import (
    pipeline_chain,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import OperationalBomLine
from procurement_intelligence_lab.platform.semantics.evidence_graph import (
    EvidenceNodeKind,
    source_chain,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)


def _provenance() -> DecisionProvenance:
    return DecisionProvenance(
        local_provenance_context(),
        "test-resolver",
        ComponentKind.DETERMINISTIC,
        "1",
    )


def test_evidence_chain_is_ui_framework_independent() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    chain = source_chain("GPU quantity", (evidence,))

    assert chain.claim == "GPU quantity"
    assert chain.nodes[0].kind is EvidenceNodeKind.SOURCE_ASSERTION
    assert chain.nodes[0].evidence == (evidence,)


def test_pipeline_chain_exposes_all_drilldown_stages() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    decision = ResolutionDecision(
        "GPU-A",
        "gpu",
        ResolutionStatus.RESOLVED,
        (),
        "exact",
        _provenance(),
    )
    line = OperationalBomLine("gpu", Decimal(4), Decimal(100), "bom.xlsx", evidence)

    chain = pipeline_chain("GPU quantity", (evidence,), (decision,), (line,), "reconciled")

    assert [node.kind for node in chain.nodes] == [
        EvidenceNodeKind.SOURCE_ASSERTION,
        EvidenceNodeKind.RESOLUTION,
        EvidenceNodeKind.OPERATIONAL_STATE,
        EvidenceNodeKind.RECONCILIATION,
    ]
    assert chain.nodes[-1].status == "reconciled"
