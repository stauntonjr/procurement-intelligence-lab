from datetime import UTC, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.adapters.memory_ledger import InMemoryAssertionLedger
from procurement_intelligence_lab.adapters.memory_retrieval import InMemoryLexicalProjection
from procurement_intelligence_lab.domain.assertions import AssertionPredicate, SourceAssertion
from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.ledger import AssertionLedgerEntry
from procurement_intelligence_lab.domain.retrieval import (
    ProjectionBuildRequest,
    ProjectionKind,
    ProjectionStatus,
)


def _entries() -> tuple[AssertionLedgerEntry, ...]:
    ledger = InMemoryAssertionLedger()
    evidence = EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B"))
    first = ledger.append(
        SourceAssertion("GPU-A", AssertionPredicate.HAS_QUANTITY, Decimal(4), evidence),
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = ledger.append(
        SourceAssertion(
            "GPU-B",
            AssertionPredicate.HAS_DESCRIPTION,
            "GPU accelerator",
            evidence,
        ),
        observed_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    return first, second


def _request() -> ProjectionBuildRequest:
    return ProjectionBuildRequest(
        "lexical-bom",
        ProjectionKind.LEXICAL,
        "1",
        "config-v1",
        datetime(2026, 1, 3, tzinfo=UTC),
    )


def test_projection_builds_from_ledger_entries_and_exposes_source_metadata() -> None:
    projection = InMemoryLexicalProjection()
    manifest = projection.build(_entries(), request=_request())

    assert manifest.status is ProjectionStatus.READY
    assert len(manifest.source_entry_ids) == 2
    hit = projection.search("lexical-bom", "accelerator")[0]
    assert hit.entry.assertion.evidence.artifact_id == "bom.xlsx"
    assert hit.epistemic_status == "source_assertion"
    assert hit.projection_manifest_id == manifest.manifest_id


def test_failed_or_deleted_projection_cannot_silently_serve_stale_results() -> None:
    projection = InMemoryLexicalProjection()
    projection.build(_entries(), request=_request())

    failed = projection.fail(
        "lexical-bom",
        reason="index corruption",
        recorded_at=datetime(2026, 1, 4, tzinfo=UTC),
    )
    assert failed.status is ProjectionStatus.FAILED
    with pytest.raises(LookupError, match="not ready"):
        projection.search("lexical-bom", "GPU")

    rebuilt = projection.build(_entries(), request=_request())
    deleted = projection.delete("lexical-bom", recorded_at=datetime(2026, 1, 5, tzinfo=UTC))
    assert rebuilt.status is ProjectionStatus.READY
    assert deleted.status is ProjectionStatus.DELETED
    with pytest.raises(LookupError, match="not ready"):
        projection.search("lexical-bom", "GPU")


def test_projection_requires_explicit_lifecycle_inputs() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ProjectionBuildRequest(
            "lexical-bom",
            ProjectionKind.LEXICAL,
            "1",
            "config-v1",
            datetime(2026, 1, 3),  # noqa: DTZ001
        )
