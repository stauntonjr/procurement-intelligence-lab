"""Deterministic governing-claim selection for procurement policy v1."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from procurement_intelligence_lab.platform.semantics.errors import (
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)

POLICY_ID = "procurement-governing-claims/v1"


class GoverningPredicate(StrEnum):
    """Predicates with explicit authority rules in policy v1."""

    REQUIRED_QUANTITY = "required_quantity"
    ORDERED_QUANTITY = "ordered_quantity"
    PLANNED_UNIT_PRICE = "planned_unit_price"
    COMMITTED_UNIT_PRICE = "committed_unit_price"
    EXPECTED_DELIVERY = "expected_delivery"
    OBSERVED_DELIVERY = "observed_delivery"


class GoverningSourceType(StrEnum):
    """Source roles used by policy v1; names do not convey authority alone."""

    APPROVED_BOM_REVISION = "approved_bom_revision"
    APPROVED_PURCHASE_ORDER_LINE = "approved_purchase_order_line"
    ACCEPTED_SUPPLIER_QUOTE = "accepted_supplier_quote"
    SUPPLIER_CONFIRMED_COMMITMENT = "supplier_confirmed_commitment"
    RECEIPT = "receipt"
    INSPECTION = "inspection"


class GoverningClaimStatus(StrEnum):
    GOVERNED = "governed"
    GOVERNED_SHARED_VALUE = "governed_shared_value"
    UNRESOLVED = "unresolved"


_AUTHORIZED_SOURCE_TYPES: dict[GoverningPredicate, frozenset[GoverningSourceType]] = {
    GoverningPredicate.REQUIRED_QUANTITY: frozenset({GoverningSourceType.APPROVED_BOM_REVISION}),
    GoverningPredicate.ORDERED_QUANTITY: frozenset(
        {GoverningSourceType.APPROVED_PURCHASE_ORDER_LINE}
    ),
    GoverningPredicate.PLANNED_UNIT_PRICE: frozenset({GoverningSourceType.ACCEPTED_SUPPLIER_QUOTE}),
    GoverningPredicate.COMMITTED_UNIT_PRICE: frozenset(
        {GoverningSourceType.APPROVED_PURCHASE_ORDER_LINE}
    ),
    GoverningPredicate.EXPECTED_DELIVERY: frozenset(
        {GoverningSourceType.SUPPLIER_CONFIRMED_COMMITMENT}
    ),
    GoverningPredicate.OBSERVED_DELIVERY: frozenset(
        {GoverningSourceType.RECEIPT, GoverningSourceType.INSPECTION}
    ),
}


@dataclass(frozen=True)
class GoverningClaim:
    """One authority candidate before reconciliation; it is not a governed value."""

    claim_id: str
    canonical_key: str
    predicate: GoverningPredicate
    value: Decimal | datetime
    unit: str
    source_type: GoverningSourceType
    scope: StateScope
    evidence: EvidenceRef
    revision_id: str
    supersedes_revision_ids: tuple[str, ...]
    approved_at: datetime | None
    effective_from: datetime
    effective_until: datetime | None
    document_at: datetime
    ingested_at: datetime
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not all((self.claim_id.strip(), self.canonical_key.strip(), self.unit.strip())):
            raise SemanticContractError("governing claims require ID, canonical key, and unit")
        if isinstance(self.value, Decimal):
            if not self.value.is_finite() or self.value < Decimal(0):
                raise SemanticContractError(
                    "numeric governing claim values must be finite and non-negative"
                )
        elif self.value.tzinfo is None:
            raise TemporalContractError("temporal governing claim values must be timezone-aware")
        if self.predicate is GoverningPredicate.EXPECTED_DELIVERY:
            if not isinstance(self.value, datetime):
                raise SemanticContractError("expected delivery claims require a temporal value")
        elif not isinstance(self.value, Decimal):
            raise SemanticContractError("this governing predicate requires a numeric value")
        if not self.revision_id.strip():
            raise SemanticContractError("governing claims require a revision identity")
        if self.revision_id in self.supersedes_revision_ids:
            raise SemanticContractError("a revision cannot supersede itself")
        if len(set(self.supersedes_revision_ids)) != len(self.supersedes_revision_ids):
            raise SemanticContractError("superseded revision identities must be unique")
        timestamps = (self.effective_from, self.document_at, self.ingested_at)
        if self.approved_at is not None:
            timestamps += (self.approved_at,)
        if self.effective_until is not None:
            timestamps += (self.effective_until,)
        if self.observed_at is not None:
            timestamps += (self.observed_at,)
        if any(item.tzinfo is None for item in timestamps):
            raise TemporalContractError("governing claim timestamps must be timezone-aware")
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise TemporalContractError("effective interval must end after it starts")
        if self.predicate is GoverningPredicate.OBSERVED_DELIVERY and self.observed_at is None:
            raise TemporalContractError("observed delivery claims require observed_at")


@dataclass(frozen=True)
class GoverningClaimDecision:
    """Policy-backed required-quantity result with all alternatives retained."""

    canonical_key: str
    as_of: datetime
    status: GoverningClaimStatus
    value: Decimal | datetime | None
    unit: str | None
    governing: tuple[GoverningClaim, ...]
    losing: tuple[GoverningClaim, ...]
    policy_id: str = POLICY_ID
    dispositions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise TemporalContractError("governing decisions require timezone-aware as-of time")
        if not self.canonical_key.strip() or not self.policy_id.strip():
            raise SemanticContractError("governing decisions require subject and policy identity")
        if self.status is GoverningClaimStatus.UNRESOLVED:
            if self.value is not None or self.unit is not None or self.governing:
                raise SemanticContractError(
                    "unresolved decisions cannot select a value or governing claim"
                )
        elif self.value is None or self.unit is None or not self.governing:
            raise SemanticContractError("governed decisions require value, unit, and evidence")
        candidates = self.governing + self.losing
        if len({item.claim_id for item in candidates}) != len(candidates):
            raise SemanticContractError("governing decisions cannot duplicate candidates")
        if not self.dispositions:
            object.__setattr__(
                self,
                "dispositions",
                tuple((item.claim_id, _disposition(item, self)) for item in candidates),
            )
        elif {item[0] for item in self.dispositions} != {item.claim_id for item in candidates}:
            raise SemanticContractError("governing decisions require one disposition per candidate")


def reconcile_required_quantity(
    candidates: tuple[GoverningClaim, ...],
    *,
    canonical_key: str,
    request_context: RequestContext,
    as_of: datetime,
) -> GoverningClaimDecision:
    """Apply policy v1 to approved BOM revisions without inferring source order."""

    request_context.require(Permission.READ_STATE)
    if as_of.tzinfo is None:
        raise TemporalContractError("query as-of time must be timezone-aware")
    relevant = tuple(
        sorted(
            (
                item
                for item in candidates
                if item.canonical_key == canonical_key
                and item.predicate is GoverningPredicate.REQUIRED_QUANTITY
                and _matches_scope(item.scope, request_context)
            ),
            key=lambda item: item.claim_id,
        )
    )
    eligible = tuple(item for item in relevant if _eligible_required_quantity(item, as_of))
    active = tuple(item for item in eligible if not _superseded(item, eligible))
    losing = tuple(item for item in relevant if item not in active)
    if not active:
        return GoverningClaimDecision(
            canonical_key, as_of, GoverningClaimStatus.UNRESOLVED, None, None, (), losing
        )
    signatures = {(item.value, item.unit) for item in active}
    if len(signatures) != 1:
        return GoverningClaimDecision(
            canonical_key,
            as_of,
            GoverningClaimStatus.UNRESOLVED,
            None,
            None,
            (),
            relevant,
        )
    value, unit = next(iter(signatures))
    status = (
        GoverningClaimStatus.GOVERNED
        if len(active) == 1
        else GoverningClaimStatus.GOVERNED_SHARED_VALUE
    )
    return GoverningClaimDecision(canonical_key, as_of, status, value, unit, active, losing)


def reconcile_claims(
    candidates: tuple[GoverningClaim, ...],
    *,
    predicate: GoverningPredicate,
    canonical_key: str,
    request_context: RequestContext,
    as_of: datetime,
) -> GoverningClaimDecision:
    """Apply the explicit v1 authority rule for a supported predicate."""

    if predicate is GoverningPredicate.REQUIRED_QUANTITY:
        return reconcile_required_quantity(
            candidates,
            canonical_key=canonical_key,
            request_context=request_context,
            as_of=as_of,
        )
    request_context.require(Permission.READ_STATE)
    if as_of.tzinfo is None:
        raise TemporalContractError("query as-of time must be timezone-aware")
    relevant = tuple(
        sorted(
            (
                item
                for item in candidates
                if item.canonical_key == canonical_key
                and item.predicate is predicate
                and _matches_scope(item.scope, request_context)
            ),
            key=lambda item: item.claim_id,
        )
    )
    eligible = tuple(item for item in relevant if _eligible_for_predicate(item, predicate, as_of))
    if not eligible:
        return GoverningClaimDecision(
            canonical_key, as_of, GoverningClaimStatus.UNRESOLVED, None, None, (), relevant
        )
    units = {item.unit for item in eligible}
    if len(units) != 1:
        return GoverningClaimDecision(
            canonical_key, as_of, GoverningClaimStatus.UNRESOLVED, None, None, (), relevant
        )
    unit = next(iter(units))
    if predicate in (GoverningPredicate.ORDERED_QUANTITY, GoverningPredicate.OBSERVED_DELIVERY):
        if not all(isinstance(item.value, Decimal) for item in eligible):
            return GoverningClaimDecision(
                canonical_key, as_of, GoverningClaimStatus.UNRESOLVED, None, None, (), relevant
            )
        return GoverningClaimDecision(
            canonical_key,
            as_of,
            GoverningClaimStatus.GOVERNED,
            sum((item.value for item in eligible if isinstance(item.value, Decimal)), Decimal(0)),
            unit,
            eligible,
            tuple(item for item in relevant if item not in eligible),
        )
    values = {item.value for item in eligible}
    if len(values) != 1:
        return GoverningClaimDecision(
            canonical_key, as_of, GoverningClaimStatus.UNRESOLVED, None, None, (), relevant
        )
    value = next(iter(values))
    status = (
        GoverningClaimStatus.GOVERNED
        if len(eligible) == 1
        else GoverningClaimStatus.GOVERNED_SHARED_VALUE
    )
    return GoverningClaimDecision(
        canonical_key,
        as_of,
        status,
        value,
        unit,
        eligible,
        tuple(item for item in relevant if item not in eligible),
    )


def _matches_scope(scope: StateScope, context: RequestContext) -> bool:
    return (scope.tenant_id, scope.project_id, scope.site_id) == (
        context.tenant_id,
        context.project_id,
        context.site_id,
    )


def _eligible_required_quantity(candidate: GoverningClaim, as_of: datetime) -> bool:
    return (
        candidate.source_type is GoverningSourceType.APPROVED_BOM_REVISION
        and candidate.approved_at is not None
        and candidate.approved_at <= as_of
        and candidate.effective_from <= as_of
        and (candidate.effective_until is None or as_of < candidate.effective_until)
    )


def _eligible_for_predicate(
    candidate: GoverningClaim,
    predicate: GoverningPredicate,
    as_of: datetime,
) -> bool:
    if (
        candidate.source_type not in _AUTHORIZED_SOURCE_TYPES[predicate]
        or candidate.effective_from > as_of
        or (candidate.effective_until is not None and as_of >= candidate.effective_until)
    ):
        return False
    if predicate is GoverningPredicate.OBSERVED_DELIVERY:
        return candidate.observed_at is not None and candidate.observed_at <= as_of
    return candidate.approved_at is not None and candidate.approved_at <= as_of


def _disposition(candidate: GoverningClaim, decision: GoverningClaimDecision) -> str:
    if candidate in decision.governing:
        return "governing"
    if candidate.source_type not in _AUTHORIZED_SOURCE_TYPES[candidate.predicate]:
        return "ineligible: source type is not authorized"
    if (
        candidate.predicate is not GoverningPredicate.OBSERVED_DELIVERY
        and candidate.approved_at is None
    ):
        return "ineligible: approval missing"
    if candidate.effective_from > decision.as_of:
        return "ineligible: not yet effective"
    if candidate.effective_until is not None and candidate.effective_until <= decision.as_of:
        return "stale: effective interval ended"
    if candidate.revision_id in {
        superseding_id
        for governing in decision.governing
        for superseding_id in governing.supersedes_revision_ids
    }:
        return "retained: superseded"
    if decision.status is GoverningClaimStatus.UNRESOLVED:
        return "conflicting: no value established"
    return "retained: non-governing"


def _superseded(candidate: GoverningClaim, eligible: tuple[GoverningClaim, ...]) -> bool:
    return any(
        candidate.revision_id in successor.supersedes_revision_ids
        for successor in eligible
        if successor.claim_id != candidate.claim_id
    )
