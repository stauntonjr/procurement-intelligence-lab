"""Stage-specific immutable values and actual transformation evidence."""

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import cast

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.identity import canonical, same, text
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import (
    AssertionOrigin,
    SourceAssertion,
)
from procurement_intelligence_lab.platform.semantics.batch_identity import (
    assertion_batch_id,
    normalization_batch_id,
)
from procurement_intelligence_lab.platform.semantics.document_lineage import (
    validate_assertions,
    validate_normalization,
)
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    MappedField,
    StructuredDocument,
    StructuredElement,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    DocumentStageError,
    PackageExecutionContractError,
)
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention


def require(condition: bool) -> None:
    if not condition:
        raise PackageExecutionContractError(
            "stage output must retain exact typed input, lineage and provenance"
        )


def immutable(value: object) -> None:
    """Reject mutable nested transport values before deriving any output identity."""
    if value is None or type(value) in (str, int, bool, bytes, date, datetime, Decimal):
        return
    if isinstance(value, Enum):
        return
    if type(value) is tuple:
        for item in cast(tuple[object, ...], value):
            immutable(item)
        return
    require(is_dataclass(value) and not isinstance(value, type))
    require(getattr(getattr(value, "__dataclass_params__", None), "frozen", False))
    assert is_dataclass(value) and not isinstance(value, type)
    for field in fields(value):
        immutable(getattr(value, field.name))


def immutable_output(value: object) -> None:
    try:
        immutable(value)
    except RecursionError:
        require(False)


def event(
    kind: str,
    provenance: DecisionProvenance,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
    parents: tuple[str, ...] = (),
    schema: str | None = None,
) -> TransformationEvent:
    edges = tuple(ProvenanceEdge(ProvenanceRelation.USED_INPUT, x) for x in inputs)
    if schema is not None:
        edges += (ProvenanceEdge(ProvenanceRelation.USED_SCHEMA, schema),)
    return TransformationEvent(kind, provenance, edges, outputs, parents)


@dataclass(frozen=True)
class CapturedOutput:
    artifact: Artifact
    event: TransformationEvent

    def __post_init__(self) -> None:
        immutable_output(self)
        require(type(self.artifact) is Artifact and type(self.event) is TransformationEvent)
        require(
            same(
                self.event,
                event(
                    "artifact-capture", self.artifact.provenance, self.input_ids, self.reference_ids
                ),
            )
        )
        canonical(self)

    @property
    def stage(self) -> StageId:
        return StageId.INGEST

    @property
    def source(self) -> SourceReference:
        return self.artifact.source

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (self.artifact.artifact_id,)

    @property
    def input_ids(self) -> tuple[str, ...]:
        return (self.source.reference_id,)


@dataclass(frozen=True)
class StructuredOutput:
    previous: CapturedOutput
    document: StructuredDocument
    event: TransformationEvent

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.previous) is CapturedOutput
            and type(self.document) is StructuredDocument
            and type(self.event) is TransformationEvent
        )
        require(all(type(x) is StructuredElement for x in self.document.elements))
        require(same(self.document.artifact, self.previous.artifact))
        require(
            same(
                self.event,
                event(
                    "document-structuring",
                    self.document.provenance,
                    self.input_ids,
                    self.reference_ids,
                    (self.previous.event.event_id,),
                ),
            )
        )
        canonical(self)

    @property
    def stage(self) -> StageId:
        return StageId.STRUCTURE

    @property
    def source(self) -> SourceReference:
        return self.previous.source

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (self.document.document_id,)

    @property
    def input_ids(self) -> tuple[str, ...]:
        return self.previous.reference_ids


@dataclass(frozen=True)
class MappedOutput:
    previous: StructuredOutput
    document: MappedDocument
    event: TransformationEvent

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.previous) is StructuredOutput
            and type(self.document) is MappedDocument
            and type(self.event) is TransformationEvent
        )
        require(all(type(x) is MappedField for x in self.document.fields))
        require(same(self.document.source_document, self.previous.document))
        require(
            same(
                self.event,
                event(
                    "schema-mapping",
                    self.document.provenance,
                    self.input_ids,
                    self.reference_ids,
                    (self.previous.event.event_id,),
                    self.document.mapping_schema,
                ),
            )
        )
        canonical(self)

    @property
    def stage(self) -> StageId:
        return StageId.MAP

    @property
    def source(self) -> SourceReference:
        return self.previous.source

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (self.document.mapped_document_id,)

    @property
    def input_ids(self) -> tuple[str, ...]:
        return self.previous.reference_ids


