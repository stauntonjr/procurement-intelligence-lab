"""Compose complete admitted facts with existing procurement policies."""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from procurement_intelligence_lab.application.anomaly_service import AnomalyService
from procurement_intelligence_lab.domains.procurement.anomalies import (
    AnomalyKind,
    CoverageGapPolicy,
    MissingPurchaseOrderPolicy,
    QuantityMismatchPolicy,
)
from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    AnomalyAssessment,
    AnomalyAssessmentInput,
    QualifiedOrderLine,
    QuantityAssessmentPolicies,
)
from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningPredicate,
    GoverningSourceType,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import (
    GovernedRequiredQuantityState,
    project_governed_required_quantity,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
    StateScope,
)
from procurement_intelligence_lab.ports.corpus import CorpusNotFoundError, CorpusReader


@dataclass(frozen=True)
class InvestigationRequest:
    canonical_key: str
    as_of: datetime

    def __post_init__(self) -> None:
        if not self.canonical_key.strip() or len(self.canonical_key) > 100:
            raise ValueError("item must be a nonempty canonical key of at most 100 characters")
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")


@dataclass(frozen=True)
class InvestigationResult:
    snapshot_id: str
    governed: GovernedRequiredQuantityState
    assessment: AnomalyAssessment
    evidence: tuple[EvidenceRef, ...]
    ordered_quantity: Decimal | None


@dataclass(frozen=True)
class CorpusInvestigationService:
    reader: CorpusReader

    def investigate(
        self, request: InvestigationRequest, *, context: RequestContext
    ) -> InvestigationResult:
        context.require(Permission.READ_STATE)
        inventory = self.reader.inventory(context=context)
        # Defend the service boundary even for other port implementations.
        for fact in inventory.facts:
            if (fact.scope.tenant_id, fact.scope.project_id, fact.scope.site_id) != (
                context.tenant_id,
                context.project_id,
                context.site_id,
            ):
                raise ScopeAuthorizationError("source scope does not match request")
        facts = tuple(f for f in inventory.facts if f.canonical_key == request.canonical_key)
        if not facts:
            raise CorpusNotFoundError("item not found in admitted scope")
        # Keep all non-order sources, including non-authoritative quotes, in governance dispositions.
        claims = tuple(
            GoverningClaim(
                f.evidence.evidence_id,
                f.canonical_key,
                GoverningPredicate.REQUIRED_QUANTITY,
                f.quantity,
                f.unit,
                GoverningSourceType(f.role),
                f.scope,
                f.evidence,
                f.revision_id,
                f.supersedes,
                f.approved_at,
                f.effective_from,
                f.effective_until,
                f.document_at,
                f.ingested_at,
            )
            for f in facts
            if f.role != "approved_purchase_order_line"
        )
        governed = project_governed_required_quantity(
            claims,
            canonical_key=request.canonical_key,
            request_context=context,
            as_of=request.as_of,
        )
        scope = (
            governed.expected.scope
            if governed.expected
            else StateScope(
                context.tenant_id, context.project_id, context.site_id, inventory.snapshot_id
            )
        )
        orders = tuple(
            QualifiedOrderLine(
                f.line_id,
                f.assertion_id,
                f.quantity,
                f.unit,
                scope,
                max(f.effective_from, f.approved_at) if f.approved_at else f.effective_from,
                f.approved_at is not None,
                (f.evidence, f.authority),
            )
            for f in facts
            if f.role == "approved_purchase_order_line"
        )
        policies = QuantityAssessmentPolicies(
            MissingPurchaseOrderPolicy("corpus-missing/v1"),
            QuantityMismatchPolicy("corpus-quantity/v1"),
            CoverageGapPolicy("corpus-coverage/v1"),
        )
        evidence = tuple(ref for f in facts for ref in (f.evidence, f.authority))
        provenance = DecisionProvenance(
            replace(
                local_provenance_context(),
                workflow_name="corpus-investigation",
                config_digest=policies.digest,
                input_snapshot_ids=(inventory.snapshot_id,),
            ),
            "qualified-quantity-assessment",
            ComponentKind.DETERMINISTIC,
            "1",
            policy_version="procurement-anomaly-assessment/v1",
        )
        assessments = AnomalyService(policies, provenance, request.as_of).assess(
            AnomalyAssessmentInput(
                request.canonical_key,
                scope,
                request.as_of,
                governed.expected,
                expected_unit=governed.decision.unit or "each",
                governance_decision_ids=(governed.decision.decision_id,),
                governance_evidence=tuple(
                    ref
                    for f in facts
                    if f.role != "approved_purchase_order_line"
                    for ref in (f.evidence, f.authority)
                ),
                ordered_lines=orders,
            ),
            request_context=context,
        )
        assessment = next(a for a in assessments if a.kind is AnomalyKind.QUANTITY_MISMATCH)
        # Project only positively admitted assertions after the domain has established comparability.
        eligible = dict(assessment.input_dispositions)
        unique = {
            line.assertion_id: line for line in orders if eligible[line.assertion_id] == "eligible"
        }
        ordered_quantity = (
            sum((line.quantity for line in unique.values()), Decimal(0))
            if assessment.status.value in {"clear", "anomaly"}
            else None
        )
        return InvestigationResult(
            inventory.snapshot_id, governed, assessment, evidence, ordered_quantity
        )
