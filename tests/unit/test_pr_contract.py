import json
from pathlib import Path
from typing import Any

from tools.check_pr_contract import SCENARIO_IDS, SCENARIO_ROWS, main, validate


def semantic_body(revision: str = "a" * 40) -> str:
    rows = "\n".join(
        f"| {scenario} | yes | tests/unit/test_pr_contract.py |" for scenario in SCENARIO_ROWS
    )
    contract = {
        "authoritative_inputs": "repository evidence",
        "authoritative_output": "required checks",
        "scope_as_of": "repository and current revision",
        "governing_policy": "deterministic checks",
        "evidence_retained": "CI artifacts",
        "typed_failures": "non-zero exit",
    }
    evidence: dict[str, object] = {
        "schema_version": 1,
        "issue": "#145",
        "revision": revision,
        "surfaces": ["pull request contract"],
        "instructions": ["AGENTS.md"],
        "skills": [".agents/skills/semantic-change-loop/SKILL.md"],
        "contract": contract,
        "scenarios": [
            {
                "id": SCENARIO_IDS[scenario],
                "disposition": "applicable",
                "evidence": ["tests/unit/test_pr_contract.py"],
                "rationale": "",
            }
            for scenario in SCENARIO_ROWS
        ],
        "commands": [
            {
                "argv": ["make", "semantic-preflight"],
                "outcome": "passed",
                "evidence": "CI check",
            }
        ],
        "review": {
            "revision": revision,
            "mode": "self_fresh_pass",
            "findings": [],
            "unresolved_findings": [],
        },
        "completion": "ready",
    }
    evidence_json = json.dumps(evidence, indent=2)
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
## Semantic evidence JSON
```json
{evidence_json}
```
## Review disposition
- Reviewed revision: {revision}
complete
"""


def dependabot_body(*, include_trace: bool = True) -> str:
    trace = """<!--
updated-dependencies:
- dependency-name: actions/setup-uv
  dependency-version: 10.0.0
  update-type: version-update:semver-major
