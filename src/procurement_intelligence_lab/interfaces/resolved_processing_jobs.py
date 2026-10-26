"""Trusted local developer jobs; explicit commands grant no operational-agent authority."""

import argparse
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, NoReturn

from procurement_intelligence_lab.application.archived_planned_execution import (
    execution_archive_receipt_payload,
)
from procurement_intelligence_lab.application.archived_resolved_execution import (
    ArchivedResolvedBomResult,
)
from procurement_intelligence_lab.application.planned_resolved_bom_execution import (
    PlannedResolvedBomExecution,
)
from procurement_intelligence_lab.application.resolved_prefix_job_admission import (
    pin_resolved_prefix_job,
)
from procurement_intelligence_lab.application.resolved_prefix_jobs import (
    ResolvedAttemptAcknowledgementUnavailable,
)
from procurement_intelligence_lab.bootstrap import (
    build_planned_resolved_bom_service,
    build_resolved_execution_archive_reader,
    build_resolved_prefix_job_reader,
    build_resolved_prefix_job_service,
    build_resolved_prefix_jobs,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn
from procurement_intelligence_lab.interfaces.assertion_archive import export_content
from procurement_intelligence_lab.interfaces.execute_package import policy, read, request
from procurement_intelligence_lab.interfaces.processing_job_inputs import (
    job_scope,
    parse_arrival,
    parse_expected_version,
    parse_integer,
)
from procurement_intelligence_lab.interfaces.resolution_inputs import (
    resolution_policy,
    resolved_request,
)
from procurement_intelligence_lab.platform.execution.identity import encoded
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ResolvedExecutionArchiveReceipt,
)
from procurement_intelligence_lab.platform.execution.resolution_runner import (
    ResolvedPrefixExecution,
)
from procurement_intelligence_lab.platform.planning.inputs import load_config, load_registry
from procurement_intelligence_lab.platform.processing.errors import (
    JobContractError as LegacyJobContractError,
)
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    JobStatus,
    ResolvedAbandonAttemptCommand,
    ResolvedAttemptSuccess,
    ResolvedJobJournalReceipt,
    ResolvedJobView,
    ResolvedStartAttemptCommand,
    StartIntent,
    job_key,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobContractError,
    ResolvedJobUnavailableError,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveUnavailableError,
    SemanticContractError,
    SemanticTypeContractError,
)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ResolvedJobContractError("invalid local job arguments; use --help")


def journal_receipt_payload(receipt: ResolvedJobJournalReceipt) -> dict[str, Any]:
    t = receipt.transition
    return {
        "record_id": t.record_id,
        "scope": vars(t.scope),
        "job_id": t.job_id,
        "sequence": t.sequence,
        "version": t.version,
        "kind": t.kind.value,
        "status": t.status.value,
        "recorded_at": t.recorded_at.isoformat(),
        "command": encoded(t.command),
        "attempt": encoded(t.attempt),
        "failure": encoded(t.failure),
        "attempt_receipt_digest": t.success.completed.execution.receipt_digest
        if t.success
        else None,
        "retained_archive_receipt": archive_receipt_payload(t.success.retained)
        if t.success
        else None,
    }


def view_payload(view: ResolvedJobView) -> dict[str, Any]:
    return {
        "profile": "local-resolved-prefix-jobs/v1",
        "stop_after": "RESOLVE",
        "recipe_id": view.definition.definition.recipe_id,
        "candidate_snapshot_id": view.definition.definition.candidate_input.snapshot.snapshot_id,
        "candidate_raw_sha256": view.definition.definition.candidate_input.raw_sha256,
        "resolution_policy_reference": view.definition.definition.policy.reference.reference_id,
        "job_id": view.definition.job_id,
        "request_digest": view.definition.request_digest,
        "scope": vars(view.definition.scope),
        "status": view.status.value,
        "version": view.version,
        "processing_complete": view.status is JobStatus.SUCCEEDED,
        "attempt": encoded(view.latest.transition.attempt),
        "arrival": encoded(view.definition.arrival),
        "job_journal_receipt": journal_receipt_payload(view.latest),
    }


