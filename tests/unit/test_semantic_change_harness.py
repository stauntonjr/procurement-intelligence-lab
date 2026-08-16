import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.validate_semantic_change import (
    CONTRACT_FIELDS,
    ROOT,
    SCENARIO_FAMILIES,
    main,
    validate_evidence,
    validate_routing,
    validate_skills,
)

EXAMPLE = ROOT / "docs" / "development" / "semantic-change-evidence.example.json"
SCHEMA = ROOT / "docs" / "development" / "semantic-change-evidence.schema.json"
ROUTING = ROOT / "evals" / "development_agents" / "skill-routing.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_canonical_semantic_change_example_is_valid() -> None:
    assert validate_evidence(load(EXAMPLE)) == ()


def test_schema_and_validator_require_the_same_contract_and_scenarios() -> None:
    schema = load(SCHEMA)
    contract_required = schema["properties"]["contract"]["required"]
    scenario_ids = schema["properties"]["scenarios"]["items"]["properties"]["id"]["enum"]

    assert set(contract_required) == set(CONTRACT_FIELDS)
    assert set(scenario_ids) == set(SCENARIO_FAMILIES)


def test_semantic_evidence_rejects_missing_and_duplicate_scenarios() -> None:
    evidence = deepcopy(load(EXAMPLE))
    evidence["scenarios"][-1] = deepcopy(evidence["scenarios"][0])

    errors = validate_evidence(evidence)

    assert "duplicate scenario id: empty_missing_unknown" in errors
    assert any("safe_counterexample" in error for error in errors)


def test_semantic_evidence_requires_executable_evidence_or_rationale() -> None:
    evidence = deepcopy(load(EXAMPLE))
    evidence["scenarios"][0]["evidence"] = []
    evidence["scenarios"][3]["rationale"] = ""

    errors = validate_evidence(evidence)

    assert "scenarios[0].evidence is required when applicable" in errors
    assert "scenarios[3].rationale is required when not applicable" in errors


def test_semantic_evidence_rejects_unresolvable_evidence_reference() -> None:
    evidence = deepcopy(load(EXAMPLE))
    evidence["scenarios"][0]["evidence"] = ["tests/unit/missing_test.py::test_missing"]

    assert (
        "scenarios[0].evidence does not resolve: tests/unit/missing_test.py::test_missing"
        in validate_evidence(evidence)
    )


def test_semantic_evidence_rejects_fields_outside_the_canonical_schema() -> None:
    evidence = deepcopy(load(EXAMPLE))
    evidence["claim"] = "unvalidated"
    evidence["contract"]["implicit_policy"] = "latest wins"
    evidence["scenarios"][0]["hidden_case"] = True
    evidence["commands"][0]["ignored_failure"] = True
    evidence["review"]["approval"] = "assumed"

    errors = validate_evidence(evidence)

    assert any("evidence contains unexpected fields" in error for error in errors)
    assert any("contract contains unexpected fields" in error for error in errors)
    assert any("scenarios[0] contains unexpected fields" in error for error in errors)
    assert any("commands[0] contains unexpected fields" in error for error in errors)
    assert any("review contains unexpected fields" in error for error in errors)


def test_semantic_evidence_is_bound_to_reviewed_revision() -> None:
    evidence = deepcopy(load(EXAMPLE))
    evidence["review"]["revision"] = "b" * 40

    errors = validate_evidence(evidence, expected_revision="c" * 40)

    assert "review.revision must match revision" in errors
    assert any("does not match expected revision" in error for error in errors)


def test_ready_evidence_rejects_failed_commands_and_unresolved_findings() -> None:
    evidence = deepcopy(load(EXAMPLE))
    evidence["commands"][0]["outcome"] = "failed"
    evidence["review"]["unresolved_findings"] = ["missing public-path evidence"]

    errors = validate_evidence(evidence)

    assert "commands[0] must pass before completion is ready" in errors
    assert "review.unresolved_findings must be empty before completion is ready" in errors


def test_skill_routing_fixture_covers_positive_negative_and_safe_cases() -> None:
    assert validate_routing(load(ROUTING)) == ()


def test_repository_skills_are_natively_discoverable_and_valid() -> None:
    assert validate_skills() == ()


def test_skill_routing_fixture_rejects_answer_leakage_and_unknown_skills() -> None:
    routing = deepcopy(load(ROUTING))
    routing["cases"][0]["prompt"] = "Copy the answer from C001 known-bad behavior"
    routing["cases"][0]["expected_skills"] = ["missing-skill"]

    errors = validate_routing(routing)

    assert "cases[0].prompt references public challenge IDs or known-bad fixtures" in errors
    assert "cases[0] references unknown skill: missing-skill" in errors


def test_new_skills_contain_no_scaffold_placeholders() -> None:
    for skill in ("semantic-change-loop", "review-semantic-change"):
        content = (ROOT / ".agents" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "TODO" not in content


def test_semantic_validator_returns_typed_failure_for_malformed_json(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    malformed = tmp_path / "evidence.json"
    malformed.write_text("{", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_semantic_change", "--evidence", str(malformed)])

    assert main() == 1
    assert "semantic harness input error" in capsys.readouterr().out
