"""Qualify installed local jobs using public callers and isolated synthetic inputs."""

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    original, original_context, original_policy, original_registry, original_config = (
        Path(x).absolute() for x in sys.argv[1:6]
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    with TemporaryDirectory(prefix="local-prefix-jobs-probe-", dir=Path.cwd()) as folder:
        root = Path(folder)
        source = root / "source.xlsx"
        content = original.read_bytes()
        source.write_bytes(content)

        def run(module: str, args: list[str], code: str | None = None):
            done = subprocess.run(
                [sys.executable, "-m", "procurement_intelligence_lab.interfaces." + module, *args],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if code is not None:
                if done.returncode != 2 or done.stdout or json.loads(done.stderr)["code"] != code:
                    raise RuntimeError("installed local job failed safe rejection: " + done.stderr)
                return json.loads(done.stderr)
            if done.returncode or done.stderr:
                raise RuntimeError("installed local job command failed: " + done.stderr)
            return json.loads(done.stdout)

        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(run("domain_package", [])))
        context = root / "context.json"
        context.write_bytes(original_context.read_bytes())
        policy = root / "policy.json"
        policy.write_bytes(original_policy.read_bytes())
        registry = root / "registry.json"
        descriptors = json.loads(original_registry.read_text())
        for descriptor in descriptors["implementations"]:
            descriptor["required_settings"] = []
            descriptor["optional_settings"] = []
        registry.write_text(json.dumps(descriptors))
        config = root / "config.toml"
        config.write_text(
            original_config.read_text().replace('endpoint_ref = "fixture://offline"', "")
        )
        arrival = root / "arrival.json"
        q = json.loads(context.read_text())
        arrival.write_text(
            json.dumps(
                {
                    "event_id": "installed-arrival",
                    "expected_content_hash": sha256(content).hexdigest(),
                    "expected_byte_length": len(content),
                    "announced_at": q["captured_at"],
                }
            )
        )
        scope = root / "scope.json"
        scope.write_text(json.dumps(q["scope"]))
        inputs = [
            str(source),
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
            "--config",
            str(config),
            "--context",
            str(context),
            "--normalization-policy",
            str(policy),
        ]
        submit = [
            "submit",
            *inputs,
            "--arrival",
            str(arrival),
            "--idempotency-key",
            "installed-request",
        ]
        if env.get("PIL_LOCAL_PREFIX_JOBS_EXPECT_MISSING_DRIVER") == "1":
            source.unlink()
            env["PIL_ASSERTION_ARCHIVE_DSN"] = "postgresql://invalid.local/unused"
            error = run(
                "processing_jobs", submit, "pil.infrastructure.local_prefix_job_unavailable"
            )
            if "storage extra" not in error["message"]:
                raise RuntimeError("base wheel did not prove local-job missing-driver boundary")
            print(json.dumps({"local_prefix_jobs_missing_driver": "passed"}))
            return 0
        if not env.get("PIL_ASSERTION_ARCHIVE_DSN"):
            raise RuntimeError("installed job probe requires isolated storage DSN")
        run("assertion_archive", ["init"])
        run("planned_execution_archive", ["init"])
        run("processing_jobs", submit, "pil.infrastructure.local_prefix_job_unavailable")
        run("processing_jobs", ["init"])
        # First archive retention is a separate completed invocation, not this job attempt.
        prior = run("execute_package", [*inputs, "--stop-after", "ASSERT", "--archive"])
        admitted = run("processing_jobs", submit)
        job_id = admitted["job_id"]
        if admitted["status"] != "SUBMITTED" or admitted["processing_complete"]:
            raise RuntimeError("submission fabricated processing completion")

        def scoped(identifier: str):
            return ["--scope", str(scope), "--job-id", identifier]

        def start(identifier: str, key: str, version: int, kind: str = "run"):
            return [
                kind,
                *scoped(identifier),
                "--command-key",
                key,
                "--actor",
                "installed-developer",
                "--expected-version",
                str(version),
            ]

        if run("processing_jobs", submit)["job_journal_receipt"] != admitted["job_journal_receipt"]:
            raise RuntimeError("installed submission replay changed acknowledgement")
        source.write_bytes(content + b"changed")
        run("processing_jobs", start(job_id, "first", 1), "pil.input.local_prefix_job_invalid")
        if run("processing_jobs", ["show", *scoped(job_id)])["status"] != "FAILED":
            raise RuntimeError("observed source mismatch was not recorded as failure")
        source.write_bytes(content)
        first = run("processing_jobs", start(job_id, "retry", 3, "retry"))
        current = first["attempt_execution_receipt"]
        retained = first["retained_execution_receipt"]
        if (
            current["receipt_digest"] == retained["receipt_digest"]
            or current["execution_digest"] != retained["execution_digest"]
        ):
            raise RuntimeError("installed result lost current versus first retained distinction")
        if retained["receipt_digest"] != prior["retained_execution_receipt"]["receipt_digest"]:
            raise RuntimeError("job overwrote first retained execution")
        if (
            len(first["transformations"]) != 5
            or len(current["entries"]) != 12
            or any(e["status"] != "NOT_EXECUTED" for e in current["entries"][5:])
        ):
            raise RuntimeError("installed job lost actual-prefix boundary")
        # Test-only installed public-main harness exits just after durable STARTED.
        second_submit = submit.copy()
        second_submit[-1] = "abandon-request"
        second = run("processing_jobs", second_submit)
        second_id = second["job_id"]
        harness = """import os
from procurement_intelligence_lab.interfaces import processing_jobs as cli
factory=cli.build_local_prefix_jobs
def build(dsn):
    jobs=factory(dsn); original=jobs.start
    def start(*args,**kwargs):
        original(*args,**kwargs)
        os._exit(86)
    jobs.start=start
    return jobs
cli.build_local_prefix_jobs=build
raise SystemExit(cli.main())
"""
        crashed = subprocess.run(
            [sys.executable, "-c", harness, *start(second_id, "first", 1)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if crashed.returncode != 86 or crashed.stdout or crashed.stderr:
            raise RuntimeError("installed child did not reach durable STARTED")
        running = run("processing_jobs", ["show", *scoped(second_id)])
        if running["status"] != "RUNNING":
            raise RuntimeError("restart invented a terminal attempt outcome")
        abandon = [
            "abandon",
            *scoped(second_id),
            "--command-key",
            "abandon",
            "--actor",
            "installed-developer",
            "--expected-version",
            "2",
            "--attempt-id",
            running["attempt"]["attempt_id"],
            "--reason",
            "terminated test child",
        ]
        run("processing_jobs", abandon)
        rerun = run("processing_jobs", start(second_id, "retry", 3, "retry"))
        if rerun["archive_receipt"] != first["archive_receipt"]:
            raise RuntimeError("identical explicit retry duplicated original evidence")
        late = run("processing_jobs", abandon)
        if (
            late["status"] != "SUCCEEDED"
            or late["receipt_is_current"]
            or late["historical_command_receipt"]["status"] != "ABANDONED"
        ):
            raise RuntimeError("late abandon replay changed current successful attempt")
        for path in (source, manifest, context, policy, registry, config, arrival):
            path.unlink()
        replay = run("processing_jobs", start(job_id, "retry", 3, "retry"))
        if not replay["historical"] or replay["attempt_execution_receipt"] != current:
            raise RuntimeError("installed command replay executed or changed its result")
        recovered = run("processing_jobs", ["result", *scoped(job_id)])
        if (
            recovered["attempt_execution_receipt"] != current
            or recovered["retained_execution_receipt"] != retained
        ):
            raise RuntimeError("installed source/config-free recovery changed evidence")
        page = run("processing_jobs", ["history", *scoped(job_id), "--limit", "2"])
        if not page["has_more"] or page["next_after_sequence"] != 2:
            raise RuntimeError("installed history did not retain transition multiplicity")
        output = root / "export.xlsx"
        run("processing_jobs", ["content", *scoped(job_id), "--output", str(output)])
        if output.read_bytes() != content:
            raise RuntimeError("installed job export changed original bytes")
        old = run(
            "assertion_archive",
            [
                "show",
                "--scope",
                str(scope),
                "--snapshot-id",
                first["archive_receipt"]["snapshot_id"],
            ],
        )
        if old["assertion_batch"] != first["assertion_batch"]:
            raise RuntimeError("installed local job altered legacy source assertions")
        print(
            json.dumps(
                {
                    "local_prefix_jobs_smoke": "passed",
                    "actual_stages": 5,
                    "logical_stages": 12,
                    "source_and_config_deleted": True,
                    "current_and_retained_distinct": True,
                    "explicit_retry_and_abandonment": True,
                    "restart_result_export_equal": True,
                    "legacy_assertions_equal": True,
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
