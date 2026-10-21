"""A synchronous three-stage adoption service, not a general physical-plan executor."""

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.document_lineage import (
    validate_capture,
    validate_mapping,
    validate_structure,
)
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.strategies import (
    IngestStrategy,
    MapStrategy,
    StructureStrategy,
)
from procurement_intelligence_lab.platform.semantics.values import SemanticValue


def provenance_payload(value: DecisionProvenance) -> dict[str, object]:
    return {
        **asdict(value),
        "provenance_id": value.provenance_id,
        "context": {
            **asdict(value.context),
            "context_id": value.context.context_id,
            "started_at": value.context.started_at.isoformat(),
        },
    }


def scalar_payload(value: SemanticValue | None) -> str | int | bool | None:
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    return value


@dataclass(frozen=True)
class DocumentStageResult:
    artifact: Artifact
    structured: StructuredDocument
    mapped: MappedDocument
    transformations: tuple[TransformationEvent, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "executed_stages": ["INGEST", "STRUCTURE", "MAP"],
            "artifact": {
                "artifact_id": self.artifact.artifact_id,
                "content_hash": self.artifact.content_hash,
                "byte_length": self.artifact.byte_length,
                "media_type": self.artifact.media_type,
                "captured_at": self.artifact.captured_at.isoformat(),
                "source": {
                    **asdict(self.artifact.source),
                    "reference_id": self.artifact.source.reference_id,
                    "observed_at": self.artifact.source.observed_at.isoformat(),
                },
                "provenance": provenance_payload(self.artifact.provenance),
            },
            "structured_document": {
                "document_id": self.structured.document_id,
                "provenance": provenance_payload(self.structured.provenance),
                "elements": [
                    {
                        "element_id": x.element_id,
                        "kind": x.kind,
                        "ordinal": x.ordinal,
                        "text": x.text,
                        "evidence": x.evidence.as_dict(),
                    }
                    for x in self.structured.elements
                ],
            },
            "mapped_document": {
                "mapped_document_id": self.mapped.mapped_document_id,
                "source_document_id": self.structured.document_id,
                "mapping_schema": self.mapped.mapping_schema,
                "provenance": provenance_payload(self.mapped.provenance),
                "fields": [
                    {
                        "field_key": x.field_key,
                        "field_name": x.field_name,
                        "raw_value": scalar_payload(x.raw_value),
                        "status": x.status.value,
                        "diagnostic": x.diagnostic,
                        "evidence": x.evidence.as_dict(),
                    }
                    for x in self.mapped.fields
                ],
            },
            "transformations": [
                {
                    "event_id": x.event_id,
                    "event_type": x.event_type,
                    "input_edges": [
                        {"relation": edge.relation.value, "target_id": edge.target_id}
                        for edge in x.input_edges
                    ],
                    "output_ids": x.output_ids,
                    "parent_event_ids": x.parent_event_ids,
                    "provenance": provenance_payload(x.provenance),
                }
                for x in self.transformations
            ],
        }


def with_input_snapshot(provenance: DecisionProvenance, input_id: str) -> DecisionProvenance:
    snapshots = tuple(dict.fromkeys((*provenance.context.input_snapshot_ids, input_id)))
    return replace(provenance, context=replace(provenance.context, input_snapshot_ids=snapshots))


@dataclass(frozen=True)
class DocumentStages:
    ingest: IngestStrategy
    structure: StructureStrategy
    mapper: MapStrategy
    ingest_provenance: DecisionProvenance
    structure_provenance: DecisionProvenance
    mapping_provenance: DecisionProvenance
    mapping_schema: str

    def run(self, source: SourceReference) -> DocumentStageResult:
        capture_provenance = with_input_snapshot(self.ingest_provenance, source.reference_id)
        captured = self.ingest.ingest(source, provenance=capture_provenance)
        artifact = validate_capture(source, captured, capture_provenance)
        structure_provenance = with_input_snapshot(self.structure_provenance, artifact.artifact_id)
        document = self.structure.structure(artifact, provenance=structure_provenance)
        validate_structure(artifact, document, structure_provenance)
        mapping_provenance = with_input_snapshot(self.mapping_provenance, document.document_id)
        mapped = self.mapper.map_document(document, provenance=mapping_provenance)
        validate_mapping(document, mapped, self.mapping_schema, mapping_provenance)
        capture_event = TransformationEvent(
            "artifact-capture",
            artifact.provenance,
            (ProvenanceEdge(ProvenanceRelation.USED_INPUT, source.reference_id),),
            (artifact.artifact_id,),
        )
        structure_event = TransformationEvent(
            "document-structuring",
            document.provenance,
            (ProvenanceEdge(ProvenanceRelation.USED_INPUT, artifact.artifact_id),),
            (document.document_id,),
            (capture_event.event_id,),
        )
        mapping_event = TransformationEvent(
            "schema-mapping",
            mapped.provenance,
            (
                ProvenanceEdge(ProvenanceRelation.USED_INPUT, document.document_id),
                ProvenanceEdge(ProvenanceRelation.USED_SCHEMA, self.mapping_schema),
            ),
            (mapped.mapped_document_id,),
            (structure_event.event_id,),
        )
        return DocumentStageResult(
            artifact, document, mapped, (capture_event, structure_event, mapping_event)
        )
