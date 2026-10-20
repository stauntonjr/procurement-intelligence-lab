"""Compose NORMALIZE after the existing three-stage document service."""

from dataclasses import asdict, dataclass

from procurement_intelligence_lab.application.document_stages import (
    DocumentStageResult,
    DocumentStages,
    provenance_payload,
    scalar_payload,
    with_input_snapshot,
)
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import DocumentStageError
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.strategies import NormalizeStrategy


@dataclass(frozen=True)
class NormalizedDocumentResult:
    stages: DocumentStageResult
    observations: tuple[NormalizedObservation, ...]
    provenance: DecisionProvenance
    policy_reference: str

    @property
    def batch_id(self) -> str:
        return stable_id(
            "normalization-batch",
            self.stages.mapped.mapped_document_id,
            tuple(x.observation_id for x in self.observations),
            self.provenance.provenance_id,
            self.policy_reference,
        )

    @property
    def transformation(self) -> TransformationEvent:
        return TransformationEvent(
            "value-normalization",
            self.provenance,
            (
                ProvenanceEdge(
                    ProvenanceRelation.USED_INPUT, self.stages.mapped.mapped_document_id
                ),
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, self.policy_reference),
            ),
            (self.batch_id, *(x.observation_id for x in self.observations)),
            (self.stages.transformations[-1].event_id,),
        )

    def as_dict(self) -> dict[str, object]:
        result = self.stages.as_dict()
        result["executed_stages"] = ["INGEST", "STRUCTURE", "MAP", "NORMALIZE"]
        result["normalization"] = {
            "batch_id": self.batch_id,
            "policy_reference": self.policy_reference,
            "source_document_id": self.stages.mapped.mapped_document_id,
            "provenance": provenance_payload(self.provenance),
            "observations": [
                {
                    "observation_id": x.observation_id,
                    "observation_key": x.observation_key,
                    "subject_hint": x.subject_hint,
                    "predicate": x.predicate,
                    "value": scalar_payload(x.value),
                    "unit": x.unit,
                    "scope": asdict(x.scope),
                    "effective_at": x.effective_at.isoformat(),
                    "status": x.status.value,
                    "diagnostic": x.diagnostic,
                    "provenance": provenance_payload(x.provenance),
                    "source_field": {
                        "field_key": x.source_field.field_key,
                        "field_name": x.source_field.field_name,
                        "raw_value": scalar_payload(x.source_field.raw_value),
                        "evidence": x.source_field.evidence.as_dict(),
                        "status": x.source_field.status.value,
                        "diagnostic": x.source_field.diagnostic,
                    },
                }
                for x in self.observations
            ],
        }
        event = self.transformation
        result["transformations"] = [
            {
                "event_id": x.event_id,
                "event_type": x.event_type,
                "input_edges": [
                    {"relation": e.relation.value, "target_id": e.target_id} for e in x.input_edges
                ],
                "output_ids": x.output_ids,
                "parent_event_ids": x.parent_event_ids,
                "provenance": provenance_payload(x.provenance),
            }
            for x in (*self.stages.transformations, event)
        ]
        return result


@dataclass(frozen=True)
class NormalizedDocumentStages:
    documents: DocumentStages
    normalizer: NormalizeStrategy
    normalization_provenance: DecisionProvenance
    policy_reference: str

    def __post_init__(self) -> None:
        if not self.policy_reference.strip():
            raise DocumentStageError("normalization requires a policy reference")

    def run(self, source: SourceReference) -> NormalizedDocumentResult:
        stages = self.documents.run(source)
        provenance = with_input_snapshot(
            with_input_snapshot(self.normalization_provenance, stages.mapped.mapped_document_id),
            self.policy_reference,
        )
        observations = self.normalizer.normalize(stages.mapped, provenance=provenance)
        if len(observations) != len(stages.mapped.fields):
            raise DocumentStageError("normalization must retain every mapped field exactly once")
        for observation, field in zip(observations, stages.mapped.fields, strict=True):
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
        return NormalizedDocumentResult(stages, observations, provenance, self.policy_reference)
