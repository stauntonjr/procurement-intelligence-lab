from decimal import Decimal

from procurement_intelligence_lab.application.pipeline import run_bom_pipeline
from procurement_intelligence_lab.domain.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domain.resolution import ResolutionStatus


def test_bom_pipeline_preserves_layers_and_excludes_unresolved_state() -> None:
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B", "C", "D"))
    bom = Bom(
        "bom.xlsx",
        (
            BomLine("GPU-A", "GPU", Decimal(4), Decimal(100), evidence),
            BomLine("UNKNOWN", "GPU", Decimal(8), Decimal(100), evidence),
        ),
    )

    result = run_bom_pipeline(bom, ("GPU-A",))

    assert len(result.assertions) == 8
    assert [decision.status for decision in result.decisions] == [
        ResolutionStatus.RESOLVED,
        ResolutionStatus.UNRESOLVED,
    ]
    assert result.reconciled_lines[0].canonical_key == "GPU-A"
    assert result.reconciled_lines[0].quantity == Decimal(4)
