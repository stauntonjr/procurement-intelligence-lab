from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.evidence import source_chain


def test_evidence_ids_are_deterministic_and_location_sensitive() -> None:
    first = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    same = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    different = EvidenceRef("bom.xlsx", "hash", "BOM", 3, ("A", "B"))

    assert first.evidence_id == same.evidence_id
    assert first.evidence_id != different.evidence_id


def test_chain_and_node_ids_are_deterministic() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    first = source_chain("gpu_quantity", (evidence,))
    same = source_chain("gpu_quantity", (evidence,))

    assert first.claim_id == same.claim_id
    assert first.chain_id == same.chain_id
    assert first.nodes[0].node_id == same.nodes[0].node_id
