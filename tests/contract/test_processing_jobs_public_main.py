"""Actual public-main acknowledgement loss and killed-process restart evidence."""

import json
import os
import select
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.interfaces import processing_jobs
from procurement_intelligence_lab.platform.processing.errors import JobUnavailableError
from tests.integration.test_planned_execution_archive_cli import run, success
from tests.integration.test_processing_jobs_cli import initialized, scoped, start_args


@pytest.mark.parametrize(
    "method,status",
    [
        ("submit", "SUBMITTED"),
        ("start", "RUNNING"),
        ("fail", "FAILED"),
        ("complete", "SUCCEEDED"),
        ("abandon", "ABANDONED"),
    ],
)
def test_commit_then_lost_ack_public_main_recovers_actual_state(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    method: str,
    status: str,
):
    args, scope, _, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    jobs = bootstrap.build_local_prefix_jobs(archive_dsn)
    command = start_args(scope, job_id)
    if method == "submit":
        command = args.copy()
        command[-1] = "different-request"
    elif method == "fail":
        Path(args[1]).unlink()
    elif method == "abandon":
        from procurement_intelligence_lab.platform.semantics.scope import StateScope
        from tests.contract.test_postgres_local_prefix_jobs import first

        view = jobs.load(StateScope(**json.loads(scope.read_text())), job_id)
        claim = jobs.start(first(view.definition), now=view.latest.transition.recorded_at)
        command = [
            "abandon",
            *scoped(scope, job_id),
            "--command-key",
            "abandon",
            "--actor",
            "developer",
            "--expected-version",
            "2",
            "--attempt-id",
            claim.token.attempt_id,
            "--reason",
            "unresolved process",
        ]
    original = getattr(jobs, method)

    def lost(*values: Any, **kwargs: Any) -> Any:
        original(*values, **kwargs)
        raise JobUnavailableError("acknowledgement unavailable")

    monkeypatch.setattr(jobs, method, lost)

    def built(_: str):
        return jobs

    monkeypatch.setattr(processing_jobs, "build_local_prefix_jobs", built)
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setattr(sys, "argv", ["processing_jobs", *command])
    assert processing_jobs.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["code"] == "pil.infrastructure.local_prefix_job_unavailable"
    if method == "submit":
        job_id = success(run("processing_jobs", command, archive_dsn))["job_id"]
    error = json.loads(captured.err)
    assert error["job_id"] == job_id
    assert error["scope"] == json.loads(scope.read_text())
    assert "status" not in error and "processing_complete" not in error
    if method in ("submit", "start"):
        assert "attempt_id" not in error
    else:
        assert error["attempt_id"]
    shown = success(run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn))
    assert shown["status"] == status
    assert shown["processing_complete"] == (status == "SUCCEEDED")


@pytest.mark.parametrize("boundary,status", [("start", "RUNNING"), ("complete", "SUCCEEDED")])
def test_killed_public_process_retains_exact_durable_boundary(
    archive_dsn: str, tmp_path: Path, boundary: str, status: str
):
    _, scope, content, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    harness = tmp_path / "kill_boundary.py"
    harness.write_text("""import os,sys
from procurement_intelligence_lab.interfaces import processing_jobs as cli
boundary=sys.argv.pop(1); signal=int(sys.argv.pop(1)); hold=int(sys.argv.pop(1))
factory=cli.build_local_prefix_jobs
def build(dsn):
    jobs=factory(dsn); original=getattr(jobs,boundary)
    def retained(*args,**kwargs):
        result=original(*args,**kwargs)
        os.write(signal,b"retained\\n")
        os.read(hold,1)
        return result
    setattr(jobs,boundary,retained)
    return jobs
cli.build_local_prefix_jobs=build
raise SystemExit(cli.main())
""")
    ready_read, ready_write = os.pipe()
    hold_read, hold_write = os.pipe()
    child = subprocess.Popen(
        [
            sys.executable,
            str(harness),
            boundary,
            str(ready_write),
            str(hold_read),
            *start_args(scope, job_id),
        ],
        env={**os.environ, "PIL_ASSERTION_ARCHIVE_DSN": archive_dsn},
        pass_fds=(ready_write, hold_read),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    os.close(ready_write)
    os.close(hold_read)
    try:
        assert select.select([ready_read], [], [], 15)[0], "child did not reach retained boundary"
        assert os.read(ready_read, 64) == b"retained\n"
        child.terminate()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
        for fd in (ready_read, hold_write):
            os.close(fd)
    shown = success(run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn))
    assert shown["status"] == status
    if boundary == "complete":
        output = tmp_path / "recovered.xlsx"
        success(
            run(
                "processing_jobs",
                ["content", *scoped(scope, job_id), "--output", str(output)],
                archive_dsn,
            )
        )
        assert output.read_bytes() == content
    else:
        attempt = shown["attempt"]["attempt_id"]
        success(
            run(
                "processing_jobs",
                [
                    "abandon",
                    *scoped(scope, job_id),
                    "--command-key",
                    "abandon",
                    "--actor",
                    "developer",
                    "--expected-version",
                    "2",
                    "--attempt-id",
                    attempt,
                    "--reason",
                    "terminated local child",
                ],
                archive_dsn,
            )
        )
        done = success(
            run(
                "processing_jobs",
                start_args(scope, job_id, kind="retry", key="retry", version=3),
                archive_dsn,
            )
        )
        assert done["status"] == "SUCCEEDED"


@pytest.mark.parametrize("kind", ["run", "retry", "result"])
def test_retained_archive_outage_preserves_known_recovery_ids(
    archive_dsn: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
):
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveUnavailableError

    args, scope, content, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    command = start_args(scope, job_id)
    if kind == "retry":
        source = Path(args[1])
        source.unlink()
        assert run("processing_jobs", command, archive_dsn).returncode == 2
        failed = success(run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn))
        assert failed["status"] == "FAILED"
        source.write_bytes(content)
        command = start_args(scope, job_id, kind="retry", key="retry", version=3)
    elif kind == "result":
        success(run("processing_jobs", command, archive_dsn))
        command = ["result", *scoped(scope, job_id)]

    class UnavailableReader:
        def show(self, *values: Any, **kwargs: Any) -> Any:
            raise ArchiveUnavailableError("retained archive temporarily unavailable")

    def unavailable_reader(_: str):
        return UnavailableReader()

    monkeypatch.setattr(
        processing_jobs, "build_planned_execution_archive_reader", unavailable_reader
    )
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", archive_dsn)
    monkeypatch.setattr(sys, "argv", ["processing_jobs", *command])
    assert processing_jobs.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    error = json.loads(captured.err)
    assert error["code"] == "pil.infrastructure.archive_unavailable"
    assert error["scope"] == json.loads(scope.read_text())
    assert error["job_id"] == job_id
    assert "status" not in error and "processing_complete" not in error
    shown = success(run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn))
    assert shown["status"] == "SUCCEEDED"
    assert error["attempt_id"] == shown["attempt"]["attempt_id"]
    assert shown["version"] == (5 if kind == "retry" else 3)
