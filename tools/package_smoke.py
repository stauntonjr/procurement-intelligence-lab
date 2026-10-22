"""Build, inspect, install, and run the distributable wheel in isolation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import venv
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = (
    "procurement_intelligence_lab/examples/synthetic_bom.xlsx",
    "procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx",
    "procurement_intelligence_lab/examples/showcase_review_sources_v1.json",
    "procurement_intelligence_lab/examples/showcase_order_short.xlsx",
    "procurement_intelligence_lab/examples/showcase_order_matched.xlsx",
    "procurement_intelligence_lab/examples/showcase_bom_revision_a.xlsx",
    "procurement_intelligence_lab/examples/showcase_bom_revision_b.xlsx",
    "procurement_intelligence_lab/examples/showcase_bom_revision_b_equal.xlsx",
    "procurement_intelligence_lab/examples/anomaly_sources_v1.json",
    "procurement_intelligence_lab/examples/anomaly_lifecycle_v1.json",
)


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the package smoke test")

    with tempfile.TemporaryDirectory(prefix="procurement-package-smoke-") as directory:
        temporary = Path(directory)
        distribution = temporary / "dist"
        subprocess.run(
            [uv, "build", "--out-dir", str(distribution)],
            cwd=ROOT,
            check=True,
        )
        wheels = sorted(distribution.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        wheel = wheels[0]
        stage_source = temporary / "shared-stage-source.xlsx"
        with ZipFile(wheel) as archive:
            missing = sorted(set(RESOURCES) - set(archive.namelist()))
            if missing:
                raise RuntimeError(f"wheel is missing runtime resources {missing}")
            stage_source.write_bytes(
                archive.read("procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx")
            )

            corpus = "procurement_intelligence_lab/examples/corpus_v1/"
            manifest = json.loads(archive.read(corpus + "manifest.json"))
            for doc in manifest["documents"]:
                for key in ("path", "metadata_path"):
                    if corpus + doc[key] not in archive.namelist():
                        raise RuntimeError("wheel is missing an admitted corpus source")
            if any(
                "/evals/" in name
                or name.endswith(
                    (
                        "/gold.json",
                        "/qrels.json",
                        "/queries.json",
                        "/gold-review.json",
                        "/pilot-gold.json",
                        "/pilot-gold-review.json",
                    )
                )
                for name in archive.namelist()
            ):
                raise RuntimeError("wheel includes evaluator-only material")

        probe = ROOT / "tools/order_package_probe.py"
        execution_fixture = ROOT / "tests/fixtures/execution"
        execution_context = temporary / "prefix-context.json"
        context = json.loads((ROOT / "tests/fixtures/bom-stages/context.json").read_text())
        context["code_revision"] = tomllib.loads(
            (execution_fixture / "procurement-config.toml").read_text()
        )["application_version"]
        execution_context.write_text(json.dumps(context))
        prefix_outputs: list[str] = []

        def prefix_probe(python: Path):
            return subprocess.run(
                [
                    str(python),
                    str(ROOT / "tools/package_execution_probe.py"),
                    str(stage_source),
                    str(execution_context),
                    str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
                    str(execution_fixture / "procurement-registry.json"),
                    str(execution_fixture / "procurement-config.toml"),
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )

        probe_outputs: list[str] = []
        pythons: list[Path] = []
        for index in (1, 2):
            environment = temporary / f"venv-{index}"
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / (
                "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
            )
            pythons.append(python)
            subprocess.run(
                [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
                cwd=temporary,
                check=True,
            )
            probe_run = subprocess.run(
                [str(python), str(probe)],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            corpus_probe = subprocess.run(
                [str(python), str(ROOT / "tools/corpus_package_probe.py")],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [str(python), str(ROOT / "tools/agent_run_package_probe.py")],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            manifest_run = subprocess.run(
                [str(python), "-m", "procurement_intelligence_lab.interfaces.domain_package"],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads(manifest_run.stdout)
            if manifest["domain"] != {"id": "procurement", "version": "0.1.0"}:
                raise RuntimeError("installed procurement package identity drifted")
            if manifest["source_profile"]["id"] != "bom-table" or len(manifest["stages"]) != 12:
                raise RuntimeError("installed procurement source profile is incomplete")
            if [
                (stage["mode"], stage["neutral_semantics"]) for stage in manifest["stages"][9:]
            ] != [
                ("EMPTY", "no_predictions"),
                ("EMPTY", "no_decisions_or_recommendations"),
                ("EMPTY", "no_action_attempted"),
            ]:
                raise RuntimeError("installed package declares unimplemented late-stage behavior")
            unsupported_profile = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.domain_package",
                    "--source-profile",
                    "purchase-order",
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            if (
                unsupported_profile.returncode != 2
                or unsupported_profile.stdout
                or not any(
                    issue["code"] == "unknown_source_profile"
                    for issue in json.loads(unsupported_profile.stderr)["issues"]
                )
            ):
                raise RuntimeError("installed manifest command silently accepts an unknown profile")
            # The descriptor fixtures advertise compatibility only; they contain no executors.
            planning_fixture = ROOT / "tests/fixtures/planning"
            planning_outputs: list[str] = []
            for domain in ("procurement", "conformance"):
                planning_manifest = temporary / f"{domain}-manifest.json"
                planning_manifest.write_text(
                    manifest_run.stdout
                    if domain == "procurement"
                    else (planning_fixture / "conformance-manifest.json").read_text()
                )
                planned = subprocess.run(
                    [
                        str(python),
                        "-m",
                        "procurement_intelligence_lab.interfaces.plan_package",
                        "--manifest",
                        str(planning_manifest),
                        "--registry",
                        str(planning_fixture / f"{domain}-registry.json"),
                        "--config",
                        str(planning_fixture / f"{domain}-config.toml"),
                    ],
                    cwd=temporary,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                plan_envelope = json.loads(planned.stdout)
                plan = plan_envelope["plan"]
                plan_bytes = json.dumps(
                    plan, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
                if plan_envelope["plan_hash"] != hashlib.sha256(plan_bytes).hexdigest():
                    raise RuntimeError(
                        "installed plan hash does not identify its canonical payload"
                    )
                if len(plan["stages"]) != 12 or len(plan["physical_steps"]) != (
                    9 if domain == "procurement" else 1
                ):
                    raise RuntimeError(
                        "installed planner lost logical stages or executable selections"
                    )
                if (
                    plan["domain"]["id"] != domain
                    or plan["stages"][-1]["disposition"] != "TYPED_EMPTY"
                ):
                    raise RuntimeError("installed planner lost domain or neutral semantics")
                planning_outputs.append(planned.stdout.strip())
            missing_registry = temporary / "missing-registry.json"
            missing_registry.write_text('{"schema_version":"1.0","implementations":[]}')
            rejected_plan = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.plan_package",
                    "--manifest",
                    str(temporary / "conformance-manifest.json"),
                    "--registry",
                    str(missing_registry),
                    "--config",
                    str(planning_fixture / "conformance-config.toml"),
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            if (
                rejected_plan.returncode != 2
                or rejected_plan.stdout
                or not any(
                    issue["code"] == "unknown_implementation"
                    for issue in json.loads(rejected_plan.stderr)["issues"]
                )
            ):
                raise RuntimeError("installed planner did not reject an unavailable implementation")
            stage_run = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.bom_stages",
                    str(stage_source),
                    "--context",
                    str(ROOT / "tests/fixtures/bom-stages/context.json"),
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            stage_payload = json.loads(stage_run.stdout)
            if stage_payload["executed_stages"] != ["INGEST", "STRUCTURE", "MAP"]:
                raise RuntimeError(
                    "installed shared-stage command lost its actual execution boundary"
                )
            fields = stage_payload["mapped_document"]["fields"]
            gpu_quantity = next(field for field in fields if field["field_key"] == "BOM!C2")
            if gpu_quantity["raw_value"] != "4" or gpu_quantity["evidence"]["cells"] != ["C"]:
                raise RuntimeError("installed mapping lost raw quantity or source cell evidence")
            events = stage_payload["transformations"]
            if len(events) != 3 or events[2]["parent_event_ids"] != [events[1]["event_id"]]:
                raise RuntimeError("installed shared stages lost transformation parentage")
            normalized = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.bom_stages",
                    str(stage_source),
                    "--context",
                    str(ROOT / "tests/fixtures/bom-stages/context.json"),
                    "--normalization-policy",
                    str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            normalized_payload = json.loads(normalized.stdout)
            quantity = next(
                x
                for x in normalized_payload["normalization"]["observations"]
                if x["observation_key"] == "BOM!C2"
            )
            if (
                quantity["value"] != "4"
                or quantity["unit"] != "each"
                or quantity["source_field"]["raw_value"] != "4"
                or quantity["source_field"]["evidence"]["cells"] != ["C"]
            ):
                raise RuntimeError(
                    "installed normalization lost exact value, units or source evidence"
                )
            if (
                normalized_payload["executed_stages"] != ["INGEST", "STRUCTURE", "MAP", "NORMALIZE"]
                or len(normalized_payload["transformations"]) != 4
            ):
                raise RuntimeError("installed normalization lost its actual stage boundary")
            asserted = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.bom_stages",
                    str(stage_source),
                    "--context",
                    str(ROOT / "tests/fixtures/bom-stages/context.json"),
                    "--normalization-policy",
                    str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
                    "--assertions",
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            assertion_payload = json.loads(asserted.stdout)
            claims = assertion_payload["assertion_batch"]["claims"]
            claim = next(x for x in claims if x["trace"]["mapped_field_key"] == "BOM!C2")
            if (
                assertion_payload["executed_stages"]
                != ["INGEST", "STRUCTURE", "MAP", "NORMALIZE", "ASSERT"]
                or len(assertion_payload["transformations"]) != 5
                or claim["value"] != "4"
                or claim["raw_value"] != "4"
                or claim["unit"] != "each"
                or claim["status"] != "observed"
                or claim["evidence"]["cells"] != ["C"]
                or claim["trace"]["normalization_event_id"]
                != assertion_payload["transformations"][3]["event_id"]
                or claim["trace"]["assertion_event_id"]
                != assertion_payload["transformations"][4]["event_id"]
                or claim["confidence_diagnostic"] != "not estimated"
            ):
                raise RuntimeError("installed source assertions lost claim meaning or provenance")
            missing_policy = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.bom_stages",
                    str(stage_source),
                    "--context",
                    str(ROOT / "tests/fixtures/bom-stages/context.json"),
                    "--assertions",
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            if (
                missing_policy.returncode != 2
                or missing_policy.stdout
                or json.loads(missing_policy.stderr)["code"] != "pil.input.document_stage_invalid"
            ):
                raise RuntimeError("installed ASSERT accepted missing normalization policy")
            invalid_policy = temporary / "invalid-normalization-policy.json"
            invalid_policy.write_text('{"currency":"USD"}')
            invalid_normalization = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.bom_stages",
                    str(stage_source),
                    "--context",
                    str(ROOT / "tests/fixtures/bom-stages/context.json"),
                    "--normalization-policy",
                    str(invalid_policy),
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            if (
                invalid_normalization.returncode != 2
                or invalid_normalization.stdout
                or json.loads(invalid_normalization.stderr)["code"]
                != "pil.input.normalization_policy_invalid"
            ):
                raise RuntimeError(
                    "installed normalization did not reject missing unit/currency policy"
                )
            invalid_source = temporary / "invalid-stage-source.xlsx"
            invalid_source.write_bytes(b"not XLSX")
            invalid_stage = subprocess.run(
                [
                    str(python),
                    "-m",
                    "procurement_intelligence_lab.interfaces.bom_stages",
                    str(invalid_source),
                    "--context",
                    str(ROOT / "tests/fixtures/bom-stages/context.json"),
                ],
                cwd=temporary,
                check=False,
                capture_output=True,
                text=True,
            )
            if (
                invalid_stage.returncode != 2
                or invalid_stage.stdout
                or json.loads(invalid_stage.stderr)["code"]
                != "pil.interpretation.document_structure_invalid"
            ):
                raise RuntimeError(
                    "installed shared stages did not report typed unsupported-source failure"
                )
            prefix_run = prefix_probe(python)
            missing_planned_archive = subprocess.run(
                [
                    str(python),
                    str(ROOT / "tools/package_planned_execution_archive_probe.py"),
                    str(stage_source),
                    str(execution_context),
                    str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
                    str(execution_fixture / "procurement-registry.json"),
                    str(execution_fixture / "procurement-config.toml"),
                ],
                cwd=temporary,
                env={**os.environ, "PIL_PLANNED_ARCHIVE_EXPECT_MISSING_DRIVER": "1"},
                check=True,
                capture_output=True,
                text=True,
            )
            print(missing_planned_archive.stdout.strip())
            prefix_outputs.append(prefix_run.stdout.strip())
            print(prefix_run.stdout.strip())
            probe_outputs.append(
                probe_run.stdout.strip()
                + corpus_probe.stdout.strip()
                + manifest_run.stdout.strip()
                + "".join(planning_outputs)
                + stage_run.stdout.strip()
                + normalized.stdout.strip()
                + asserted.stdout.strip()
                + prefix_run.stdout.strip()
            )
        if probe_outputs[0] != probe_outputs[1]:
            raise RuntimeError("semantic identities changed across clean installation paths")

        python = pythons[0]
        completed = subprocess.run(
            [str(python), "-m", "procurement_intelligence_lab"],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        if payload["claims"]["gpu_quantity"]["value"] != "4":
            raise RuntimeError("installed demo returned an unexpected GPU quantity")
        web_help = subprocess.run(
            [str(python), "-m", "procurement_intelligence_lab.interfaces.web", "--help"],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )
        if "--host" not in web_help.stdout or "--port" not in web_help.stdout:
            raise RuntimeError("installed web server does not document host and port options")

        unavailable = subprocess.run(
            [
                str(python),
                "-m",
                "procurement_intelligence_lab.interfaces.workflow",
                "--database",
                str(temporary / "base-workflow.db"),
                "start",
                "--project",
                "atlas",
                "--item",
                "GPU-A",
                "--as-of",
                "2026-10-01T00:00:00Z",
            ],
            cwd=temporary,
            capture_output=True,
            text=True,
            check=False,
        )
        if unavailable.returncode != 1 or json.loads(unavailable.stdout) != {
            "code": "pil.infrastructure.workflow_unavailable",
            "category": "infrastructure",
        }:
            raise RuntimeError("base install does not fail clearly without optional workflow extra")
        missing_storage = subprocess.run(
            [
                str(python),
                "-m",
                "procurement_intelligence_lab.interfaces.assertion_archive",
                "init",
            ],
            env={
                **os.environ,
                "PIL_ASSERTION_ARCHIVE_DSN": "postgresql://unavailable.invalid/unused",
            },
            cwd=temporary,
            capture_output=True,
            text=True,
            check=False,
        )
        if (
            missing_storage.returncode != 2
            or missing_storage.stdout
            or "storage extra" not in json.loads(missing_storage.stderr)["message"]
        ):
            raise RuntimeError("base wheel did not report absent optional storage driver")
        missing_review_storage = subprocess.run(
            [str(python), "-m", "procurement_intelligence_lab.interfaces.document_review", "init"],
            cwd=temporary,
            env={**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": "configured-but-driver-absent"},
            check=False,
            capture_output=True,
            text=True,
        )
        if (
            missing_review_storage.returncode != 2
            or missing_review_storage.stdout
            or "storage extra" not in json.loads(missing_review_storage.stderr)["message"]
            or json.loads(missing_review_storage.stderr)["code"]
            != "pil.infrastructure.document_review_unavailable"
        ):
            raise RuntimeError("base wheel did not report typed missing review storage extra")

        missing_dependency_storage = subprocess.run(
            [
                str(python),
                "-m",
                "procurement_intelligence_lab.interfaces.correction_impact",
                "init",
            ],
            cwd=temporary,
            env={**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": "configured-but-driver-absent"},
            check=False,
            capture_output=True,
            text=True,
        )
        if (
            missing_dependency_storage.returncode != 2
            or missing_dependency_storage.stdout
            or "storage extra" not in json.loads(missing_dependency_storage.stderr)["message"]
            or json.loads(missing_dependency_storage.stderr)["code"]
            != "pil.infrastructure.dependency_unavailable"
        ):
            raise RuntimeError("base wheel did not report typed missing dependency storage extra")

        source_query_scope = temporary / "base-query-scope.json"
        source_query_scope.write_text(
            json.dumps(
                {
                    "tenant_id": "synthetic",
                    "project_id": "base-query",
                    "site_id": "lab",
                    "version": "1",
                }
            )
        )
        source_query_context = temporary / "base-query-context.json"
        source_query_context.write_text(
            json.dumps(
                {
                    "run_id": "base-query",
                    "code_revision": "installed-smoke",
                    "started_at": "2026-10-21T00:00:00+00:00",
                }
            )
        )
        missing_query_storage = subprocess.run(
            [
                str(python),
                "-m",
                "procurement_intelligence_lab.interfaces.archived_bom_query",
                "--scope",
                str(source_query_scope),
                "--snapshot-id",
                "not-read",
                "--request-id",
                "not-recorded",
                "--context",
                str(source_query_context),
            ],
            cwd=temporary,
            env={
                **os.environ,
                "PIL_ASSERTION_ARCHIVE_DSN": "configured-but-driver-absent",
                "PIL_DOCUMENT_REVIEWER_ID": "package-smoke-human",
            },
            check=False,
            capture_output=True,
            text=True,
        )
        if (
            missing_query_storage.returncode != 2
            or missing_query_storage.stdout
            or "storage extra" not in json.loads(missing_query_storage.stderr)["message"]
            or json.loads(missing_query_storage.stderr)["code"]
            != "pil.infrastructure.archive_unavailable"
        ):
            raise RuntimeError("base wheel did not report typed missing query storage extra")

        selected_reviews = temporary / "base-selected-reviews.json"
        selected_reviews.write_text(json.dumps({"task_ids": ["not-read"]}))
        missing_reviewed_storage = subprocess.run(
            [
                str(python),
                "-m",
                "procurement_intelligence_lab.interfaces.reviewed_bom_query",
                "--scope",
                str(source_query_scope),
                "--snapshot-id",
                "not-read",
                "--request-id",
                "not-recorded",
                "--reviews",
                str(selected_reviews),
                "--as-of",
                "2026-10-20T00:00:00+00:00",
                "--context",
                str(source_query_context),
            ],
            cwd=temporary,
            env={
                **os.environ,
                "PIL_ASSERTION_ARCHIVE_DSN": "configured-but-driver-absent",
                "PIL_DOCUMENT_REVIEWER_ID": "package-smoke-human",
            },
            check=False,
            capture_output=True,
            text=True,
        )
        if (
            missing_reviewed_storage.returncode != 2
            or missing_reviewed_storage.stdout
            or "storage extra" not in json.loads(missing_reviewed_storage.stderr)["message"]
            or json.loads(missing_reviewed_storage.stderr)["code"]
            != "pil.infrastructure.archive_unavailable"
        ):
            raise RuntimeError(
                "base wheel did not report typed missing reviewed-query storage extra"
            )

        requirements = temporary / "workflow-requirements.txt"
        subprocess.run(
            [
                uv,
                "export",
                "--frozen",
                "--no-dev",
                "--extra",
                "workflow",
                "--extra",
                "storage",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(python),
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            cwd=temporary,
            check=True,
        )
        subprocess.run(
            [str(python), str(ROOT / "tools/workflow_package_probe.py")],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            [str(python), str(ROOT / "tools/review_web_package_probe.py")],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            [str(python), str(ROOT / "tools/live_review_package_probe.py")],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            [str(python), str(ROOT / "tools/original_showcase_package_probe.py")],
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )

        storage_prefix = prefix_probe(python)
        if storage_prefix.stdout.strip() != prefix_outputs[0]:
            raise RuntimeError("optional workflow/storage install changed prefix computation")
        print(storage_prefix.stdout.strip())

        if base := os.environ.get("PIL_TEST_POSTGRES_DSN"):
            from uuid import uuid4

            import psycopg
            from psycopg import sql
            from psycopg.conninfo import make_conninfo

            schema = "pil_planned_package_" + uuid4().hex
            with psycopg.connect(base, autocommit=True) as connection:
                connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            try:
                subprocess.run(
                    [
                        str(python),
                        str(ROOT / "tools/package_planned_execution_archive_probe.py"),
                        str(stage_source),
                        str(execution_context),
                        str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
                        str(execution_fixture / "procurement-registry.json"),
                        str(execution_fixture / "procurement-config.toml"),
                    ],
                    cwd=temporary,
                    env={
                        **os.environ,
                        "PIL_ASSERTION_ARCHIVE_DSN": make_conninfo(
                            base, options=f"-c search_path={schema}"
                        ),
                    },
                    check=True,
                    text=True,
                )
            finally:
                with psycopg.connect(base, autocommit=True) as connection:
                    connection.execute(
                        sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                    )
        else:
            print("planned archive storage qualification not requested: set PIL_TEST_POSTGRES_DSN")

        subprocess.run(
            [
                str(python),
                str(ROOT / "tools/archive_package_probe.py"),
                str(stage_source),
                str(ROOT / "tests/fixtures/bom-stages/context.json"),
                str(ROOT / "tests/fixtures/bom-stages/normalization-policy.json"),
            ],
            cwd=temporary,
            check=True,
            text=True,
        )

    print("package smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