@dataclass(frozen=True)
class NormalizedOutput:
    previous: MappedOutput
    observations: tuple[NormalizedObservation, ...]
    provenance: DecisionProvenance
    policy_reference: str

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.previous) is MappedOutput
            and type(self.observations) is tuple
            and type(self.provenance) is DecisionProvenance
        )
        require(all(type(x) is NormalizedObservation for x in self.observations))
        text(self.policy_reference)
        try:
            validate_normalization(
                self.source, self.previous.document, self.observations, self.provenance
            )
        except DocumentStageError:
            require(False)
        for o, f in zip(self.observations, self.previous.document.fields, strict=True):
            require(
                same(o.source_field, f)
                and same(o.scope, self.source.scope)
                and same(o.effective_at, self.source.observed_at)
                and same(o.provenance, self.provenance)
            )
        canonical(self)

    @property
    def stage(self) -> StageId:
        return StageId.NORMALIZE

    @property
    def source(self) -> SourceReference:
        return self.previous.source

    @property
    def batch_id(self) -> str:
        return normalization_batch_id(
            self.previous.document.mapped_document_id,
            tuple(x.observation_id for x in self.observations),
            self.provenance.provenance_id,
            self.policy_reference,
        )

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (self.batch_id, *(x.observation_id for x in self.observations))

    @property
    def input_ids(self) -> tuple[str, ...]:
        return (*self.previous.reference_ids, self.policy_reference)

    @property
    def event(self) -> TransformationEvent:
        return event(
            "value-normalization",
            self.provenance,
            self.input_ids,
            self.reference_ids,
            (self.previous.event.event_id,),
        )


@dataclass(frozen=True)
class AssertedOutput:
    previous: NormalizedOutput
    assertions: tuple[SourceAssertion, ...]
    mentions: tuple[EntityMention, ...]
    origin: AssertionOrigin
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.previous) is NormalizedOutput
            and type(self.assertions) is tuple
            and type(self.mentions) is tuple
            and type(self.origin) is AssertionOrigin
            and type(self.provenance) is DecisionProvenance
        )
        require(
            all(type(x) is SourceAssertion for x in self.assertions)
            and all(type(x) is EntityMention for x in self.mentions)
        )
        require(
            same(self.origin.artifact, self.previous.previous.previous.previous.artifact)
            and same(self.origin.normalization_event, self.previous.event)
            and self.origin.normalization_batch_id == self.previous.batch_id
        )
        try:
            validate_assertions(
                self.source,
                self.previous.observations,
                self.assertions,
                self.mentions,
                self.origin,
                self.provenance,
            )
        except DocumentStageError:
            require(False)
        for claim, observation in zip(self.assertions, self.previous.observations, strict=True):
            require(claim.context is not None)
            assert claim.context is not None
            require(
                same(claim.context.observation, observation)
                and same(claim.context.origin, self.origin)
                and same(claim.context.provenance, self.provenance)
            )
        claims = {claim.assertion_id: claim for claim in self.assertions}
        for mention in self.mentions:
            require(
                same(mention.scope, self.source.scope)
                and same(mention.observed_at, self.source.observed_at)
                and all(same(claims.get(claim.assertion_id), claim) for claim in mention.assertions)
            )
        canonical(self)

    @property
    def stage(self) -> StageId:
        return StageId.ASSERT

    @property
    def source(self) -> SourceReference:
        return self.previous.source

    @property
    def batch_id(self) -> str:
        return assertion_batch_id(
            self.origin.origin_id,
            tuple(x.assertion_id for x in self.assertions),
            tuple(x.mention_id for x in self.mentions),
            self.provenance.provenance_id,
        )

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (
            self.batch_id,
            *(x.assertion_id for x in self.assertions),
            *(x.mention_id for x in self.mentions),
        )

    @property
    def input_ids(self) -> tuple[str, ...]:
        return (self.previous.batch_id, self.origin.origin_id)

    @property
    def event(self) -> TransformationEvent:
        return event(
            "source-assertion",
            self.provenance,
            self.input_ids,
            self.reference_ids,
            (self.previous.event.event_id,),
        )

    @property
    def chain(self) -> tuple["StageOutput", ...]:
        n = self.previous
        m = n.previous
        s = m.previous
        return (s.previous, s, m, n, self)


type StageInput = (
    SourceReference | CapturedOutput | StructuredOutput | MappedOutput | NormalizedOutput
)
type StageOutput = (
    CapturedOutput | StructuredOutput | MappedOutput | NormalizedOutput | AssertedOutput
)
