"""Explicit selected-review source view; no source rewrite or governing-state selection."""

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.domains.procurement.bom import distinct_sku_values
from procurement_intelligence_lab.domains.procurement.document_reviews import validate_bom_review
from procurement_intelligence_lab.domains.procurement.source_queries import (
    execution_digest,
    validate_local_execution,
    validated_sku_inputs,
)
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.dependencies import (
    ApprovedCorrectionRef,
    ArchivedClaimRef,
    ClaimDependency,
    DependencyManifest,
    DependencyRoot,
    aware,
)
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    ReviewHistory,
    ReviewOutcome,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    SourceQueryContractError,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)

POLICY = "selected-reviewed-source-skus/v1"
WORKFLOW = "reviewed-source-sku-query"
QUERY_COMPONENT = "procurement-reviewed-source-sku-set"
ROW_COMPONENT = "procurement-reviewed-sku-row"


def reviewed_query_provenance(context: ProvenanceContext) -> DecisionProvenance:
    if type(context) is not ProvenanceContext:
        raise SourceQueryContractError("reviewed query requires typed execution context")
    return DecisionProvenance(
        context, QUERY_COMPONENT, ComponentKind.DETERMINISTIC, "1", policy_version=POLICY
    )


def reviewed_row_provenance(context: ProvenanceContext) -> DecisionProvenance:
    if type(context) is not ProvenanceContext:
        raise SourceQueryContractError("reviewed row requires typed execution context")
    return DecisionProvenance(
        context, ROW_COMPONENT, ComponentKind.DETERMINISTIC, "1", policy_version=POLICY
    )


def validate_provenance(
    p: DecisionProvenance, snapshot_id: str, component: str, as_of: datetime
) -> None:
    if type(p) is not DecisionProvenance:
        raise SourceQueryContractError("reviewed producer requires typed provenance")
    validate_local_execution(p.context, snapshot_id, WORKFLOW)
    if (
        p.component_kind is not ComponentKind.DETERMINISTIC
        or any(
            type(x) is not str
            for x in (p.component_name, p.implementation_version, p.policy_version)
        )
        or p.component_name != component
        or p.implementation_version != "1"
        or p.policy_version != POLICY
        or any(
            x is not None
            for x in (
                p.model_provider,
                p.model_id,
                p.model_revision,
                p.prompt_version,
                p.schema_version,
            )
        )
    ):
        raise SourceQueryContractError("reviewed producer component/implementation/policy is fixed")
    try:
        aware(as_of)
    except SemanticContractError:
        raise SourceQueryContractError("reviewed as-of requires aware fixed-offset time") from None
    if as_of > p.context.started_at:
        raise SourceQueryContractError("reviewed as-of cannot follow execution start")


def correction_root(review: ReviewHistory) -> ApprovedCorrectionRef:
    if type(review) is not ReviewHistory or review.decision is None or review.correction_id is None:
        raise SourceQueryContractError("reviewed value requires an approved review")
    p = review.task.proposal
    return ApprovedCorrectionRef(
        ArchivedClaimRef(p.snapshot_id, p.previous.assertion_id),
        review.task.task_id,
        review.task.digest,
        review.decision.decision_id,
        review.correction_id,
    )


@dataclass(frozen=True)
class ReviewedSkuRow:
    source: SourceAssertion
    review: ReviewHistory
    as_of: datetime
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        if type(self.source) is not SourceAssertion or type(self.review) is not ReviewHistory:
            raise SourceQueryContractError("reviewed row requires typed source and review")
        proposal = self.review.task.proposal
        validate_provenance(self.provenance, proposal.snapshot_id, ROW_COMPONENT, self.as_of)
        try:
            validate_bom_review(proposal)
        except SemanticContractError:
            raise SourceQueryContractError(
                "reviewed row requires a supported BOM SKU review"
            ) from None
        if (
            type(self.source.predicate) is not AssertionPredicate
            or self.source.predicate.value != AssertionPredicate.HAS_SKU.value
            or proposal.previous != self.source
            or self.review.decision is None
            or self.review.decision.command.outcome is not ReviewOutcome.APPROVE
            or self.review.decision.recorded_at > self.as_of
            or self.source.context is None
            or self.source.context.origin.recorded_at > self.as_of
        ):
            raise SourceQueryContractError(
                "reviewed row requires exact source and visible SKU approval"
            )

    @property
    def value(self) -> str | None:
        value = self.review.task.proposal.proposed_value
        if value is not None and type(value) is not str:
            raise SourceQueryContractError("reviewed SKU is text or explicit unknown")
        return value

    @property
    def reference_id(self) -> str:
        return stable_id(
            "reviewed-source-sku-row-v1",
            self.source.assertion_id,
            correction_root(self.review),
            self.review.digest,
            self.as_of.isoformat(),
            execution_digest(self.provenance),
        )

    @property
    def event(self) -> TransformationEvent:
        return TransformationEvent(
            "selected-sku-correction-application",
            self.provenance,
            tuple(
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, x)
                for x in sorted(
                    (self.source.assertion_id, correction_root(self.review).reference_id)
                )
            ),
            (self.reference_id,),
            (),
        )


