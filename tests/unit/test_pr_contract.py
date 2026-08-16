from tools.check_pr_contract import SCENARIO_ROWS, validate


def semantic_body(revision: str = "a" * 40) -> str:
    rows = "\n".join(
        f"| {scenario} | yes | tests/unit/test_contract.py |" for scenario in SCENARIO_ROWS
    )
    return f"""## Summary
Harness
## Why
Prevent recurrence
## Milestone and issue
- Primary milestone: M0
- Linked issue: #145
- Semantic change: yes
- Non-semantic rationale: n/a
## Semantic contract
- Authoritative inputs: repository evidence
- Authoritative output: required checks
- Scope/as-of rule: repository and current revision
- Governing policy: deterministic checks
- Evidence retained: CI artifacts
- Typed failure behavior: non-zero exit
- Behavior evidence: artifacts/semantic-change.json
## Scenario coverage
| Scenario | Applicable? | Test/evidence |
|---|---:|---|
{rows}
## Evidence / validation
make check
## Review disposition
- Reviewed revision: {revision}
complete
"""


def test_pr_contract_rejects_empty_template() -> None:
    assert "missing value: Primary milestone" in validate("## Summary\n")


def test_pr_contract_accepts_complete_semantic_contract_bound_to_head() -> None:
    revision = "a" * 40
    assert validate(semantic_body(revision), expected_revision=revision) == ()


def test_pr_contract_requires_every_semantic_scenario_family() -> None:
    body = semantic_body().replace("| Scope/time/as-of | yes | tests/unit/test_contract.py |\n", "")

    assert "missing completed scenario row: Scope/time/as-of" in validate(body)


def test_pr_contract_rejects_placeholder_scenario_evidence() -> None:
    body = semantic_body().replace(
        "| Safe counterexample/unrelated change | yes | tests/unit/test_contract.py |",
        "| Safe counterexample/unrelated change | n/a | pending |",
    )

    assert (
        "scenario row requires evidence or rationale: Safe counterexample/unrelated change"
        in validate(body)
    )


def test_pr_contract_rejects_stale_review_revision() -> None:
    errors = validate(semantic_body("a" * 40), expected_revision="b" * 40)

    assert any("does not match PR head" in error for error in errors)


def test_pr_contract_allows_non_semantic_safe_path_with_rationale() -> None:
    body = """## Summary
Fix typo
## Why
Correct spelling
## Milestone and issue
- Primary milestone: M0
- Linked issue: #145
- Semantic change: no
- Non-semantic rationale: Wording-only documentation correction with no behavior change
## Semantic contract
Not applicable
## Scenario coverage
Not applicable
## Evidence / validation
docs check
## Review disposition
not requested
"""

    assert validate(body) == ()


def test_pr_contract_rejects_unexplained_non_semantic_claim() -> None:
    body = """## Summary
Change
## Why
Reason
## Milestone and issue
- Primary milestone: M0
- Linked issue: #145
- Semantic change: no
- Non-semantic rationale: n/a
## Semantic contract
N/A
## Scenario coverage
N/A
## Evidence / validation
N/A
## Review disposition
N/A
"""

    assert "non-semantic changes require a concrete Non-semantic rationale" in validate(body)
