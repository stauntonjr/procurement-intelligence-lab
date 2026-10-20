"""Explicit composition helpers for application services."""

from collections.abc import Callable
from datetime import UTC, datetime

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
