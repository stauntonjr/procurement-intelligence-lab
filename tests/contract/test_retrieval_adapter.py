from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from procurement_intelligence_lab.adapters.memory_retrieval import InMemoryLexicalProjection
from procurement_intelligence_lab.domain.assertions import AssertionPredicate, SourceAssertion
from procurement_intelligence_lab.domain.bom import EvidenceRef
from procurement_intelligence_lab.domain.ledger import AssertionLedgerEntry
from procurement_intelligence_lab.domain.retrieval import ProjectionBuildRequest, ProjectionKind
from procurement_intelligence_lab.domain.scope import Permission, RequestContext


def _entries() -> tuple[AssertionLedgerEntry, ...]:
    assertion = SourceAssertion(
        "GPU-A",
        AssertionPredicate.HAS_QUANTITY,
        Decimal(4),
        EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A",)),
    )
    return (AssertionLedgerEntry(1, assertion, datetime(2026, 1, 1, tzinfo=UTC)),)


def _request() -> ProjectionBuildRequest:
    scope = RequestContext(
        "user", "tenant", "project", "site", frozenset({Permission.SEARCH}), "trace"
    )
    return ProjectionBuildRequest(
        "projection",
        ProjectionKind.LEXICAL,
        "1",
        "digest",
        datetime(2026, 1, 2, tzinfo=UTC),
        scope,
    )


@pytest.mark.contract
@pytest.mark.parametrize("kind", [ProjectionKind.VECTOR, ProjectionKind.GRAPH])
def test_lexical_adapter_rejects_unsupported_projection_kinds(kind: ProjectionKind) -> None:
    with pytest.raises(ValueError, match="does not support"):
        InMemoryLexicalProjection().build(_entries(), request=replace(_request(), kind=kind))
