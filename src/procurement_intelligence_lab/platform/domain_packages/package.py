"""Declarative domain-package records and the ratified platform stage catalog."""

from dataclasses import dataclass
from enum import StrEnum


class StageId(StrEnum):
    INGEST = "INGEST"
    STRUCTURE = "STRUCTURE"
    MAP = "MAP"
    NORMALIZE = "NORMALIZE"
    ASSERT = "ASSERT"
    RESOLVE = "RESOLVE"
    RECONCILE = "RECONCILE"
    DERIVE = "DERIVE"
    DETECT = "DETECT"
    PREDICT = "PREDICT"
    DECIDE = "DECIDE"
    ACT = "ACT"


STAGE_ORDER: tuple[StageId, ...] = tuple(StageId)


class StageMode(StrEnum):
    EXECUTE = "EXECUTE"
    PASSTHROUGH = "PASSTHROUGH"
    EMPTY = "EMPTY"


@dataclass(frozen=True)
class StageDefinition:
    """Platform-owned meaning and contract for one logical stage."""

    stage: StageId
    input_contract: str
    output_contract: str
    guarantee: str
    topology_index: int
    empty_result: str


STAGE_CATALOG: tuple[StageDefinition, ...] = (
    StageDefinition(
        StageId.INGEST,
        "SourceReference",
        "Artifact",
        "immutable capture identity",
        0,
        "no_captured_artifacts",
    ),
    StageDefinition(
        StageId.STRUCTURE,
        "Artifact",
        "StructuredDocument",
        "structure without domain meaning",
        1,
        "no_structured_documents",
    ),
    StageDefinition(
        StageId.MAP,
        "StructuredDocument",
        "MappedDocument",
        "schema meaning and source locations",
        2,
        "no_mapped_documents",
    ),
    StageDefinition(
        StageId.NORMALIZE,
        "MappedDocument",
        "NormalizedObservation",
        "comparable values with provenance",
        3,
        "no_normalized_observations",
    ),
    StageDefinition(
        StageId.ASSERT,
        "NormalizedObservation",
        "SourceAssertion",
        "claims remain distinct from truth",
        4,
        "no_assertions_or_mentions",
    ),
    StageDefinition(
        StageId.RESOLVE,
        "SourceAssertion",
        "ResolutionDecision",
        "abstention remains valid",
        5,
        "no_resolution_decisions",
    ),
    StageDefinition(
        StageId.RECONCILE,
        "CanonicalizedAssertion",
        "OperationalState",
        "governing and losing claims remain evidenced",
        6,
        "no_governed_state_records",
    ),
    StageDefinition(
        StageId.DERIVE,
        "OperationalState",
        "DerivedFact",
        "derived facts retain evidence links",
        7,
        "no_derived_facts",
    ),
    StageDefinition(
        StageId.DETECT,
        "OperationalState",
        "Anomaly",
        "anomalies remain distinct from predictions and actions",
        8,
        "no_anomalies",
    ),
    StageDefinition(
        StageId.PREDICT,
        "EvidenceAndState",
        "Prediction",
        "uncertainty and execution provenance",
        9,
        "no_predictions",
    ),
    StageDefinition(
        StageId.DECIDE,
        "FactsAnomaliesPredictions",
        "Decision",
        "authority and evidence are explicit",
        10,
        "no_decisions_or_recommendations",
    ),
    StageDefinition(
        StageId.ACT,
        "ApprovedDecision",
        "ActionResult",
        "authorized, idempotent, auditable result",
        11,
        "no_action_attempted",
    ),
)

STAGE_DEFINITIONS: dict[StageId, StageDefinition] = {item.stage: item for item in STAGE_CATALOG}


@dataclass(frozen=True)
class StageBinding:
    """Domain-owned declarative requirements for one catalog stage."""

    stage: StageId
    mode: StageMode
    requirements: tuple[str, ...] = ()
    domain_config_ref: str | None = None
    policy_refs: tuple[str, ...] = ()
    eval_suite_ref: str | None = None
    neutral_semantics: str | None = None
    output_contract_verified: bool = False


@dataclass(frozen=True)
class SourceProfile:
    """A complete, source-specific variant of a domain package."""

    profile_id: str
    profile_version: str
    bindings: tuple[StageBinding, ...]


@dataclass(frozen=True)
class DomainPackage:
    """Side-effect-free typed authoring data for one vertical."""

    schema_version: str
    domain_id: str
    domain_version: str
    source_profiles: tuple[SourceProfile, ...]
