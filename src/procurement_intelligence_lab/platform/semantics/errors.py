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
