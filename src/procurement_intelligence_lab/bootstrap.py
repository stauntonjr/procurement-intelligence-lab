"""Explicit composition helpers for application services."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from procurement_intelligence_lab.application.planned_bom_execution import (
        PlannedBomExecutionService,
    )
    from procurement_intelligence_lab.platform.planning.contracts import (
        ImplementationConfig,
        ImplementationDescriptor,
        ImplementationRegistry,
    )

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
    validate_bom_policy_declaration,
)
from procurement_intelligence_lab.domains.procurement.observation_assertions import (
    BomAssert,
    validate_bom_assertions,
)
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
from procurement_intelligence_lab.ports.artifacts import ArtifactContentStore


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


def build_bom_stage_service(
    *,
    captured_at: datetime,
    context: ProvenanceContext,
    content_store: ArtifactContentStore | None = None,
) -> DocumentStages:
    """Wire the first three real strategies; content retention lasts for this service instance."""
    store = content_store if content_store is not None else MemoryArtifactContent()
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
    *,
    captured_at: datetime,
    context: ProvenanceContext,
    policy: BomNormalizationPolicy,
    content_store: ArtifactContentStore | None = None,
) -> NormalizedDocumentStages:
    """Extend the same captured-document path with an explicitly configured domain normalizer."""
    return NormalizedDocumentStages(
        build_bom_stage_service(
            captured_at=captured_at, context=context, content_store=content_store
        ),
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
    *,
    captured_at: datetime,
    context: ProvenanceContext,
    policy: BomNormalizationPolicy,
    content_store: ArtifactContentStore | None = None,
) -> AssertedDocumentStages:
    """Adopt source claims with immutable per-run origin, before identity resolution."""
    return AssertedDocumentStages(
        build_bom_normalization_service(
            captured_at=captured_at, context=context, policy=policy, content_store=content_store
        ),
        BomAssert,
        DecisionProvenance(
            context,
            "bom-source-assertions",
            ComponentKind.DETERMINISTIC,
            "1",
            policy_version="bom-assertions@1",
        ),
        captured_at,
        validate_bom_assertions,
    )


def archive_codec():
    """Only the composition root registers concrete predicate enums for portable persistence."""
    from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
    from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
    from procurement_intelligence_lab.platform.semantics.archive import (
        ArchiveReceipt,
        DocumentSnapshot,
    )
    from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
    from procurement_intelligence_lab.platform.semantics.assertions import (
        AssertionOrigin,
        SourceAssertion,
        SourceAssertionContext,
    )
    from procurement_intelligence_lab.platform.semantics.dependencies import (
        ApprovedCorrectionRef,
        ArchivedClaimRef,
        ClaimDependency,
        DependencyManifest,
        DependencySnapshot,
    )
    from procurement_intelligence_lab.platform.semantics.document_reviews import (
        DocumentReviewDecision,
        DocumentReviewTask,
        ReviewDecisionCommand,
        ReviewHistory,
        ReviewOutcome,
        ReviewProposal,
        ReviewWorkflow,
    )
    from procurement_intelligence_lab.platform.semantics.documents import (
        MappedDocument,
        MappedField,
        StructuredDocument,
        StructuredElement,
    )
    from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
    from procurement_intelligence_lab.platform.semantics.evidence import (
        EvidenceRef,
        RecordLocation,
        TabularLocation,
    )
    from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
    from procurement_intelligence_lab.platform.semantics.provenance import (
        ProvenanceEdge,
        ProvenanceRelation,
        TransformationEvent,
    )
    from procurement_intelligence_lab.platform.semantics.resolution import EntityMention
    from procurement_intelligence_lab.platform.semantics.scope import StateScope

    return SemanticCodec(
        (
            ApprovedCorrectionRef,
            ArchivedClaimRef,
            ClaimDependency,
            DependencyManifest,
            DependencySnapshot,
            ArchiveReceipt,
            DocumentSnapshot,
            ReviewProposal,
            DocumentReviewTask,
            ReviewDecisionCommand,
            DocumentReviewDecision,
            ReviewHistory,
            Artifact,
            SourceReference,
            AssertionOrigin,
            SourceAssertion,
            SourceAssertionContext,
            MappedDocument,
            MappedField,
            StructuredDocument,
            StructuredElement,
            EvidenceRef,
            RecordLocation,
            TabularLocation,
            NormalizedObservation,
            ProvenanceContext,
            DecisionProvenance,
            ProvenanceEdge,
            TransformationEvent,
            EntityMention,
            StateScope,
        ),
        (
            AssertionPredicate,
            EpistemicStatus,
            ComponentKind,
            ProvenanceRelation,
            ReviewWorkflow,
            ReviewOutcome,
        ),
    )


def build_assertion_archive(dsn: str):
    """Driver import is lazy so the base wheel remains independent of storage extras."""
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError

    try:
        from procurement_intelligence_lab.adapters.postgres_archive import PostgresAssertionArchive
    except ImportError:
        raise ArchiveUnavailableError("archive requires the installed storage extra") from None
    return PostgresAssertionArchive(dsn, archive_codec())


def build_bom_archive_service(
    *, captured_at: datetime, context: ProvenanceContext, policy: BomNormalizationPolicy, dsn: str
):
    from procurement_intelligence_lab.application.archived_documents import ArchivedDocumentStages

    store = MemoryArtifactContent()
    return ArchivedDocumentStages(
        build_bom_assertion_service(
            captured_at=captured_at, context=context, policy=policy, content_store=store
        ),
        store,
        build_assertion_archive(dsn),
        tuple(sorted(policy.as_dict().items())),
    )


def build_archive_reader(dsn: str):
    from procurement_intelligence_lab.application.archived_documents import ArchiveReader

    return ArchiveReader(
        build_assertion_archive(dsn), validate_bom_assertions, validate_bom_policy_declaration
    )


def build_document_review_journal(dsn: str):
    from procurement_intelligence_lab.platform.semantics.errors import ReviewUnavailableError

    try:
        from procurement_intelligence_lab.adapters.postgres_document_reviews import (
            PostgresDocumentReviewJournal,
        )
    except ImportError:
        raise ReviewUnavailableError(
            "document review requires the installed storage extra"
        ) from None
    return PostgresDocumentReviewJournal(dsn, archive_codec(), build_assertion_archive(dsn))


def build_document_review_service(dsn: str, *, clock: Callable[[], datetime] | None = None):
    from procurement_intelligence_lab.application.document_reviews import DocumentReviewService
    from procurement_intelligence_lab.domains.procurement.document_reviews import (
        validate_bom_review,
    )

    return DocumentReviewService(
        build_assertion_archive(dsn),
        build_document_review_journal(dsn),
        validate_bom_review,
        clock or (lambda: datetime.now(UTC)),
    )


def build_dependency_store(dsn: str):
    from procurement_intelligence_lab.platform.semantics.errors import DependencyUnavailableError

    try:
        from procurement_intelligence_lab.adapters.postgres_dependencies import (
            PostgresDependencyStore,
        )
    except ImportError:
        raise DependencyUnavailableError(
            "dependencies require the installed storage extra"
        ) from None
    return PostgresDependencyStore(
        dsn, archive_codec(), build_assertion_archive(dsn), build_document_review_journal(dsn)
    )


def build_correction_impact_service(dsn: str, *, clock: Callable[[], datetime] | None = None):
    from procurement_intelligence_lab.application.correction_impact import CorrectionImpactService

    return CorrectionImpactService(
        build_dependency_store(dsn),
        build_document_review_service(dsn),
        clock or (lambda: datetime.now(UTC)),
    )


def build_archived_bom_query_service(dsn: str, *, clock: Callable[[], datetime] | None = None):
    from procurement_intelligence_lab.application.archived_bom_queries import (
        ArchivedBomQueryService,
    )
    from procurement_intelligence_lab.domains.procurement.source_queries import SourceSkuQuery

    return ArchivedBomQueryService(
        build_archive_reader(dsn),
        build_dependency_store(dsn),
        SourceSkuQuery,
        clock or (lambda: datetime.now(UTC)),
    )


def build_reviewed_bom_query_service(dsn: str, *, clock: Callable[[], datetime] | None = None):
    from procurement_intelligence_lab.application.reviewed_bom_queries import (
        ReviewedBomQueryService,
    )
    from procurement_intelligence_lab.domains.procurement.reviewed_source_queries import (
        ReviewedSourceSkuQuery,
    )

    return ReviewedBomQueryService(
        build_archive_reader(dsn),
        build_document_review_service(dsn),
        build_dependency_store(dsn),
        ReviewedSourceSkuQuery,
        clock or (lambda: datetime.now(UTC)),
    )


def bom_execution_descriptors() -> tuple["ImplementationDescriptor", ...]:
    """Actual supported adapter advertisements; later plan stages are deliberately absent."""
    from procurement_intelligence_lab.platform.domain_packages.package import STAGE_CATALOG, StageId
    from procurement_intelligence_lab.platform.planning.contracts import (
        ContractRef,
        ImplementationDescriptor,
    )

    ids = (
        "local-file-capture",
        "xlsx-cell-structure",
        "bom-table-map",
        "bom-value-normalization",
        "bom-source-assertions",
    )
    return tuple(
        ImplementationDescriptor(
            name,
            "1.0",
            "1",
            d.stage,
            ContractRef(d.input_contract, "1.0"),
            ContractRef(d.output_contract, "1.0"),
            ("tables",) if d.stage is StageId.STRUCTURE else (),
            "1.0",
        )
        for name, d in zip(ids, STAGE_CATALOG[:5], strict=True)
    )


def build_planned_bom_service(
    *,
    manifest: bytes,
    registry: "ImplementationRegistry",
    config: "ImplementationConfig",
    policy: BomNormalizationPolicy,
    clock: Callable[[], datetime],
    content_store: ArtifactContentStore | None = None,
) -> "PlannedBomExecutionService":
    """Assemble actual strategy executors explicitly; execution itself performs no lookup by domain."""
    from procurement_intelligence_lab.adapters.package_document_executors import (
        AssertExecutor,
        CaptureExecutor,
        MapExecutor,
        NormalizeExecutor,
        StructureExecutor,
    )
    from procurement_intelligence_lab.application.planned_bom_execution import (
        PlannedBomExecutionService,
    )
    from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
    from procurement_intelligence_lab.platform.execution.executors import (
        ExecutorRegistration,
        ExecutorRegistry,
    )
    from procurement_intelligence_lab.platform.execution.identity import digest

    store = content_store if content_store is not None else MemoryArtifactContent()
    descriptors = bom_execution_descriptors()
    schema = ResolvedReference(
        BOM_TABLE_SCHEMA.reference_id, BOM_TABLE_SCHEMA.reference_id, digest(BOM_TABLE_SCHEMA)
    )
    normal = ResolvedReference(
        "procurement.normalize/bom-decimal@1", policy.reference_id, digest(policy)
    )
    assertion = ResolvedReference(
        "procurement.assert/bom-claims@1", "bom-assertions@1", digest(("bom-assertions@1", "1"))
    )

    def factory(captured_at: datetime) -> ExecutorRegistry:
        return ExecutorRegistry(
            (
                ExecutorRegistration(
                    descriptors[0], (), (), CaptureExecutor(LocalFileIngest(store, captured_at))
                ),
                ExecutorRegistration(
                    descriptors[1],
                    (),
                    (),
                    StructureExecutor(XlsxStructure(store, BOM_TABLE_SCHEMA.sheet_name)),
                    schema_version="xlsx-cells@1",
                ),
                ExecutorRegistration(
                    descriptors[2],
                    (),
                    (schema,),
                    MapExecutor(BomTableMap(), BOM_TABLE_SCHEMA.reference_id),
                    schema_version=BOM_TABLE_SCHEMA.schema_id,
                ),
                ExecutorRegistration(
                    descriptors[3],
                    (),
                    (normal,),
                    NormalizeExecutor(BomNormalize(policy), policy.reference_id),
                    policy_version=policy.reference_id,
                    schema_version="bom-decimal@1",
                ),
                ExecutorRegistration(
                    descriptors[4],
                    (),
                    (assertion,),
                    AssertExecutor(BomAssert, validate_bom_assertions),
                    policy_version="bom-assertions@1",
                ),
            )
        )

    return PlannedBomExecutionService(manifest, registry, config, factory, clock)
