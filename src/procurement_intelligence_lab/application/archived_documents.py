"""Materialize or reconstruct source evidence without reopening its original URI."""

from collections.abc import Callable
from dataclasses import asdict, dataclass

from procurement_intelligence_lab.application.asserted_document_stages import (
    AssertedDocumentResult,
    AssertedDocumentStages,
)
from procurement_intelligence_lab.application.document_stages import DocumentStageResult
from procurement_intelligence_lab.application.normalized_document_stages import (
    NormalizedDocumentResult,
)
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt, DocumentSnapshot
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore
from procurement_intelligence_lab.ports.assertion_archive import AssertionArchive


def snapshot_for(
    result: AssertedDocumentResult, policy_parameters: tuple[tuple[str, str], ...] = ()
) -> DocumentSnapshot:
    n = result.normalized
    snapshot = DocumentSnapshot(
        n.stages.structured,
        n.stages.mapped,
        n.observations,
        result.assertions,
        result.mentions,
        (*n.stages.transformations, n.transformation, result.transformation),
        result.origin,
        n.policy_reference,
        policy_parameters,
    )
    result_for(snapshot)
    return snapshot


def result_for(snapshot: DocumentSnapshot) -> AssertedDocumentResult:
    stages = DocumentStageResult(
        snapshot.artifact, snapshot.structured, snapshot.mapped, snapshot.transformations[:3]
    )
    normalized = NormalizedDocumentResult(
        stages,
        snapshot.observations,
        snapshot.transformations[3].provenance,
        snapshot.normalization_policy_reference,
    )
    result = AssertedDocumentResult(
        normalized,
        snapshot.assertions,
        snapshot.mentions,
        snapshot.origin,
        snapshot.transformations[4].provenance,
    )
    if (
        normalized.batch_id != snapshot.origin.normalization_batch_id
        or normalized.transformation != snapshot.transformations[3]
        or result.transformation != snapshot.transformations[4]
    ):
        raise ArchiveContractError("snapshot stage receipts do not match retained records")
    return result


def receipt_payload(receipt: ArchiveReceipt) -> dict[str, object]:
    return {
        **asdict(receipt),
        "recorded_at": receipt.recorded_at.isoformat(),
        "receipt_id": receipt.receipt_id,
    }


@dataclass(frozen=True)
class ArchivedDocumentResult:
    result: AssertedDocumentResult
    receipt: ArchiveReceipt
    policy_parameters: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, object]:
        payload = {**self.result.as_dict(), "archive_receipt": receipt_payload(self.receipt)}
        if self.policy_parameters:
            payload["normalization_policy"] = dict(self.policy_parameters)
        return payload


@dataclass(frozen=True)
class ArchivedDocumentStages:
    documents: AssertedDocumentStages
    content_store: ArtifactContentStore
    archive: AssertionArchive
    policy_parameters: tuple[tuple[str, str], ...]

    def run(self, source: SourceReference) -> ArchivedDocumentResult:
        result = self.documents.run(source)
        snapshot = snapshot_for(result, self.policy_parameters)
        receipt = self.archive.append(
            snapshot, self.content_store.get(snapshot.artifact.content_hash)
        )
        return ArchivedDocumentResult(result, receipt, self.policy_parameters)


@dataclass(frozen=True)
class ArchiveReader:
    archive: AssertionArchive
    assertion_validator: Callable[
        [tuple[NormalizedObservation, ...], tuple[SourceAssertion, ...], tuple[EntityMention, ...]],
        None,
    ]

    policy_validator: Callable[[tuple[tuple[str, str], ...], str], None]

    def show(self, scope: StateScope, snapshot_id: str) -> ArchivedDocumentResult:
        receipt, snapshot = self.archive.load(scope, snapshot_id)
        self.assertion_validator(snapshot.observations, snapshot.assertions, snapshot.mentions)
        self.policy_validator(
            snapshot.normalization_policy_parameters, snapshot.normalization_policy_reference
        )
        return ArchivedDocumentResult(
            result_for(snapshot), receipt, snapshot.normalization_policy_parameters
        )
