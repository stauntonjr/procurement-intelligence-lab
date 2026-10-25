"""Compare complete installed legacy public results with identical paths, pins and clock.

Run under the development environment with baseline/candidate installed Python paths,
repository root, task-owned base DSN file and output path. DSNs never enter receipts.
The injected public-main clock is fixed only to make complete receipt equality observable.
"""

import json
import os
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


def main():
    baseline, candidate, repo, dsn_file, output_path = (Path(x).absolute() for x in sys.argv[1:])
    dsn = dsn_file.read_text().strip()
    wrapper = """import importlib,sys
from datetime import UTC,datetime
name=sys.argv.pop(1)
m=importlib.import_module('procurement_intelligence_lab.interfaces.'+name)
class Clock:
    @staticmethod
    def now(tz=None): return datetime(2026,10,19,0,0,10,tzinfo=UTC)
    fromisoformat=staticmethod(datetime.fromisoformat)
if hasattr(m,'datetime'): m.datetime=Clock
raise SystemExit(m.main())
"""
    results = []
    with tempfile.TemporaryDirectory(prefix="pil-239-legacy-") as folder:
        root = Path(folder)
        source = root / "source.xlsx"
        source.write_bytes(
            (
                repo / "src/procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx"
            ).read_bytes()
        )
        context = json.loads((repo / "tests/fixtures/bom-stages/context.json").read_text())
        context["code_revision"] = "a8de65db7ae6b6192a937ae930859d1b205be5aa"
        ctx = root / "context.json"
        ctx.write_text(json.dumps(context))
        scope = root / "scope.json"
        scope.write_text(json.dumps(context["scope"]))
        registry = root / "registry.json"
        reg = json.loads(
            (repo / "tests/fixtures/resolved-execution/procurement-registry.json").read_text()
        )
        for descriptor in reg["implementations"]:
            descriptor["required_settings"] = descriptor["optional_settings"] = []
        registry.write_text(json.dumps(reg))
        config = root / "config.toml"
        config.write_text(
            (repo / "tests/fixtures/resolved-execution/procurement-config.toml")
            .read_text()
            .replace(
                'application_version = "test-revision"',
                'application_version = "' + context["code_revision"] + '"',
            )
            .replace('endpoint_ref = "fixture://offline"', "")
        )
        manifest = root / "manifest.json"
        norm = repo / "tests/fixtures/bom-stages/normalization-policy.json"
        arrival = root / "arrival.json"
        arrival.write_text(
            json.dumps(
                {
                    "event_id": "legacy-exact",
                    "expected_content_hash": sha256(source.read_bytes()).hexdigest(),
                    "expected_byte_length": source.stat().st_size,
                    "announced_at": context["captured_at"],
                }
            )
        )
        for python in (baseline, candidate):
            schema = "pil_239_legacy_" + uuid4().hex
            with psycopg.connect(dsn, autocommit=True) as conn:
                conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env["PIL_ASSERTION_ARCHIVE_DSN"] = make_conninfo(
                dsn, options=f"-c search_path={schema}"
            )
            records = []

            def run(module, argv, *, python=python, env=env, records=records):
                command = [str(python), "-I", "-c", wrapper, module, *map(str, argv)]
                done = subprocess.run(
                    command, cwd=root, env=env, capture_output=True, text=True, check=False
                )
                assert done.returncode == 0 and not done.stderr, done.stderr
                body = json.loads(done.stdout)
                records.append({"module": module, "args": list(map(str, argv)), "result": body})
                return body

            try:
                manifest.write_text(json.dumps(run("domain_package", [])))
                run("bom_stages", [source, "--context", ctx])
                run(
                    "bom_stages",
                    [source, "--context", ctx, "--normalization-policy", norm, "--assertions"],
                )
                for module in (
                    "assertion_archive",
                    "planned_execution_archive",
                    "resolved_execution_archive",
                    "processing_jobs",
                ):
                    run(module, ["init"])
                common = [
                    source,
                    "--manifest",
                    manifest,
                    "--registry",
                    registry,
                    "--config",
                    config,
                    "--context",
                    ctx,
                    "--normalization-policy",
                    norm,
                ]
                five = run("execute_package", [*common, "--stop-after", "ASSERT", "--archive"])
                six = run(
                    "execute_resolved_package",
                    [
                        *common,
                        "--stop-after",
                        "RESOLVE",
                        "--archive",
                        "--resolution-policy",
                        repo / "tests/fixtures/resolved-execution/resolution-policy.json",
                        "--candidate-snapshot",
                        repo / "tests/fixtures/resolved-execution/candidate-snapshot.json",
                    ],
                )
                run(
                    "assertion_archive",
                    [
                        "show",
                        "--scope",
                        scope,
                        "--snapshot-id",
                        five["archive_receipt"]["snapshot_id"],
                    ],
                )
                for module, body in (
                    ("planned_execution_archive", five),
                    ("resolved_execution_archive", six),
                ):
                    args = [
                        "--scope",
                        scope,
                        "--execution-digest",
                        body["execution_receipt"]["execution_digest"],
                    ]
                    run(module, ["show", *args])
                    export = root / (module + ".json")
                    run(
                        module,
                        [
                            "export" if module == "resolved_execution_archive" else "content",
                            *args,
                            "--output",
                            export,
                        ],
                    )
                    records.append(
                        {
                            "module": module
                            + (
                                ":full-codec-export"
                                if module == "resolved_execution_archive"
                                else ":original-source-content"
                            ),
                            "bytes_hex": export.read_bytes().hex(),
                        }
                    )
                    export.unlink()
                codec_script = """import json,os,sys
from procurement_intelligence_lab.bootstrap import archive_codec,build_planned_execution_archive_reader
from procurement_intelligence_lab.platform.semantics.scope import StateScope
s=json.load(open(sys.argv[1]))
r=build_planned_execution_archive_reader(os.environ['PIL_ASSERTION_ARCHIVE_DSN']).show(StateScope(**s),sys.argv[2]).retained
print(archive_codec().dumps(r))
"""
                done = subprocess.run(
                    [
                        str(python),
                        "-I",
                        "-c",
                        codec_script,
                        str(scope),
                        five["execution_receipt"]["execution_digest"],
                    ],
                    cwd=root,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                records.append(
                    {
                        "module": "planned-archive:full-codec",
                        "bytes_hex": done.stdout.strip().encode().hex(),
                    }
                )
                job = run(
                    "processing_jobs",
                    ["submit", *common, "--arrival", arrival, "--idempotency-key", "legacy-exact"],
                )
                jargs = ["--scope", scope, "--job-id", job["job_id"]]
                run(
                    "processing_jobs",
                    [
                        "run",
                        *jargs,
                        "--command-key",
                        "first",
                        "--actor",
                        "synthetic",
                        "--expected-version",
                        "1",
                    ],
                )
                for op in ("show", "result", "history"):
                    run("processing_jobs", [op, *jargs])
                results.append(records)
            finally:
                with psycopg.connect(dsn, autocommit=True) as conn:
                    conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
    assert results[0] == results[1], "complete legacy public results or codec exports differ"
    canonical = json.dumps(results[0], sort_keys=True, separators=(",", ":")).encode()
    receipt = {
        "full_json_and_codec_exactly_equal": True,
        "operations": len(results[0]),
        "sha256": sha256(canonical).hexdigest(),
        "clock": "fixed public-main clock 2026-10-19T00:00:10Z; no fields removed",
        "source_revision_pin": context["code_revision"],
        "baseline_python": str(baseline),
        "candidate_python": str(candidate),
    }
    output_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