def archive_receipt_payload(r: ResolvedExecutionArchiveReceipt) -> dict[str, Any]:
    return {
        "receipt_id": r.receipt_id,
        "sequence": r.sequence,
        "execution_digest": r.execution_digest,
        "retained_receipt_digest": r.retained_receipt_digest,
        "scope": vars(r.scope),
        "snapshot_id": r.snapshot_id,
        "prefix_receipt": execution_archive_receipt_payload(r.prefix_receipt),
    }


def result_payload(success: ResolvedAttemptSuccess) -> dict[str, Any]:
    r = success.completed.execution
    retained = (
        build_resolved_execution_archive_reader(configured_dsn())
        .show(success.retained.scope, success.retained.execution_digest)
        .retained
    )
    data = ArchivedResolvedBomResult(
        PlannedResolvedBomExecution(ResolvedPrefixExecution(r.output, r)), retained
    ).as_dict()
    data["attempt_execution_receipt"] = data.pop("execution_receipt")
    data["attempt_prefix_execution_receipt"] = data.pop("prefix_execution_receipt")
    for role in (
        "attempt_execution_receipt",
        "attempt_prefix_execution_receipt",
        "retained_execution_receipt",
        "retained_embedded_prefix_execution_receipt",
        "retained_prefix_execution_receipt",
    ):
        data[role].pop("durable_run_journal_updated", None)
        data[role].pop("result_cache_updated", None)
    return data


