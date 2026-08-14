"""Validate and execute deterministic development-agent challenge manifests."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "evals" / "development_agents" / "challenges"


class Challenge(TypedDict):
    id: str
    title: str
    finding_commit: str
    oracle: str
    test_command: list[str]
    surfaces: list[str]
    prevention: list[str]


def load_challenges() -> tuple[Challenge, ...]:
    challenges: list[Challenge] = []
    seen: set[str] = set()
    for path in sorted(MANIFESTS.glob("C*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        required = {
            "id",
            "title",
            "finding_commit",
            "oracle",
            "test_command",
            "surfaces",
            "prevention",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(f"{path.relative_to(ROOT)} missing {sorted(missing)!r}")
        if value["id"] in seen:
            raise ValueError(f"duplicate challenge ID {value['id']!r}")
        if path.stem != value["id"]:
            raise ValueError(f"{path.name} does not match challenge ID {value['id']!r}")
        if not isinstance(value["test_command"], list) or not value["test_command"]:
            raise ValueError(f"{value['id']} requires a non-empty argv test_command")
        seen.add(value["id"])
        challenges.append(value)
    expected = {f"C{number:03d}" for number in range(1, 9)}
    if seen != expected:
        raise ValueError(
            f"challenge set mismatch: expected {sorted(expected)}, found {sorted(seen)}"
        )
    return tuple(challenges)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--challenge", action="append", default=[])
    args = parser.parse_args()
    challenges = load_challenges()
    selected = set(args.challenge)
    if selected - {item["id"] for item in challenges}:
        raise ValueError(f"unknown challenge IDs: {sorted(selected)!r}")
    if args.validate_only:
        print(f"validated {len(challenges)} challenge manifests")
        return 0

    for challenge in challenges:
        if selected and challenge["id"] not in selected:
            continue
        print(f"{challenge['id']}: {challenge['title']}")
        print(f"  $ {shlex.join(challenge['test_command'])}")
        subprocess.run(challenge["test_command"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
