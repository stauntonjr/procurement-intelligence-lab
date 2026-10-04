"""Public evaluator CLI retains full denominators when startup transport fails."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import run_g2_pilot


def test_public_runner_finalizes_startup_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "report.json"
    database = tmp_path / "runs.db"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_g2_pilot",
            "--run-live",
            "--python",
            sys.executable,
            "--database",
            str(database),
            "--output",
            str(output),
        ],
    )

    def unavailable(*_: Any, **__: Any) -> Any:
        raise TimeoutError("model discovery timeout")

    monkeypatch.setattr(run_g2_pilot, "urlopen", unavailable)
    assert run_g2_pilot.main() == 1
    report = json.loads(output.read_text())
    assert report["acceptance"] == "not_ready"
    assert report["evaluation_use"] == "development_regression"
    assert "inspected" in report["limits"]
    assert "not held-out" in report["limits"]
    assert report["interpretation"]["counts"] == {
        "pass": 0,
        "fail": 0,
        "unknown": 48,
        "not_applicable": 0,
    }
    assert len(report["attempt_audit"]) == 48
    assert all(row["model_calls"] is None for row in report["attempt_audit"])
    assert report["operation_errors"] == ["TimeoutError"]


def test_public_runner_refuses_to_overwrite_prior_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "prior.json"
    output.write_text("retained")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_g2_pilot",
            "--run-live",
            "--python",
            sys.executable,
            "--database",
            str(tmp_path / "runs.db"),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(ValueError, match="fresh database/output"):
        run_g2_pilot.main()
    assert output.read_text() == "retained"


def fresh_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    from dataclasses import asdict

    from procurement_intelligence_lab.interfaces.live_review import compose_live
    from tests.unit.test_fresh_g2_cohort import fixture

    manifest, frozen = fixture(tmp_path / "selected-dataset")
    frozen["freshness"]["runtime_versions"] = asdict(
        compose_live(tmp_path / "preflight.db").runs.versions
    )
    manifest.write_text(json.dumps(frozen))
    output = tmp_path / "fresh-report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_g2_pilot",
            "--run-live",
            "--python",
            sys.executable,
            "--database",
            str(tmp_path / "fresh-runs.db"),
            "--output",
            str(output),
            "--dataset",
            str(manifest.parent),
            "--manifest",
            str(manifest),
        ],
    )
    return manifest, output


def test_selected_fresh_caller_retains_startup_denominators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hashlib import sha256

    manifest, output = fresh_args(tmp_path, monkeypatch)

    def unavailable(*_: Any, **__: Any) -> Any:
        raise TimeoutError("no inference")

    monkeypatch.setattr(run_g2_pilot, "urlopen", unavailable)
    assert run_g2_pilot.main() == 1
    report = json.loads(output.read_text())
    assert report["evaluation_use"] == "fresh_language_holdout"
    assert report["interpretation_manifest_sha256"] == sha256(manifest.read_bytes()).hexdigest()
    assert (
        report["dataset_manifest_sha256"]
        == sha256((manifest.parent / "manifest.json").read_bytes()).hexdigest()
    )
    assert report["interpretation"]["counts"]["unknown"] == 48
    assert report["limits"] == "Known sources; new language only."


def test_selected_frozen_runtime_refuses_drift_before_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, output = fresh_args(tmp_path, monkeypatch)
    data = json.loads(manifest.read_text())
    data["freshness"]["runtime_versions"]["prompt"] = "changed"
    manifest.write_text(json.dumps(data))

    def prohibited(*_: Any, **__: Any) -> Any:
        pytest.fail("model discovery must not run after binding drift")

    monkeypatch.setattr(run_g2_pilot, "urlopen", prohibited)
    with pytest.raises(ValueError, match="runtime changed"):
        run_g2_pilot.main()
    assert not output.exists()


def test_selected_dataset_reaches_real_main_baseline_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager
    from io import StringIO

    manifest, output = fresh_args(tmp_path, monkeypatch)

    def discovery(*_a: Any, **_kw: Any) -> StringIO:
        return StringIO("{}")

    monkeypatch.setattr(run_g2_pilot, "urlopen", discovery)

    @contextmanager
    def inspector(_python: Path):
        yield "http://test.invalid"

    seen: list[tuple[str, Path]] = []

    def baseline(url: str, directory: Path):
        seen.append((url, directory))
        return {"ready": False}

    monkeypatch.setattr(run_g2_pilot, "installed_inspector", inspector)
    monkeypatch.setattr(run_g2_pilot, "evaluate", baseline)
    assert run_g2_pilot.main() == 1
    assert seen == [("http://test.invalid", manifest.parent)]
    assert json.loads(output.read_text())["interpretation"]["counts"]["unknown"] == 48
