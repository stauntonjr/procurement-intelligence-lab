"""The actual offline CLI retains all six roles and never fabricates readiness."""

import json
import subprocess
import sys
from pathlib import Path


def run(manifest: Path, root: Path, output: Path):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.consolidate_g2_evidence",
            "--manifest",
            str(manifest),
            "--artifact-root",
            str(root),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_actual_cli_missing_bundle_keeps_denominators_unknown(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "reports": {}}))
    output = tmp_path / "dossier.json"
    done = run(manifest, tmp_path, output)
    assert done.returncode == 1, done.stdout + done.stderr
    report = json.loads(output.read_text())
    assert len(report["groups"]) == 6
    assert not report["bounded_installed_suite_ready"]
    assert not report["release_ready"]
    assert all(
        r["evidence_status"] == "unknown" and r["real_model_attempts"] is None
        for r in report["groups"].values()
    )
    original = output.read_bytes()
    assert run(manifest, tmp_path, output).returncode != 0
    assert output.read_bytes() == original


def test_actual_cli_refuses_artifact_escape_and_hash_drift(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reports": {
                    "fresh_language": {"path": "../private.json", "sha256": "0" * 64},
                    "candidate_controls": {"path": "input.json", "sha256": "0" * 64},
                },
            }
        )
    )
    (tmp_path / "input.json").write_text("{}")
    output = tmp_path / "dossier.json"
    done = run(manifest, tmp_path, output)
    assert done.returncode == 1, done.stdout + done.stderr
    report = json.loads(output.read_text())
    assert report["groups"]["fresh_language"]["evidence_status"] == "fail"
    assert report["groups"]["candidate_controls"]["evidence_status"] == "fail"
    assert not report["bounded_installed_suite_ready"]


def test_actual_baseline_cli_exercises_http_without_inference(tmp_path: Path):
    output = tmp_path / "baseline.json"
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.consolidate_g2_evidence",
            "--measure-baseline",
            "--python",
            sys.executable,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        # This correctness check performs 512 sequential HTTP requests. Hosted CI
        # can exceed three minutes; request timings remain in the report rather
        # than making runner throughput an implicit product acceptance threshold.
        timeout=600,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    report = json.loads(output.read_text())
    assert report["structured"]["counts"]["pass"] == 48
    assert (
        len(report["investigation_requests"]) == report["investigation_http_seconds"]["count"] == 48
    )
    assert len(report["source_requests"]) == report["source_http_seconds"]["count"] == 464
    assert report["investigation_http_seconds"]["min"] >= 0
    assert "no natural-language interpretation, model calls" in report["condition"]


def test_actual_cli_checks_primary_http_status_after_hash_verification(tmp_path: Path):
    from hashlib import sha256

    ids = [f"query-{i}" for i in range(48)]
    versions = {"application": "fixed"}
    for status, expected in ((500, "fail"), (None, "unknown")):
        raw = {
            "versions": versions,
            "structured": {
                "results": [{"id": i, "outcome": "pass"} for i in ids],
                "source_references_resolved": 1,
            },
            "investigation_requests": [{"id": i, "status": status, "seconds": 0.1} for i in ids],
            "source_requests": [{"status": 200, "seconds": 0.1}],
        }
        source = tmp_path / "raw.json"
        source.write_text(json.dumps(raw))
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "target_versions": versions,
                    "reports": {
                        "deterministic_baseline": {
                            "path": source.name,
                            "sha256": sha256(source.read_bytes()).hexdigest(),
                            "ids": ids,
                            "versions": versions,
                            "use": "gating",
                            "source_checks": 1,
                            "http_statuses": {i: 200 for i in ids},
                        }
                    },
                }
            )
        )
        output = tmp_path / f"{expected}.json"
        done = run(manifest, tmp_path, output)
        assert done.returncode == 1
        group = json.loads(output.read_text())["groups"]["deterministic_baseline"]
        assert group["evidence_status"] == expected, group
        assert group["real_model_attempts"] == 0
