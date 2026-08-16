"""Enforce immutable, allowlisted GitHub Actions workflow references."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
ALLOWLIST = ROOT / ".github" / "actions-allowlist.json"
USES_RE = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*([^\s#]+)\s*(?:#\s*(.*))?$")
ACTION_RE = re.compile(r"^(?P<repository>[^@]+)@(?P<revision>[^\s]+)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}$")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def workflow_references(
    workflow_dir: Path = WORKFLOW_DIR,
) -> list[tuple[Path, int, str, str | None]]:
    references: list[tuple[Path, int, str, str | None]] = []
    for path in sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES_RE.match(line)
            if match:
                references.append((path, line_number, match.group(1), match.group(2)))
    return references


def validate(*, workflow_dir: Path = WORKFLOW_DIR, allowlist: Path = ALLOWLIST) -> list[str]:
    errors: list[str] = []
    try:
        policy = json.loads(allowlist.read_text(encoding="utf-8"))
        allowed = {item["repository"] for item in policy["allowed_actions"]}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return [
            (
                f"{_display_path(allowlist)}: invalid actions allowlist "
                f"({exc.__class__.__name__}: {exc})"
            )
        ]

    for path, line_number, reference, comment in workflow_references(workflow_dir):
        match = ACTION_RE.match(reference)
        location = f"{_display_path(path)}:{line_number}"
        if not match:
            errors.append(f"{location}: malformed Action reference {reference!r}")
            continue
        repository, revision = match.group("repository"), match.group("revision")
        repository_root = "/".join(repository.split("/")[:2])
        if repository_root not in allowed:
            errors.append(f"{location}: Action {repository_root!r} is not allowlisted")
        if not SHA_RE.fullmatch(revision):
            errors.append(f"{location}: Action {repository} is not pinned to a full SHA")
        if not comment or not VERSION_COMMENT_RE.fullmatch(comment.strip()):
            errors.append(f"{location}: pinned Action needs a readable version comment")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("GitHub Actions supply-chain check failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"GitHub Actions supply-chain check passed ({len(workflow_references())} references)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
