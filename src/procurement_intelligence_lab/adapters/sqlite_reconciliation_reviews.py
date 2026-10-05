"""SQLite adapter for scoped prospective reconciliation decisions."""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import cast

from procurement_intelligence_lab.domains.procurement.review_reconciliation import (
    HumanReconciliationDecision,
    ReconciliationReviewOutcome,
)
from procurement_intelligence_lab.platform.semantics.briefs import (
    BriefConflict,
    BriefIntegrityError,
    canonical,
)
from procurement_intelligence_lab.platform.semantics.evidence import (
    EvidenceRef,
    RecordLocation,
    TabularLocation,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    StateScope,
)


class ReconciliationReviewStoreError(BriefIntegrityError):
    """Stored reconciliation data is unavailable or inconsistent."""


def _payload(item: HumanReconciliationDecision) -> str:
    return canonical(
        {
            "decision_id": item.decision_id,
            "brief_id": item.brief_id,
            "brief_digest": item.brief_digest,
            "subject_key": item.subject_key,
            "scope": {
                "tenant_id": item.scope.tenant_id,
                "project_id": item.scope.project_id,
                "site_id": item.scope.site_id,
                "version": item.scope.version,
            },
            "outcome": item.outcome.value,
            "candidate_claim_ids": item.candidate_claim_ids,
            "selected_claim_id": item.selected_claim_id,
            "rationale": item.rationale,
            "reviewer_id": item.reviewer_id,
            "policy_id": item.policy_id,
            "recorded_at": item.recorded_at.isoformat(),
            "effective_at": item.effective_at.isoformat(),
            "evidence": [ref.as_dict() for ref in item.evidence],
        }
    )


def _decode_evidence(data: dict[str, object]) -> EvidenceRef:
    if data["location_kind"] == "record":
        location = RecordLocation(str(data["collection"]), str(data["record_key"]))
    elif data["location_kind"] == "tabular":
        location = TabularLocation(
            str(data["sheet"]), int(cast(int, data["row"])), tuple(cast(list[str], data["cells"]))
        )
    else:
        raise ValueError("unsupported evidence location")
    result = EvidenceRef(str(data["artifact_id"]), str(data["content_hash"]), location)
    if result.evidence_id != data["evidence_id"]:
        raise ValueError("evidence identity differs")
    return result


def _decision(raw: str) -> HumanReconciliationDecision:
    try:
        data = json.loads(raw)
        scope = StateScope(**data.pop("scope"))
        evidence = tuple(_decode_evidence(item) for item in data.pop("evidence"))
        data["outcome"] = ReconciliationReviewOutcome(data["outcome"])
        data["candidate_claim_ids"] = tuple(data["candidate_claim_ids"])
        data["recorded_at"] = datetime.fromisoformat(data["recorded_at"])
        data["effective_at"] = datetime.fromisoformat(data["effective_at"])
        return HumanReconciliationDecision(scope=scope, evidence=evidence, **data)
    except (KeyError, TypeError, ValueError) as error:
        raise ReconciliationReviewStoreError("invalid stored reconciliation decision") from error


class SqliteReconciliationReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        with self._connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS reconciliation_reviews (decision_id TEXT PRIMARY KEY, brief_id TEXT UNIQUE NOT NULL, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, site_id TEXT NOT NULL, subject_key TEXT NOT NULL, effective_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        try:
            db = sqlite3.connect(self.path, timeout=5)
            try:
                with db:
                    yield db
            finally:
                db.close()
        except sqlite3.Error as error:
            raise ReconciliationReviewStoreError(
                "reconciliation database operation failed"
            ) from error

    @staticmethod
    def _scope(item: HumanReconciliationDecision, context: RequestContext) -> None:
        if (item.scope.tenant_id, item.scope.project_id, item.scope.site_id, item.reviewer_id) != (
            context.tenant_id,
            context.project_id,
            context.site_id,
            context.principal_id,
        ):
            raise BriefConflict("reconciliation owner or scope differs from authorized caller")

    def record(
        self, decision: HumanReconciliationDecision, *, context: RequestContext
    ) -> HumanReconciliationDecision:
        context.require(Permission.REVIEW)
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        self._scope(decision, context)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM reconciliation_reviews WHERE brief_id=?", (decision.brief_id,)
            ).fetchone()
            if row:
                previous = _decision(row[0])
                if previous != decision:
                    raise BriefConflict("reconciliation replay changed decision or binding")
                return previous
            db.execute(
                "INSERT INTO reconciliation_reviews VALUES (?,?,?,?,?,?,?,?)",
                (
                    decision.decision_id,
                    decision.brief_id,
                    context.tenant_id,
                    context.project_id,
                    context.site_id,
                    decision.subject_key,
                    decision.effective_at.isoformat(),
                    _payload(decision),
                ),
            )
        return decision

    def latest(
        self, subject_key: str, as_of: datetime, *, context: RequestContext
    ) -> HumanReconciliationDecision | None:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        with self._connection() as db:
            row = db.execute(
                "SELECT payload,tenant_id,project_id,site_id,subject_key,effective_at FROM reconciliation_reviews WHERE tenant_id=? AND project_id=? AND site_id=? AND subject_key=? AND effective_at<=? ORDER BY effective_at DESC,decision_id DESC LIMIT 1",
                (
                    context.tenant_id,
                    context.project_id,
                    context.site_id,
                    subject_key,
                    as_of.isoformat(),
                ),
            ).fetchone()
        if row is None:
            return None
        item = _decision(row[0])
        self._scope(item, context)
        if (row[1], row[2], row[3], row[4], row[5]) != (
            item.scope.tenant_id,
            item.scope.project_id,
            item.scope.site_id,
            item.subject_key,
            item.effective_at.isoformat(),
        ):
            raise ReconciliationReviewStoreError(
                "stored reconciliation columns differ from payload"
            )
        return item

    def for_brief(
        self, brief_id: str, *, context: RequestContext
    ) -> HumanReconciliationDecision | None:
        context.require(Permission.READ_STATE)
        context.require(Permission.READ_EVIDENCE)
        with self._connection() as db:
            row = db.execute(
                "SELECT payload FROM reconciliation_reviews WHERE brief_id=? AND tenant_id=? AND project_id=? AND site_id=?",
                (brief_id, context.tenant_id, context.project_id, context.site_id),
            ).fetchone()
        if row is None:
            return None
        item = _decision(row[0])
        self._scope(item, context)
        return item
