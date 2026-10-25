"""Typed failures and stable codes shared by universal semantic contracts."""

from enum import StrEnum
from typing import ClassVar


class ErrorCategory(StrEnum):
    """Closed failure taxonomy used by code, logs, and external boundaries."""

    INPUT = "input"
    INTERPRETATION = "interpretation"
    IDENTITY = "identity"
    POLICY = "policy"
    INFRASTRUCTURE = "infrastructure"
    TRANSIENT = "transient"
    AUTHORIZATION = "authorization"


class ErrorCode(StrEnum):
    """Stable identifiers for implemented platform semantic failures."""

    LOCAL_PREFIX_JOB_INVALID = "pil.input.local_prefix_job_invalid"
    LOCAL_PREFIX_JOB_CONFLICT = "pil.policy.local_prefix_job_conflict"
    LOCAL_PREFIX_JOB_BUSY = "pil.policy.local_prefix_job_busy"
    LOCAL_PREFIX_JOB_FENCED = "pil.policy.local_prefix_job_fenced"
    LOCAL_PREFIX_JOB_NOT_FOUND = "pil.input.local_prefix_job_not_found"
    LOCAL_PREFIX_JOB_INTEGRITY_INVALID = "pil.infrastructure.local_prefix_job_integrity_invalid"
    LOCAL_PREFIX_JOB_UNAVAILABLE = "pil.infrastructure.local_prefix_job_unavailable"
    SOURCE_QUERY_INVALID = "pil.input.source_query_invalid"
    RECONCILIATION_INPUT_UNSUPPORTED = "pil.input.reconciliation_input_unsupported"
    PACKAGE_EXECUTION_INVALID = "pil.input.package_execution_invalid"
    PACKAGE_EXECUTION_CONTRACT_INVALID = "pil.interpretation.package_execution_contract_invalid"
    PACKAGE_PLANNING_INVALID = "pil.input.package_planning_invalid"
    ARTIFACT_SOURCE_UNAVAILABLE = "pil.infrastructure.artifact_source_unavailable"
    ARTIFACT_CONTENT_INVALID = "pil.infrastructure.artifact_content_invalid"
    SOURCE_REFERENCE_UNSUPPORTED = "pil.input.source_reference_unsupported"
    DOCUMENT_STRUCTURE_INVALID = "pil.interpretation.document_structure_invalid"
    SCHEMA_MAPPING_INVALID = "pil.interpretation.schema_mapping_invalid"
    DOCUMENT_STAGE_INVALID = "pil.input.document_stage_invalid"
    NORMALIZATION_INVALID = "pil.interpretation.normalization_invalid"
    NORMALIZATION_POLICY_INVALID = "pil.input.normalization_policy_invalid"
    ARCHIVE_CONTRACT_INVALID = "pil.input.archive_contract_invalid"
    ARCHIVE_NOT_FOUND = "pil.input.archive_not_found"
    ARCHIVE_CONFLICT = "pil.policy.archive_conflict"
    ARCHIVE_INTEGRITY_INVALID = "pil.infrastructure.archive_integrity_invalid"
    ARCHIVE_UNAVAILABLE = "pil.infrastructure.archive_unavailable"
    DOCUMENT_REVIEW_CONTRACT_INVALID = "pil.input.document_review_contract_invalid"
    DOCUMENT_REVIEW_NOT_FOUND = "pil.input.document_review_not_found"
    DOCUMENT_REVIEW_CONFLICT = "pil.policy.document_review_conflict"
    DOCUMENT_REVIEW_INTEGRITY_INVALID = "pil.infrastructure.document_review_integrity_invalid"
    DOCUMENT_REVIEW_UNAVAILABLE = "pil.infrastructure.document_review_unavailable"
    DEPENDENCY_CONTRACT_INVALID = "pil.input.dependency_contract_invalid"
    DEPENDENCY_NOT_FOUND = "pil.input.dependency_not_found"
    DEPENDENCY_CONFLICT = "pil.policy.dependency_conflict"
    DEPENDENCY_INTEGRITY_INVALID = "pil.infrastructure.dependency_integrity_invalid"
    DEPENDENCY_UNAVAILABLE = "pil.infrastructure.dependency_unavailable"
    SOURCE_ASSERTION_INVALID = "pil.interpretation.source_assertion_invalid"
    DOMAIN_PACKAGE_INVALID = "pil.input.domain_package_invalid"
    BRIEF_NOT_FOUND = "pil.input.brief_not_found"
    BRIEF_REVIEW_CONFLICT = "pil.policy.brief_review_conflict"
    BRIEF_STORE_UNAVAILABLE = "pil.infrastructure.brief_store_unavailable"
    WORKFLOW_UNAVAILABLE = "pil.infrastructure.workflow_unavailable"
    WORKFLOW_BUDGET_EXCEEDED = "pil.policy.workflow_budget_exceeded"
    AGENT_TOOL_ADMISSION_FAILED = "pil.infrastructure.agent_tool_admission_failed"
    AGENT_TOOL_TIMEOUT = "pil.transient.agent_tool_timeout"
    AGENT_TOOL_UNAVAILABLE = "pil.infrastructure.agent_tool_unavailable"
    AGENT_TOOL_INVALID_RESULT = "pil.input.agent_tool_invalid_result"
    AGENT_RUN_NOT_FOUND = "pil.input.agent_run_not_found"
    AGENT_RUN_CONFLICT = "pil.policy.agent_run_conflict"
    AGENT_RUN_STORE_UNAVAILABLE = "pil.infrastructure.agent_run_store_unavailable"
    SEMANTIC_CONTRACT_VIOLATION = "pil.input.semantic_contract_violation"
    SEMANTIC_TYPE_CONTRACT_VIOLATION = "pil.input.semantic_type_contract_violation"
    SCOPE_CONTRACT_VIOLATION = "pil.input.scope_contract_violation"
    SCOPE_MISMATCH = "pil.policy.scope_mismatch"
    TEMPORAL_CONTRACT_VIOLATION = "pil.input.temporal_contract_violation"
    POLICY_CONTRACT_VIOLATION = "pil.policy.contract_violation"
    RECONCILIATION_POLICY_NO_MATCH = "pil.policy.reconciliation_no_governing_source"
    AUTHORITY_CONTRACT_VIOLATION = "pil.authorization.authority_contract_violation"
    AUTHORITY_SCOPE_MISMATCH = "pil.authorization.scope_mismatch"
    REQUEST_SCOPE_DENIED = "pil.authorization.request_scope_denied"
    IDEMPOTENCY_CONTRACT_VIOLATION = "pil.policy.idempotency_contract_violation"


