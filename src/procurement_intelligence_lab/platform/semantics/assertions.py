"""Reusable source-assertion records that preserve claims before truth."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id

type AssertionValue = str | bool | int | Decimal | date | datetime


@dataclass(frozen=True)
class SourceAssertion:
    subject_key: str
    predicate: StrEnum
    value: AssertionValue
    evidence: EvidenceRef
    source_system: str = "document"
    transformation_event_id: str | None = None

    def __post_init__(self) -> None:
        if not self.subject_key or not self.source_system:
            raise ValueError("assertion subject and source system are required")

    @property
    def assertion_id(self) -> str:
        return stable_id(
            "assertion",
            self.subject_key,
            self.predicate.value,
            str(self.value),
            self.evidence.evidence_id,
            self.source_system,
            self.transformation_event_id,
        )
