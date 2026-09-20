from datetime import UTC, datetime
from decimal import Decimal

from procurement_intelligence_lab.domains.procurement.anomalies import (
    CoverageGapPolicy,
    ExpectedObservedAnomalyPolicies,
    MissingPurchaseOrderPolicy,
    QuantityMismatchPolicy,
    StaleRevisionPolicy,
    SubstitutionPolicy,
    detect_expected_observed_anomalies,
    detect_stale_revision,
)
from procurement_intelligence_lab.domains.procurement.provenance import local_provenance_context
from procurement_intelligence_lab.domains.procurement.state import (
    ExpectedObservedState,
    ExpectedRequirement,
)
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def test_absent_observation_does_not_prove_missing_purchase_order() -> None:
    evidence = (EvidenceRef("bom.xlsx", "hash", "BOM", 2, ("A", "B")),)
    state = ExpectedObservedState(
        ExpectedRequirement(
            "GPU-A",
            Decimal(4),
            StateScope("tenant", "project", "site", "governed-v1"),
            datetime(2026, 1, 1, tzinfo=UTC),
            evidence,
        ),
        None,
    )
    policies = ExpectedObservedAnomalyPolicies(
        MissingPurchaseOrderPolicy("missing-po/v1"),
        QuantityMismatchPolicy("quantity/v1"),
        SubstitutionPolicy("substitution/v1"),
        CoverageGapPolicy("coverage/v1"),
    )
    provenance = DecisionProvenance(
        local_provenance_context(),
        "legacy-state-orchestration",
        ComponentKind.DETERMINISTIC,
        "1",
    )

    assert (
        detect_expected_observed_anomalies(
            state,
            policy=policies,
            provenance=provenance,
            detected_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        == ()
    )


def test_unequal_revision_labels_do_not_prove_supersession() -> None:
    evidence = (EvidenceRef("revision.json", "hash", "revisions", 2, ("A", "B")),)
    provenance = DecisionProvenance(
        local_provenance_context(),
        "revision-assessment",
        ComponentKind.DETERMINISTIC,
        "1",
    )

    assert (
        detect_stale_revision(
            "GPU-A",
            "B",
            "A",
            evidence,
            is_superseded=False,
            policy=StaleRevisionPolicy("revision/v1"),
            provenance=provenance,
            detected_at=datetime(2026, 1, 2, tzinfo=UTC),
            scope=StateScope("tenant", "project", "site", "governed-v1"),
        )
        is None
    )
