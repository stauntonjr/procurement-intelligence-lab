"""Inference ledger; application checks run ownership before any access."""

import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from procurement_intelligence_lab.platform.semantics.interpretation import (
    InterpretationCall,
    ModelFailure,
)


class SqliteInterpretationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        with self._connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS interpretation_calls (run_id TEXT PRIMARY KEY REFERENCES agent_runs(run_id), payload TEXT NOT NULL)"
            )

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        try:
            db = sqlite3.connect(self.path, timeout=5)
            try:
                db.execute("PRAGMA foreign_keys = ON")
                with db:
                    yield db
            finally:
                db.close()
        except sqlite3.Error as error:
            raise ModelFailure("interpretation_store_unavailable") from error

    @staticmethod
    def _encode(call: InterpretationCall) -> str:
        data = asdict(call)
        data["as_of"] = call.as_of.isoformat()
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _get(db: sqlite3.Connection, run_id: str) -> InterpretationCall:
        row = db.execute(
            "SELECT payload FROM interpretation_calls WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise ModelFailure("interpretation_store_unavailable")
        try:
            data: dict[str, Any] = json.loads(cast(str, row[0]))
            data["as_of"] = datetime.fromisoformat(data["as_of"])
            return InterpretationCall(**data)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ModelFailure("interpretation_store_unavailable") from error

    def create(self, call: InterpretationCall) -> None:
        if call.status != "pending":
            raise ValueError("create pending only")
        with self._connection() as db:
            db.execute(
                "INSERT INTO interpretation_calls VALUES (?,?)", (call.run_id, self._encode(call))
            )

    def finish(self, call: InterpretationCall) -> None:
        if call.status == "pending":
            raise ValueError("finish terminal only")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            original = self._get(db, call.run_id)
            if original.status != "pending" or (original.question_hash, original.as_of) != (
                call.question_hash,
                call.as_of,
            ):
                raise ModelFailure("interpretation_store_unavailable")
            db.execute(
                "UPDATE interpretation_calls SET payload=? WHERE run_id=?",
                (self._encode(call), call.run_id),
            )

    def get(self, run_id: str) -> InterpretationCall:
        with self._connection() as db:
            return self._get(db, run_id)
