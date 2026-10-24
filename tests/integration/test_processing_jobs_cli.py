"""Real public commands, restart recovery and strict developer-boundary errors."""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from tests.integration.test_execute_package_cli import inputs
from tests.integration.test_planned_execution_archive_cli import failure, run, success

pytestmark = pytest.mark.integration


def submission_inputs(tmp_path: Path):
    args = inputs(tmp_path)
    args = args[: args.index("--stop-after")] + args[args.index("--stop-after") + 2 :]
    # New jobs retain no opaque settings, including planning-only later stages.
    registry = tmp_path / "registry.json"
    value = json.loads(Path(args[args.index("--registry") + 1]).read_text())
    for descriptor in value["implementations"]:
        descriptor["required_settings"] = []
        descriptor["optional_settings"] = []
    registry.write_text(json.dumps(value))
    args[args.index("--registry") + 1] = str(registry)
    config = tmp_path / "config.toml"
    config.write_text(
        Path(args[args.index("--config") + 1])
        .read_text()
        .replace('endpoint_ref = "fixture://offline"', "")
    )
    args[args.index("--config") + 1] = str(config)
    policy = tmp_path / "policy.json"
    policy.write_bytes(Path(args[args.index("--normalization-policy") + 1]).read_bytes())
    args[args.index("--normalization-policy") + 1] = str(policy)
    context = json.loads(Path(args[args.index("--context") + 1]).read_text())
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(context["scope"]))
    arrival = tmp_path / "arrival.json"
    content = Path(args[0]).read_bytes()
    arrival.write_text(
        json.dumps(
            {
                "event_id": "arrival-1",
                "expected_content_hash": sha256(content).hexdigest(),
                "expected_byte_length": len(content),
                "announced_at": context["captured_at"],
            }
        )
    )
    return (
        ["submit", *args, "--arrival", str(arrival), "--idempotency-key", "request-1"],
        scope,
        content,
    )


def initialized(tmp_path: Path, dsn: str):
    args, scope, content = submission_inputs(tmp_path)
    success(run("assertion_archive", ["init"], dsn))
    success(run("planned_execution_archive", ["init"], dsn))
    success(run("processing_jobs", ["init"], dsn))
    submitted = success(run("processing_jobs", args, dsn))
    return args, scope, content, submitted


def scoped(scope: Path, job_id: str):
    return ["--scope", str(scope), "--job-id", job_id]


def start_args(
    scope: Path, job_id: str, *, key: str = "start", version: int = 1, kind: str = "run"
):
    return [
        kind,
        *scoped(scope, job_id),
        "--command-key",
        key,
        "--actor",
        "developer",
        "--expected-version",
        str(version),
    ]


def test_actual_submit_run_delete_inputs_restart_export_and_old_reader(
    archive_dsn: str, tmp_path: Path
):
    args, scope, content, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    assert submitted["status"] == "SUBMITTED" and not submitted["processing_complete"]
    assert (
        success(run("processing_jobs", args, archive_dsn))["job_journal_receipt"]
        == submitted["job_journal_receipt"]
    )
    first = success(run("processing_jobs", start_args(scope, job_id), archive_dsn))
    assert first["status"] == "SUCCEEDED" and first["processing_complete"]
    assert not first["historical"] and first["command_receipt"]["version"] == 2
    receipt = first["attempt_execution_receipt"]
    assert len(receipt["entries"]) == 12 and len(first["transformations"]) == 5
    assert all(r["status"] == "NOT_EXECUTED" for r in receipt["entries"][5:])
    assert "durable_run_journal_updated" not in receipt and "result_cache_updated" not in receipt
    for item in args:
        p = Path(item)
        if p.is_file() and p != scope:
            p.unlink()
    replay = success(run("processing_jobs", start_args(scope, job_id), archive_dsn))
    assert replay["historical"] and replay["command_receipt"] == first["command_receipt"]
    result = success(run("processing_jobs", ["result", *scoped(scope, job_id)], archive_dsn))
    assert result["attempt_execution_receipt"] == receipt
    assert result["retained_execution_receipt"] == first["retained_execution_receipt"]
    page = success(
        run("processing_jobs", ["history", *scoped(scope, job_id), "--limit", "2"], archive_dsn)
    )
    assert len(page["receipts"]) == 2 and page["has_more"] and page["next_after_sequence"] == 2
    tail = success(
        run(
            "processing_jobs",
            ["history", *scoped(scope, job_id), "--after-sequence", "2"],
            archive_dsn,
        )
    )
    assert len(tail["receipts"]) == 1 and not tail["has_more"]
    export = tmp_path / "export.xlsx"
    command = ["content", *scoped(scope, job_id), "--output", str(export)]
    success(run("processing_jobs", command, archive_dsn))
    assert export.read_bytes() == content
    failure(run("processing_jobs", command, archive_dsn), "pil.input.archive_contract_invalid")
    old = success(
        run(
            "assertion_archive",
            [
                "show",
                "--scope",
                str(scope),
                "--snapshot-id",
                first["archive_receipt"]["snapshot_id"],
            ],
            archive_dsn,
        )
    )
    assert old["assertion_batch"] == first["assertion_batch"]
    data = json.loads(scope.read_text())
    data["project_id"] = "foreign"
    scope.write_text(json.dumps(data))
    failure(
        run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn),
        "pil.input.local_prefix_job_not_found",
    )


