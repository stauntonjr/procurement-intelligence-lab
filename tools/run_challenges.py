"""Validate and execute deterministic development-agent challenge manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "evals" / "development_agents" / "challenges"


class MutationOperation(TypedDict):
    path: str
    find: str
    replace: str


class Challenge(TypedDict):
    id: str
    title: str
    introducing_commit: str
    oracle: str
    known_bad: str
    known_bad_mutation: list[MutationOperation]
    known_bad_failure_pattern: str
    test_command: list[str]
    surfaces: list[str]
    prevention: list[str]


def load_challenges() -> tuple[Challenge, ...]:
    challenges: list[Challenge] = []
    seen: set[str] = set()
    for path in sorted(MANIFESTS.glob("C*.json")):
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, dict):
            raise TypeError(f"{path.relative_to(ROOT)} must be a JSON object")
        value = cast(dict[str, object], raw_value)
        required = {
            "id",
            "title",
            "introducing_commit",
            "oracle",
            "known_bad",
            "known_bad_mutation",
            "known_bad_failure_pattern",
            "test_command",
            "surfaces",
            "prevention",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(f"{path.relative_to(ROOT)} missing {sorted(missing)!r}")
        for field in (
            "id",
            "title",
            "introducing_commit",
            "oracle",
            "known_bad",
            "known_bad_failure_pattern",
        ):
            if not isinstance(value[field], str) or not value[field]:
                raise ValueError(f"{path.name} requires a non-empty string {field}")
        try:
            re.compile(cast(str, value["known_bad_failure_pattern"]))
        except re.error as exc:
            raise ValueError(f"{path.name} has invalid known_bad_failure_pattern") from exc
        if re.fullmatch(r"[0-9a-f]{40}", cast(str, value["introducing_commit"])) is None:
            raise ValueError(f"{path.name} requires a full introducing_commit SHA")
        for field in ("test_command", "surfaces", "prevention"):
            entries = value[field]
            if (
                not isinstance(entries, list)
                or not entries
                or not all(isinstance(entry, str) and entry for entry in entries)
            ):
                raise ValueError(f"{value['id']} requires non-empty string entries in {field}")
        mutations = value["known_bad_mutation"]
        if not isinstance(mutations, list) or not mutations:
            raise ValueError(f"{value['id']} requires at least one known_bad_mutation")
        for mutation in mutations:
            if not isinstance(mutation, dict):
                raise TypeError(f"{value['id']} mutation must be an object")
            if set(mutation) != {"path", "find", "replace"}:
                raise ValueError(f"{value['id']} mutation requires path, find, and replace")
            path_value, find_value, replace_value = (
                mutation["path"],
                mutation["find"],
                mutation["replace"],
            )
            if not isinstance(path_value, str) or not path_value:
                raise ValueError(f"{value['id']} mutation path must be a non-empty string")
            mutation_path = Path(path_value)
            if mutation_path.is_absolute() or ".." in mutation_path.parts:
                raise ValueError(f"{value['id']} mutation path must stay within the checkout")
            if not isinstance(find_value, str) or not find_value:
                raise ValueError(f"{value['id']} mutation find must be a non-empty string")
            if not isinstance(replace_value, str):
                raise TypeError(f"{value['id']} mutation replace must be a string")
            try:
                source = (ROOT / mutation_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ValueError(
                    f"{value['id']} mutation path {path_value!r} could not be read"
                ) from exc
            occurrences = source.count(find_value)
            if occurrences != 1:
                raise ValueError(
                    f"{value['id']} mutation expected one match in {path_value}, "
                    f"found {occurrences}"
                )
        challenge = cast(Challenge, value)
        if challenge["id"] in seen:
            raise ValueError(f"duplicate challenge ID {challenge['id']!r}")
        if path.stem != challenge["id"]:
            raise ValueError(f"{path.name} does not match challenge ID {challenge['id']!r}")
        seen.add(challenge["id"])
        challenges.append(challenge)
    expected = {f"C{number:03d}" for number in range(1, 12)}
    if seen != expected:
        raise ValueError(
            f"challenge set mismatch: expected {sorted(expected)}, found {sorted(seen)}"
        )
    return tuple(challenges)


def _revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _mutation_command(command: list[str]) -> list[str]:
    if command[:3] == ["uv", "run", "pytest"]:
        return [sys.executable, "-m", "pytest", *command[3:]]
    if command[:3] == ["uv", "run", "python"]:
        return [sys.executable, *command[3:]]
    raise ValueError(f"known-bad execution does not support {shlex.join(command)}")


def run_known_bad(challenge: Challenge) -> tuple[subprocess.CompletedProcess[str], float]:
    ignored = shutil.ignore_patterns(
        ".git",
        ".venv",
        ".pytest_cache",
        "__pycache__",
        "artifacts",
        ".coverage",
        "coverage.xml",
    )
    with tempfile.TemporaryDirectory(prefix=f"{challenge['id'].lower()}-known-bad-") as directory:
        checkout = Path(directory) / "checkout"
        shutil.copytree(ROOT, checkout, ignore=ignored)
        for mutation in challenge["known_bad_mutation"]:
            path = checkout / mutation["path"]
            source = path.read_text(encoding="utf-8")
            occurrences = source.count(mutation["find"])
            if occurrences != 1:
                raise ValueError(
                    f"{challenge['id']} mutation expected one match in {mutation['path']}, "
                    f"found {occurrences}"
                )
            path.write_text(
                source.replace(mutation["find"], mutation["replace"], 1),
                encoding="utf-8",
            )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join((str(checkout / "src"), str(checkout)))
        started = time.monotonic()
        completed = subprocess.run(
            _mutation_command(challenge["test_command"]),
            cwd=checkout,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        return completed, round(time.monotonic() - started, 3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--challenge", action="append", default=[])
    parser.add_argument("--results", type=Path)
    parser.add_argument("--model", default="not-specified")
    parser.add_argument("--configuration", default="not-specified")
    parser.add_argument("--verify-known-bad", action="store_true")
    args = parser.parse_args()
    challenges = load_challenges()
    selected = set(args.challenge)
    if selected - {item["id"] for item in challenges}:
        raise ValueError(f"unknown challenge IDs: {sorted(selected)!r}")
    if args.validate_only:
        print(f"validated {len(challenges)} challenge manifests")
        return 0

    started_at = dt.datetime.now(dt.UTC)
    results: list[dict[str, object]] = []
    exit_code = 0
    for challenge in challenges:
        if selected and challenge["id"] not in selected:
            continue
        print(f"{challenge['id']}: {challenge['title']}")
        print(f"  $ {shlex.join(challenge['test_command'])}")
        started = time.monotonic()
        completed = subprocess.run(challenge["test_command"], cwd=ROOT, check=False)
        public_status = "passed" if completed.returncode == 0 else "failed"
        known_bad_status = "not_run"
        known_bad_return_code: int | None = None
        known_bad_duration: float | None = None
        if args.verify_known_bad and completed.returncode == 0:
            known_bad_completed, known_bad_duration = run_known_bad(challenge)
            known_bad_return_code = known_bad_completed.returncode
            known_bad_output = known_bad_completed.stdout + known_bad_completed.stderr
            failure_matched = (
                known_bad_return_code != 0
                and re.search(challenge["known_bad_failure_pattern"], known_bad_output) is not None
            )
            known_bad_status = (
                "rejected"
                if failure_matched
                else "wrong_failure"
                if known_bad_return_code != 0
                else "survived"
            )
            print(f"  known bad: {known_bad_status}")
            if known_bad_status != "rejected":
                print(known_bad_completed.stdout)
                print(known_bad_completed.stderr)
        passed = completed.returncode == 0 and known_bad_status in {"not_run", "rejected"}
        outcome = "passed" if passed else "failed"
        detection = (
            "public_oracle_detected_known_bad"
            if known_bad_status == "rejected"
            else "public_oracle_missed_known_bad"
            if known_bad_status == "survived"
            else "public_oracle_wrong_known_bad_failure"
            if known_bad_status == "wrong_failure"
            else f"public_oracle_{public_status}"
        )
        results.append(
            {
                "id": challenge["id"],
                "outcome": outcome,
                "return_code": completed.returncode,
                "duration_seconds": round(time.monotonic() - started, 3),
                "prevention": f"not_evaluated_public_oracle_{public_status}",
                "detection": detection,
                "repair": "not_evaluated",
                "known_bad_outcome": known_bad_status,
                "known_bad_return_code": known_bad_return_code,
                "known_bad_duration_seconds": known_bad_duration,
            }
        )
        if not passed:
            exit_code = 1
    if args.results is not None:
        payload = {
            "schema_version": 1,
            "kind": "development-agent-public-challenge-run",
            "revision": _revision(),
            "model": args.model,
            "configuration": args.configuration,
            "started_at": started_at.isoformat(),
            "completed_at": dt.datetime.now(dt.UTC).isoformat(),
            "results": results,
        }
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