class SemanticContractError(ValueError):
    """Raised when a semantic record violates an intrinsic invariant."""

    category: ClassVar[ErrorCategory] = ErrorCategory.INPUT
    code: ClassVar[ErrorCode] = ErrorCode.SEMANTIC_CONTRACT_VIOLATION

    def __init__(self, message: str) -> None:
        if not message.strip():
            raise ValueError("semantic contract errors require a non-empty message")
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        """Return the stable public failure envelope without a stack trace."""
        return {
            "code": self.code.value,
            "category": self.category.value,
            "message": str(self),
        }


class SemanticTypeContractError(TypeError):
    """Raised when a semantic caller supplies an unsupported runtime type."""

    category: ClassVar[ErrorCategory] = ErrorCategory.INPUT
    code: ClassVar[ErrorCode] = ErrorCode.SEMANTIC_TYPE_CONTRACT_VIOLATION

    def __init__(self, message: str) -> None:
        if not message.strip():
            raise ValueError("semantic type contract errors require a non-empty message")
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        """Return the stable public failure envelope without a stack trace."""
        return {
            "code": self.code.value,
            "category": self.category.value,
            "message": str(self),
        }


class ScopeContractError(SemanticContractError):
    """Raised when a required scope value is absent or malformed."""

    code = ErrorCode.SCOPE_CONTRACT_VIOLATION


class ScopeMismatchError(SemanticContractError):
    """Raised when records from different governed scopes are composed."""

    category = ErrorCategory.POLICY
    code = ErrorCode.SCOPE_MISMATCH


class TemporalContractError(SemanticContractError):
    """Raised when a semantic timestamp is naive or temporally inconsistent."""

    code = ErrorCode.TEMPORAL_CONTRACT_VIOLATION


class AuthorityContractError(SemanticContractError):
    """Raised when a decision or action lacks explicit authority."""

    category = ErrorCategory.AUTHORIZATION
    code = ErrorCode.AUTHORITY_CONTRACT_VIOLATION


class AuthorityScopeMismatchError(AuthorityContractError):
    """Raised when authority is presented for a different governed scope."""

    code = ErrorCode.AUTHORITY_SCOPE_MISMATCH


class ScopeAuthorizationError(PermissionError):
    """Raised when a request lacks an explicit authorized scope."""

    category: ClassVar[ErrorCategory] = ErrorCategory.AUTHORIZATION
    code: ClassVar[ErrorCode] = ErrorCode.REQUEST_SCOPE_DENIED

    def __init__(self, message: str) -> None:
        if not message.strip():
            raise ValueError("scope authorization errors require a non-empty message")
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        """Return the stable public failure envelope without a stack trace."""
        return {
            "code": self.code.value,
            "category": self.category.value,
            "message": str(self),
        }


class PolicyContractError(SemanticContractError):
    """Raised when a well-formed value violates an explicit policy contract."""

    category = ErrorCategory.POLICY
    code = ErrorCode.POLICY_CONTRACT_VIOLATION


class IdempotencyContractError(SemanticContractError):
    """Raised when an action has no stable idempotency boundary."""

    category = ErrorCategory.POLICY
    code = ErrorCode.IDEMPOTENCY_CONTRACT_VIOLATION


class ArtifactSourceError(SemanticContractError):
    """The explicit source bytes cannot be read."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.ARTIFACT_SOURCE_UNAVAILABLE


class ArtifactContentError(SemanticContractError):
    """Captured content is absent or fails its identity/integrity contract."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.ARTIFACT_CONTENT_INVALID


