"""Validate and execute deterministic development-agent challenge manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "evals" / "development_agents" / "challenges"


class Challenge(TypedDict):
    id: str
    title: str
    finding_commit: str
    oracle: str
    known_bad: str
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
            "finding_commit",
            "oracle",
            "known_bad",
            "test_command",
            "surfaces",
            "prevention",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(f"{path.relative_to(ROOT)} missing {sorted(missing)!r}")
        for field in ("id", "title", "finding_commit", "oracle", "known_bad"):
            if not isinstance(value[field], str) or not value[field]:
                raise ValueError(f"{path.name} requires a non-empty string {field}")
        for field in ("test_command", "surfaces", "prevention"):
            entries = value[field]
            if (
                not isinstance(entries, list)
                or not entries
                or not all(isinstance(entry, str) and entry for entry in entries)
            ):
                raise ValueError(f"{value['id']} requires non-empty string entries in {field}")
        challenge = cast(Challenge, value)
        if challenge["id"] in seen:
            raise ValueError(f"duplicate challenge ID {challenge['id']!r}")
        if path.stem != challenge["id"]:
            raise ValueError(f"{path.name} does not match challenge ID {challenge['id']!r}")
        seen.add(challenge["id"])
        challenges.append(challenge)
    expected = {f"C{number:03d}" for number in range(1, 9)}
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--challenge", action="append", default=[])
    parser.add_argument("--results", type=Path)
    parser.add_argument("--model", default="not-specified")
    parser.add_argument("--configuration", default="not-specified")
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
        outcome = "passed" if completed.returncode == 0 else "failed"
        public_status = "passed" if completed.returncode == 0 else "failed"
        results.append(
            {
                "id": challenge["id"],
                "outcome": outcome,
                "return_code": completed.returncode,
                "duration_seconds": round(time.monotonic() - started, 3),
                "prevention": f"not_evaluated_public_oracle_{public_status}",
                "detection": f"public_oracle_{public_status}",
                "repair": "not_evaluated",
            }
        )
        if completed.returncode != 0:
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
