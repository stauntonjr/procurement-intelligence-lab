"""Explicit additive correction-root capability; base dependency schema1 is unchanged."""

from typing import Any, LiteralString, cast

import psycopg

from procurement_intelligence_lab.platform.semantics.dependencies import (
    ApprovedCorrectionRef,
    DependencySnapshot,
)
from procurement_intelligence_lab.platform.semantics.document_reviews import (
    ReviewHistory,
    ReviewOutcome,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    DependencyContractError,
    DependencyIntegrityError,
    DependencyNotFoundError,
    DependencyUnavailableError,
    ReviewIntegrityError,
    ReviewNotFoundError,
    ReviewUnavailableError,
)
from procurement_intelligence_lab.ports.document_reviews import DocumentReviewJournal

CAPABILITY = "approved_correction_roots/v1"
_SCHEMA = (
    "CREATE TABLE pil_dependency_correction_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)",
    "INSERT INTO pil_dependency_correction_meta VALUES (1,1)",
    "CREATE TABLE pil_dependency_correction_roots (scope TEXT NOT NULL, dependency_snapshot_id TEXT NOT NULL, correction_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL, assertion_id TEXT NOT NULL, task_id TEXT NOT NULL, task_digest TEXT NOT NULL, decision_id TEXT NOT NULL, PRIMARY KEY(scope,dependency_snapshot_id,correction_id), FOREIGN KEY(scope,dependency_snapshot_id) REFERENCES pil_dependency_snapshots(scope,snapshot_id), FOREIGN KEY(scope,source_snapshot_id,assertion_id) REFERENCES pil_archive_members(scope,snapshot_id,assertion_id), FOREIGN KEY(scope,task_id) REFERENCES pil_document_review_tasks(scope,task_id), FOREIGN KEY(scope,decision_id) REFERENCES pil_document_review_decisions(scope,decision_id))",
    *(
        f"CREATE TRIGGER pil_dependency_correction_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION pil_archive_immutable()"
        for table in ("pil_dependency_correction_meta", "pil_dependency_correction_roots")
    ),
)

type Connection = psycopg.Connection[dict[str, Any]]


def check_capability(conn: Connection) -> None:
    row = conn.execute("SELECT to_regclass('pil_dependency_correction_meta') AS name").fetchone()
    if row is None or row["name"] is None:
        raise DependencyUnavailableError("explicit approved correction root capability is required")
    if conn.execute("SELECT singleton,version FROM pil_dependency_correction_meta").fetchall() != [
        {"singleton": 1, "version": 1}
    ]:
        raise DependencyIntegrityError("unsupported correction-root capability version")
    conn.execute(
        "SELECT scope,dependency_snapshot_id,correction_id,source_snapshot_id,assertion_id,task_id,task_digest,decision_id FROM pil_dependency_correction_roots LIMIT 0"
    )


def initialize(conn: Connection) -> None:
    if conn.execute("SELECT singleton,version FROM pil_document_review_meta").fetchall() != [
        {"singleton": 1, "version": 1}
    ]:
        raise DependencyIntegrityError("correction roots require initialized review schema1")
    row = conn.execute("SELECT to_regclass('pil_dependency_correction_meta') AS name").fetchone()
    if row is not None and row["name"] is None:
        for statement in _SCHEMA:
            conn.execute(cast(LiteralString, statement))
    check_capability(conn)


def roots(snapshot: DependencySnapshot) -> tuple[ApprovedCorrectionRef, ...]:
    return tuple(r for r in snapshot.manifest.roots if type(r) is ApprovedCorrectionRef)


def membership(root: ApprovedCorrectionRef) -> tuple[str, ...]:
    return (
        root.correction_id,
        root.source.snapshot_id,
        root.source.assertion_id,
        root.task_id,
        root.task_digest,
        root.decision_id,
    )


def verify_sources(
    snapshot: DependencySnapshot, journal: DocumentReviewJournal | None, *, retained: bool
) -> None:
    selected = roots(snapshot)
    if not selected:
        return
    if journal is None:
        raise DependencyUnavailableError("correction roots require a review evidence reader")
    for root in selected:
        try:
            history = journal.get(snapshot.manifest.scope, root.task_id, snapshot.recorded_at)
        except ReviewUnavailableError:
            raise DependencyUnavailableError("correction review backend is unavailable") from None
        except ReviewIntegrityError:
            raise DependencyIntegrityError("correction review evidence is corrupt") from None
        except ReviewNotFoundError:
            if retained:
                raise DependencyIntegrityError(
                    "retained correction review evidence is missing"
                ) from None
            raise DependencyNotFoundError(
                "correction root requires exact scoped review evidence"
            ) from None
        if type(history) is not ReviewHistory:
            raise DependencyIntegrityError("correction reader returned invalid review evidence")
        decision = history.decision
        if (
            history.task.digest != root.task_digest
            or history.task.proposal.snapshot_id != root.source.snapshot_id
            or history.task.proposal.previous.assertion_id != root.source.assertion_id
            or history.task.proposal.scope != snapshot.manifest.scope
            or decision is None
            or decision.command.outcome is not ReviewOutcome.APPROVE
            or decision.decision_id != root.decision_id
            or history.correction_id != root.correction_id
            or decision.recorded_at > snapshot.recorded_at
            or any(
                root.reference_id in claim.inputs
                and claim.event.provenance.context.started_at < decision.recorded_at
                for claim in snapshot.manifest.claims
            )
        ):
            if retained:
                raise DependencyIntegrityError(
                    "retained correction root differs from approved review"
                )
            raise DependencyContractError("correction root must bind exact visible approved review")


def verify_memberships(conn: Connection, scope_id: str, snapshot: DependencySnapshot) -> None:
    expected = {membership(root) for root in roots(snapshot)}
    exists = conn.execute(
        "SELECT to_regclass('pil_dependency_correction_roots') AS name"
    ).fetchone()
    if expected:
        check_capability(conn)
    if exists is None or exists["name"] is None:
        return
    rows = conn.execute(
        "SELECT correction_id,source_snapshot_id,assertion_id,task_id,task_digest,decision_id FROM pil_dependency_correction_roots WHERE scope=%s AND dependency_snapshot_id=%s",
        (scope_id, snapshot.snapshot_id),
    ).fetchall()
    if {
        tuple(
            r[key]
            for key in (
                "correction_id",
                "source_snapshot_id",
                "assertion_id",
                "task_id",
                "task_digest",
                "decision_id",
            )
        )
        for r in rows
    } != expected:
        raise DependencyIntegrityError("correction root membership differs from retained manifest")
