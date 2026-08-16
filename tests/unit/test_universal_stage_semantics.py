from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from procurement_intelligence_lab.platform.domain_packages.contract_registry import (
    CONTRACT_DEFINITIONS,
    CONTRACT_REGISTRY,
    ContractRegistration,
    ContractRegistryError,
    validate_stage_contract_registry,
)
from procurement_intelligence_lab.platform.domain_packages.package import STAGE_CATALOG
from procurement_intelligence_lab.platform.semantics.actions import (
    ActionApproval,
    ActionResult,
    ActionStatus,
    ApprovedDecision,
)
from procurement_intelligence_lab.platform.semantics.anomalies import (
    Anomaly,
    AnomalySeverity,
    AnomalyStatus,
)
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.decisions import (
    Decision,
    DecisionAuthority,
    DecisionOutcome,
    FactsAnomaliesPredictions,
)
from procurement_intelligence_lab.platform.semantics.derivation import DerivedFact
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    MappedField,
    StructuredDocument,
    StructuredElement,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    AuthorityContractError,
    IdempotencyContractError,
    ScopeMismatchError,
    SemanticContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.evidence import (
    EvidenceRef,
    RecordLocation,
)
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.prediction import (
    EvidenceAndState,
    Prediction,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
)
from procurement_intelligence_lab.platform.semantics.reconciliation import (
    ReconciliationDecision,
    ReconciliationStatus,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    CanonicalizedAssertion,
    EntityMention,
    ResolutionDecision,
    ResolutionStatus,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.state import (
    OperationalState,
    StateAttribute,
    StateFreshness,
)
from procurement_intelligence_lab.platform.semantics.strategies import STAGE_STRATEGIES


class InventoryPredicate(StrEnum):
    HAS_COUNT = "has_count"


class InventoryAnomalyKind(StrEnum):
    COUNT_MISMATCH = "count_mismatch"


@dataclass(frozen=True)
class CountMismatch:
    expected: int
    observed: int

    @property
    def kind(self) -> InventoryAnomalyKind:
        return InventoryAnomalyKind.COUNT_MISMATCH


@dataclass(frozen=True)
class PipelineFixture:
    scope: StateScope
    evidence: EvidenceRef
    source: SourceReference
    artifact: Artifact
    structured: StructuredDocument
    mapped: MappedDocument
    observation: NormalizedObservation
    assertion: SourceAssertion
    mention: EntityMention
    resolution: ResolutionDecision
    canonicalized: CanonicalizedAssertion
    reconciliation: ReconciliationDecision
    state: OperationalState
    fact: DerivedFact
    anomaly: Anomaly
    prediction_input: EvidenceAndState
    prediction: Prediction
    decision_input: FactsAnomaliesPredictions
    decision: Decision
    approved: ApprovedDecision
    action: ActionResult


def _time(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, tzinfo=UTC)


def _provenance() -> DecisionProvenance:
    return DecisionProvenance(
        ProvenanceContext(
            "inventory-run",
            "inventory-pipeline",
            "1",
            "revision",
            "image",
            "config",
            None,
            ("snapshot",),
            _time(8),
        ),
        "inventory-stage",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="inventory-policy@1",
    )


def _pipeline_fixture() -> PipelineFixture:
    scope = StateScope("tenant", "inventory", "warehouse", "snapshot-v1")
    provenance = _provenance()
    source = SourceReference("inventory-api", "inventory://rack/7", scope, _time(9), "7")
    artifact = Artifact(source, "sha256:abc", "application/json", 4, _time(10), provenance)
    evidence = EvidenceRef(
        artifact.artifact_id,
        artifact.content_hash,
        RecordLocation("racks", "rack-7"),
    )
    structured = StructuredDocument(
        artifact,
        (StructuredElement("count-node", "record", 0, "4", evidence),),
        provenance,
    )
    mapped_field = MappedField(
        "rack-7/count",
        "count",
        Decimal(4),
        evidence,
        EpistemicStatus.OBSERVED,
    )
    mapped = MappedDocument(structured, "inventory.counts@1", (mapped_field,), provenance)
    observation = NormalizedObservation(
        "rack-7/count",
        "rack-7",
        "has_count",
        Decimal(4),
        "item",
        mapped_field,
        scope,
        _time(11),
        EpistemicStatus.OBSERVED,
        provenance,
    )
    assertion = SourceAssertion(
        "rack-7", InventoryPredicate.HAS_COUNT, Decimal(4), evidence, "inventory-api"
    )
    mention = EntityMention("rack-7", "storage-rack", (assertion,), scope, _time(11))
    resolution = ResolutionDecision(
        "rack-7",
        "inventory:rack-7",
        ResolutionStatus.RESOLVED,
        (assertion,),
        "authoritative rack identifier",
        provenance,
    )
    canonicalized = CanonicalizedAssertion(assertion, resolution, scope, _time(11))
    reconciliation = ReconciliationDecision(
        "inventory:rack-7",
        ReconciliationStatus.RECONCILED,
        (canonicalized,),
        (),
        "inventory.authority@1",
        "authoritative cycle count",
        provenance,
    )
    state = OperationalState(
        "inventory:rack-7",
        scope,
        _time(12),
        StateFreshness.CURRENT,
        (StateAttribute("count", Decimal(4), EpistemicStatus.OBSERVED, (evidence,), "item"),),
        (evidence,),
        provenance,
        reconciliation.reconciliation_id,
    )
    fact = DerivedFact(
        "inventory:rack-7",
        "available_count",
        Decimal(4),
        scope,
        _time(12),
        (evidence,),
        (state.state_id,),
        provenance,
        unit="item",
    )
    anomaly = Anomaly(
        "inventory:rack-7",
        CountMismatch(4, 3),
        AnomalySeverity.WARNING,
        AnomalyStatus.OPEN,
        (evidence,),
        "inventory.count-drift@1",
        provenance,
        _time(13),
        scope,
    )
    prediction_input = EvidenceAndState(scope, _time(13), (evidence,), (state,))
    prediction = Prediction(
        "inventory:rack-7",
        "tomorrow_count",
        Decimal(3),
        Decimal("0.75"),
        "calibrated interval from held-out counts",
        scope,
        _time(13),
        _time(14),
        _time(15),
        (evidence,),
        prediction_input,
        provenance,
        "item",
    )
    decision_input = FactsAnomaliesPredictions(scope, _time(13), (fact,), (anomaly,), (prediction,))
    decision_authority = DecisionAuthority(
        "inventory-review", "reviewer", "inventory reviewer", scope
    )
    decision = Decision(
        "inventory:rack-7",
        DecisionOutcome.RECOMMEND,
        "recount the rack",
        "inventory.recount@1",
        decision_authority,
        decision_input,
        (evidence,),
        _time(14),
        provenance,
    )
    approval_authority = DecisionAuthority(
        "inventory-action", "approver", "warehouse approver", scope, True
    )
    approval = ActionApproval(decision.decision_id, approval_authority, _time(15), (evidence,))
    approved = ApprovedDecision(decision, approval)
    action = ActionResult(
        approved,
        "request-cycle-count",
        "rack-7:count:2026-01-01",
        ActionStatus.SUCCEEDED,
        _time(16),
        (evidence,),
        provenance,
        _time(17),
        "work-order-7",
    )
    return PipelineFixture(
        scope,
        evidence,
        source,
        artifact,
        structured,
        mapped,
        observation,
        assertion,
        mention,
        resolution,
        canonicalized,
        reconciliation,
        state,
        fact,
        anomaly,
        prediction_input,
        prediction,
        decision_input,
        decision,
        approved,
        action,
    )


def test_non_procurement_fixture_exercises_every_typed_stage_contract() -> None:
    pipeline = _pipeline_fixture()

    outputs = (
        pipeline.artifact,
        pipeline.structured,
        pipeline.mapped,
        pipeline.observation,
        pipeline.assertion,
        pipeline.resolution,
        pipeline.state,
        pipeline.fact,
        pipeline.anomaly,
        pipeline.prediction,
        pipeline.decision,
        pipeline.action,
    )

    assert len(outputs) == len(STAGE_CATALOG)
    assert pipeline.source.reference_id
    assert pipeline.mention.mention_id
    assert pipeline.canonicalized.canonicalized_assertion_id
    assert pipeline.reconciliation.reconciliation_id
    assert pipeline.prediction_input.input_id
    assert pipeline.decision_input.input_id
    assert pipeline.action.action_id


def test_every_catalog_contract_resolves_to_a_concrete_type() -> None:
    names = {
        name
        for definition in STAGE_CATALOG
        for name in (definition.input_contract, definition.output_contract)
    }

    assert names <= CONTRACT_REGISTRY.keys()
    assert all(isinstance(CONTRACT_REGISTRY[name], type) for name in names)
    assert all(CONTRACT_REGISTRY[name].__name__ == name for name in names)


def test_every_catalog_stage_has_one_runtime_strategy_protocol() -> None:
    assert tuple(STAGE_STRATEGIES) == tuple(item.stage for item in STAGE_CATALOG)
    assert all(getattr(strategy, "_is_protocol", False) for strategy in STAGE_STRATEGIES.values())


def test_contract_registry_rejects_missing_duplicate_and_drifted_names() -> None:
    without_action = tuple(item for item in CONTRACT_DEFINITIONS if item.name != "ActionResult")
    with_duplicate = CONTRACT_DEFINITIONS + (CONTRACT_DEFINITIONS[0],)
    drifted = CONTRACT_DEFINITIONS + (ContractRegistration("RenamedActionResult", ActionResult),)

    with pytest.raises(ContractRegistryError, match="missing_stage_contract.*ActionResult"):
        validate_stage_contract_registry(registrations=without_action)
    with pytest.raises(ContractRegistryError, match="duplicate_contract_name"):
        validate_stage_contract_registry(registrations=with_duplicate)
    with pytest.raises(ContractRegistryError, match="contract_name_drift"):
        validate_stage_contract_registry(registrations=drifted)


def test_artifact_contract_rejects_malformed_and_temporal_identity() -> None:
    pipeline = _pipeline_fixture()

    with pytest.raises(SemanticContractError, match="system and URI"):
        replace(pipeline.source, source_system="")
    with pytest.raises(TemporalContractError, match="observed_at"):
        replace(pipeline.source, observed_at=datetime(2026, 1, 1, 9))  # noqa: DTZ001
    with pytest.raises(SemanticContractError, match="source_version"):
        replace(pipeline.source, source_version="")
    with pytest.raises(SemanticContractError, match="hash and media"):
        replace(pipeline.artifact, content_hash="")
    with pytest.raises(SemanticContractError, match="non-negative"):
        replace(pipeline.artifact, byte_length=-1)
    with pytest.raises(TemporalContractError, match="captured_at"):
        replace(pipeline.artifact, captured_at=datetime(2026, 1, 1, 10))  # noqa: DTZ001
    with pytest.raises(TemporalContractError, match="cannot precede"):
        replace(pipeline.artifact, captured_at=_time(8))


def test_structure_and_mapping_reject_duplicate_or_untraceable_content() -> None:
    pipeline = _pipeline_fixture()
    duplicate = pipeline.structured.elements[0]
    foreign_evidence = EvidenceRef(
        "other-artifact", "other-hash", RecordLocation("racks", "rack-7")
    )

    with pytest.raises(SemanticContractError, match="element IDs"):
        StructuredDocument(
            pipeline.artifact,
            (duplicate, duplicate),
            _provenance(),
        )
    with pytest.raises(SemanticContractError, match="source artifact"):
        StructuredDocument(
            pipeline.artifact,
            (replace(duplicate, evidence=foreign_evidence),),
            _provenance(),
        )
    with pytest.raises(SemanticContractError, match="structured document"):
        MappedDocument(
            pipeline.structured,
            "inventory.counts@1",
            (
                MappedField(
                    "rack-7/count",
                    "count",
                    4,
                    foreign_evidence,
                    EpistemicStatus.OBSERVED,
                ),
            ),
            _provenance(),
        )


def test_missing_and_unresolved_are_not_silent_values() -> None:
    pipeline = _pipeline_fixture()
    mapped_field = pipeline.mapped.fields[0]

    with pytest.raises(SemanticContractError, match="unresolved status"):
        replace(mapped_field, raw_value=None)
    with pytest.raises(SemanticContractError, match="must not carry a value"):
        replace(mapped_field, status=EpistemicStatus.UNRESOLVED)
    with pytest.raises(SemanticContractError, match="unresolved status"):
        replace(pipeline.observation, value=None)
    with pytest.raises(SemanticContractError, match="missing source field"):
        replace(
            pipeline.observation,
            source_field=replace(
                mapped_field,
                raw_value=None,
                status=EpistemicStatus.UNRESOLVED,
                diagnostic="missing",
            ),
        )
    with pytest.raises(SemanticContractError, match="finite"):
        replace(mapped_field, raw_value=Decimal("NaN"))


def test_unresolved_resolution_cannot_become_a_canonical_assertion() -> None:
    pipeline = _pipeline_fixture()
    unresolved = replace(
        pipeline.resolution,
        canonical_key=None,
        status=ResolutionStatus.UNRESOLVED,
    )

    with pytest.raises(SemanticContractError, match="resolved identity"):
        replace(pipeline.canonicalized, resolution=unresolved)
    unrelated = replace(
        pipeline.assertion,
        subject_key="rack-8",
    )
    with pytest.raises(SemanticContractError, match="share a subject"):
        replace(pipeline.canonicalized, assertion=unrelated)


def test_resolution_decision_rejects_blank_identifiers_with_typed_failures() -> None:
    pipeline = _pipeline_fixture()

    with pytest.raises(SemanticContractError, match="mention and rationale"):
        replace(pipeline.resolution, mention=" ")
    with pytest.raises(SemanticContractError, match="mention and rationale"):
        replace(pipeline.resolution, rationale="\t")
    with pytest.raises(SemanticContractError, match="canonical key"):
        replace(pipeline.resolution, canonical_key=" ")
    with pytest.raises(SemanticContractError, match="must not carry"):
        replace(
            pipeline.resolution,
            canonical_key="rack-7",
            status=ResolutionStatus.UNRESOLVED,
        )


def test_reconciliation_rejects_duplicate_and_cross_scope_claims() -> None:
    pipeline = _pipeline_fixture()
    other_scope = StateScope("tenant", "other", "warehouse", "snapshot-v1")
    other = replace(pipeline.canonicalized, scope=other_scope)

    with pytest.raises(SemanticContractError, match="more than once"):
        replace(
            pipeline.reconciliation,
            governing=(pipeline.canonicalized,),
            losing=(pipeline.canonicalized,),
        )
    with pytest.raises(SemanticContractError, match="one scope"):
        replace(
            pipeline.reconciliation,
            governing=(pipeline.canonicalized,),
            losing=(other,),
        )


def test_operational_state_requires_complete_attribute_evidence() -> None:
    pipeline = _pipeline_fixture()
    foreign = EvidenceRef("other", "hash", RecordLocation("other", "1"))

    with pytest.raises(SemanticContractError, match="include every attribute"):
        replace(pipeline.state, evidence=(foreign,))
    with pytest.raises(SemanticContractError, match="names must be unique"):
        replace(
            pipeline.state,
            attributes=(pipeline.state.attributes[0], pipeline.state.attributes[0]),
        )
    with pytest.raises(SemanticContractError, match="evidence must be unique"):
        replace(pipeline.state, evidence=(pipeline.evidence, pipeline.evidence))


def test_derived_fact_requires_finite_evidenced_unique_lineage() -> None:
    pipeline = _pipeline_fixture()

    with pytest.raises(SemanticContractError, match="finite"):
        replace(pipeline.fact, value=Decimal("Infinity"))
    with pytest.raises(TemporalContractError, match="as_of"):
        replace(pipeline.fact, as_of=datetime(2026, 1, 1, 12))  # noqa: DTZ001
    with pytest.raises(SemanticContractError, match="evidence and source"):
        replace(pipeline.fact, evidence=())
    with pytest.raises(SemanticContractError, match="must be unique"):
        replace(pipeline.fact, source_state_ids=(pipeline.state.state_id,) * 2)
    with pytest.raises(SemanticContractError, match="inferred"):
        replace(pipeline.fact, status=EpistemicStatus.OBSERVED)
    with pytest.raises(SemanticContractError, match="unit"):
        replace(pipeline.fact, unit="")


@given(
    confidence=st.decimals(
        min_value=Decimal(0),
        max_value=Decimal(1),
        allow_nan=False,
        allow_infinity=False,
        places=6,
    )
)
def test_prediction_accepts_closed_probability_boundary(confidence: Decimal) -> None:
    prediction = replace(_pipeline_fixture().prediction, confidence=confidence)

    assert Decimal(0) <= prediction.confidence <= Decimal(1)


@pytest.mark.parametrize("confidence", [Decimal("-0.1"), Decimal("1.1"), Decimal("NaN")])
def test_prediction_rejects_invalid_uncertainty(confidence: Decimal) -> None:
    with pytest.raises(SemanticContractError, match="confidence"):
        replace(_pipeline_fixture().prediction, confidence=confidence)


def test_prediction_inputs_reject_future_or_cross_scope_state() -> None:
    pipeline = _pipeline_fixture()
    other_scope = StateScope("tenant", "other", "warehouse", "snapshot-v1")

    with pytest.raises(ScopeMismatchError):
        replace(
            pipeline.prediction_input,
            states=(replace(pipeline.state, scope=other_scope),),
        )
    with pytest.raises(TemporalContractError, match="future"):
        replace(pipeline.prediction_input, as_of=_time(11))
    with pytest.raises(SemanticContractError, match="states must be unique"):
        replace(pipeline.prediction_input, states=(pipeline.state, pipeline.state))


def test_prediction_rejects_empty_malformed_or_inconsistent_horizon() -> None:
    pipeline = _pipeline_fixture()

    with pytest.raises(SemanticContractError, match="requires evidence"):
        EvidenceAndState(pipeline.scope, _time(13), (), ())
    with pytest.raises(TemporalContractError, match="timezone-aware"):
        replace(
            pipeline.prediction_input,
            as_of=datetime(2026, 1, 1, 13),  # noqa: DTZ001
        )
    with pytest.raises(SemanticContractError, match="subject and outcome"):
        replace(pipeline.prediction, subject_key="")
    with pytest.raises(SemanticContractError, match="uncertainty basis"):
        replace(pipeline.prediction, uncertainty_basis="")
    with pytest.raises(TemporalContractError, match="timestamps"):
        replace(
            pipeline.prediction,
            horizon_end=datetime(2026, 1, 1, 15),  # noqa: DTZ001
        )
    with pytest.raises(TemporalContractError, match="horizon"):
        replace(pipeline.prediction, horizon_start=_time(12))
    with pytest.raises(SemanticContractError, match="require evidence"):
        replace(pipeline.prediction, evidence=())
    other_scope = StateScope("tenant", "other", "warehouse", "snapshot-v1")
    with pytest.raises(ScopeMismatchError, match="prediction and inputs"):
        replace(
            pipeline.prediction,
            inputs=EvidenceAndState(other_scope, _time(13), (pipeline.evidence,), ()),
        )
    with pytest.raises(TemporalContractError, match="input as_of"):
        replace(
            pipeline.prediction,
            inputs=replace(pipeline.prediction_input, as_of=_time(14)),
        )
    with pytest.raises(SemanticContractError, match="originate"):
        replace(
            pipeline.prediction,
            evidence=(EvidenceRef("other", "hash", RecordLocation("other", "prediction")),),
        )


def test_late_stage_identities_change_with_material_inputs() -> None:
    pipeline = _pipeline_fixture()
    changed_state = replace(pipeline.state, as_of=_time(11))
    changed_prediction_input = replace(
        pipeline.prediction_input,
        states=(changed_state,),
    )
    changed_prediction = replace(
        pipeline.prediction,
        inputs=changed_prediction_input,
    )
    changed_decision_input = replace(
        pipeline.decision_input,
        predictions=(changed_prediction,),
    )
    changed_decision = replace(pipeline.decision, inputs=changed_decision_input)

    assert changed_prediction.input_id != pipeline.prediction.input_id
    assert changed_prediction.prediction_id != pipeline.prediction.prediction_id
    assert changed_decision_input.input_id != pipeline.decision_input.input_id
    assert changed_decision.decision_id != pipeline.decision.decision_id


def test_decision_inputs_reject_unscoped_anomalies_and_future_results() -> None:
    pipeline = _pipeline_fixture()

    with pytest.raises(ScopeMismatchError, match="explicit state scope"):
        replace(
            pipeline.decision_input,
            anomalies=(replace(pipeline.anomaly, scope=cast(StateScope, None)),),
        )
    with pytest.raises(TemporalContractError, match="future predictions"):
        replace(pipeline.decision_input, as_of=_time(12))


def test_decision_inputs_and_authority_fail_closed() -> None:
    pipeline = _pipeline_fixture()
    other_scope = StateScope("tenant", "other", "warehouse", "snapshot-v1")

    with pytest.raises(SemanticContractError, match="requires facts"):
        FactsAnomaliesPredictions(pipeline.scope, _time(13))
    with pytest.raises(SemanticContractError, match="duplicates"):
        replace(pipeline.decision_input, facts=(pipeline.fact, pipeline.fact))
    with pytest.raises(ScopeMismatchError, match="facts"):
        replace(
            pipeline.decision_input,
            facts=(replace(pipeline.fact, scope=other_scope),),
        )
    with pytest.raises(TemporalContractError, match="future facts"):
        replace(
            pipeline.decision_input,
            facts=(replace(pipeline.fact, as_of=_time(14)),),
        )
    with pytest.raises(TemporalContractError, match="future anomalies"):
        replace(
            pipeline.decision_input,
            anomalies=(replace(pipeline.anomaly, detected_at=_time(14)),),
        )
    with pytest.raises(AuthorityContractError, match="principal"):
        replace(pipeline.decision.authority, principal_id="")
    with pytest.raises(ScopeMismatchError, match="authority"):
        replace(
            pipeline.decision,
            authority=replace(pipeline.decision.authority, scope=other_scope),
        )
    with pytest.raises(TemporalContractError, match="decided_at"):
        replace(
            pipeline.decision,
            decided_at=datetime(2026, 1, 1, 14),  # noqa: DTZ001
        )
    with pytest.raises(TemporalContractError, match="cannot precede"):
        replace(pipeline.decision, decided_at=_time(12))
    with pytest.raises(SemanticContractError, match="require evidence"):
        replace(pipeline.decision, evidence=())


def test_action_requires_authority_approval_idempotency_and_consistent_status() -> None:
    pipeline = _pipeline_fixture()
    unprivileged = replace(
        pipeline.approved.approval.authority,
        may_approve_actions=False,
    )

    with pytest.raises(AuthorityContractError, match="explicitly permit"):
        replace(pipeline.approved.approval, authority=unprivileged)
    with pytest.raises(IdempotencyContractError):
        replace(pipeline.action, idempotency_key="")
    with pytest.raises(SemanticContractError, match="require completed_at"):
        replace(pipeline.action, completed_at=None)
    with pytest.raises(SemanticContractError, match="failure reason"):
        replace(pipeline.action, status=ActionStatus.FAILED, failure_reason=None)


def test_approval_and_action_audit_transitions_fail_closed() -> None:
    pipeline = _pipeline_fixture()
    approval = pipeline.approved.approval
    other_scope = StateScope("tenant", "other", "warehouse", "snapshot-v1")

    with pytest.raises(AuthorityContractError, match="decision ID"):
        replace(approval, decision_id="")
    with pytest.raises(TemporalContractError, match="approval timestamp"):
        replace(approval, approved_at=datetime(2026, 1, 1, 15))  # noqa: DTZ001
    with pytest.raises(AuthorityContractError, match="requires evidence"):
        replace(approval, evidence=())
    with pytest.raises(AuthorityContractError, match="evidence must be unique"):
        replace(approval, evidence=(pipeline.evidence, pipeline.evidence))
    with pytest.raises(AuthorityContractError, match="recommended"):
        ApprovedDecision(
            replace(pipeline.decision, outcome=DecisionOutcome.REJECT),
            approval,
        )
    with pytest.raises(AuthorityContractError, match="exact decision"):
        replace(pipeline.approved, approval=replace(approval, decision_id="decision:other"))
    with pytest.raises(ScopeMismatchError, match="share one scope"):
        replace(
            pipeline.approved,
            approval=replace(
                approval,
                authority=replace(approval.authority, scope=other_scope),
            ),
        )
    with pytest.raises(TemporalContractError, match="precede the decision"):
        replace(pipeline.approved, approval=replace(approval, approved_at=_time(13)))
    with pytest.raises(SemanticContractError, match="action kind"):
        replace(pipeline.action, action_kind="")
    with pytest.raises(TemporalContractError, match="attempted_at"):
        replace(
            pipeline.action,
            attempted_at=datetime(2026, 1, 1, 16),  # noqa: DTZ001
        )
    with pytest.raises(TemporalContractError, match="precede approval"):
        replace(pipeline.action, attempted_at=_time(14))
    with pytest.raises(TemporalContractError, match="completed_at"):
        replace(
            pipeline.action,
            completed_at=datetime(2026, 1, 1, 17),  # noqa: DTZ001
        )
    with pytest.raises(TemporalContractError, match="precede its attempt"):
        replace(pipeline.action, completed_at=_time(15))
    with pytest.raises(SemanticContractError, match="audit evidence"):
        replace(pipeline.action, evidence=())
    with pytest.raises(SemanticContractError, match="evidence must be unique"):
        replace(pipeline.action, evidence=(pipeline.evidence, pipeline.evidence))
    with pytest.raises(SemanticContractError, match="external_reference"):
        replace(pipeline.action, external_reference="")
    with pytest.raises(SemanticContractError, match="only failed"):
        replace(pipeline.action, failure_reason="unexpected")


def test_empty_action_stage_is_distinct_from_an_attempted_action_result() -> None:
    pipeline = _pipeline_fixture()

    attempted = replace(
        pipeline.action,
        status=ActionStatus.ATTEMPTED,
        completed_at=None,
        external_reference=None,
    )

    assert attempted.status is ActionStatus.ATTEMPTED
    assert attempted.action_id
