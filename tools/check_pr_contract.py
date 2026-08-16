"""Fail pull requests that omit the repository's executable-specification fields."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from tools.validate_semantic_change import validate_evidence

REQUIRED_HEADINGS = (
    "Summary",
    "Why",
    "Milestone and issue",
    "Semantic contract",
    "Scenario coverage",
    "Evidence / validation",
    "Review disposition",
)
REQUIRED_VALUES = (
    "Primary milestone",
    "Linked issue",
)
SEMANTIC_VALUES = (
    "Authoritative inputs",
    "Authoritative output",
    "Scope/as-of rule",
    "Governing policy",
    "Evidence retained",
    "Typed failure behavior",
    "Behavior evidence",
    "Reviewed revision",
)
SCENARIO_ROWS = (
    "Empty/missing/unknown",
    "Duplicate/many/conflict",
    "Scope/time/as-of",
    "Zero/negative/fractional/boundary",
    "Unsupported capability/malformed input",
    "Public caller and clean package",
    "Safe counterexample/unrelated change",
)
SCENARIO_IDS = dict(
    zip(
        SCENARIO_ROWS,
        (
            "empty_missing_unknown",
            "multiplicity_conflict",
            "scope_time",
            "numeric_boundaries",
            "unsupported_malformed",
            "public_artifact",
            "safe_counterexample",
        ),
        strict=True,
    )
)
CONTRACT_LABELS = {
    "Authoritative inputs": "authoritative_inputs",
    "Authoritative output": "authoritative_output",
    "Scope/as-of rule": "scope_as_of",
    "Governing policy": "governing_policy",
    "Evidence retained": "evidence_retained",
    "Typed failure behavior": "typed_failures",
}
SEMANTIC_PATH_PREFIXES = (
    ".agents/",
    ".github/instructions/",
    ".github/workflows/",
    "evals/",
    "examples/",
    "src/",
    "tests/",
    "tools/",
)
SEMANTIC_PATHS = {
    ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/pull_request_template.md",
    "AGENTS.md",
    "Makefile",
    "pyproject.toml",
    "uv.lock",
}


def _value(body: str, label: str) -> str | None:
    match = re.search(rf"(?m)^- {re.escape(label)}:\s*(.*)$", body)
    if match is None or not match.group(1).strip():
        return None
    return match.group(1).strip()


def _scenario_rows(body: str) -> dict[str, tuple[str, str]]:
    row = re.compile(
        r"(?m)^\s*\|\s*(?P<name>[^|\r\n]+)\|\s*"
        r"(?P<disposition>yes|no|n/a)\s*\|\s*(?P<evidence>[^|\r\n]+)\s*\|?\s*$",
        re.IGNORECASE,
    )
    return {
        match.group("name").strip().casefold(): (
            match.group("disposition").casefold(),
            match.group("evidence").strip(),
        )
        for match in row.finditer(body)
    }


def requires_semantic_contract(paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        path for path in paths if path in SEMANTIC_PATHS or path.startswith(SEMANTIC_PATH_PREFIXES)
    )


def _embedded_evidence(body: str) -> tuple[object | None, str | None]:
    match = re.search(
        r"(?ms)^## Semantic evidence JSON\s*$\s*```json\s*$\s*(?P<payload>.*?)\s*^```\s*$",
        body,
    )
    if match is None:
        return None, "missing Semantic evidence JSON block"
    try:
        return json.loads(match.group("payload")), None
    except json.JSONDecodeError as error:
        return None, f"Semantic evidence JSON is malformed: {error}"


def _cross_validate_evidence(body: str, evidence: object) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    errors: list[str] = []
    linked_issue = _value(body, "Linked issue")
    issue_match = re.search(r"#\d+", linked_issue or "")
    if issue_match is not None and evidence.get("issue") != issue_match.group():
        errors.append("Semantic evidence issue must match Linked issue")
    contract = evidence.get("contract")
    if isinstance(contract, dict):
        for label, field in CONTRACT_LABELS.items():
            if _value(body, label) != contract.get(field):
                errors.append(f"Semantic evidence contract must match {label}")
    rows = _scenario_rows(body)
    scenarios = evidence.get("scenarios")
    if isinstance(scenarios, list):
        dispositions = {
            item.get("id"): item.get("disposition") for item in scenarios if isinstance(item, dict)
        }
        for row_name, scenario_id in SCENARIO_IDS.items():
            row = rows.get(row_name.casefold())
            if row is None:
                continue
            expected = "applicable" if row[0] == "yes" else "not_applicable"
            if dispositions.get(scenario_id) != expected:
                errors.append(f"Semantic evidence disposition must match scenario row: {row_name}")
    return errors


def validate(
    body: str,
    *,
    expected_revision: str | None = None,
    changed_files: tuple[str, ...] = (),
) -> tuple[str, ...]:
    errors: list[str] = []
    for heading in REQUIRED_HEADINGS:
        if not re.search(rf"(?m)^## {re.escape(heading)}\s*$", body):
            errors.append(f"missing heading: {heading}")
    for label in REQUIRED_VALUES:
        if _value(body, label) is None:
            errors.append(f"missing value: {label}")
    semantic_change = _value(body, "Semantic change")
    if semantic_change is None or semantic_change.casefold() not in {"yes", "no"}:
        errors.append("Semantic change must be yes or no")
        return tuple(errors)
    if semantic_change.casefold() == "no":
        semantic_paths = requires_semantic_contract(changed_files)
        if semantic_paths:
            errors.append(
                "Semantic change cannot be no for executable or harness paths: "
                + ", ".join(semantic_paths)
            )
        rationale = _value(body, "Non-semantic rationale")
        if rationale is None or rationale.casefold().startswith(("n/a", "none", "no ")):
            errors.append("non-semantic changes require a concrete Non-semantic rationale")
        return tuple(errors)
    for label in SEMANTIC_VALUES:
        if _value(body, label) is None:
            errors.append(f"missing value: {label}")
    rows = _scenario_rows(body)
    for scenario in SCENARIO_ROWS:
        entry = rows.get(scenario.casefold())
        if entry is None:
            errors.append(f"missing completed scenario row: {scenario}")
        elif entry[1].casefold() in {"n/a", "none", "todo", "tbd", "pending", "-"}:
            errors.append(f"scenario row requires evidence or rationale: {scenario}")
    reviewed_revision = _value(body, "Reviewed revision")
    if reviewed_revision is not None:
        if re.fullmatch(r"[0-9a-f]{40}", reviewed_revision) is None:
            errors.append("Reviewed revision must be a 40-character lowercase git SHA")
        elif expected_revision is not None and reviewed_revision != expected_revision:
            errors.append(
                f"Reviewed revision {reviewed_revision} does not match PR head {expected_revision}"
            )
    evidence, evidence_error = _embedded_evidence(body)
    if evidence_error is not None:
        errors.append(evidence_error)
    else:
        errors.extend(
            f"semantic evidence: {error}"
            for error in validate_evidence(evidence, expected_revision=expected_revision)
        )
        errors.extend(_cross_validate_evidence(body, evidence))
    return tuple(errors)


def main() -> int:
    body = os.environ.get("PR_BODY", "")
    changed_files_path = os.environ.get("PR_CHANGED_FILES_PATH")
    changed_files: tuple[str, ...] = ()
    if changed_files_path:
        changed_files = tuple(
            line.strip()
            for line in Path(changed_files_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    errors = validate(
        body,
        expected_revision=os.environ.get("PR_HEAD_SHA"),
        changed_files=changed_files,
    )
    if errors:
        print("Pull request contract is incomplete:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("pull request contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
