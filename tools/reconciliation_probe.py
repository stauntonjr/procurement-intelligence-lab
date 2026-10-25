"""Qualify real installed retained-operation commands with explicit synthetic inputs."""

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    for name in (
        "source",
        "fixtures",
        "legacy-fixtures",
        "normalization-policy",
        "producer-context",
        "corpus",
        "wheel",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--code-revision", required=True)
    args = parser.parse_args()
    python = str(args.python.absolute())
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    corpus = json.loads(args.corpus.read_text())
    calls = []
    examples = []
    with tempfile.TemporaryDirectory(prefix="pil-reconciliation-installed-") as folder:
        root = Path(folder)

        def run(module, argv, error=None):
            command = [
                python,
                "-I",
                "-m",
                "procurement_intelligence_lab.interfaces." + module,
                *map(str, argv),
            ]
            start = perf_counter()
            done = subprocess.run(
                command, cwd=root, env=env, capture_output=True, text=True, check=False
            )
            calls.append(
                {"argv": command, "exit_code": done.returncode, "seconds": perf_counter() - start}
            )
            assert "Traceback" not in done.stderr and "postgresql://" not in done.stderr, (
                done.stderr
            )
            if error:
                assert done.returncode == 2 and not done.stdout, done.stderr
                out = json.loads(done.stderr)
                assert out["code"] == error, out
                return out
            assert done.returncode == 0 and not done.stderr, done.stderr
            return json.loads(done.stdout)

        runtime_argv = [
            python,
            "-I",
            "-c",
            "import json,platform,importlib.util,procurement_intelligence_lab as p; print(json.dumps({'version':platform.python_version(),'package_path':p.__file__,'storage_driver_available':importlib.util.find_spec('psycopg') is not None}))",
        ]
        runtime_done = subprocess.run(
            runtime_argv, cwd=root, env=env, capture_output=True, text=True, check=True
        )
        runtime = json.loads(runtime_done.stdout)
        assert "site-packages" in runtime["package_path"], runtime
        calls.append({"argv": runtime_argv, "exit_code": runtime_done.returncode})
        for module in ("reconcile_resolved_package", "reconciliation_archive"):
            done = subprocess.run(
                [python, "-I", "-m", "procurement_intelligence_lab.interfaces." + module, "--help"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            assert done.returncode == 0 and "usage:" in done.stdout and not done.stderr
            calls.append({"argv": done.args, "exit_code": done.returncode})
        manifest = root / "operation-manifest.json"
        manifest.write_text(
            json.dumps(
                run("domain_package", ["--source-profile", "retained-resolved-required-quantity"])
            )
        )
        legacy_manifest = root / "producer-manifest.json"
        legacy_manifest.write_text(json.dumps(run("domain_package", [])))
        context = json.loads((args.fixtures / "context.json").read_text())
        context["code_revision"] = args.code_revision
        context_path = root / "context.json"
        context_path.write_text(json.dumps(context))
        config = root / "config.toml"
        config.write_text(
            (args.fixtures / "procurement-config.toml")
            .read_text()
            .replace("1" * 40, args.code_revision)
        )
        registry = root / "registry.json"
        registry.write_bytes((args.fixtures / "procurement-registry.json").read_bytes())
        policy = root / "governing-policy.json"
        policy.write_bytes((args.fixtures / "governing-policy.json").read_bytes())
        authority = root / "authority.json"
        scope = root / "scope.json"
        scope.write_text(json.dumps(context["scope"]))
        base = [
            "--manifest",
            manifest,
            "--context",
            context_path,
            "--config",
            config,
            "--registry",
            registry,
            "--governing-policy",
            policy,
            "--authority",
            authority,
            "--as-of",
            "2026-10-19T00:00:00+00:00",
        ]

        def record(digest, artifact, i):
            return {
                "execution_digest": digest,
                "artifact_id": artifact["artifact_id"],
                "content_hash": artifact["content_hash"],
                "revision_id": f"r{i}",
                "supersedes_revision_ids": [],
                "source_role": "approved_bom_revision",
                "approval": {
                    "record_ref": f"synthetic-{i}",
                    "approved_at": "2026-10-19T00:00:00+00:00",
                },
                "effective_from": "2026-10-19T00:00:00+00:00",
                "effective_until": None,
                "document_at": "2026-10-19T00:00:00+00:00",
            }

        if not env.get("PIL_ASSERTION_ARCHIVE_DSN"):
            authority.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "producers": [
                            record(
                                "0" * 64, {"artifact_id": "synthetic", "content_hash": "1" * 64}, 0
                            )
                        ],
                    }
                )
            )
            env["PIL_ASSERTION_ARCHIVE_DSN"] = "postgresql://unused.invalid/no-driver"
            run(
                "reconcile_resolved_package",
                [*base, "--producer-digest", "0" * 64],
                "pil.infrastructure.archive_unavailable",
            )
            assert not runtime["storage_driver_available"], runtime
            result = {
                "probe": "passed",
                "mode": "base-missing-storage",
                "commands": calls,
                "cases": [],
            }
        else:
            for module in (
                "assertion_archive",
                "planned_execution_archive",
                "resolved_execution_archive",
                "reconciliation_archive",
            ):
                run(module, ["init"])
            producer_context = json.loads(args.producer_context.read_text())
            producer_context["code_revision"] = args.code_revision
            pc = root / "producer-context.json"
            pc.write_text(json.dumps(producer_context))
            producer_config = root / "producer-config.toml"
            original_config = (args.legacy_fixtures / "procurement-config.toml").read_text()
            producer_config.write_text(
                original_config.replace(
                    'application_version = "test-revision"',
                    'application_version = "' + args.code_revision + '"',
                )
            )
            candidate = root / "candidate.json"
            catalog = json.loads((args.legacy_fixtures / "candidate-snapshot.json").read_text())
            catalog["keys"] = ["GPU-A"]
            catalog["scope"] = context["scope"]
            candidate.write_text(json.dumps(catalog))
            producer_context["scope"] = context["scope"]
            pc.write_text(json.dumps(producer_context))
            pbase = [
                "--stop-after",
                "RESOLVE",
                "--manifest",
                legacy_manifest,
                "--context",
                pc,
                "--normalization-policy",
                args.normalization_policy.absolute(),
                "--registry",
                (args.legacy_fixtures / "procurement-registry.json").absolute(),
                "--config",
                producer_config,
                "--resolution-policy",
                (args.legacy_fixtures / "resolution-policy.json").absolute(),
                "--candidate-snapshot",
                candidate,
                "--archive",
            ]
            input_pins = {p.name: p.read_bytes().hex() for p in root.iterdir() if p.is_file()}
            retained_for_recovery = None
            recovery_sources = []
            for case in corpus["cases"]:
                changes = case["changes"]
                records = []
                sources = []
                command = base[:]
                for i, quantities in enumerate(case["producer_quantities"]):
                    source = root / (case["id"] + f"-{i}.xlsx")
                    sku = changes.get("sku", "GPU-A")
                    header = '<row r="1"><c r="A1"><v>SKU</v></c><c r="B1"><v>Description</v></c><c r="C1"><v>Quantity</v></c><c r="D1"><v>Unit Price</v></c></row>'
                    rows = "".join(
                        f'<row r="{j + 2}"><c r="A{j + 2}"><v>{sku}</v></c><c r="C{j + 2}"><v>{q if q is not None else ""}</v></c></row>'
                        for j, q in enumerate(quantities)
                    )
                    xml = (
                        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                        + header
                        + rows
                        + "</sheetData></worksheet>"
                    )
                    with (
                        ZipFile(args.source) as original,
                        ZipFile(source, "w", ZIP_DEFLATED) as output,
                    ):
                        for info in original.infolist():
                            data = (
                                xml.encode()
                                if info.filename == "xl/worksheets/sheet1.xml"
                                else original.read(info.filename)
                            )
                            output.writestr(info, data)
                        output.writestr(
                            "synthetic-case.txt",
                            case["id"] + ("-0" if changes.get("identical") else f"-{i}"),
                        )
                    if i and changes.get("identical"):
                        source.write_bytes(bytes.fromhex(sources[0]["bytes_hex"]))
                    body = run("execute_resolved_package", [source, *pbase])
                    key = body["execution_receipt"]["execution_digest"]
                    command += ["--producer-digest", key]
                    r = record(key, body["artifact"], i)
                    if changes.get("supersedes") and i == 1:
                        r["supersedes_revision_ids"] = ["r0"]
                    if changes.get("outside_supersedes"):
                        r["supersedes_revision_ids"] = ["outside-selected"]
                    if "approval" in changes:
                        r["approval"] = changes["approval"]
                    if "approved_at" in changes:
                        r["approval"]["approved_at"] = changes["approved_at"]
                    for field in ("effective_from", "effective_until"):
                        if field in changes:
                            r[field] = changes[field]
                    records.append(r)
                    sources.append(
                        {
                            "bytes_hex": source.read_bytes().hex(),
                            "sha256": sha256(source.read_bytes()).hexdigest(),
                            "worksheet_xml": xml,
                            "producer_digest": key,
                        }
                    )
                authority.write_text(json.dumps({"schema_version": "1.0", "producers": records}))
                raw = authority.read_bytes()
                if error := changes.get("error"):
                    actual = run("reconcile_resolved_package", command, error)
                    examples.append(
                        {
                            "id": case["id"],
                            "sources": sources,
                            "authority": json.loads(raw),
                            "authority_raw_json_hex": raw.hex(),
                            "expected": case,
                            "actual_error": actual,
                        }
                    )
                    continue
                body = run("reconcile_resolved_package", [*command, "--archive"])
                current = body["current_operation"]
                states, decisions = current["states"], current["decisions"]
                value = states[0]["attributes"][0]["value"] if states else None
                assert value == case["expected_value"], (case["id"], value)
                assert sum(len(d["governing"]) for d in decisions) == case["expected_governing"], (
                    case["id"]
                )
                assert sum(len(d["losing"]) for d in decisions) == case["expected_losing"], case[
                    "id"
                ]
                assert sum(e["status"] == "SUCCEEDED" for e in current["entries"]) == 1
                assert not current["package_execution_complete"]
                assert all(
                    s["freshness"] == "unknown"
                    and s["scope"]["version"] != context["scope"]["version"]
                    for s in states
                )
                authority.write_text(
                    json.dumps(
                        {"schema_version": "1.0", "producers": list(reversed(records))}, indent=2
                    )
                )
                # Reverse the explicit producer argument order as well as metadata order.
                prefix = command[: len(base)]
                ids = command[len(base) :]
                reversed_ids = [v for i in range(len(ids) - 2, -1, -2) for v in ids[i : i + 2]]
                retry = run("reconcile_resolved_package", [*prefix, *reversed_ids, "--archive"])
                assert retry["current_operation"]["execution_digest"] == current["execution_digest"]
                assert retry["archive_receipt"] == body["archive_receipt"]
                assert retry["first_retained_operation"] == body["first_retained_operation"]
                assert (
                    retry["current_operation"]["authority"]["raw_sha256"]
                    != current["authority"]["raw_sha256"]
                )
                examples.append(
                    {
                        "id": case["id"],
                        "sources": sources,
                        "authority": json.loads(raw),
                        "authority_raw_json_hex": raw.hex(),
                        "expected": case,
                        "actual": {
                            "value": value,
                            "decisions": decisions,
                            "states": states,
                            "domain_audit": current["domain_audit"],
                        },
                        "permutation_and_raw_audit": "passed",
                    }
                )
                if case["id"] == "shared":
                    retained_for_recovery = body
                    recovery_sources = sources
            assert retained_for_recovery
            key = retained_for_recovery["current_operation"]["execution_digest"]
            for path in root.iterdir():
                if path != scope and path.is_file():
                    path.unlink()
            rargs = ["--scope", scope, "--execution-digest", key]
            shown = run("reconciliation_archive", ["show", *rargs])
            assert shown["current_operation"] == retained_for_recovery["first_retained_operation"]
            run("reconciliation_archive", ["history", "--scope", scope])
            content_manifest = run("reconciliation_archive", ["content-manifest", *rargs])
            assert content_manifest["original_source_bytes_included"] is False
            export = root / "result.json"
            run("reconciliation_archive", ["export", *rargs, "--output", export])
            run(
                "reconciliation_archive",
                ["export", *rargs, "--output", export],
                "pil.input.archive_contract_invalid",
            )
            for i, source in enumerate(recovery_sources):
                output = root / f"recovered-{i}.xlsx"
                run(
                    "resolved_execution_archive",
                    [
                        "content",
                        "--scope",
                        scope,
                        "--execution-digest",
                        source["producer_digest"],
                        "--output",
                        output,
                    ],
                )
                assert output.read_bytes() == bytes.fromhex(source["bytes_hex"])
            result = {
                "probe": "passed",
                "mode": "storage",
                "input_pins_hex": input_pins,
                "case_count": len(examples),
                "case_errors": 0,
                "recovery": {
                    "input_files_deleted": True,
                    "result_export_sha256": sha256(export.read_bytes()).hexdigest(),
                    "companion_sources_exact": len(recovery_sources),
                },
                "cases": examples,
                "commands": calls,
            }
        result.update(
            {
                "python": python,
                "installed_runtime": runtime,
                "controller_python": platform.python_version(),
                "code_revision": args.code_revision,
                "wheel_sha256": sha256(args.wheel.read_bytes()).hexdigest(),
                "population": corpus["population"],
            }
        )
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {
                    k: v
                    for k, v in result.items()
                    if k not in ("commands", "cases", "input_pins_hex")
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
