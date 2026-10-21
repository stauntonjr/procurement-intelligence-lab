"""Compose ASSERT with explicit per-run origin and validate returned lineage."""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import cast

from procurement_intelligence_lab.application.document_stages import (
    provenance_payload,
    scalar_payload,
    with_input_snapshot,
)
from procurement_intelligence_lab.application.normalized_document_stages import (
    NormalizedDocumentResult,
    NormalizedDocumentStages,
)
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import (
    AssertionOrigin,
    SourceAssertion,
)
from procurement_intelligence_lab.platform.semantics.batch_identity import assertion_batch_id
from procurement_intelligence_lab.platform.semantics.document_lineage import validate_assertions
from procurement_intelligence_lab.platform.semantics.errors import DocumentStageError
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention
from procurement_intelligence_lab.platform.semantics.strategies import AssertStrategy


@dataclass(frozen=True)
class AssertedDocumentResult:
    normalized: NormalizedDocumentResult
    assertions: tuple[SourceAssertion, ...]
    mentions: tuple[EntityMention, ...]
    origin: AssertionOrigin
    provenance: DecisionProvenance

    @property
    def batch_id(self) -> str:
        return assertion_batch_id(
            self.origin.origin_id,
            tuple(x.assertion_id for x in self.assertions),
            tuple(x.mention_id for x in self.mentions),
            self.provenance.provenance_id,
        )

    @property
    def transformation(self) -> TransformationEvent:
        return TransformationEvent(
            "source-assertion",
            self.provenance,
            (
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, self.normalized.batch_id),
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, self.origin.origin_id),
            ),
            (
                self.batch_id,
                *(x.assertion_id for x in self.assertions),
                *(x.mention_id for x in self.mentions),
            ),
            (self.normalized.transformation.event_id,),
        )

    def as_dict(self) -> dict[str, object]:
        result = self.normalized.as_dict()
        result["executed_stages"] = ["INGEST", "STRUCTURE", "MAP", "NORMALIZE", "ASSERT"]
        mentions = {a.assertion_id: m.mention_id for m in self.mentions for a in m.assertions}
        event = self.transformation
        assertion_event_id = event.event_id
        claims: list[dict[str, object]] = []
        for claim in self.assertions:
            context = claim.context
            if context is None:
                raise DocumentStageError("ASSERT output requires derivation context")
            observation = context.observation
            claims.append(
                {
                    "assertion_id": claim.assertion_id,
                    "subject_hint": claim.subject_key,
                    "predicate": claim.predicate.value,
                    "value": scalar_payload(claim.value),
                    "unit": observation.unit,
                    "status": observation.status.value,
                    "diagnostic": observation.diagnostic,
                    "evidence": claim.evidence.as_dict(),
                    "raw_value": scalar_payload(observation.source_field.raw_value),
                    "scope": asdict(observation.scope),
                    "source_observed_at": observation.effective_at.isoformat(),
                    "recorded_at": context.origin.recorded_at.isoformat(),
                    "source_system": claim.source_system,
                    "source_version": context.origin.artifact.source.source_version,
                    "immutable_content_version": context.origin.artifact.content_hash,
                    "confidence_diagnostic": context.confidence_diagnostic,
                    "provenance": provenance_payload(context.provenance),
                    "mention_id": mentions.get(claim.assertion_id),
                    "mention_diagnostic": None
                    if claim.assertion_id in mentions
                    else "no nonblank source SKU; identity unresolved",
                    "trace": {
                        "observation_id": observation.observation_id,
                        "mapped_field_key": observation.source_field.field_key,
                        "mapped_document_id": self.normalized.stages.mapped.mapped_document_id,
                        "structured_document_id": self.normalized.stages.structured.document_id,
                        "artifact_id": context.origin.artifact.artifact_id,
                        "normalization_batch_id": self.normalized.batch_id,
                        "normalization_event_id": claim.transformation_event_id,
                        "assertion_event_id": assertion_event_id,
                        "origin_id": context.origin.origin_id,
                    },
                }
            )
        result["assertion_batch"] = {
            "batch_id": self.batch_id,
            "origin_id": self.origin.origin_id,
            "provenance": provenance_payload(self.provenance),
            "claims": claims,
            "entity_mentions": [
                {
                    "mention_id": x.mention_id,
                    "text": x.text,
                    "entity_type": x.entity_type,
                    "scope": asdict(x.scope),
                    "observed_at": x.observed_at.isoformat(),
                    "assertion_ids": [a.assertion_id for a in x.assertions],
                }
                for x in self.mentions
            ],
        }
        event = self.transformation
        result["transformations"] = [
            *cast(list[dict[str, object]], result["transformations"]),
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "input_edges": [
                    {"relation": e.relation.value, "target_id": e.target_id}
                    for e in event.input_edges
                ],
                "output_ids": event.output_ids,
                "parent_event_ids": event.parent_event_ids,
                "provenance": provenance_payload(event.provenance),
            },
        ]
        return result


@dataclass(frozen=True)
class AssertedDocumentStages:
    documents: NormalizedDocumentStages
    assertion_factory: Callable[[AssertionOrigin], AssertStrategy]
    assertion_provenance: DecisionProvenance
    recorded_at: datetime
    assertion_validator: Callable[
        [tuple[NormalizedObservation, ...], tuple[SourceAssertion, ...], tuple[EntityMention, ...]],
        None,
    ]

    def run(self, source: SourceReference) -> AssertedDocumentResult:
        normalized = self.documents.run(source)
        origin = AssertionOrigin(
            normalized.stages.artifact,
            normalized.batch_id,
            normalized.transformation,
            self.recorded_at,
        )
        provenance = self.assertion_provenance
        for snapshot in (normalized.batch_id, normalized.transformation.event_id, origin.origin_id):
            provenance = with_input_snapshot(provenance, snapshot)
        assertions, mentions = self.assertion_factory(origin).assert_observations(
            normalized.observations, provenance=provenance
        )
        validate_assertions(
            source, normalized.observations, assertions, mentions, origin, provenance
        )
        self.assertion_validator(normalized.observations, assertions, mentions)
        return AssertedDocumentResult(normalized, assertions, mentions, origin, provenance)
