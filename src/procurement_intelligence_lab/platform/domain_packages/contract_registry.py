"""Concrete Python contract registry for language-neutral stage definitions."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from procurement_intelligence_lab.platform.domain_packages.package import (
    STAGE_CATALOG,
    StageDefinition,
)
from procurement_intelligence_lab.platform.semantics.actions import (
    ActionResult,
    ApprovedDecision,
)
from procurement_intelligence_lab.platform.semantics.anomalies import Anomaly
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.decisions import (
    Decision,
    FactsAnomaliesPredictions,
)
from procurement_intelligence_lab.platform.semantics.derivation import DerivedFact
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.prediction import EvidenceAndState, Prediction
from procurement_intelligence_lab.platform.semantics.reconciliation import (
    ReconciliationDecision,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    CanonicalizedAssertion,
    EntityMention,
    ResolutionDecision,
)
from procurement_intelligence_lab.platform.semantics.state import OperationalState


@dataclass(frozen=True)
class ContractRegistration:
    name: str
    python_type: type[object]


@dataclass(frozen=True)
class ContractRegistryIssue:
    code: str
    contract: str
    message: str


class ContractRegistryError(ValueError):
    """Raised when stage names do not resolve to unique concrete contracts."""

    def __init__(self, issues: tuple[ContractRegistryIssue, ...]) -> None:
        self.issues = issues
        detail = "; ".join(f"{item.code} for {item.contract}: {item.message}" for item in issues)
        super().__init__(detail)


CONTRACT_DEFINITIONS: tuple[ContractRegistration, ...] = (
    ContractRegistration("SourceReference", SourceReference),
    ContractRegistration("Artifact", Artifact),
    ContractRegistration("StructuredDocument", StructuredDocument),
    ContractRegistration("MappedDocument", MappedDocument),
    ContractRegistration("NormalizedObservation", NormalizedObservation),
    ContractRegistration("SourceAssertion", SourceAssertion),
    ContractRegistration("EntityMention", EntityMention),
    ContractRegistration("ResolutionDecision", ResolutionDecision),
    ContractRegistration("CanonicalizedAssertion", CanonicalizedAssertion),
    ContractRegistration("ReconciliationDecision", ReconciliationDecision),
    ContractRegistration("OperationalState", OperationalState),
    ContractRegistration("DerivedFact", DerivedFact),
    ContractRegistration("Anomaly", Anomaly),
    ContractRegistration("EvidenceAndState", EvidenceAndState),
    ContractRegistration("Prediction", Prediction),
    ContractRegistration("FactsAnomaliesPredictions", FactsAnomaliesPredictions),
    ContractRegistration("Decision", Decision),
    ContractRegistration("ApprovedDecision", ApprovedDecision),
    ContractRegistration("ActionResult", ActionResult),
)


def validate_stage_contract_registry(
    catalog: tuple[StageDefinition, ...] = STAGE_CATALOG,
    registrations: tuple[ContractRegistration, ...] = CONTRACT_DEFINITIONS,
) -> MappingProxyType[str, type[object]]:
    """Return an immutable registry or fail on missing, duplicate, or drifted names."""

    issues: list[ContractRegistryIssue] = []
    names = tuple(item.name for item in registrations)
    for name in sorted({item for item in names if names.count(item) > 1}):
        issues.append(
            ContractRegistryIssue(
                "duplicate_contract_name",
                name,
                "each contract name must be registered exactly once",
            )
        )
    for item in registrations:
        python_type_value = cast(object, item.python_type)
        if not isinstance(python_type_value, type):
            issues.append(
                ContractRegistryIssue(
                    "invalid_contract_type",
                    item.name,
                    "registration must reference a concrete Python type",
                )
            )
        elif item.name != item.python_type.__name__:
            issues.append(
                ContractRegistryIssue(
                    "contract_name_drift",
                    item.name,
                    f"registered type is named {item.python_type.__name__!r}",
                )
            )
    registry = {item.name: item.python_type for item in registrations}
    for definition in catalog:
        for direction, contract_name in (
            ("input", definition.input_contract),
            ("output", definition.output_contract),
        ):
            if contract_name not in registry:
                issues.append(
                    ContractRegistryIssue(
                        "missing_stage_contract",
                        contract_name,
                        f"{definition.stage.value} {direction} has no registered type",
                    )
                )
    if issues:
        raise ContractRegistryError(tuple(issues))
    return MappingProxyType(registry)


CONTRACT_REGISTRY = validate_stage_contract_registry()