@dataclass(frozen=True)
class ReviewedSourceSkuQuery:
    snapshot: DocumentSnapshot
    reviews: tuple[ReviewHistory, ...]
    as_of: datetime
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        source = validated_sku_inputs(self.snapshot)
        validate_provenance(self.provenance, self.snapshot.snapshot_id, QUERY_COMPONENT, self.as_of)
        if self.snapshot.origin.recorded_at > self.as_of:
            raise SourceQueryContractError("reviewed as-of cannot precede source recording")
        if (
            type(self.reviews) is not tuple
            or not 1 <= len(self.reviews) <= 32
            or any(type(r) is not ReviewHistory for r in self.reviews)
        ):
            raise SourceQueryContractError("reviewed selection requires1..32 typed histories")
        if len({r.task.task_id for r in self.reviews}) != len(self.reviews) or len(
            {r.task.proposal.previous.assertion_id for r in self.reviews}
        ) != len(self.reviews):
            raise SourceQueryContractError("selected tasks and source assertions must be unique")
        originals = {a.assertion_id: a for a in source}
        for r in self.reviews:
            p = r.task.proposal
            if (
                p.scope != self.snapshot.artifact.source.scope
                or p.snapshot_id != self.snapshot.snapshot_id
                or originals.get(p.previous.assertion_id) != p.previous
            ):
                raise SourceQueryContractError(
                    "selected review must bind exact source snapshot and SKU"
                )
        # The selected reviews are a set; canonicalize once during frozen construction.
        object.__setattr__(
            self, "reviews", tuple(sorted(self.reviews, key=lambda r: r.task.task_id))
        )
        _ = self.rows

    @property
    def rows(self) -> tuple[ReviewedSkuRow, ...]:
        originals = {a.assertion_id: a for a in validated_sku_inputs(self.snapshot)}
        return tuple(
            ReviewedSkuRow(
                originals[r.task.proposal.previous.assertion_id],
                r,
                self.as_of,
                reviewed_row_provenance(self.provenance.context),
            )
            for r in self.reviews
        )

    @property
    def inputs(self) -> tuple[tuple[str, str | None], ...]:
        selected = {row.source.assertion_id: row for row in self.rows}
        return tuple(
            (selected[a.assertion_id].reference_id, selected[a.assertion_id].value)
            if a.assertion_id in selected
            else (a.assertion_id, cast(str | None, a.value))
            for a in validated_sku_inputs(self.snapshot)
        )

    @property
    def known_skus(self) -> tuple[str, ...]:
        return distinct_sku_values(
            value for _, value in self.inputs if value is not None and value.strip()
        )

    @property
    def missing_reference_ids(self) -> tuple[str, ...]:
        return tuple(ref for ref, value in self.inputs if value is None or not value.strip())

    @property
    def value(self) -> tuple[str, ...] | None:
        return None if self.missing_reference_ids else self.known_skus

    @property
    def status(self) -> EpistemicStatus:
        return (
            EpistemicStatus.UNRESOLVED if self.missing_reference_ids else EpistemicStatus.INFERRED
        )

    @property
    def execution_digest(self) -> str:
        return execution_digest(self.provenance)

    @property
    def reference_id(self) -> str:
        return stable_id(
            "selected-reviewed-source-sku-query-v1",
            self.snapshot.snapshot_id,
            self.as_of.isoformat(),
            tuple((correction_root(r), r.digest) for r in self.reviews),
            self.inputs,
            self.execution_digest,
        )

    @property
    def event(self) -> TransformationEvent:
        return TransformationEvent(
            "selected-reviewed-source-sku-query",
            self.provenance,
            tuple(
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, ref) for ref, _ in sorted(self.inputs)
            ),
            (self.reference_id,),
            tuple(
                sorted(
                    (
                        self.snapshot.transformations[-1].event_id,
                        *(r.event.event_id for r in self.rows),
                    )
                )
            ),
        )


def reviewed_dependency_manifest(
    query: ReviewedSourceSkuQuery, request_id: str
) -> DependencyManifest:
    roots: list[DependencyRoot] = [
        ArchivedClaimRef(query.snapshot.snapshot_id, a.assertion_id)
        for a in validated_sku_inputs(query.snapshot)
    ]
    roots.extend(correction_root(r) for r in query.reviews)
    claims = [ClaimDependency(r.reference_id, r.event) for r in query.rows] + [
        ClaimDependency(query.reference_id, query.event)
    ]
    return DependencyManifest(
        query.snapshot.artifact.source.scope,
        request_id,
        tuple(sorted(roots, key=lambda r: r.reference_id)),
        tuple(sorted(claims, key=lambda c: c.reference_id)),
    )
