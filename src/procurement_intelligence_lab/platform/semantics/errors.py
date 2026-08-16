"""Typed failures shared by universal semantic contracts."""


class SemanticContractError(ValueError):
    """Raised when a semantic record violates an intrinsic invariant."""


class ScopeMismatchError(SemanticContractError):
    """Raised when records from different governed scopes are composed."""


class TemporalContractError(SemanticContractError):
    """Raised when a semantic timestamp is naive or temporally inconsistent."""


class AuthorityContractError(SemanticContractError):
    """Raised when a decision or action lacks explicit authority."""


class IdempotencyContractError(SemanticContractError):
    """Raised when an action has no stable idempotency boundary."""
