"""Explicit composition helpers for application services."""

from datetime import datetime

from procurement_intelligence_lab.application.anomaly_service import AnomalyService
from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    QuantityAssessmentPolicies,
)
from procurement_intelligence_lab.domains.procurement.package import (
    BOM_PROFILE_ID,
    PROCUREMENT_PACKAGE,
)
from procurement_intelligence_lab.platform.domain_packages.compiler import (
    CompiledManifest,
    compile_domain_package,
)
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance


def build_application() -> None:
    """Placeholder for explicit dependency-injection composition."""
    return


def build_anomaly_service(
    policies: QuantityAssessmentPolicies,
    provenance: DecisionProvenance,
    detected_at: datetime,
) -> AnomalyService:
    """Compose the authorized anomaly service from explicit immutable dependencies."""
    return AnomalyService(policies, provenance, detected_at)


def compile_procurement_manifest(*, source_profile: str = BOM_PROFILE_ID) -> CompiledManifest:
    """Select the shipped vertical at composition, then use the domain-neutral compiler."""
    return compile_domain_package(PROCUREMENT_PACKAGE, source_profile=source_profile)
