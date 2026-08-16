"""Validate semantic-change evidence and skill-routing fixtures."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
SCENARIO_FAMILIES = (
    "empty_missing_unknown",
    "multiplicity_conflict",
    "scope_time",
    "numeric_boundaries",
    "unsupported_malformed",
    "public_artifact",
    "safe_counterexample",
)
CONTRACT_FIELDS = (
    "authoritative_inputs",
    "authoritative_output",
    "scope_as_of",
    "governing_policy",
    "evidence_retained",
    "typed_failures",
)
ROUTING_KINDS = {"positive", "negative", "safe_counterexample"}
EVIDENCE_FIELDS = {
    "schema_version",
    "issue",
    "revision",
    "surfaces",
    "instructions",
    "skills",
    "contract",
    "scenarios",
    "commands",
    "review",
    "completion",
}
SCENARIO_FIELDS = {"id", "disposition", "evidence", "rationale"}
COMMAND_FIELDS = {"argv", "outcome", "evidence"}
REVIEW_FIELDS = {"revision", "mode", "findings", "unresolved_findings"}
ROUTING_FIELDS = {"schema_version", "cases"}
ROUTING_CASE_FIELDS = {"id", "kind", "prompt", "expected_skills", "forbidden_skills"}


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: object) -> list[str] | None:
    if not isinstance(value, list) or not all(_nonempty_string(item) for item in value):
        return None
    return [str(item) for item in value]


def _unexpected_fields(value: dict[object, object], allowed: set[str], field: str) -> list[str]:
    unexpected = {str(key) for key in value if key not in allowed}
    return [f"{field} contains unexpected fields: {sorted(unexpected)!r}"] if unexpected else []


def _validate_repo_paths(paths: object, field: str, root: Path) -> list[str]:
    errors: list[str] = []
    values = _string_list(paths)
    if values is None or not values:
        return [f"{field} must be a non-empty string list"]
    for value in values:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{field} path must stay inside the repository: {value}")
        elif not (root / path).is_file():
            errors.append(f"{field} path does not exist: {value}")
    return errors


def _validate_contract(value: object) -> list[str]:
    if not isinstance(value, dict):
        return ["contract must be an object"]
    errors = _unexpected_fields(value, set(CONTRACT_FIELDS), "contract")
    errors.extend(
        f"contract.{field} must be a non-empty string"
        for field in CONTRACT_FIELDS
        if not _nonempty_string(value.get(field))
    )
    return errors


def _validate_scenarios(value: object, root: Path) -> list[str]:
    if not isinstance(value, list):
        return ["scenarios must be a list"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, scenario in enumerate(value):
        prefix = f"scenarios[{index}]"
        if not isinstance(scenario, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_unexpected_fields(scenario, SCENARIO_FIELDS, prefix))
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        if scenario_id in seen:
            errors.append(f"duplicate scenario id: {scenario_id}")
        seen.add(scenario_id)
        disposition = scenario.get("disposition")
        if disposition not in {"applicable", "not_applicable"}:
            errors.append(f"{prefix}.disposition must be applicable or not_applicable")
        evidence = _string_list(scenario.get("evidence"))
        rationale = scenario.get("rationale")
        if not isinstance(rationale, str):
            errors.append(f"{prefix}.rationale must be a string")
        if disposition == "applicable" and (evidence is None or not evidence):
            errors.append(f"{prefix}.evidence is required when applicable")
        elif disposition == "applicable" and evidence is not None:
            for reference in evidence:
                reference_path = reference.split("::", 1)[0]
                if reference.startswith("command:"):
                    if not reference.removeprefix("command:").strip():
                        errors.append(f"{prefix}.evidence command reference is empty")
                    continue
                path = Path(reference_path)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not (root / reference_path).is_file()
                ):
                    errors.append(f"{prefix}.evidence does not resolve: {reference}")
        if disposition == "not_applicable" and not _nonempty_string(rationale):
            errors.append(f"{prefix}.rationale is required when not applicable")
    expected = set(SCENARIO_FAMILIES)
    missing = expected - seen
    unknown = seen - expected
    if missing:
        errors.append(f"missing scenario families: {sorted(missing)!r}")
    if unknown:
        errors.append(f"unknown scenario families: {sorted(unknown)!r}")
    return errors


def _validate_commands(value: object, *, completion: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["commands must be a non-empty list"]
    errors: list[str] = []
    for index, command in enumerate(value):
        prefix = f"commands[{index}]"
        if not isinstance(command, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_unexpected_fields(command, COMMAND_FIELDS, prefix))
        argv = _string_list(command.get("argv"))
        if argv is None or not argv:
            errors.append(f"{prefix}.argv must be a non-empty string list")
        if command.get("outcome") not in {"passed", "failed", "skipped"}:
            errors.append(f"{prefix}.outcome must be passed, failed, or skipped")
        if not _nonempty_string(command.get("evidence")):
            errors.append(f"{prefix}.evidence must be a non-empty string")
        if completion == "ready" and command.get("outcome") != "passed":
            errors.append(f"{prefix} must pass before completion is ready")
    return errors


def _validate_review(value: object, revision: object, completion: object) -> list[str]:
    if not isinstance(value, dict):
        return ["review must be an object"]
    errors = _unexpected_fields(value, REVIEW_FIELDS, "review")
    if value.get("revision") != revision:
        errors.append("review.revision must match revision")
    if value.get("mode") not in {"self_fresh_pass", "independent_fresh_context"}:
        errors.append("review.mode must name a fresh review mode")
    for field in ("findings", "unresolved_findings"):
        if _string_list(value.get(field)) is None:
            errors.append(f"review.{field} must be a string list")
    if completion == "ready" and value.get("unresolved_findings") != []:
        errors.append("review.unresolved_findings must be empty before completion is ready")
    return errors


def validate_evidence(
    value: object, *, expected_revision: str | None = None, root: Path = ROOT
) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ("evidence must be a JSON object",)
    errors = _unexpected_fields(value, EVIDENCE_FIELDS, "evidence")
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(value.get("issue"), str) or re.fullmatch(r"#\d+", value["issue"]) is None:
        errors.append("issue must use #NUMBER form")
    revision = value.get("revision")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        errors.append("revision must be a 40-character lowercase git SHA")
    elif expected_revision is not None and revision != expected_revision:
        errors.append(f"revision {revision} does not match expected revision {expected_revision}")
    if _string_list(value.get("surfaces")) in (None, []):
        errors.append("surfaces must be a non-empty string list")
    errors.extend(_validate_repo_paths(value.get("instructions"), "instructions", root))
    errors.extend(_validate_repo_paths(value.get("skills"), "skills", root))
    errors.extend(_validate_contract(value.get("contract")))
    errors.extend(_validate_scenarios(value.get("scenarios"), root))
    completion = value.get("completion")
    if completion not in {"ready", "not_ready"}:
        errors.append("completion must be ready or not_ready")
    errors.extend(_validate_commands(value.get("commands"), completion=completion))
    errors.extend(_validate_review(value.get("review"), revision, completion))
    return tuple(errors)


def validate_routing(value: object, *, root: Path = ROOT) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ("routing fixture must be a JSON object",)
    errors = _unexpected_fields(value, ROUTING_FIELDS, "routing fixture")
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"routing schema_version must be {SCHEMA_VERSION}")
    cases = value.get("cases")
    if not isinstance(cases, list) or not cases:
        return tuple(errors + ["routing cases must be a non-empty list"])
    seen_ids: set[str] = set()
    seen_kinds: set[str] = set()
    challenge_leak = re.compile(r"\bC00[1-8]\b|known[- ]bad", re.IGNORECASE)
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        errors.extend(_unexpected_fields(case, ROUTING_CASE_FIELDS, prefix))
        case_id = case.get("id")
        if not _nonempty_string(case_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif str(case_id) in seen_ids:
            errors.append(f"duplicate routing case id: {case_id}")
        else:
            seen_ids.add(str(case_id))
        kind = case.get("kind")
        if kind not in ROUTING_KINDS:
            errors.append(f"{prefix}.kind is invalid")
        else:
            seen_kinds.add(str(kind))
        prompt = case.get("prompt")
        if not _nonempty_string(prompt):
            errors.append(f"{prefix}.prompt must be a non-empty string")
            errors.append(f"{prefix}.prompt references public challenge IDs or known-bad fixtures")
        expected = _string_list(case.get("expected_skills"))
        forbidden = _string_list(case.get("forbidden_skills"))
        if expected is None or forbidden is None:
            errors.append(f"{prefix} skill lists must contain strings")
            continue
        overlap = set(expected) & set(forbidden)
        if overlap:
            errors.append(f"{prefix} expects and forbids {sorted(overlap)!r}")
        for skill in set(expected + forbidden):
            if not (root / ".agents" / "skills" / skill / "SKILL.md").is_file():
                errors.append(f"{prefix} references unknown skill: {skill}")
    missing_kinds = ROUTING_KINDS - seen_kinds
    if missing_kinds:
        errors.append(f"routing fixture missing kinds: {sorted(missing_kinds)!r}")
    return tuple(errors)


def validate_skills(*, root: Path = ROOT) -> tuple[str, ...]:
    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        return (".agents/skills directory is missing",)
    errors: list[str] = []
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        path = skill_dir / "SKILL.md"
        if not path.is_file():
            errors.append(f"skill is missing SKILL.md: {skill_dir.name}")
            continue
        content = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n", content, re.DOTALL)
        if match is None:
            errors.append(f"skill is missing YAML frontmatter: {skill_dir.name}")
            continue
        frontmatter = match.group("frontmatter")
        name = re.search(r"(?m)^name:\s*(.+?)\s*$", frontmatter)
        description = re.search(r"(?m)^description:\s*(.+?)\s*$", frontmatter)
        if name is None or name.group(1) != skill_dir.name:
            errors.append(f"skill name must match directory: {skill_dir.name}")
        if description is None or not description.group(1).strip():
            errors.append(f"skill description is missing: {skill_dir.name}")
        if "TODO" in content:
            errors.append(f"skill contains scaffold placeholder: {skill_dir.name}")
    return tuple(errors)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--expected-revision")
    parser.add_argument("--routing", type=Path)
    parser.add_argument("--skills", action="store_true")
    args = parser.parse_args()
    if args.evidence is None and args.routing is None and not args.skills:
        parser.error("provide --evidence, --routing, and/or --skills")
    errors: list[str] = []
    try:
        if args.evidence is not None:
            errors.extend(
                validate_evidence(_load(args.evidence), expected_revision=args.expected_revision)
            )
        if args.routing is not None:
            errors.extend(validate_routing(_load(args.routing)))
        if args.skills:
            errors.extend(validate_skills())
    except (OSError, json.JSONDecodeError) as error:
        print(f"semantic harness input error: {error}")
        return 1
    if errors:
        print("semantic harness validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("semantic harness validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
