"""Scoped atomic brief/receipt/result ledger; checkpoints confer no authority."""

import json
import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from procurement_intelligence_lab.adapters.sqlite_agent_runs import RunStoreError, decode_run
from procurement_intelligence_lab.platform.semantics.briefs import (
    BriefConflict,
    BriefIntegrityError,
    BriefNotFound,
    ReviewBrief,
    ReviewReceipt,
    SavedBrief,
    brief_dto,
    canonical,
)
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


class BriefStoreError(BriefIntegrityError):
    """Storage or stored integrity cannot satisfy the exact brief contract."""


def _payload(record: ReviewReceipt | SavedBrief) -> str:
    return canonical(
        {k: v.isoformat() if isinstance(v, datetime) else v for k, v in asdict(record).items()}
    )


def _brief(raw: str) -> ReviewBrief:
    try:
        data = json.loads(raw)
        brief = ReviewBrief(
            data["brief_id"],
            decode_run(canonical(data["run"])),
            data["version"],
            data["item"],
            datetime.fromisoformat(data["as_of"]),
            data["snapshot_id"],
            data["content_json"],
            datetime.fromisoformat(data["created_at"]),
        )
        if data != brief_dto(brief):
            raise ValueError("stored digest/fields differ")
        return brief
    except (ValueError, KeyError, TypeError, RunStoreError) as error:
        raise BriefStoreError("invalid stored brief") from error


def _receipt(raw: str) -> ReviewReceipt:
    try:
        data: dict[str, Any] = json.loads(raw)
        data["reviewed_at"] = datetime.fromisoformat(data["reviewed_at"])
        data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return ReviewReceipt(**data)
    except (ValueError, KeyError, TypeError) as error:
        raise BriefStoreError("invalid stored receipt") from error


def _saved(raw: str) -> SavedBrief:
    try:
        data: dict[str, Any] = json.loads(raw)
        data["saved_at"] = datetime.fromisoformat(data["saved_at"])
        return SavedBrief(**data)
    except (ValueError, KeyError, TypeError) as error:
        raise BriefStoreError("invalid stored result") from error


class SqliteBriefStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        with self._connection() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                raise BriefStoreError("unsupported database schema")
            db.execute(
                "CREATE TABLE IF NOT EXISTS review_briefs (brief_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, site_id TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS active_briefs (run_id TEXT PRIMARY KEY, brief_id TEXT NOT NULL REFERENCES review_briefs(brief_id))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS brief_receipts (brief_id TEXT PRIMARY KEY REFERENCES review_briefs(brief_id), payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS saved_briefs (brief_id TEXT PRIMARY KEY REFERENCES review_briefs(brief_id), idempotency_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute("PRAGMA user_version = 1")

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        try:
            db = sqlite3.connect(self.path, timeout=5)
            try:
                db.execute("PRAGMA foreign_keys=ON")
                with db:
                    yield db
            finally:
                db.close()
        except sqlite3.Error as error:
            raise BriefStoreError("brief database operation failed") from error

    @staticmethod
    def _get(
        db: sqlite3.Connection, run_id: str, brief_id: str | None, context: RequestContext
    ) -> ReviewBrief:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        row = db.execute(
            "SELECT b.payload,b.brief_id FROM review_briefs b WHERE b.run_id=? AND b.principal_id=? AND b.tenant_id=? AND b.project_id=? AND b.site_id=? AND b.brief_id=COALESCE(?,(SELECT brief_id FROM active_briefs WHERE run_id=?))",
            (
                run_id,
                context.principal_id,
                context.tenant_id,
                context.project_id,
                context.site_id,
                brief_id,
                run_id,
            ),
        ).fetchone()
        if row is None:
            if (
                brief_id is None
                and db.execute(
                    "SELECT 1 FROM review_briefs WHERE run_id=? AND principal_id=? AND tenant_id=? AND project_id=? AND site_id=?",
                    (
                        run_id,
                        context.principal_id,
                        context.tenant_id,
                        context.project_id,
                        context.site_id,
                    ),
                ).fetchone()
            ):
                raise BriefStoreError("active version is absent or inconsistent with stored briefs")
            raise BriefNotFound("brief not found in authorized owner scope")
        brief = _brief(row[0])
        if (
            brief.run.run_id,
            brief.run.principal_id,
            brief.run.tenant_id,
            brief.run.project_id,
            brief.run.site_id,
            brief.brief_id,
        ) != (
            run_id,
            context.principal_id,
            context.tenant_id,
            context.project_id,
            context.site_id,
            row[1],
        ):
            raise BriefStoreError("stored brief owner/identity mismatch")
        return brief

    @staticmethod
    def _active(db: sqlite3.Connection, brief: ReviewBrief) -> None:
        row = db.execute(
            "SELECT brief_id FROM active_briefs WHERE run_id=?", (brief.run.run_id,)
        ).fetchone()
        if row is None or row[0] != brief.brief_id:
            raise BriefConflict("brief version is no longer active")

    def get(self, run_id: str, brief_id: str | None, *, context: RequestContext) -> ReviewBrief:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        with self._connection() as db:
            return self._get(db, run_id, brief_id, context)

    def put(self, brief: ReviewBrief, *, context: RequestContext) -> None:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        if (
            brief.run.principal_id,
            brief.run.tenant_id,
            brief.run.project_id,
            brief.run.site_id,
        ) != (context.principal_id, context.tenant_id, context.project_id, context.site_id):
            raise BriefConflict("brief owner differs from authorized caller")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                previous = self._get(db, brief.run.run_id, None, context)
            except BriefNotFound:
                previous = None
            if brief.version != (previous.version + 1 if previous else 1):
                raise BriefConflict("brief version changed concurrently")
            if db.execute(
                "SELECT 1 FROM review_briefs WHERE brief_id=?", (brief.brief_id,)
            ).fetchone():
                raise BriefConflict("brief already exists")
            db.execute(
                "INSERT INTO review_briefs VALUES (?,?,?,?,?,?,?)",
                (
                    brief.brief_id,
                    brief.run.run_id,
                    brief.run.principal_id,
                    brief.run.tenant_id,
                    brief.run.project_id,
                    brief.run.site_id,
                    canonical(brief_dto(brief)),
                ),
            )
            db.execute(
                "INSERT INTO active_briefs VALUES (?,?) ON CONFLICT(run_id) DO UPDATE SET brief_id=excluded.brief_id",
                (brief.run.run_id, brief.brief_id),
            )

    def decide(self, receipt: ReviewReceipt, *, context: RequestContext) -> ReviewReceipt:
        context.require(Permission.REVIEW)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            brief = self._get(db, receipt.run_id, receipt.brief_id, context)
            self._active(db, brief)
            if (
                receipt.digest != brief.digest
                or receipt.reviewer_id != context.principal_id
                or receipt.reviewed_at < brief.created_at
            ):
                raise BriefConflict("receipt differs from authorized exact brief")
            row = db.execute(
                "SELECT payload FROM brief_receipts WHERE brief_id=?", (brief.brief_id,)
            ).fetchone()
            if row:
                previous = _receipt(row[0])
                if previous.reviewed_at < brief.created_at:
                    raise BriefStoreError("stored receipt precedes brief creation")
                if (
                    previous.brief_id,
                    previous.run_id,
                    previous.digest,
                    previous.reviewer_id,
                    previous.decision,
                ) != (
                    receipt.brief_id,
                    receipt.run_id,
                    receipt.digest,
                    receipt.reviewer_id,
                    receipt.decision,
                ):
                    raise BriefConflict("review replay changed decision or binding")
                return previous
            db.execute(
                "INSERT INTO brief_receipts VALUES (?,?)", (brief.brief_id, _payload(receipt))
            )
            return receipt

    def save(
        self, brief: ReviewBrief, clock: Callable[[], datetime], *, context: RequestContext
    ) -> SavedBrief:
        context.require(Permission.REVIEW)
        context.require(Permission.ACT)
        context.require(Permission.READ_EVIDENCE)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            stored = self._get(db, brief.run.run_id, brief.brief_id, context)
            self._active(db, stored)
            if stored != brief:
                raise BriefConflict("save differs from immutable stored brief")
            row = db.execute(
                "SELECT payload FROM brief_receipts WHERE brief_id=?", (brief.brief_id,)
            ).fetchone()
            if row is None:
                raise BriefConflict("brief has no review receipt")
            receipt = _receipt(row[0])
            if receipt.reviewed_at < brief.created_at:
                raise BriefStoreError("stored receipt precedes brief creation")
            if (
                receipt.brief_id,
                receipt.run_id,
                receipt.digest,
                receipt.reviewer_id,
                receipt.decision,
            ) != (brief.brief_id, brief.run.run_id, brief.digest, context.principal_id, "approve"):
                raise BriefConflict("receipt does not authorize exact brief")
            row = db.execute(
                "SELECT payload,idempotency_key FROM saved_briefs WHERE brief_id=?",
                (brief.brief_id,),
            ).fetchone()
            if row:
                saved = _saved(row[0])
                if row[1] != saved.idempotency_key:
                    raise BriefStoreError("saved relational key differs from payload")
                if (saved.brief_id, saved.run_id, saved.digest, saved.idempotency_key) != (
                    brief.brief_id,
                    brief.run.run_id,
                    brief.digest,
                    brief.idempotency_key,
                ):
                    raise BriefStoreError("stored result binding differs")
                if saved.saved_at < receipt.reviewed_at or saved.saved_at >= receipt.expires_at:
                    raise BriefStoreError("stored save time differs from approval validity")
                return saved
            now = clock()
            if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
                raise ValueError("save clock must be aware")
            if now < receipt.reviewed_at or now >= receipt.expires_at:
                raise BriefConflict("review receipt is expired or future")
            saved = SavedBrief(
                str(uuid4()),
                brief.brief_id,
                brief.run.run_id,
                brief.digest,
                brief.idempotency_key,
                now,
            )
            db.execute(
                "INSERT INTO saved_briefs VALUES (?,?,?)",
                (brief.brief_id, brief.idempotency_key, _payload(saved)),
            )
            return saved

    def saved(self, brief: ReviewBrief, *, context: RequestContext) -> SavedBrief | None:
        """Read the result ledger, validating bindings rather than trusting checkpoints."""
        with self._connection() as db:
            stored = self._get(db, brief.run.run_id, brief.brief_id, context)
            if stored != brief:
                raise BriefStoreError("saved lookup differs from immutable brief")
            row = db.execute(
                "SELECT payload,idempotency_key FROM saved_briefs WHERE brief_id=?",
                (brief.brief_id,),
            ).fetchone()
            if row is None:
                return None
            saved = _saved(row[0])
            approval = db.execute(
                "SELECT payload FROM brief_receipts WHERE brief_id=?", (brief.brief_id,)
            ).fetchone()
            if approval is None:
                raise BriefStoreError("saved result has no approval record")
            receipt = _receipt(approval[0])
            if (
                (saved.brief_id, saved.run_id, saved.digest, saved.idempotency_key)
                != (brief.brief_id, brief.run.run_id, brief.digest, brief.idempotency_key)
                or row[1] != saved.idempotency_key
                or (
                    receipt.brief_id,
                    receipt.run_id,
                    receipt.digest,
                    receipt.reviewer_id,
                    receipt.decision,
                )
                != (brief.brief_id, brief.run.run_id, brief.digest, context.principal_id, "approve")
                or receipt.reviewed_at < brief.created_at
                or not receipt.reviewed_at <= saved.saved_at < receipt.expires_at
            ):
                raise BriefStoreError("saved result or receipt differs from exact brief binding")
            return saved

    def receipt(self, brief: ReviewBrief, *, context: RequestContext) -> ReviewReceipt | None:
        with self._connection() as db:
            stored = self._get(db, brief.run.run_id, brief.brief_id, context)
            if stored != brief:
                raise BriefStoreError("receipt lookup differs from immutable brief")
            row = db.execute(
                "SELECT payload FROM brief_receipts WHERE brief_id=?", (brief.brief_id,)
            ).fetchone()
            if row is None:
                return None
            receipt = _receipt(row[0])
            if (receipt.brief_id, receipt.run_id, receipt.digest, receipt.reviewer_id) != (
                brief.brief_id,
                brief.run.run_id,
                brief.digest,
                context.principal_id,
            ) or receipt.reviewed_at < brief.created_at:
                raise BriefStoreError("receipt differs from exact brief binding")
            return receipt
