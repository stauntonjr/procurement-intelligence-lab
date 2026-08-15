"""Validate and execute deterministic development-agent challenge manifests."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import TypedDict, cast

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
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, dict):
            raise TypeError(f"{path.relative_to(ROOT)} must be a JSON object")
        value = cast(dict[str, object], raw_value)
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
        for field in ("id", "title", "finding_commit", "oracle"):
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