class SourceReferenceError(SemanticContractError):
    """A source reference requests an unsupported transport or URI variant."""

    code = ErrorCode.SOURCE_REFERENCE_UNSUPPORTED


class DocumentStructureError(SemanticContractError):
    """The captured document cannot be structured by the selected adapter."""

    category = ErrorCategory.INTERPRETATION
    code = ErrorCode.DOCUMENT_STRUCTURE_INVALID


class SchemaMappingError(SemanticContractError):
    """Structured evidence cannot be mapped under the selected schema."""

    category = ErrorCategory.INTERPRETATION
    code = ErrorCode.SCHEMA_MAPPING_INVALID


class DocumentStageError(SemanticContractError):
    """Stage inputs, caller context or returned lineage violate the contract."""

    code = ErrorCode.DOCUMENT_STAGE_INVALID


class NormalizationError(SemanticContractError):
    """Mapped evidence cannot be interpreted under the selected normalization profile."""

    category = ErrorCategory.INTERPRETATION
    code = ErrorCode.NORMALIZATION_INVALID


class NormalizationPolicyError(SemanticContractError):
    """A normalization policy is missing or contains unsupported declarations."""

    code = ErrorCode.NORMALIZATION_POLICY_INVALID


class SourceAssertionError(SemanticContractError):
    """Source claims or their derivation context violate the assertion contract."""

    category = ErrorCategory.INTERPRETATION
    code = ErrorCode.SOURCE_ASSERTION_INVALID


class ArchiveContractError(SemanticContractError):
    """Archive inputs cannot satisfy the portable snapshot contract."""

    code = ErrorCode.ARCHIVE_CONTRACT_INVALID


class ArchiveNotFoundError(SemanticContractError):
    """No archive record is available within the exact requested scope."""

    code = ErrorCode.ARCHIVE_NOT_FOUND


class ArchiveConflictError(SemanticContractError):
    """An immutable identity was reused with different content."""

    category = ErrorCategory.POLICY
    code = ErrorCode.ARCHIVE_CONFLICT


class ArchiveIntegrityError(SemanticContractError):
    """Stored data is missing, corrupt or incompatible with its claimed identity."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.ARCHIVE_INTEGRITY_INVALID


class ArchiveUnavailableError(SemanticContractError):
    """The selected persistence backend cannot complete this operation."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.ARCHIVE_UNAVAILABLE


class ReviewContractError(SemanticContractError):
    """Typed document-review boundary failure."""

    category = ErrorCategory.INPUT
    code = ErrorCode.DOCUMENT_REVIEW_CONTRACT_INVALID


class ReviewNotFoundError(SemanticContractError):
    """Typed document-review boundary failure."""

    category = ErrorCategory.INPUT
    code = ErrorCode.DOCUMENT_REVIEW_NOT_FOUND


class ReviewConflictError(SemanticContractError):
    """Typed document-review boundary failure."""

    category = ErrorCategory.POLICY
    code = ErrorCode.DOCUMENT_REVIEW_CONFLICT


class ReviewIntegrityError(SemanticContractError):
    """Typed document-review boundary failure."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.DOCUMENT_REVIEW_INTEGRITY_INVALID


class ReviewUnavailableError(SemanticContractError):
    """Typed document-review boundary failure."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.DOCUMENT_REVIEW_UNAVAILABLE


class DependencyContractError(SemanticContractError):
    """Typed dependency contract failure."""

    category = ErrorCategory.INPUT
    code = ErrorCode.DEPENDENCY_CONTRACT_INVALID


class DependencyNotFoundError(SemanticContractError):
    """Typed dependency notfound failure."""

    category = ErrorCategory.INPUT
    code = ErrorCode.DEPENDENCY_NOT_FOUND


class DependencyConflictError(SemanticContractError):
    """Typed dependency conflict failure."""

    category = ErrorCategory.POLICY
    code = ErrorCode.DEPENDENCY_CONFLICT


class DependencyIntegrityError(SemanticContractError):
    """Typed dependency integrity failure."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.DEPENDENCY_INTEGRITY_INVALID


class DependencyUnavailableError(SemanticContractError):
    """Typed dependency unavailable failure."""

    category = ErrorCategory.INFRASTRUCTURE
    code = ErrorCode.DEPENDENCY_UNAVAILABLE


class SourceQueryContractError(SemanticContractError):
    """An archived source query cannot establish its required input contract."""

    code = ErrorCode.SOURCE_QUERY_INVALID


class PackageExecutionError(SemanticContractError):
    """An execution request or runtime selection cannot be admitted."""

    code = ErrorCode.PACKAGE_EXECUTION_INVALID


class PackageExecutionContractError(SemanticContractError):
    """Invoked executor returned incompatible or substituted evidence."""

    category = ErrorCategory.INTERPRETATION
    code = ErrorCode.PACKAGE_EXECUTION_CONTRACT_INVALID


class UnsupportedReconciliationInputError(PackageExecutionError):
    """Valid retained source evidence lies outside the explicit operation profile."""

    code = ErrorCode.RECONCILIATION_INPUT_UNSUPPORTED
