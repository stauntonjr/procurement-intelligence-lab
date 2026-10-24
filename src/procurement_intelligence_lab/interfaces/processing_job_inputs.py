"""Strict bounded job input documents and numeric arguments."""

import re
from pathlib import Path

from procurement_intelligence_lab.interfaces.execute_package import record, time
from procurement_intelligence_lab.interfaces.planned_execution_archive import scope_file
from procurement_intelligence_lab.platform.processing.contracts import MAX_COUNTER, ArtifactArrival
from procurement_intelligence_lab.platform.processing.errors import JobContractError
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def parse_integer(raw: str, *, minimum: int = 1, maximum: int = MAX_COUNTER) -> int:
    if type(raw) is not str or len(raw) > 19 or re.fullmatch("[0-9]+", raw) is None:
        raise JobContractError("job counter requires an exact bounded integer")
    value = int(raw)
    if not minimum <= value <= maximum:
        raise JobContractError("job counter is outside its supported range")
    return value


def parse_expected_version(raw: str) -> int:
    return parse_integer(raw)


def parse_arrival(raw: bytes, source: SourceReference) -> ArtifactArrival:
    try:
        value = record(raw)
        if set(value) != {
            "event_id",
            "expected_content_hash",
            "expected_byte_length",
            "announced_at",
        }:
            raise JobContractError("arrival requires exact declaration fields")
        return ArtifactArrival(
            source.scope,
            value["event_id"],
            source,
            value["expected_content_hash"],
            value["expected_byte_length"],
            time(value["announced_at"]),
        )
    except (SemanticContractError, TypeError, ValueError, UnicodeError):
        raise JobContractError(
            "arrival requires bounded unambiguous expected-byte evidence"
        ) from None


def job_scope(path: Path) -> StateScope:
    try:
        return scope_file(path)
    except (SemanticContractError, TypeError, ValueError, UnicodeError):
        raise JobContractError("job scope requires four bounded exact identity strings") from None
