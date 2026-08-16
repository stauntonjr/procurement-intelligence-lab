"""Deterministic architecture checks used by local and CI validation."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "procurement_intelligence_lab"
PLATFORM = PACKAGE / "platform"
DOMAINS = PACKAGE / "domains"
PORTS = PACKAGE / "ports"
PROJECT_ROOT = "procurement_intelligence_lab"
REQUIRED_HARNESS_PATHS = (
    "tests/contract/test_claim_semantics.py",
    "tests/integration/test_web_happy_path.py",
    "tests/regression/test_state_invariants.py",
    "src/procurement_intelligence_lab/examples/synthetic_bom.xlsx",
    ".agents/skills/implement-domain-logic/SKILL.md",
    ".agents/skills/test-public-interface/SKILL.md",
    ".agents/skills/release-smoke/SKILL.md",
    ".agents/skills/run-agent-challenges/SKILL.md",
    ".agents/skills/manage-github-planning/SKILL.md",
    ".agents/skills/semantic-change-loop/SKILL.md",
    ".agents/skills/review-semantic-change/SKILL.md",
    "docs/development/semantic-change-evidence.schema.json",
    "evals/development_agents/skill-routing.json",
    "tools/validate_semantic_change.py",
    ".github/planning.json",
)


def imported_roots(path: Path) -> set[str]:
    """Return top-level modules imported by a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".", 1)[0])
    return roots


def absolute_imports(path: Path) -> set[str]:
    """Return absolute module names imported by a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.add(node.module)
    return imports


def main() -> int:
    """Enforce framework and dependency direction for platform and vertical semantics."""
    violations: list[str] = []
    allowed = set(sys.stdlib_module_names) | {PROJECT_ROOT}

    if not PLATFORM.is_dir():
        violations.append(f"required platform directory is missing: {PLATFORM.relative_to(ROOT)}")

    semantic_roots = (PLATFORM, DOMAINS)
    for directory in semantic_roots:
        for path in sorted(directory.rglob("*.py")):
            for module in sorted(imported_roots(path) - allowed):
                violations.append(f"{path.relative_to(ROOT)} imports third-party module {module!r}")

    for path in sorted(PLATFORM.rglob("*.py")):
        for module in sorted(absolute_imports(path)):
            if module.startswith(f"{PROJECT_ROOT}.domains."):
                violations.append(
                    f"{path.relative_to(ROOT)} imports vertical-owned module {module!r}"
                )

    for path in sorted(PORTS.rglob("*.py")):
        for module in sorted(absolute_imports(path)):
            if module.startswith(f"{PROJECT_ROOT}.domains."):
                violations.append(
                    f"{path.relative_to(ROOT)} imports concrete vertical module {module!r}"
                )

    for vertical in sorted(path for path in DOMAINS.iterdir() if path.is_dir()):
        own_prefix = f"{PROJECT_ROOT}.domains.{vertical.name}"
        for path in sorted(vertical.rglob("*.py")):
            for module in sorted(absolute_imports(path)):
                if module.startswith(f"{PROJECT_ROOT}.domains.") and not module.startswith(
                    own_prefix
                ):
                    violations.append(
                        f"{path.relative_to(ROOT)} imports sibling vertical module {module!r}"
                    )

    legacy_domain = PACKAGE / "domain"
    if legacy_domain.exists() and any(legacy_domain.iterdir()):
        violations.append(
            "ambiguous legacy package src/procurement_intelligence_lab/domain must remain absent"
        )

    for required in REQUIRED_HARNESS_PATHS:
        if not (ROOT / required).is_file():
            violations.append(f"required harness artifact is missing: {required}")

    if violations:
        print("Architecture boundary violations:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("architecture import checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
