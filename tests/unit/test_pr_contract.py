from tools.check_pr_contract import validate


def test_pr_contract_rejects_empty_template() -> None:
    assert "missing value: Primary milestone" in validate("## Summary\n")


def test_pr_contract_accepts_completed_contract() -> None:
    body = """## Summary
Harness
## Why
Prevent recurrence
## Milestone and issue
- Primary milestone: M0
- Linked issue: #3
## Semantic contract
- Authoritative inputs: repository evidence
- Authoritative output: required checks
- Scope/as-of rule: repository and current revision
- Governing policy: deterministic checks
- Evidence retained: CI artifacts
- Typed failure behavior: non-zero exit
## Scenario coverage
| Scenario | Applicable? | Test/evidence |
|---|---:|---|
| Empty/missing/unknown | yes | unit test |
## Evidence / validation
make check
## Review disposition
pending
"""
    assert validate(body) == ()


def test_pr_contract_accepts_compact_scenario_row_without_trailing_pipe() -> None:
    body = """## Summary
Harness
## Why
Prevent recurrence
## Milestone and issue
- Primary milestone: M0
- Linked issue: #3
## Semantic contract
- Authoritative inputs: repository evidence
- Authoritative output: required checks
- Scope/as-of rule: repository and current revision
- Governing policy: deterministic checks
- Evidence retained: CI artifacts
- Typed failure behavior: non-zero exit
## Scenario coverage
|Empty/missing/unknown|yes|unit test
## Evidence / validation
make check
## Review disposition
complete
"""
    assert validate(body) == ()
