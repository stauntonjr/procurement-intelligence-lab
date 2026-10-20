"""Immutable complete source snapshots; persistence does not establish governing truth."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.platform.semantics.artifacts import Artifact
from procurement_intelligence_lab.platform.semantics.assertions import (
    AssertionOrigin,
    SourceAssertion,
)
from procurement_intelligence_lab.platform.semantics.batch_identity import (
    assertion_batch_id,
    normalization_batch_id,
)
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import (
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class DocumentSnapshot:
    structured: StructuredDocument
    mapped: MappedDocument
    observations: tuple[NormalizedObservation, ...]
    assertions: tuple[SourceAssertion, ...]
    mentions: tuple[EntityMention, ...]
    transformations: tuple[TransformationEvent, ...]
    origin: AssertionOrigin
    normalization_policy_reference: str
    normalization_policy_parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.normalization_policy_parameters != tuple(
            sorted(self.normalization_policy_parameters)
        ) or len(dict(self.normalization_policy_parameters)) != len(
            self.normalization_policy_parameters
        ):
            raise ArchiveContractError(
                "snapshot policy parameters must be unique and canonically ordered"
            )
        if (
            not self.normalization_policy_reference.strip()
            or self.mapped.source_document != self.structured
            or self.origin.artifact != self.artifact
        ):
            raise ArchiveContractError("snapshot must retain its complete captured source")
        if len(self.transformations) != 5 or tuple(x.event_type for x in self.transformations) != (
            "artifact-capture",
            "document-structuring",
            "schema-mapping",
            "value-normalization",
            "source-assertion",
        ):
            raise ArchiveContractError("snapshot requires the five source-stage transformations")
        if self.transformations[0].parent_event_ids or any(
            x.parent_event_ids != (previous.event_id,)
            for previous, x in zip(self.transformations, self.transformations[1:])
        ):
            raise ArchiveContractError("snapshot transformation ancestry is incomplete")
        used = ProvenanceRelation.USED_INPUT
        capture = TransformationEvent(
            "artifact-capture",
            self.artifact.provenance,
            (ProvenanceEdge(used, self.artifact.source.reference_id),),
            (self.artifact.artifact_id,),
        )
        structure = TransformationEvent(
            "document-structuring",
            self.structured.provenance,
            (ProvenanceEdge(used, self.artifact.artifact_id),),
            (self.structured.document_id,),
            (capture.event_id,),
        )
        mapping = TransformationEvent(
            "schema-mapping",
            self.mapped.provenance,
            (
                ProvenanceEdge(used, self.structured.document_id),
                ProvenanceEdge(ProvenanceRelation.USED_SCHEMA, self.mapped.mapping_schema),
            ),
            (self.mapped.mapped_document_id,),
            (structure.event_id,),
        )
        if self.transformations[:3] != (capture, structure, mapping):
            raise ArchiveContractError("snapshot source transformation inputs/outputs disagree")
        if self.transformations[3].input_edges != (
            ProvenanceEdge(used, self.mapped.mapped_document_id),
            ProvenanceEdge(used, self.normalization_policy_reference),
        ) or self.transformations[4].input_edges != (
            ProvenanceEdge(used, self.origin.normalization_batch_id),
            ProvenanceEdge(used, self.origin.origin_id),
        ):
            raise ArchiveContractError("snapshot semantic transformation inputs disagree")
        if self.origin.normalization_batch_id != normalization_batch_id(
            self.mapped.mapped_document_id,
            tuple(x.observation_id for x in self.observations),
            self.transformations[3].provenance.provenance_id,
            self.normalization_policy_reference,
        ):
            raise ArchiveContractError("snapshot normalization batch identity disagrees")
        if self.transformations[4].output_ids[0] != assertion_batch_id(
            self.origin.origin_id,
            tuple(x.assertion_id for x in self.assertions),
            tuple(x.mention_id for x in self.mentions),
            self.transformations[4].provenance.provenance_id,
        ):
            raise ArchiveContractError("snapshot assertion batch identity disagrees")
        if self.transformations[4].output_ids[1:] != (
            *(x.assertion_id for x in self.assertions),
            *(x.mention_id for x in self.mentions),
        ):
            raise ArchiveContractError("snapshot assertion outputs are incomplete")
        if self.origin.normalization_event != self.transformations[3] or self.transformations[
            3
        ].output_ids != (
            self.origin.normalization_batch_id,
            *(x.observation_id for x in self.observations),
        ):
            raise ArchiveContractError(
                "snapshot normalization origin must retain every observation"
            )
        if tuple(x.source_field for x in self.observations) != self.mapped.fields or len(
            self.assertions
        ) != len(self.observations):
            raise ArchiveContractError("snapshot must retain every field, observation and claim")
        for claim, observation in zip(self.assertions, self.observations, strict=True):
            if (
                claim.context is None
                or claim.context.observation != observation
                or claim.context.origin != self.origin
                or claim.context.provenance != self.transformations[4].provenance
            ):
                raise ArchiveContractError("snapshot assertion context is incomplete or foreign")
        if len({x.assertion_id for x in self.assertions}) != len(self.assertions):
            raise ArchiveContractError("snapshot claim identities must be unique")
        claims = {x.assertion_id: x for x in self.assertions}
        if len({x.mention_id for x in self.mentions}) != len(self.mentions) or any(
            m.scope != self.artifact.source.scope
            or m.observed_at != self.artifact.source.observed_at
            or any(claims.get(a.assertion_id) != a for a in m.assertions)
            for m in self.mentions
        ):
            raise ArchiveContractError("snapshot mentions must retain source scope/time and claims")

    @property
    def artifact(self) -> Artifact:
        return self.structured.artifact

    @property
    def snapshot_id(self) -> str:
        return stable_id(
            "document-snapshot-v1",
            self.artifact.artifact_id,
            self.mapped.mapped_document_id,
            self.origin.origin_id,
            tuple(x.observation_id for x in self.observations),
            tuple(x.assertion_id for x in self.assertions),
            tuple(x.mention_id for x in self.mentions),
            tuple(x.event_id for x in self.transformations),
            self.normalization_policy_reference,
        )


@dataclass(frozen=True)
class ArchiveReceipt:
    sequence: int
    snapshot_id: str
    scope: StateScope
    artifact_id: str
    content_hash: str
    assertion_count: int
    recorded_at: datetime

    def __post_init__(self) -> None:
        if (
            self.sequence < 1
            or self.assertion_count < 0
            or not all((self.snapshot_id, self.artifact_id, self.content_hash))
            or self.recorded_at.tzinfo is None
        ):
            raise ArchiveContractError(
                "archive receipt requires positive sequence and explicit source/time"
            )

    @property
    def receipt_id(self) -> str:
        return stable_id(
            "archive-receipt-v1",
            self.sequence,
            self.snapshot_id,
            self.scope,
            self.artifact_id,
            self.content_hash,
            self.assertion_count,
            self.recorded_at.isoformat(),
        )
