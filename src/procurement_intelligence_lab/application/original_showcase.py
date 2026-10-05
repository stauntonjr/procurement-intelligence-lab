"""Reuse original fixture policy/identity behind the existing investigation tool."""

from dataclasses import dataclass
from datetime import UTC, datetime

from procurement_intelligence_lab.application.corpus_investigation import (
    InvestigationRequest,
    InvestigationResult,
)
from procurement_intelligence_lab.application.showcase import (
    ShowcaseScenario,
    showcase_order_comparison,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext
from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError, CorpusNotFoundError
from procurement_intelligence_lab.ports.review_sources import ReviewSources


@dataclass(frozen=True)
class OriginalShowcaseInvestigator:
    sources: ReviewSources
    scenario: ShowcaseScenario

    def __post_init__(self) -> None:
        if self.scenario not in (
            ShowcaseScenario.ORDER_MISMATCH,
            ShowcaseScenario.ORDER_UNRESOLVED,
            ShowcaseScenario.ORDER_MISSING,
        ):
            raise ValueError("unsupported original review snapshot")

    def investigate(
        self, request: InvestigationRequest, *, context: RequestContext
    ) -> InvestigationResult:
        snapshot = self.sources.snapshot_id(context=context)
        if request.canonical_key != "GPU-A" or request.as_of != datetime(2026, 1, 15, tzinfo=UTC):
            raise ValueError("original showcase requires its exact item and fixed cutoff")
        result = showcase_order_comparison(self.scenario, request_context=context)
        assessment = next(a for a in result.assessments if a.kind.value == "quantity_mismatch")
        evidence = tuple(
            {
                ref.evidence_id: ref
                for ref in (
                    *(claim.evidence for claim in result.requirement.candidates),
                    *result.order_evidence,
                )
            }.values()
        )
        if self.sources.source_ids(context=context) != frozenset(
            ref.evidence_id for ref in evidence
        ):
            raise CorpusAdmissionError(
                "original service must cover the complete admitted source set"
            )
        # The service's original refs must resolve in the configured admitted source set.
        try:
            for ref in evidence:
                if self.sources.source_by_id(ref.evidence_id, context=context).evidence != ref:
                    raise CorpusAdmissionError("original service/source identity mismatch")
        except CorpusNotFoundError as error:
            raise CorpusAdmissionError("original service/source identity mismatch") from error
        if self.sources.snapshot_id(context=context) != snapshot:
            raise CorpusAdmissionError("original source snapshot changed during investigation")
        return InvestigationResult(
            snapshot,
            result.requirement.governed_state,
            assessment,
            evidence,
            result.ordered_quantity,
        )
