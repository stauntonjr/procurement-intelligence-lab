"""Commit a disposable snapshot so conformance tests do not require a clean developer tree."""

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def conformance_checkout(repo: Path) -> Path:
    repo.mkdir()
    shutil.copytree(
        ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    (repo / "tools").mkdir()
    shutil.copyfile(ROOT / "tools/benchmark_bom_stages.py", repo / "tools/benchmark_bom_stages.py")
    shutil.copyfile(
        ROOT / "tools/benchmark_bom_normalization.py", repo / "tools/benchmark_bom_normalization.py"
    )
    shutil.copytree(
        ROOT / "evals/extraction/bom-stages-v1", repo / "evals/extraction/bom-stages-v1"
    )
    shutil.copytree(
        ROOT / "evals/extraction/bom-normalization-v1",
        repo / "evals/extraction/bom-normalization-v1",
    )
    shutil.copyfile(ROOT / ".gitignore", repo / ".gitignore")
    for args in (
        ["init", "-q"],
        ["add", "."],
        [
            "-c",
            "user.name=Contract",
            "-c",
            "user.email=contract@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return repo
