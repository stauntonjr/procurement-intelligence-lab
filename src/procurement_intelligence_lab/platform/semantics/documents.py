"""Universal structure and schema-mapping contracts."""

from dataclasses import dataclass

from procurement_intelligence_lab.platform.semantics.artifacts import Artifact
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.values import (
    SemanticValue,
    validate_semantic_value,
)


@dataclass(frozen=True)
class StructuredElement:
    element_id: str
    kind: str
    ordinal: int
    text: str
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        if not self.element_id.strip() or not self.kind.strip():
            raise SemanticContractError("structured element ID and kind are required")
        if self.ordinal < 0:
            raise SemanticContractError("structured element ordinal must be non-negative")


@dataclass(frozen=True)
class StructuredDocument:
    artifact: Artifact
    elements: tuple[StructuredElement, ...]
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        element_ids = tuple(item.element_id for item in self.elements)
        ordinals = tuple(item.ordinal for item in self.elements)
        if len(element_ids) != len(set(element_ids)):
            raise SemanticContractError("structured element IDs must be unique")
        if len(ordinals) != len(set(ordinals)):
            raise SemanticContractError("structured element ordinals must be unique")
        for item in self.elements:
            if (
                item.evidence.artifact_id != self.artifact.artifact_id
                or item.evidence.content_hash != self.artifact.content_hash
            ):
                raise SemanticContractError(
                    "structured element evidence must reference the source artifact"
                )

    @property
    def document_id(self) -> str:
        return stable_id(
            "structured-document",
            self.artifact.artifact_id,
            tuple(item.element_id for item in self.elements),
            self.provenance.provenance_id,
        )


@dataclass(frozen=True)
class MappedField:
    field_key: str
    field_name: str
    raw_value: SemanticValue | None
    evidence: EvidenceRef
    status: EpistemicStatus
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        if not self.field_key.strip() or not self.field_name.strip():
            raise SemanticContractError("mapped field key and name are required")
        if self.raw_value is None:
            if self.status is not EpistemicStatus.UNRESOLVED or not self.diagnostic:
                raise SemanticContractError(
                    "missing mapped values require unresolved status and a diagnostic"
                )
        elif self.status is EpistemicStatus.UNRESOLVED:
            raise SemanticContractError("unresolved mapped fields must not carry a value")
        else:
            validate_semantic_value(self.raw_value)


@dataclass(frozen=True)
class MappedDocument:
    source_document: StructuredDocument
    mapping_schema: str
    fields: tuple[MappedField, ...]
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        if not self.mapping_schema.strip():
            raise SemanticContractError("mapping schema is required")
        field_keys = tuple(item.field_key for item in self.fields)
        if len(field_keys) != len(set(field_keys)):
            raise SemanticContractError("mapped field keys must be unique")
        source_evidence = {item.evidence.evidence_id for item in self.source_document.elements}
        if any(item.evidence.evidence_id not in source_evidence for item in self.fields):
            raise SemanticContractError(
                "mapped fields must retain evidence from the structured document"
            )

    @property
    def mapped_document_id(self) -> str:
        return stable_id(
            "mapped-document",
            self.source_document.document_id,
            self.mapping_schema,
            tuple(item.field_key for item in self.fields),
            self.provenance.provenance_id,
        )