def test_changed_source_failure_and_manual_retry(archive_dsn: str, tmp_path: Path):
    args, scope, content, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    source = Path(args[1])
    source.write_bytes(content + b"changed")
    failure(
        run("processing_jobs", start_args(scope, job_id), archive_dsn),
        "pil.input.local_prefix_job_invalid",
    )
    assert (
        success(run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn))["status"]
        == "FAILED"
    )
    source.write_bytes(content)
    done = success(
        run(
            "processing_jobs",
            start_args(scope, job_id, key="retry", version=3, kind="retry"),
            archive_dsn,
        )
    )
    assert done["status"] == "SUCCEEDED"
    failure(
        run(
            "processing_jobs",
            start_args(scope, job_id, key="again", version=5, kind="retry"),
            archive_dsn,
        ),
        "pil.policy.local_prefix_job_conflict",
    )


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["unknown"],
        ["show"],
        ["history", "--scope", "missing", "--job-id", "bad", "--limit", "201"],
        ["history", "--scope", "missing", "--job-id", "bad", "--after-sequence", "-1"],
        [
            "run",
            "--scope",
            "missing",
            "--job-id",
            "bad",
            "--command-key",
            "x",
            "--actor",
            "developer",
            "--expected-version",
            "1.5",
        ],
    ],
)
def test_bad_arguments_are_safe_before_storage(args: list[str]):
    failure(run("processing_jobs", args, ""), "pil.input.local_prefix_job_invalid")


@pytest.mark.parametrize(
    "mode",
    [
        "duplicate",
        "unicode",
        "nonfinite",
        "future",
        "negative",
        "fractional",
        "boolean",
        "hash",
        "extra",
        "oversize",
        "settings",
    ],
)
def test_malformed_admission_fails_without_capture_or_journal(
    archive_dsn: str, tmp_path: Path, mode: str
):
    args, _scope, _ = submission_inputs(tmp_path)
    arrival = Path(args[args.index("--arrival") + 1])
    value = json.loads(arrival.read_text())
    expected = "pil.input.local_prefix_job_invalid"
    if mode == "duplicate":
        arrival.write_text('{"event_id":"one","event_id":"two"}')
    elif mode == "unicode":
        arrival.write_bytes(b"\xff")
    elif mode == "nonfinite":
        arrival.write_text('{"expected_byte_length":NaN}')
    elif mode == "oversize":
        arrival.write_bytes(b" " * 32769)
        expected = "pil.input.package_execution_invalid"
    elif mode == "settings":
        config = Path(args[args.index("--config") + 1])
        config.write_text(
            config.read_text().replace(
                "[selections.settings]", '[selections.settings]\nsecret = "not-retained"'
            )
        )
        # Planner rejects undeclared settings before any source access.
        expected = "pil.input.package_planning_invalid"
    else:
        field, changed = {
            "future": ("announced_at", "2999-01-01T00:00:00+00:00"),
            "negative": ("expected_byte_length", -1),
            "fractional": ("expected_byte_length", 1.5),
            "boolean": ("expected_byte_length", True),
            "hash": ("expected_content_hash", "A" * 64),
            "extra": ("unexpected", "field"),
        }[mode]
        value[field] = changed
        arrival.write_text(json.dumps(value))
    Path(args[1]).unlink()
    failure(run("processing_jobs", args, archive_dsn), expected)


def test_corrupt_linked_evidence_is_never_public_success_or_empty(archive_dsn: str, tmp_path: Path):
    import psycopg

    _, scope, _, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    success(run("processing_jobs", start_args(scope, job_id), archive_dsn))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute("ALTER TABLE pil_planned_executions DISABLE TRIGGER USER")
        conn.execute("UPDATE pil_planned_executions SET payload_sha256=repeat('0',64)")
    for kind in ("show", "result", "history", "content"):
        args = [kind, *scoped(scope, job_id)]
        if kind == "content":
            args += ["--output", str(tmp_path / "must-not-exist.xlsx")]
        failure(
            run("processing_jobs", args, archive_dsn),
            "pil.infrastructure.local_prefix_job_integrity_invalid",
        )
    assert not (tmp_path / "must-not-exist.xlsx").exists()


def test_public_start_key_cannot_change_intent_actor_or_version(archive_dsn: str, tmp_path: Path):
    _, scope, _, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    done = success(run("processing_jobs", start_args(scope, job_id), archive_dsn))
    altered = [start_args(scope, job_id, kind="retry"), start_args(scope, job_id, version=3)]
    actor = start_args(scope, job_id)
    actor[actor.index("--actor") + 1] = "different-developer"
    altered.append(actor)
    for command in altered:
        failure(
            run("processing_jobs", command, archive_dsn), "pil.policy.local_prefix_job_conflict"
        )
    shown = success(run("processing_jobs", ["show", *scoped(scope, job_id)], archive_dsn))
    assert shown["job_journal_receipt"] == done["job_journal_receipt"]


def test_stale_head_is_public_integrity_failure(archive_dsn: str, tmp_path: Path):
    import psycopg

    _, scope, _, submitted = initialized(tmp_path, archive_dsn)
    job_id = submitted["job_id"]
    with psycopg.connect(archive_dsn) as conn:
        prior = conn.execute(
            "SELECT sequence,version,status,attempt_id,fence,recorded_at FROM pil_local_prefix_job_heads"
        ).fetchone()
    assert prior is not None
    success(run("processing_jobs", start_args(scope, job_id), archive_dsn))
    with psycopg.connect(archive_dsn) as conn:
        conn.execute(
            "UPDATE pil_local_prefix_job_heads SET sequence=%s,version=%s,status=%s,attempt_id=%s,fence=%s,recorded_at=%s",
            prior,
        )
    for command in ("show", "result", "history"):
        failure(
            run("processing_jobs", [command, *scoped(scope, job_id)], archive_dsn),
            "pil.infrastructure.local_prefix_job_integrity_invalid",
        )
