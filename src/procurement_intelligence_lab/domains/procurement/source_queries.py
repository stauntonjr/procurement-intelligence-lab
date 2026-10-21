"""Actual source-local SKU query; source strings are not canonical identity or current state."""

import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.domains.procurement.bom import distinct_sku_values
from procurement_intelligence_lab.domains.procurement.observation_assertions import (
    validate_bom_assertions,
)
from procurement_intelligence_lab.platform.semantics.archive import DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.dependencies import aware, text
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyContractError,
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

POLICY = "source-sku-set/v1"
WORKFLOW = "archived-source-sku-query"
COMPONENT = "procurement-source-sku-set"


def validate_execution(context: ProvenanceContext, snapshot_id: str) -> None:
    if type(context) is not ProvenanceContext:
        raise SourceQueryContractError("source query requires a typed local execution context")
    try:
        text(snapshot_id)
        for value in (
            context.run_id,
            context.workflow_name,
            context.workflow_version,
            context.code_revision,
            context.image_digest,
            context.config_digest,
        ):
            text(value)
        for value in (context.dependency_lock_digest, context.parent_run_id):
            if value is not None:
                text(value)
        aware(context.started_at)
    except DependencyContractError:
        raise SourceQueryContractError(
            "source query execution identities/time are invalid"
        ) from None
    if (
        context.workflow_name != WORKFLOW
        or context.workflow_version != "1"
        or context.input_snapshot_ids != (snapshot_id,)
        or context.environment != ()
    ):
        raise SourceQueryContractError(
            "source query requires its fixed workflow, exact input pin and no raw environment"
        )


def query_provenance(context: ProvenanceContext) -> DecisionProvenance:
    if type(context) is not ProvenanceContext:
        raise SourceQueryContractError("source query requires a typed execution context")
    return DecisionProvenance(
        context, COMPONENT, ComponentKind.DETERMINISTIC, "1", policy_version=POLICY
    )


def execution_digest(provenance: DecisionProvenance) -> str:
    raw = json.dumps(
        asdict(provenance),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda value: value.isoformat(),
    )
    return sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class SourceSkuQuery:
    snapshot: DocumentSnapshot
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        if (
            type(self.snapshot) is not DocumentSnapshot
            or type(self.provenance) is not DecisionProvenance
        ):
            raise SourceQueryContractError(
                "source query requires a typed source snapshot and producer"
            )
        validate_execution(self.provenance.context, self.snapshot.snapshot_id)
        if self.provenance != query_provenance(self.provenance.context):
            raise SourceQueryContractError("source query producer implementation/policy is fixed")
        if self.provenance.context.started_at < self.snapshot.origin.recorded_at:
            raise SourceQueryContractError("source query execution cannot precede source recording")
        validate_bom_assertions(
            self.snapshot.observations, self.snapshot.assertions, self.snapshot.mentions
        )
        if any(type(a.predicate) is not AssertionPredicate for a in self.snapshot.assertions):
            raise SourceQueryContractError("source query requires typed procurement predicates")
        if not 1 <= len(self.inputs) <= 32:
            raise SourceQueryContractError("source query requires1..32 source-SKU claims")
        for claim in self.inputs:
            if claim.context is None or claim.context.observation.unit is not None:
                raise SourceQueryContractError(
                    "source SKU claims require complete unitless context"
                )
            if claim.value is not None:
                if type(claim.value) is not str:
                    raise SourceQueryContractError(
                        "source SKU values must be text or unresolved null"
                    )
                try:
                    claim.value.encode("utf-8")
                except UnicodeError:
                    raise SourceQueryContractError(
                        "source SKU text must contain Unicode scalars"
                    ) from None

    @property
    def inputs(self) -> tuple[SourceAssertion, ...]:
        return tuple(
            a
            for a in self.snapshot.assertions
            if a.predicate.value == AssertionPredicate.HAS_SKU.value
        )

    @property
    def known_skus(self) -> tuple[str, ...]:
        return distinct_sku_values(
            a.value for a in self.inputs if type(a.value) is str and a.value.strip()
        )

    @property
    def missing_assertion_ids(self) -> tuple[str, ...]:
        return tuple(
            a.assertion_id for a in self.inputs if a.value is None or not str(a.value).strip()
        )

    @property
    def value(self) -> tuple[str, ...] | None:
        return None if self.missing_assertion_ids else self.known_skus

    @property
    def status(self) -> EpistemicStatus:
        return (
            EpistemicStatus.UNRESOLVED if self.missing_assertion_ids else EpistemicStatus.OBSERVED
        )

    @property
    def execution_digest(self) -> str:
        return execution_digest(self.provenance)

    @property
    def reference_id(self) -> str:
        return stable_id(
            "source-sku-set-v1",
            self.snapshot.snapshot_id,
            tuple(a.assertion_id for a in self.inputs),
            POLICY,
            self.status.value,
            self.value,
            self.execution_digest,
        )

    @property
    def event(self) -> TransformationEvent:
        return TransformationEvent(
            "source-sku-set-query",
            self.provenance,
            tuple(
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, a)
                for a in sorted(c.assertion_id for c in self.inputs)
            ),
            (self.reference_id,),
            (self.snapshot.transformations[-1].event_id,),
        )
