"""Closed local-job failure boundary; diagnostics never carry driver text."""

from procurement_intelligence_lab.platform.semantics.errors import (
    ErrorCategory,
    ErrorCode,
    SemanticContractError,
)


class ResolvedJobContractError(SemanticContractError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_INVALID


class ResolvedJobConflictError(SemanticContractError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_CONFLICT
    category = ErrorCategory.POLICY


class ResolvedJobBusyError(ResolvedJobConflictError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_BUSY


class ResolvedJobFencedError(ResolvedJobConflictError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_FENCED


class ResolvedJobNotFoundError(SemanticContractError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_NOT_FOUND


class ResolvedJobIntegrityError(SemanticContractError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_INTEGRITY_INVALID
    category = ErrorCategory.INFRASTRUCTURE


class ResolvedJobUnavailableError(SemanticContractError):
    code = ErrorCode.RESOLVED_PREFIX_JOB_UNAVAILABLE
    category = ErrorCategory.INFRASTRUCTURE