-->
"""
    return f"""Bumps [actions/setup-uv](https://github.com/astral-sh/setup-uv) from 7 to 10.

{trace if include_trace else ""}"""


def test_pr_contract_rejects_empty_template() -> None:
    assert "missing value: Primary milestone" in validate("## Summary\n")


def test_pr_contract_accepts_complete_semantic_contract_bound_to_head() -> None:
    revision = "a" * 40
    assert validate(semantic_body(revision), expected_revision=revision) == ()


def test_pr_contract_accepts_bounded_dependabot_generated_body() -> None:
    assert (
        validate(
            dependabot_body(),
            expected_revision="a" * 40,
            changed_files=(".github/workflows/ci.yml",),
            author_login="dependabot[bot]",
            head_ref="dependabot/github_actions/github-actions-a1b2c3d4e5",
            base_ref="main",
        )
        == ()
    )


def test_pr_contract_accepts_each_configured_dependabot_ecosystem() -> None:
    cases = (
        ("uv", ("pyproject.toml", "uv.lock")),
        (
            "npm_and_yarn",
            (
                ".github/roadmap-steward/package.json",
                ".github/roadmap-steward/package-lock.json",
            ),
        ),
    )

    for ecosystem, changed_files in cases:
        assert (
            validate(
                dependabot_body(),
                expected_revision="a" * 40,
                changed_files=changed_files,
                author_login="dependabot[bot]",
                head_ref=f"dependabot/{ecosystem}/example-update",
                base_ref="main",
            )
            == ()
        )


def test_pr_contract_does_not_trust_generated_body_from_other_authors() -> None:
    errors = validate(
        dependabot_body(),
        expected_revision="a" * 40,
        changed_files=(".github/workflows/ci.yml",),
        author_login="octocat",
        head_ref="dependabot/github_actions/example-update",
        base_ref="main",
    )

    assert "missing heading: Summary" in errors


def test_pr_contract_rejects_dependabot_outside_managed_surface() -> None:
    errors = validate(
        dependabot_body(),
        expected_revision="a" * 40,
        changed_files=(".github/workflows/ci.yml", "src/example.py"),
        author_login="dependabot[bot]",
        head_ref="dependabot/github_actions/example-update",
        base_ref="main",
    )

    assert any("outside its managed surface: src/example.py" in error for error in errors)


def test_pr_contract_rejects_dependabot_ecosystem_mismatch() -> None:
    errors = validate(
        dependabot_body(),
        expected_revision="a" * 40,
        changed_files=("uv.lock",),
        author_login="dependabot[bot]",
        head_ref="dependabot/github_actions/example-update",
        base_ref="main",
    )

    assert any("outside its managed surface: uv.lock" in error for error in errors)


def test_pr_contract_rejects_unbounded_dependabot_context() -> None:
    cases = (
        {
            "expected_revision": "not-a-sha",
            "head_ref": "dependabot/github_actions/example-update",
            "base_ref": "main",
        },
        {
            "expected_revision": "a" * 40,
            "head_ref": "dependabot/pip/example-update",
            "base_ref": "main",
        },
        {
            "expected_revision": "a" * 40,
            "head_ref": "dependabot/github_actions/example-update",
            "base_ref": "release",
        },
    )

    for context in cases:
        assert validate(
            dependabot_body(),
            changed_files=(".github/workflows/ci.yml",),
            author_login="dependabot[bot]",
            **context,
        )


def test_pr_contract_rejects_missing_or_duplicate_dependabot_file_evidence() -> None:
    context = {
        "expected_revision": "a" * 40,
        "author_login": "dependabot[bot]",
        "head_ref": "dependabot/uv/example-update",
        "base_ref": "main",
    }

    assert "Dependabot update must change at least one managed dependency file" in validate(
        dependabot_body(), changed_files=(), **context
    )
    assert "Dependabot changed-file evidence must not contain duplicates" in validate(
        dependabot_body(), changed_files=("uv.lock", "uv.lock"), **context
    )


def test_pr_contract_rejects_dependabot_without_trace_or_full_contract() -> None:
    errors = validate(
        dependabot_body(include_trace=False),
        expected_revision="a" * 40,
        changed_files=(".github/workflows/ci.yml",),
        author_login="dependabot[bot]",
        head_ref="dependabot/github_actions/example-update",
        base_ref="main",
    )

    assert "Dependabot body must retain machine-readable dependency metadata" in errors


def test_pr_contract_accepts_full_contract_but_still_bounds_dependabot_files() -> None:
    context = {
        "expected_revision": "a" * 40,
        "author_login": "dependabot[bot]",
        "head_ref": "dependabot/github_actions/example-update",
        "base_ref": "main",
    }

    assert validate(
        semantic_body(), changed_files=(".github/workflows/ci.yml",), **context
    ) == ()
    assert any(
        "outside its managed surface: src/example.py" in error
        for error in validate(
            semantic_body(),
            changed_files=(".github/workflows/ci.yml", "src/example.py"),
            **context,
        )
    )


def test_pr_contract_requires_every_semantic_scenario_family() -> None:
    body = semantic_body().replace(
        "| Scope/time/as-of | yes | tests/unit/test_pr_contract.py |\n", ""
    )

    assert "missing completed scenario row: Scope/time/as-of" in validate(body)


def test_pr_contract_rejects_placeholder_scenario_evidence() -> None:
    body = semantic_body().replace(
        "| Safe counterexample/unrelated change | yes | tests/unit/test_pr_contract.py |",
        "| Safe counterexample/unrelated change | n/a | pending |",
    )

    assert (
        "scenario row requires evidence or rationale: Safe counterexample/unrelated change"
        in validate(body)
    )


def test_pr_contract_rejects_stale_review_revision() -> None:
    errors = validate(semantic_body("a" * 40), expected_revision="b" * 40)

    assert any("does not match PR head" in error for error in errors)


def test_pr_contract_requires_durable_embedded_evidence() -> None:
    body = semantic_body().replace("## Semantic evidence JSON", "## Evidence attachment")

    assert "missing Semantic evidence JSON block" in validate(body)


def test_pr_contract_rejects_contract_or_scenario_drift_from_embedded_evidence() -> None:
    body = (
        semantic_body()
        .replace(
            "- Governing policy: deterministic checks",
            "- Governing policy: undocumented exception",
        )
        .replace(
            "| Scope/time/as-of | yes | tests/unit/test_pr_contract.py |",
            "| Scope/time/as-of | n/a | No time behavior",
        )
    )

    errors = validate(body)

    assert "Semantic evidence contract must match Governing policy" in errors
    assert "Semantic evidence disposition must match scenario row: Scope/time/as-of" in errors


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

    assert validate(body, changed_files=("docs/development/conventions.md",)) == ()


def test_pr_contract_rejects_non_semantic_opt_out_for_executable_paths() -> None:
    body = """## Summary
Refactor
## Why
Simplify code
## Milestone and issue
- Primary milestone: M0
- Linked issue: #145
- Semantic change: no
- Non-semantic rationale: Intended to preserve behavior
## Semantic contract
Not applicable
## Scenario coverage
Not applicable
## Evidence / validation
unit tests
## Review disposition
not requested
"""

    errors = validate(
        body,
        changed_files=("src/procurement_intelligence_lab/platform/domain_packages/compiler.py",),
    )

    assert any("Semantic change cannot be no" in error for error in errors)


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


def test_pr_contract_fails_closed_when_changed_files_input_is_unreadable(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("PR_BODY", semantic_body())
    monkeypatch.setenv("PR_CHANGED_FILES_PATH", str(tmp_path / "missing.txt"))

    assert main() == 1
    assert "pull request contract input error" in capsys.readouterr().out


def test_pr_contract_main_accepts_bounded_dependabot_generated_body(
    monkeypatch: Any, tmp_path: Path
) -> None:
    changed_files = tmp_path / "changed-files.txt"
    changed_files.write_text(".github/workflows/ci.yml\n", encoding="utf-8")
    monkeypatch.setenv("PR_BODY", dependabot_body())
    monkeypatch.setenv("PR_CHANGED_FILES_PATH", str(changed_files))
    monkeypatch.setenv("PR_HEAD_SHA", "a" * 40)
    monkeypatch.setenv("PR_AUTHOR_LOGIN", "dependabot[bot]")
    monkeypatch.setenv("PR_HEAD_REF", "dependabot/github_actions/example-update")
    monkeypatch.setenv("PR_BASE_REF", "main")

    assert main() == 0
