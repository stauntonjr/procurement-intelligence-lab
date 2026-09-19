"""Versioned synthetic discrepancy scenarios for the read-only inspector."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from importlib.resources import as_file, files

from procurement_intelligence_lab.adapters.xlsx import read_bom, read_source_row
from procurement_intelligence_lab.domains.procurement.anomalies import (
    QuantityMismatchPolicy,
    detect_quantity_mismatch,
)
from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningClaimDecision,
    GoverningPredicate,
    GoverningSourceType,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import (
    GovernedRequiredQuantityState,
    project_governed_required_quantity,
)
from procurement_intelligence_lab.platform.semantics.anomalies import Anomaly
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext, StateScope


class ShowcaseScenario(StrEnum):
    ORDER_MISMATCH = "order_mismatch"
    ORDER_MATCHED = "order_matched"
    ORDER_MISSING = "order_missing"
    ORDER_UNRESOLVED = "order_unresolved"
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
    governed_state: GovernedRequiredQuantityState


def showcase_required_quantity(
    scenario: ShowcaseScenario,
    *,
    request_context: RequestContext,
) -> ShowcaseRequiredQuantityResult:
    """Evaluate one fixed scenario through the v1 governing-claim policy."""

    candidates = _scenario_candidates(scenario)
    governed_state = project_governed_required_quantity(
        candidates,
        canonical_key="GPU-A",
        request_context=request_context,
        as_of=_AS_OF,
    )
    return ShowcaseRequiredQuantityResult(
        scenario,
        _AS_OF,
        candidates,
        governed_state.decision,
        governed_state,
    )


def _scenario_candidates(scenario: ShowcaseScenario) -> tuple[GoverningClaim, ...]:
    if scenario in (
        ShowcaseScenario.ORDER_MISMATCH,
        ShowcaseScenario.ORDER_MATCHED,
        ShowcaseScenario.ORDER_MISSING,
    ):
        return (_claim("A"),)
    if scenario in (ShowcaseScenario.CONFLICT, ShowcaseScenario.ORDER_UNRESOLVED):
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


ORDER_SCENARIOS = frozenset(
    {
        ShowcaseScenario.ORDER_MISMATCH,
        ShowcaseScenario.ORDER_MATCHED,
        ShowcaseScenario.ORDER_MISSING,
        ShowcaseScenario.ORDER_UNRESOLVED,
    }
)
ORDER_POLICY = QuantityMismatchPolicy("procurement-showcase-order-quantity/v1")


@dataclass(frozen=True)
class ShowcaseOrderComparison:
    requirement: ShowcaseRequiredQuantityResult
    ordered_quantity: Decimal | None
    order_evidence: tuple[EvidenceRef, ...]
    status: str
    reason: str | None
    anomalies: tuple[Anomaly, ...]


def showcase_order_comparison(
    scenario: ShowcaseScenario, *, request_context: RequestContext
) -> ShowcaseOrderComparison:
    """Compare one explicitly admitted order row, without inventing receipt or PO state."""
    if scenario not in ORDER_SCENARIOS:
        raise SemanticContractError("unsupported order comparison scenario")
    requirement = showcase_required_quantity(scenario, request_context=request_context)
    ordered = None
    evidence: tuple[EvidenceRef, ...] = ()
    if scenario is not ShowcaseScenario.ORDER_MISSING:
        name = (
            "showcase_order_matched.xlsx"
            if scenario is ShowcaseScenario.ORDER_MATCHED
            else "showcase_order_short.xlsx"
        )
        resource = files("procurement_intelligence_lab.examples").joinpath(name)
        with as_file(resource) as path:
            rows = read_bom(path).lines
            if len(rows) != 1 or rows[0].sku != "GPU-A":
                raise SemanticContractError("synthetic order requires one GPU-A row")
            row = rows[0]
            source = read_source_row(path, evidence=row.evidence)
            if source.cells[source.headers.index("Unit")] != "each":
                raise SemanticContractError("synthetic order unit must be each")
            ordered, evidence = row.quantity, (row.evidence,)
    expected = requirement.governed_state.expected
    if expected is None or ordered is None:
        return ShowcaseOrderComparison(
            requirement,
            ordered,
            evidence,
            "not_assessed",
            "unresolved_requirement" if expected is None else "missing_observation",
            (),
        )
    from dataclasses import replace

    context = replace(
        local_provenance_context(),
        workflow_name="showcase-order-comparison",
        config_digest=ORDER_POLICY.policy_id,
        input_snapshot_ids=tuple(ref.evidence_id for ref in expected.evidence + evidence),
    )
    provenance = DecisionProvenance(
        context,
        "quantity-mismatch",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version=ORDER_POLICY.policy_id,
    )
    anomaly = detect_quantity_mismatch(
        "GPU-A",
        expected.required_quantity,
        ordered,
        expected.evidence + evidence,
        policy=ORDER_POLICY,
        provenance=provenance,
        detected_at=requirement.as_of,
        scope=expected.scope,
    )
    return ShowcaseOrderComparison(
        requirement,
        ordered,
        evidence,
        "quantity_mismatch" if anomaly else "matched",
        None,
        (anomaly,) if anomaly else (),
    )
