"""Closed local-job failure boundary; diagnostics never carry driver text."""

from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
)


class JobContractError(SemanticContractError):
    code = ErrorCode.LOCAL_PREFIX_JOB_INVALID


class JobConflictError(SemanticContractError):
    code = ErrorCode.LOCAL_PREFIX_JOB_CONFLICT
    category = ErrorCategory.POLICY


class JobBusyError(JobConflictError):
    code = ErrorCode.LOCAL_PREFIX_JOB_BUSY


class JobFencedError(JobConflictError):
    code = ErrorCode.LOCAL_PREFIX_JOB_FENCED


class JobNotFoundError(SemanticContractError):
    code = ErrorCode.LOCAL_PREFIX_JOB_NOT_FOUND


class JobIntegrityError(SemanticContractError):
    code = ErrorCode.LOCAL_PREFIX_JOB_INTEGRITY_INVALID
    category = ErrorCategory.INFRASTRUCTURE


class JobUnavailableError(SemanticContractError):
    code = ErrorCode.LOCAL_PREFIX_JOB_UNAVAILABLE
    category = ErrorCategory.INFRASTRUCTURE
