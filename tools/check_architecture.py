"""Deterministic architecture checks used by local and CI validation."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "src" / "procurement_intelligence_lab" / "domain"
PROJECT_ROOT = "procurement_intelligence_lab"


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


def main() -> int:
    """Fail when the framework-independent domain imports third-party packages."""
    violations: list[str] = []
    allowed = set(sys.stdlib_module_names) | {PROJECT_ROOT}

    for path in sorted(DOMAIN.rglob("*.py")):
        for module in sorted(imported_roots(path) - allowed):
            violations.append(f"{path.relative_to(ROOT)} imports third-party module {module!r}")

    if violations:
        print("Architecture boundary violations:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("architecture import checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
