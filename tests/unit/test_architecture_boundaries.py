from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "procurement_intelligence_lab"


def _absolute_imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module)
    return tuple(imports)


def _imports_below(directory: Path) -> tuple[tuple[Path, str], ...]:
    return tuple(
        (path, imported)
        for path in sorted(directory.rglob("*.py"))
        for imported in _absolute_imports(path)
    )


def test_platform_never_imports_a_vertical() -> None:
    platform = PACKAGE / "platform"
    assert platform.is_dir()
    violations = [
        (path.relative_to(ROOT), imported)
        for path, imported in _imports_below(platform)
        if imported.startswith("procurement_intelligence_lab.domains.")
    ]

    assert violations == []


def test_ports_never_import_a_concrete_vertical() -> None:
    violations = [
        (path.relative_to(ROOT), imported)
        for path, imported in _imports_below(PACKAGE / "ports")
        if imported.startswith("procurement_intelligence_lab.domains.")
    ]

    assert violations == []


def test_verticals_do_not_import_sibling_verticals() -> None:
    violations: list[tuple[Path, str]] = []
    domains = PACKAGE / "domains"
    for vertical in sorted(path for path in domains.iterdir() if path.is_dir()):
        own_prefix = f"procurement_intelligence_lab.domains.{vertical.name}"
        for path, imported in _imports_below(vertical):
            if imported.startswith(
                "procurement_intelligence_lab.domains."
            ) and not imported.startswith(own_prefix):
                violations.append((path.relative_to(ROOT), imported))

    assert violations == []


def test_superseded_root_prototype_is_absent() -> None:
    assert not (ROOT / "procurement_lab").exists()
