from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.evidence import (
    EvidenceNodeKind,
    source_chain,
)


def test_evidence_chain_is_ui_framework_independent() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    chain = source_chain("GPU quantity", (evidence,))

    assert chain.claim == "GPU quantity"
    assert chain.nodes[0].kind is EvidenceNodeKind.SOURCE_ASSERTION
    assert chain.nodes[0].evidence == (evidence,)
