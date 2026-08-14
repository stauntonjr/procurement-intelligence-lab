"""Application orchestration for the evidence-first BOM vertical slice."""

from dataclasses import dataclass

from procurement_intelligence_lab.domain.assertions import (
    SourceAssertion,
    assertions_for_bom,
)
from procurement_intelligence_lab.domain.bom import Bom
from procurement_intelligence_lab.domain.reconciliation import (
    ReconciledLine,
    reconcile_lines,
)
from procurement_intelligence_lab.domain.resolution import (
    ResolutionDecision,
    resolve_identifier,
)
from procurement_intelligence_lab.domain.state import project_operational_lines


@dataclass(frozen=True)
class BomPipelineResult:
    assertions: tuple[SourceAssertion, ...]
    decisions: tuple[ResolutionDecision, ...]
    reconciled_lines: tuple[ReconciledLine, ...]


def run_bom_pipeline(bom: Bom, canonical_candidates: tuple[str, ...]) -> BomPipelineResult:
    assertions = assertions_for_bom(bom)
    decisions = tuple(
        resolve_identifier(line.sku, canonical_candidates, assertions) for line in bom.lines
    )
    operational_lines = project_operational_lines(bom, decisions)
    return BomPipelineResult(assertions, decisions, reconcile_lines(operational_lines))
