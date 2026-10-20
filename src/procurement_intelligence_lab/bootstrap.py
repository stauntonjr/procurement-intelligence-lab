"""Explicit composition helpers for application services."""

from datetime import datetime

from procurement_intelligence_lab.adapters.local_artifacts import (
    LocalFileIngest,
    MemoryArtifactContent,
)
from procurement_intelligence_lab.adapters.xlsx_structure import XlsxStructure
from procurement_intelligence_lab.application.anomaly_service import AnomalyService
from procurement_intelligence_lab.application.asserted_document_stages import AssertedDocumentStages
from procurement_intelligence_lab.application.document_stages import DocumentStages
from procurement_intelligence_lab.application.normalized_document_stages import (
    NormalizedDocumentStages,
)
from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    QuantityAssessmentPolicies,
)
from procurement_intelligence_lab.domains.procurement.mapping import BomTableMap
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    BomNormalize,
)
from procurement_intelligence_lab.domains.procurement.observation_assertions import BomAssert
from procurement_intelligence_lab.domains.procurement.package import (
    BOM_PROFILE_ID,
    PROCUREMENT_PACKAGE,
)
from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA
from procurement_intelligence_lab.platform.domain_packages.compiler import (
    CompiledManifest,
    compile_domain_package,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
)


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


def build_bom_stage_service(*, captured_at: datetime, context: ProvenanceContext) -> DocumentStages:
    """Wire the first three real strategies; content retention lasts for this service instance."""
    store = MemoryArtifactContent()
    return DocumentStages(
        LocalFileIngest(store, captured_at),
        XlsxStructure(store, BOM_TABLE_SCHEMA.sheet_name),
        BomTableMap(),
        DecisionProvenance(context, "local-file-capture", ComponentKind.DETERMINISTIC, "1"),
        DecisionProvenance(
            context,
            "xlsx-cell-structure",
            ComponentKind.DETERMINISTIC,
            "1",
            schema_version="xlsx-cells@1",
        ),
        DecisionProvenance(
            context,
            "bom-table-map",
            ComponentKind.DETERMINISTIC,
            "1",
            schema_version=BOM_TABLE_SCHEMA.schema_id,
        ),
        BOM_TABLE_SCHEMA.reference_id,
    )


def build_bom_normalization_service(
    *, captured_at: datetime, context: ProvenanceContext, policy: BomNormalizationPolicy
) -> NormalizedDocumentStages:
    """Extend the same captured-document path with an explicitly configured domain normalizer."""
    return NormalizedDocumentStages(
        build_bom_stage_service(captured_at=captured_at, context=context),
        BomNormalize(policy),
        DecisionProvenance(
            context,
            "bom-value-normalization",
            ComponentKind.DETERMINISTIC,
            "1",
            policy_version=policy.reference_id,
            schema_version="bom-decimal@1",
        ),
        policy.reference_id,
    )


def build_bom_assertion_service(
    *, captured_at: datetime, context: ProvenanceContext, policy: BomNormalizationPolicy
) -> AssertedDocumentStages:
    """Adopt source claims with immutable per-run origin, before identity resolution."""
    return AssertedDocumentStages(
        build_bom_normalization_service(captured_at=captured_at, context=context, policy=policy),
        BomAssert,
        DecisionProvenance(
            context,
            "bom-source-assertions",
            ComponentKind.DETERMINISTIC,
            "1",
            policy_version="bom-assertions@1",
        ),
        captured_at,
    )
