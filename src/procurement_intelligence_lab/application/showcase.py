"""Versioned synthetic discrepancy scenarios for the read-only inspector."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from importlib.resources import as_file, files

from procurement_intelligence_lab.adapters.xlsx import read_bom, read_source_row
from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningClaimDecision,
    GoverningPredicate,
    GoverningSourceType,
    reconcile_required_quantity,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext, StateScope


class ShowcaseScenario(StrEnum):
    CONFLICT = "conflict"
    SUPERSEDED = "superseded"
    SHARED_VALUE = "shared_value"
    MISSING_APPROVAL = "missing_approval"


_AS_OF = datetime(2026, 1, 15, tzinfo=UTC)
_SCOPE = ("synthetic-tenant", "synthetic-project", "synthetic-site")


@dataclass(frozen=True)
class ShowcaseRequiredQuantityResult:
    scenario: ShowcaseScenario
    as_of: datetime
    candidates: tuple[GoverningClaim, ...]
    decision: GoverningClaimDecision


def showcase_required_quantity(
    scenario: ShowcaseScenario,
    *,
    request_context: RequestContext,
) -> ShowcaseRequiredQuantityResult:
    """Evaluate one fixed scenario through the v1 governing-claim policy."""

    candidates = _scenario_candidates(scenario)
    decision = reconcile_required_quantity(
        candidates,
        canonical_key="GPU-A",
        request_context=request_context,
        as_of=_AS_OF,
    )
    return ShowcaseRequiredQuantityResult(scenario, _AS_OF, candidates, decision)


def _scenario_candidates(scenario: ShowcaseScenario) -> tuple[GoverningClaim, ...]:
    if scenario is ShowcaseScenario.CONFLICT:
        return (_claim("A"), _claim("B"))
    if scenario is ShowcaseScenario.SUPERSEDED:
        return (
            _claim("A"),
            _claim("B", effective_from=datetime(2026, 1, 10, tzinfo=UTC), supersedes=("A",)),
        )
    if scenario is ShowcaseScenario.SHARED_VALUE:
        return (_claim("A"), _claim("B-equal"))
    if scenario is ShowcaseScenario.MISSING_APPROVAL:
        return (
            _claim("A", effective_until=datetime(2026, 1, 10, tzinfo=UTC)),
            _claim(
                "B",
                effective_from=datetime(2026, 1, 10, tzinfo=UTC),
                approved_at=None,
            ),
        )
    raise ValueError(f"unsupported showcase scenario: {scenario!r}")


def _claim(
    revision: str,
    *,
    approved_at: datetime | None = datetime(2026, 1, 1, tzinfo=UTC),
    effective_from: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    effective_until: datetime | None = None,
    supersedes: tuple[str, ...] = (),
) -> GoverningClaim:
    resource_name = {
        "A": "showcase_bom_revision_a.xlsx",
        "B": "showcase_bom_revision_b.xlsx",
        "B-equal": "showcase_bom_revision_b_equal.xlsx",
    }[revision]
    resource = files("procurement_intelligence_lab.examples").joinpath(resource_name)
    with as_file(resource) as path:
        evidence = read_bom(path).lines[0].evidence
        source_row = read_source_row(path, evidence=evidence)
    try:
        unit = source_row.cells[source_row.headers.index("Unit")]
        quantity = source_row.cells[source_row.headers.index("Quantity")]
    except ValueError as error:
        raise ValueError("showcase source row lacks a required quantity or unit column") from error
    return GoverningClaim(
        claim_id=f"showcase:{revision}",
        canonical_key="GPU-A",
        predicate=GoverningPredicate.REQUIRED_QUANTITY,
        value=Decimal(quantity),
        unit=unit,
        source_type=GoverningSourceType.APPROVED_BOM_REVISION,
        scope=StateScope(*_SCOPE, revision),
        evidence=evidence,
        revision_id=revision,
        supersedes_revision_ids=supersedes,
        approved_at=approved_at,
        effective_from=effective_from,
        effective_until=effective_until,
        document_at=datetime(2025, 12, 31, tzinfo=UTC),
        ingested_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
