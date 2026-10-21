"""Shared single-document transition guards, independent of composition or domain."""

from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import (
    AssertionOrigin,
    SourceAssertion,
)
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from procurement_intelligence_lab.platform.semantics.errors import DocumentStageError
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention


def validate_capture(
    source: SourceReference, captured: tuple[Artifact, ...], provenance: DecisionProvenance
) -> Artifact:
    if len(captured) != 1 or captured[0].source != source or captured[0].provenance != provenance:
        raise DocumentStageError("single-document capture must return exactly the requested source")
    return captured[0]


def validate_structure(
    artifact: Artifact, document: StructuredDocument, provenance: DecisionProvenance
) -> None:
    if document.artifact != artifact or document.provenance != provenance:
        raise DocumentStageError("structured output must retain the exact captured artifact")


def validate_mapping(
    document: StructuredDocument,
    mapped: MappedDocument,
    schema: str,
    provenance: DecisionProvenance,
) -> None:
    if (
        mapped.source_document != document
        or mapped.mapping_schema != schema
        or mapped.provenance != provenance
    ):
        raise DocumentStageError(
            "mapped output must retain the exact source document and configured schema"
        )


def validate_normalization(
    source: SourceReference,
    mapped: MappedDocument,
    observations: tuple[NormalizedObservation, ...],
    provenance: DecisionProvenance,
) -> None:
    if len(observations) != len(mapped.fields):
        raise DocumentStageError("normalization must retain every mapped field exactly once")
    for observation, field in zip(observations, mapped.fields, strict=True):
        if (
            observation.source_field != field
            or observation.observation_key != field.field_key
            or observation.scope != source.scope
            or observation.effective_at != source.observed_at
            or observation.provenance != provenance
        ):
            raise DocumentStageError(
                "normalized output must retain source fields, scope/time and injected provenance"
            )


def validate_assertions(
    source: SourceReference,
    observations: tuple[NormalizedObservation, ...],
    assertions: tuple[SourceAssertion, ...],
    mentions: tuple[EntityMention, ...],
    origin: AssertionOrigin,
    provenance: DecisionProvenance,
) -> None:
    if len(assertions) != len(observations) or len({x.assertion_id for x in assertions}) != len(
        assertions
    ):
        raise DocumentStageError("ASSERT must retain every observation exactly once")
    for claim, observation in zip(assertions, observations, strict=True):
        if (
            claim.context is None
            or claim.context.observation != observation
            or claim.context.origin != origin
            or claim.context.provenance != provenance
        ):
            raise DocumentStageError(
                "ASSERT must retain exact origin, observations and injected provenance"
            )
    ids = {x.assertion_id: x for x in assertions}
    seen: set[str] = set()
    for mention in mentions:
        if (
            mention.mention_id in seen
            or mention.scope != source.scope
            or mention.observed_at != source.observed_at
            or any(ids.get(x.assertion_id) != x for x in mention.assertions)
            or len({x.subject_key for x in mention.assertions}) != 1
            or not any(x.value == mention.text for x in mention.assertions)
        ):
            raise DocumentStageError(
                "ASSERT mention must retain returned claims and source scope/time"
            )
        seen.add(mention.mention_id)
