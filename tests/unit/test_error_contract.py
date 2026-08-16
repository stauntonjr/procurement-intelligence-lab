import pytest

from procurement_intelligence_lab.platform.semantics.errors import (
    AuthorityContractError,
    ErrorCategory,
    ErrorCode,
    IdempotencyContractError,
    ScopeMismatchError,
    SemanticContractError,
    TemporalContractError,
)


def test_failure_categories_are_a_closed_stable_vocabulary() -> None:
    assert {category.value for category in ErrorCategory} == {
        "input",
        "interpretation",
        "identity",
        "policy",
        "infrastructure",
        "transient",
        "authorization",
    }


def test_platform_semantic_error_codes_are_stable_and_unique() -> None:
    assert {code.value for code in ErrorCode} == {
        "pil.input.semantic_contract_violation",
        "pil.policy.scope_mismatch",
        "pil.input.temporal_contract_violation",
        "pil.authorization.authority_contract_violation",
        "pil.policy.idempotency_contract_violation",
    }
    assert len({code.value for code in ErrorCode}) == len(ErrorCode)
    with pytest.raises(ValueError):
        ErrorCode("pil.input.unknown")


def test_platform_semantic_errors_require_specific_failure_evidence() -> None:
    with pytest.raises(ValueError, match="non-empty message"):
        SemanticContractError("  ")


@pytest.mark.parametrize(
    ("error_type", "category", "code"),
    (
        (
            SemanticContractError,
            ErrorCategory.INPUT,
            ErrorCode.SEMANTIC_CONTRACT_VIOLATION,
        ),
        (ScopeMismatchError, ErrorCategory.POLICY, ErrorCode.SCOPE_MISMATCH),
        (
            TemporalContractError,
            ErrorCategory.INPUT,
            ErrorCode.TEMPORAL_CONTRACT_VIOLATION,
        ),
        (
            AuthorityContractError,
            ErrorCategory.AUTHORIZATION,
            ErrorCode.AUTHORITY_CONTRACT_VIOLATION,
        ),
        (
            IdempotencyContractError,
            ErrorCategory.POLICY,
            ErrorCode.IDEMPOTENCY_CONTRACT_VIOLATION,
        ),
    ),
)
def test_typed_semantic_errors_expose_a_boundary_safe_failure_envelope(
    error_type: type[SemanticContractError],
    category: ErrorCategory,
    code: ErrorCode,
) -> None:
    error = error_type("specific failure evidence")

    assert isinstance(error, ValueError)
    assert error.category is category
    assert error.code is code
    assert error.as_dict() == {
        "code": code.value,
        "category": category.value,
        "message": "specific failure evidence",
    }
