"""Explicit composition helpers for application services."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from procurement_intelligence_lab.application.planned_bom_execution import (
        PlannedBomExecutionService,
    )
    from procurement_intelligence_lab.application.planned_resolved_bom_execution import (
        PlannedResolvedBomExecutionService,
    )
    from procurement_intelligence_lab.domains.procurement.resolution_policy import (
        BomResolutionPolicy,
    )
    from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
    from procurement_intelligence_lab.platform.execution.resolution_archive import (
        CompletedResolvedPrefixSnapshot,
    )
    from procurement_intelligence_lab.platform.execution.resolution_inputs import (
        CandidateInputEvidence,
    )
    from procurement_intelligence_lab.platform.planning.contracts import (
        ImplementationConfig,
        ImplementationDescriptor,
        ImplementationRegistry,
    )
    from procurement_intelligence_lab.ports.local_prefix_jobs import LocalPrefixJobs
    from procurement_intelligence_lab.ports.planned_execution_archive import PlannedExecutionArchive
    from procurement_intelligence_lab.ports.resolved_execution_archive import (
        ResolvedExecutionArchive,
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
    from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
    from procurement_intelligence_lab.platform.execution.archive import (
        ArchivedPrefix,
        CompletedPrefixSnapshot,
        ExecutionArchiveReceipt,
        ExecutionHistoryPage,
    )
    from procurement_intelligence_lab.platform.execution.contracts import (
        ExecutionRequest,
        ExecutionStatus,
        PrefixExecutionReceipt,
        ResolvedReference,
        StageExecutionEntry,
    )
    from procurement_intelligence_lab.platform.execution.outputs import (
        AssertedOutput,
        CapturedOutput,
        MappedOutput,
        NormalizedOutput,
        StructuredOutput,
    )
    from procurement_intelligence_lab.platform.execution.reconciliation_archive import (
        ArchivedReconciliation,
        CompletedReconciliationSnapshot,
        ReconciliationArchiveReceipt,
        ReconciliationHistoryPage,
    )
    from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
        ReconciliationOperationReceipt,
    )
    from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
        OperationAuthorityEvidence,
        ReconciliationPolicyEvidence,
        RetainedReconciliationInputs,
    )
    from procurement_intelligence_lab.platform.execution.reconciliation_outputs import (
        ReconciledOutput,
    )
    from procurement_intelligence_lab.platform.execution.resolution_archive import (
        ArchivedResolvedPrefix,
        CompletedResolvedPrefixSnapshot,
        ResolvedExecutionArchiveReceipt,
        ResolvedExecutionHistoryPage,
    )
    from procurement_intelligence_lab.platform.execution.resolution_contracts import (
        ResolvedPrefixExecutionReceipt,
    )
    from procurement_intelligence_lab.platform.execution.resolution_inputs import (
        CandidateInputEvidence,
        CandidateSnapshot,
        ResolutionPolicyEvidence,
    )
    from procurement_intelligence_lab.platform.execution.resolution_outputs import (
        MentionResolution,
        ResolvedOutput,
    )
    from procurement_intelligence_lab.platform.planning.contracts import (
        ContractRef,
        ImplementationConfig,
        ImplementationDescriptor,
        ImplementationRegistry,
        PhysicalPlan,
        StageSelection,
    )
    from procurement_intelligence_lab.platform.processing.contracts import (
        AbandonAttemptCommand,
        ArtifactArrival,
        AttemptStatus,
        AttemptSuccess,
        AttemptToken,
        JobDefinition,
        JobFailure,
        JobHistoryPage,
        JobJournalReceipt,
        JobStatus,
        JobTransition,
        JobView,
        PinnedPrefixDefinition,
        PinnedStageMetadata,
        StartAttemptCommand,
        StartIntent,
        TransitionKind,
    )
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
    from procurement_intelligence_lab.platform.semantics.errors import ErrorCategory, ErrorCode
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

    return SemanticCodec(
        (
            OperationAuthorityEvidence,
            ReconciliationPolicyEvidence,
            RetainedReconciliationInputs,
            ReconciledOutput,
            ReconciliationOperationReceipt,
            CompletedReconciliationSnapshot,
            ReconciliationArchiveReceipt,
            ArchivedReconciliation,
            ReconciliationHistoryPage,
            ReconciliationDecision,
            OperationalState,
            StateAttribute,
            CandidateSnapshot,
            CandidateInputEvidence,
            ResolutionPolicyEvidence,
            MentionResolution,
            ResolvedOutput,
            ResolvedPrefixExecutionReceipt,
            CompletedResolvedPrefixSnapshot,
            ResolvedExecutionArchiveReceipt,
            ArchivedResolvedPrefix,
            ResolvedExecutionHistoryPage,
            ResolutionDecision,
            CanonicalizedAssertion,
            ArtifactArrival,
            PinnedStageMetadata,
            PinnedPrefixDefinition,
            JobDefinition,
            StartAttemptCommand,
            AbandonAttemptCommand,
            AttemptToken,
            JobFailure,
            AttemptSuccess,
            JobTransition,
            JobJournalReceipt,
            JobView,
            JobHistoryPage,
            ExecutionRequest,
            ContractRef,
            ImplementationDescriptor,
            ImplementationRegistry,
            StageSelection,
            ImplementationConfig,
            CompletedPrefixSnapshot,
            ExecutionArchiveReceipt,
            ArchivedPrefix,
            ExecutionHistoryPage,
            PrefixExecutionReceipt,
            ResolvedReference,
            StageExecutionEntry,
            PhysicalPlan,
            CapturedOutput,
            StructuredOutput,
            MappedOutput,
            NormalizedOutput,
            AssertedOutput,
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
            ReconciliationStatus,
            StateFreshness,
            ResolutionStatus,
            JobStatus,
            AttemptStatus,
            StartIntent,
            TransitionKind,
            ErrorCode,
            ErrorCategory,
            StageId,
            StageMode,
            ExecutionStatus,
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


def build_planned_execution_archive(dsn: str):
    """Construct storage lazily using the existing optional-driver failure boundary."""
    source = build_assertion_archive(dsn)
    from procurement_intelligence_lab.adapters.postgres_planned_execution_archive import (
        PostgresPlannedExecutionArchive,
    )

    return PostgresPlannedExecutionArchive(source, source.codec)


def validate_completed_bom_prefix(completed: "CompletedPrefixSnapshot") -> None:
    """Validate retained policy content without a current planner, executor or source URI."""
    from procurement_intelligence_lab.domains.procurement.normalization import CountUnit
    from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
    from procurement_intelligence_lab.platform.execution.identity import digest
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    s = completed.snapshot
    validate_bom_assertions(s.observations, s.assertions, s.mentions)
    validate_bom_policy_declaration(
        s.normalization_policy_parameters, s.normalization_policy_reference
    )
    parameters = dict(s.normalization_policy_parameters)
    policy = BomNormalizationPolicy(
        CountUnit(parameters["quantity_unit"]),
        parameters["currency"],
        CountUnit(parameters["price_unit"]),
    )
    expected = tuple(
        sorted(
            (
                ResolvedReference(
                    BOM_TABLE_SCHEMA.reference_id,
                    BOM_TABLE_SCHEMA.reference_id,
                    digest(BOM_TABLE_SCHEMA),
                ),
                ResolvedReference(
                    "procurement.normalize/bom-decimal@1", policy.reference_id, digest(policy)
                ),
                ResolvedReference(
                    "procurement.assert/bom-claims@1",
                    "bom-assertions@1",
                    digest(("bom-assertions@1", "1")),
                ),
            ),
            key=lambda r: r.declaration_ref,
        )
    )
    if completed.execution.references != expected:
        raise ArchiveContractError("completed prefix requires supported exact policy content")


def build_planned_bom_archive_service(
    *,
    manifest: bytes,
    registry: "ImplementationRegistry",
    config: "ImplementationConfig",
    policy: BomNormalizationPolicy,
    clock: Callable[[], datetime],
    archive_factory: Callable[[], "PlannedExecutionArchive"],
):
    from procurement_intelligence_lab.application.archived_planned_execution import (
        ArchivedPlannedBomService,
    )

    store = MemoryArtifactContent()
    executions = build_planned_bom_service(
        manifest=manifest,
        registry=registry,
        config=config,
        policy=policy,
        clock=clock,
        content_store=store,
    )
    return ArchivedPlannedBomService(
        executions,
        store,
        archive_factory,
        tuple(sorted(policy.as_dict().items())),
        validate_completed_bom_prefix,
    )


def build_planned_execution_archive_reader(dsn: str):
    from procurement_intelligence_lab.application.archived_planned_execution import (
        PlannedExecutionArchiveReader,
    )

    return PlannedExecutionArchiveReader(
        build_planned_execution_archive(dsn), validate_completed_bom_prefix
    )


def build_local_prefix_jobs(dsn: str):
    """Explicit optional local-prefix journal; construction never initializes schemas."""
    from procurement_intelligence_lab.platform.processing.errors import JobUnavailableError
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError

    try:
        archive = build_planned_execution_archive(dsn)
    except ArchiveUnavailableError:
        raise JobUnavailableError("local job storage requires the storage extra") from None
    from procurement_intelligence_lab.adapters.postgres_local_prefix_jobs import (
        PostgresLocalPrefixJobs,
    )

    return PostgresLocalPrefixJobs(archive, archive.codec)


def build_local_prefix_job_service(
    *, clock: Callable[[], datetime], journal_factory: Callable[[], "LocalPrefixJobs"]
):
    """Reconstruct only the explicitly supported stored local BOM recipe."""
    from procurement_intelligence_lab.application.local_prefix_job_admission import RECIPE
    from procurement_intelligence_lab.application.local_prefix_jobs import LocalPrefixJobService
    from procurement_intelligence_lab.domains.procurement.normalization import CountUnit
    from procurement_intelligence_lab.platform.execution.identity import same
    from procurement_intelligence_lab.platform.processing.contracts import PinnedPrefixDefinition
    from procurement_intelligence_lab.platform.processing.errors import JobContractError
    from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError

    store = MemoryArtifactContent()

    def prepare_stored(definition: PinnedPrefixDefinition):
        try:
            if definition.recipe_id != RECIPE:
                raise JobContractError("unsupported stored local-prefix recipe")
            values = dict(definition.normalization_parameters)
            policy = BomNormalizationPolicy(
                CountUnit(values["quantity_unit"]),
                values["currency"],
                CountUnit(values["price_unit"]),
            )
            executions = build_planned_bom_service(
                manifest=definition.manifest,
                registry=definition.registry,
                config=definition.config,
                policy=policy,
                clock=clock,
                content_store=store,
            )
            prepared = executions.prepare(definition.request)
            pinned = PinnedPrefixDefinition.from_prepared(
                prepared,
                recipe_id=RECIPE,
                normalization_parameters=tuple(sorted(policy.as_dict().items())),
            )
            if not same(pinned, definition):
                raise JobContractError(
                    "stored definition disagrees with supported runtime metadata"
                )
            return prepared
        except (SemanticContractError, ValueError, TypeError, KeyError, AttributeError):
            raise JobContractError(
                "stored definition is not supported by the current deployment"
            ) from None

    return LocalPrefixJobService(
        journal_factory, prepare_stored, store, validate_completed_bom_prefix, clock
    )


def build_local_prefix_job_reader(dsn: str):
    from procurement_intelligence_lab.application.local_prefix_job_reader import (
        LocalPrefixJobReader,
    )

    return LocalPrefixJobReader(build_local_prefix_jobs(dsn), validate_completed_bom_prefix)


def bom_resolution_descriptor() -> "ImplementationDescriptor":
    from procurement_intelligence_lab.platform.domain_packages.package import StageId
    from procurement_intelligence_lab.platform.planning.contracts import (
        ContractRef,
        ImplementationDescriptor,
    )

    return ImplementationDescriptor(
        "bom-normalized-exact-resolve",
        "1.0",
        "1",
        StageId.RESOLVE,
        ContractRef("SourceAssertion", "1.0"),
        ContractRef("ResolutionDecision", "1.0"),
        ("abstention", "authoritative_ids"),
        "1.0",
    )


def build_planned_resolved_bom_service(
    *,
    manifest: bytes,
    registry: "ImplementationRegistry",
    config: "ImplementationConfig",
    normalization_policy: BomNormalizationPolicy,
    resolution_policy: "BomResolutionPolicy",
    candidate_input: "CandidateInputEvidence",
    clock: Callable[[], datetime],
    content_store: ArtifactContentStore | None = None,
) -> "PlannedResolvedBomExecutionService":
    from procurement_intelligence_lab.adapters.package_resolution_executor import BomResolveExecutor
    from procurement_intelligence_lab.application.planned_resolved_bom_execution import (
        PlannedResolvedBomExecutionService,
    )
    from procurement_intelligence_lab.domains.procurement.planned_resolution import (
        BomResolve,
        validate_bom_resolution_inputs,
        validate_bom_resolved_output,
    )
    from procurement_intelligence_lab.platform.execution.identity import same
    from procurement_intelligence_lab.platform.execution.resolution_admission import (
        ResolveExecutorRegistration,
    )
    from procurement_intelligence_lab.platform.execution.resolution_contracts import (
        ResolvedExecutionRequest,
    )
    from procurement_intelligence_lab.platform.execution.resolution_inputs import admit

    prefix = build_planned_bom_service(
        manifest=manifest,
        registry=registry,
        config=config,
        policy=normalization_policy,
        clock=clock,
        content_store=content_store,
    )
    strategy = BomResolve(candidate_input.snapshot, resolution_policy)
    evidence = resolution_policy.evidence
    registration = ResolveExecutorRegistration(
        bom_resolution_descriptor(),
        (),
        (evidence.reference,),
        BomResolveExecutor(
            strategy,
            candidate_input.snapshot,
            evidence,
            strategy.audit_decisions,
            validate_bom_resolved_output,
        ),
        evidence.reference.reference_id,
    )

    def validate(request: ResolvedExecutionRequest) -> None:
        admit(
            same(request.candidate_input.snapshot, candidate_input.snapshot)
            and same(request.policy, evidence)
        )
        validate_bom_resolution_inputs(
            request.candidate_input,
            resolution_policy,
            scope=request.prefix.source.scope,
            as_of=request.prefix.captured_at,
        )

    return PlannedResolvedBomExecutionService(prefix, registration, validate, clock)


def build_resolved_execution_archive(dsn: str):
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError

    try:
        from procurement_intelligence_lab.adapters.postgres_resolved_execution_archive import (
            PostgresResolvedExecutionArchive,
        )
    except ImportError:
        raise ArchiveUnavailableError(
            "resolved archive storage capability is unavailable"
        ) from None
    return PostgresResolvedExecutionArchive(build_planned_execution_archive(dsn), archive_codec())


def validate_completed_resolved_bom_prefix(completed: "CompletedResolvedPrefixSnapshot") -> None:
    """Validate supported recorded evidence without an executor, source or config file."""
    from procurement_intelligence_lab.domains.procurement.planned_resolution import (
        validate_bom_resolution_inputs,
        validate_bom_resolved_output,
    )
    from procurement_intelligence_lab.domains.procurement.resolution_policy import (
        BomResolutionPolicy,
    )
    from procurement_intelligence_lab.platform.execution.contracts import plan_payload
    from procurement_intelligence_lab.platform.execution.identity import encoded, same
    from procurement_intelligence_lab.platform.execution.resolution_inputs import (
        load_candidate_input,
    )
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    validate_completed_bom_prefix(completed.prefix)
    r = completed.execution
    policy = BomResolutionPolicy.from_parameters(r.policy.parameters)
    candidate = load_candidate_input(r.candidate_input.raw_json)
    if not same(policy.evidence, r.policy) or not same(candidate, r.candidate_input):
        raise ArchiveContractError(
            "retained resolution requires exact supported policy and catalog"
        )
    if plan_payload(r.plan)["stages"][5]["implementation"] != encoded(bom_resolution_descriptor()):
        raise ArchiveContractError("retained resolution requires supported exact implementation")
    validate_bom_resolution_inputs(
        candidate, policy, scope=completed.scope, as_of=r.context.started_at
    )
    validate_bom_resolved_output(r.output)


def build_planned_resolved_bom_archive_service(
    *,
    manifest: bytes,
    registry: "ImplementationRegistry",
    config: "ImplementationConfig",
    normalization_policy: BomNormalizationPolicy,
    resolution_policy: "BomResolutionPolicy",
    candidate_input: "CandidateInputEvidence",
    clock: Callable[[], datetime],
    archive_factory: Callable[[], "ResolvedExecutionArchive"],
):
    from procurement_intelligence_lab.application.archived_resolved_execution import (
        ArchivedResolvedBomService,
    )

    store = MemoryArtifactContent()
    executions = build_planned_resolved_bom_service(
        manifest=manifest,
        registry=registry,
        config=config,
        normalization_policy=normalization_policy,
        resolution_policy=resolution_policy,
        candidate_input=candidate_input,
        clock=clock,
        content_store=store,
    )
    return ArchivedResolvedBomService(
        executions,
        store,
        archive_factory,
        tuple(sorted(normalization_policy.as_dict().items())),
        validate_completed_resolved_bom_prefix,
    )


def build_resolved_execution_archive_reader(dsn: str):
    from procurement_intelligence_lab.application.archived_resolved_execution import (
        ResolvedExecutionArchiveReader,
    )

    return ResolvedExecutionArchiveReader(
        build_resolved_execution_archive(dsn),
        validate_completed_resolved_bom_prefix,
        lambda retained: archive_codec().dumps(retained).encode("utf-8"),
    )


def bom_reconciliation_descriptor() -> "ImplementationDescriptor":
    from procurement_intelligence_lab.platform.domain_packages.package import StageId
    from procurement_intelligence_lab.platform.planning.contracts import (
        ContractRef,
        ImplementationDescriptor,
    )

    return ImplementationDescriptor(
        "bom-governed-required-quantity",
        "1.0",
        "1",
        StageId.RECONCILE,
        ContractRef("CanonicalizedAssertion", "1.0"),
        ContractRef("OperationalState", "1.0"),
        ("abstention",),
        "1.0",
    )


def build_reconciliation_archive(dsn: str):
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError

    try:
        from procurement_intelligence_lab.adapters.postgres_reconciliation_archive import (
            PostgresReconciliationArchive,
        )
    except ImportError:
        raise ArchiveUnavailableError("optional storage capability is unavailable") from None
    return PostgresReconciliationArchive(build_resolved_execution_archive(dsn), archive_codec())
