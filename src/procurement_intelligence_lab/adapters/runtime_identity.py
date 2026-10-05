"""Immutable identity of installed application Python bytes for composition roots."""

from hashlib import sha256
from importlib.resources import files
from pathlib import Path


def application_revision() -> str:
    package = Path(str(files("procurement_intelligence_lab")))
    digest = sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()
