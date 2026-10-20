"""Reusable source-assertion records that preserve claims before truth."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.artifacts import Artifact
from procurement_intelligence_lab.platform.semantics.errors import SourceAssertionError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import (
    DecisionProvenance,
    TransformationEvent,
)

type AssertionValue = str | bool | int | Decimal | date | datetime


@dataclass(frozen=True)
class AssertionOrigin:
    artifact: Artifact
    normalization_batch_id: str
    normalization_event: TransformationEvent
    recorded_at: datetime

    def __post_init__(self) -> None:
        if (
            not self.normalization_batch_id
            or self.normalization_event.event_type != "value-normalization"
            or self.normalization_event.output_ids[0] != self.normalization_batch_id
        ):
            raise SourceAssertionError("assertion origin requires its normalization receipt")
        if self.recorded_at.tzinfo is None or self.recorded_at < self.artifact.captured_at:
            raise SourceAssertionError("assertion recording must be aware and follow capture")

    @property
    def origin_id(self) -> str:
        return stable_id(
            "assertion-origin-v1",
            self.artifact.artifact_id,
            self.normalization_batch_id,
            self.normalization_event.event_id,
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True)
class SourceAssertionContext:
    observation: NormalizedObservation
    origin: AssertionOrigin
    provenance: DecisionProvenance
    confidence_diagnostic: str

    def __post_init__(self) -> None:
        observation, origin = self.observation, self.origin
        evidence = observation.source_field.evidence
        if (
            evidence.artifact_id != origin.artifact.artifact_id
            or evidence.content_hash != origin.artifact.content_hash
            or observation.scope != origin.artifact.source.scope
            or observation.effective_at != origin.artifact.source.observed_at
            or observation.provenance != origin.normalization_event.provenance
            or observation.observation_id not in origin.normalization_event.output_ids[1:]
        ):
            raise SourceAssertionError("assertion context must retain normalization lineage")
        if not self.confidence_diagnostic.strip():
            raise SourceAssertionError("assertion confidence requires an explicit diagnostic")

    @property
    def context_id(self) -> str:
        return stable_id(
            "source-assertion-context-v1",
            self.observation,
            self.origin.origin_id,
            self.provenance.provenance_id,
            self.confidence_diagnostic,
        )


@dataclass(frozen=True)
class SourceAssertion:
    subject_key: str
    predicate: StrEnum
    value: AssertionValue | None
    evidence: EvidenceRef
    source_system: str = "document"
    transformation_event_id: str | None = None
    context: SourceAssertionContext | None = None

    def __post_init__(self) -> None:
        if not self.subject_key or not self.source_system:
            raise SourceAssertionError("assertion subject and source system are required")
        if self.value is None and self.context is None:
            raise SourceAssertionError("null assertions require unresolved context")
        if self.context is not None:
            observation, origin = self.context.observation, self.context.origin
            if (
                self.subject_key != observation.subject_hint
                or type(self.value) is not type(observation.value)
                or self.value != observation.value
                or self.evidence != observation.source_field.evidence
                or self.source_system != origin.artifact.source.source_system
                or self.transformation_event_id != origin.normalization_event.event_id
            ):
                raise SourceAssertionError("assertion must retain its exact observation and origin")

    @property
    def assertion_id(self) -> str:
        if self.context is not None:
            return stable_id(
                "source-assertion-v1",
                self.subject_key,
                self.predicate.value,
                type(self.value).__name__,
                str(self.value),
                self.evidence.evidence_id,
                self.source_system,
                self.transformation_event_id,
                self.context.context_id,
            )
        return stable_id(
            "assertion",
            self.subject_key,
            self.predicate.value,
            str(self.value),
            self.evidence.evidence_id,
            self.source_system,
            self.transformation_event_id,
        )