def main() -> int:
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    submit = commands.add_parser("submit")
    submit.add_argument("source", type=Path)
    for name in (
        "arrival",
        "context",
        "manifest",
        "registry",
        "config",
        "normalization-policy",
        "resolution-policy",
        "candidate-snapshot",
    ):
        submit.add_argument("--" + name, type=Path, required=True)
    submit.add_argument("--idempotency-key", required=True)
    submit.add_argument("--stop-after", choices=("RESOLVE",), required=True)
    for name in ("run", "retry", "abandon", "show", "history", "result", "content"):
        command = commands.add_parser(name)
        command.add_argument("--scope", type=Path, required=True)
        command.add_argument("--job-id", required=True)
        if name in ("run", "retry", "abandon"):
            command.add_argument("--command-key", required=True)
            command.add_argument("--actor", required=True)
            command.add_argument("--expected-version", type=parse_expected_version, required=True)
        if name == "abandon":
            command.add_argument("--attempt-id", required=True)
            command.add_argument("--reason", required=True)
        if name == "history":
            command.add_argument(
                "--limit", type=lambda raw: parse_integer(raw, maximum=200), default=100
            )
            command.add_argument(
                "--after-sequence", type=lambda raw: parse_integer(raw, minimum=0), default=0
            )
        if name == "content":
            command.add_argument("--output", type=Path, required=True)
    recovery: dict[str, Any] = {}
    try:
        args = parser.parse_args()
        if args.command == "init":
            build_resolved_prefix_jobs(configured_dsn()).initialize()
            payload = {"capability": "local_resolved_prefix_jobs/v1", "initialized": True}
        elif args.command == "submit":
            now = datetime.now(UTC)
            prefix = request(args.source, read(args.context, 32768))
            arrival = parse_arrival(read(args.arrival, 32768), prefix.source)
            normal = policy(read(args.normalization_policy, 32768))
            resolution = resolution_policy(read(args.resolution_policy, 32768))
            q = resolved_request(prefix, read(args.candidate_snapshot, 32768), resolution)
            prepared = build_planned_resolved_bom_service(
                manifest=read(args.manifest, 1048576),
                registry=load_registry(read(args.registry, 1048576)),
                config=load_config(read(args.config, 1048576)),
                normalization_policy=normal,
                resolution_policy=resolution,
                candidate_input=q.candidate_input,
                clock=lambda: now,
            ).prepare(q)
            job = pin_resolved_prefix_job(
                prepared,
                arrival,
                args.idempotency_key,
                normalization_parameters=tuple(sorted(normal.as_dict().items())),
                now=now,
            )
            recovery = {"scope": vars(job.scope), "job_id": job.job_id}
            service = build_resolved_prefix_job_service(
                clock=lambda: now,
                journal_factory=lambda: build_resolved_prefix_jobs(configured_dsn()),
            )
            receipt = service.submit(job)
            view = build_resolved_prefix_job_reader(configured_dsn()).show(job.scope, job.job_id)
            payload = {
                **view_payload(view),
                "job_journal_receipt": journal_receipt_payload(receipt),
                "acknowledgement_basis": "retained_submission",
            }
        else:
            job_key(args.job_id)
            scope = job_scope(args.scope)
            recovery = {"scope": vars(scope), "job_id": args.job_id}
            if args.command in ("run", "retry"):
                command = ResolvedStartAttemptCommand(
                    scope,
                    args.job_id,
                    args.command_key,
                    args.actor,
                    args.expected_version,
                    StartIntent.FIRST if args.command == "run" else StartIntent.RETRY,
                )
                service = build_resolved_prefix_job_service(
                    clock=lambda: datetime.now(UTC),
                    journal_factory=lambda: build_resolved_prefix_jobs(configured_dsn()),
                )
                result = service.execute(command)
                attempt = result.receipt.transition.attempt
                assert attempt is not None
                recovery["attempt_id"] = attempt.attempt_id
                current = result.receipt.transition.success
                if current is None:
                    raise ResolvedJobContractError(
                        "execution returned no positive completion evidence"
                    )
                view = build_resolved_prefix_job_reader(configured_dsn()).show(scope, args.job_id)
                payload = {
                    **result_payload(current),
                    **view_payload(view),
                    "job_journal_receipt": journal_receipt_payload(result.receipt),
                    "command_receipt": journal_receipt_payload(result.command_receipt),
                    "historical": result.historical,
                    "observed_version": result.observed_version,
                }
            elif args.command == "abandon":
                command = ResolvedAbandonAttemptCommand(
                    scope,
                    args.job_id,
                    args.command_key,
                    args.actor,
                    args.expected_version,
                    args.attempt_id,
                    args.reason,
                )
                recovery["attempt_id"] = command.attempt_id
                receipt = build_resolved_prefix_job_service(
                    clock=lambda: datetime.now(UTC),
                    journal_factory=lambda: build_resolved_prefix_jobs(configured_dsn()),
                ).abandon(command)
                view = build_resolved_prefix_job_reader(configured_dsn()).show(scope, args.job_id)
                payload = {
                    **view_payload(view),
                    "historical_command_receipt": journal_receipt_payload(receipt),
                    "receipt_is_current": receipt.transition.version == view.version,
                    "observed_version": view.version,
                }
            else:
                reader = build_resolved_prefix_job_reader(configured_dsn())
                if args.command == "history":
                    page = reader.history(
                        scope, args.job_id, limit=args.limit, after_sequence=args.after_sequence
                    )
                    payload = {
                        "job_id": args.job_id,
                        "receipts": [journal_receipt_payload(r) for r in page.receipts],
                        "has_more": page.has_more,
                        "next_after_sequence": page.next_after_sequence,
                    }
                elif args.command == "show":
                    payload = view_payload(reader.show(scope, args.job_id))
                elif args.command == "result":
                    current = reader.result(scope, args.job_id)
                    view = reader.show(scope, args.job_id)
                    attempt = view.latest.transition.attempt
                    assert attempt is not None
                    recovery["attempt_id"] = attempt.attempt_id
                    payload = {
                        **result_payload(current),
                        **view_payload(view),
                    }
                else:
                    content = reader.content(scope, args.job_id)
                    export_content(args.output, content)
                    payload = {
                        "job_id": args.job_id,
                        "content_hash": sha256(content).hexdigest(),
                        "byte_length": len(content),
                        "output": str(args.output),
                    }
    except (SemanticContractError, SemanticTypeContractError) as exc:
        error: dict[str, Any] = dict(
            ResolvedJobContractError("invalid bounded resolved job input").as_dict()
            if isinstance(exc, LegacyJobContractError)
            else exc.as_dict()
        )
        if isinstance(exc, (ResolvedJobUnavailableError, ArchiveUnavailableError)):
            error.update(recovery)
            if isinstance(exc, ResolvedAttemptAcknowledgementUnavailable):
                error.update(
                    scope=vars(exc.token.scope),
                    job_id=exc.token.job_id,
                    attempt_id=exc.token.attempt_id,
                )
        print(json.dumps(error, ensure_ascii=True), file=sys.stderr)
        return 2
    except (ValueError, TypeError, UnicodeError, RecursionError):
        print(
            json.dumps(ResolvedJobContractError("invalid bounded local job input").as_dict()),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
