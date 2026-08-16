import ast
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.semantics.errors import (
    AuthorityContractError,
    AuthorityScopeMismatchError,
    ErrorCategory,
    ErrorCode,
    IdempotencyContractError,
    PolicyContractError,
    ScopeAuthorizationError,
    ScopeContractError,
    ScopeMismatchError,
    SemanticContractError,
    SemanticTypeContractError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.reconciliation import (
    ReconciliationPolicyError,
)

ROOT = Path(__file__).resolve().parents[2]
SEMANTICS = ROOT / "src" / "procurement_intelligence_lab" / "platform" / "semantics"


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
        "pil.input.semantic_type_contract_violation",
        "pil.input.scope_contract_violation",
        "pil.policy.scope_mismatch",
        "pil.input.temporal_contract_violation",
        "pil.policy.contract_violation",
        "pil.policy.reconciliation_no_governing_source",
        "pil.authorization.authority_contract_violation",
        "pil.authorization.scope_mismatch",
        "pil.authorization.request_scope_denied",
        "pil.policy.idempotency_contract_violation",
    }
    assert len({code.value for code in ErrorCode}) == len(ErrorCode)
    with pytest.raises(ValueError):
        ErrorCode("pil.input.unknown")


def test_platform_semantic_errors_require_specific_failure_evidence() -> None:
    with pytest.raises(ValueError, match="non-empty message"):
        SemanticContractError("  ")


@pytest.mark.parametrize(
    ("error_type", "base_type", "category", "code"),
    (
        (
            SemanticContractError,
            ValueError,
            ErrorCategory.INPUT,
            ErrorCode.SEMANTIC_CONTRACT_VIOLATION,
        ),
        (
            SemanticTypeContractError,
            TypeError,
            ErrorCategory.INPUT,
            ErrorCode.SEMANTIC_TYPE_CONTRACT_VIOLATION,
        ),
        (
            ScopeContractError,
            ValueError,
            ErrorCategory.INPUT,
            ErrorCode.SCOPE_CONTRACT_VIOLATION,
        ),
        (
            ScopeMismatchError,
            ValueError,
            ErrorCategory.POLICY,
            ErrorCode.SCOPE_MISMATCH,
        ),
        (
            TemporalContractError,
            ValueError,
            ErrorCategory.INPUT,
            ErrorCode.TEMPORAL_CONTRACT_VIOLATION,
        ),
        (
            AuthorityContractError,
            ValueError,
            ErrorCategory.AUTHORIZATION,
            ErrorCode.AUTHORITY_CONTRACT_VIOLATION,
        ),
        (
            AuthorityScopeMismatchError,
            ValueError,
            ErrorCategory.AUTHORIZATION,
            ErrorCode.AUTHORITY_SCOPE_MISMATCH,
        ),
        (
            ScopeAuthorizationError,
            PermissionError,
            ErrorCategory.AUTHORIZATION,
            ErrorCode.REQUEST_SCOPE_DENIED,
        ),
        (
            PolicyContractError,
            ValueError,
            ErrorCategory.POLICY,
            ErrorCode.POLICY_CONTRACT_VIOLATION,
        ),
        (
            ReconciliationPolicyError,
            ValueError,
            ErrorCategory.POLICY,
            ErrorCode.RECONCILIATION_POLICY_NO_MATCH,
        ),
        (
            IdempotencyContractError,
            ValueError,
            ErrorCategory.POLICY,
            ErrorCode.IDEMPOTENCY_CONTRACT_VIOLATION,
        ),
    ),
)
def test_typed_semantic_errors_expose_a_boundary_safe_failure_envelope(
    error_type: (
        type[SemanticContractError]
        | type[SemanticTypeContractError]
        | type[ScopeAuthorizationError]
    ),
    base_type: type[Exception],
    category: ErrorCategory,
    code: ErrorCode,
) -> None:
    error = error_type("specific failure evidence")

    assert isinstance(error, base_type)
    assert error.category is category
    assert error.code is code
    assert error.as_dict() == {
        "code": code.value,
        "category": category.value,
        "message": "specific failure evidence",
    }


def test_platform_semantic_modules_do_not_raise_untyped_builtin_failures() -> None:
    untyped = {"ValueError", "TypeError", "PermissionError"}
    violations: list[str] = []

    for path in sorted(SEMANTICS.glob("*.py")):
        if path.name == "errors.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Raise)
                and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id in untyped
            ):
                violations.append(f"{path.name}:{node.lineno}:{node.exc.func.id}")

    assert violations == []
