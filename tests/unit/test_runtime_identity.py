"""Code identity changes with bytes, not unchanged package metadata or caches."""

from pathlib import Path
from typing import Any

from procurement_intelligence_lab.adapters import runtime_identity


def test_identity_binds_sorted_python_paths_and_bytes(tmp_path: Path, monkeypatch: Any) -> None:
    def package_files(_: str) -> Path:
        return tmp_path

    monkeypatch.setattr(runtime_identity, "files", package_files)
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    first = runtime_identity.application_revision()
    (tmp_path / "cache.pyc").write_bytes(b"ignored cache")
    assert runtime_identity.application_revision() == first
    (tmp_path / "a.py").write_text("VALUE = 2\n")
    assert runtime_identity.application_revision() != first
    (tmp_path / "a.py").rename(tmp_path / "b.py")
    assert runtime_identity.application_revision() != first
