from decimal import Decimal

from procurement_intelligence_lab.domain.bom import Bom, BomLine, EvidenceRef
from procurement_intelligence_lab.domain.resolution import (
    ResolutionDecision,
    ResolutionStatus,
)
from procurement_intelligence_lab.domain.state import project_operational_lines


def test_only_resolved_lines_enter_operational_state() -> None:
    evidence = EvidenceRef("fixture.xlsx", "hash", "BOM", 2, ("A",))
    bom = Bom(
        "fixture.xlsx",
        (
            BomLine("GPU-A", "GPU", Decimal(4), Decimal(100), evidence),
            BomLine("UNKNOWN", "GPU", Decimal(8), Decimal(100), evidence),
        ),
    )
    decisions = (
        ResolutionDecision(
            "GPU-A", "gpu-canonical", ResolutionStatus.RESOLVED, (), "exact"
        ),
        ResolutionDecision("UNKNOWN", None, ResolutionStatus.UNRESOLVED, (), "missing"),
    )

    lines = project_operational_lines(bom, decisions)

    assert lines == (
        OperationalBomLine("gpu-canonical", Decimal(4), Decimal(100), "fixture.xlsx"),
    )
