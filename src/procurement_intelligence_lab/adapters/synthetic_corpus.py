"""Fail-closed filesystem admission for synthetic, hash-pinned source facts."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from procurement_intelligence_lab.adapters.xlsx import read_bom, read_source_row
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef, RecordLocation
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
    StateScope,
)
from procurement_intelligence_lab.ports.corpus import (
    CorpusAdmissionError,
    CorpusFact,
    CorpusInventory,
    CorpusNotFoundError,
    CorpusSourceRecord,
    CorpusSourceRow,
)

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "examples/corpus_v1"
DEFAULT_SCOPES = tuple(
    ("synthetic-tenant", project, "lab") for project in ("atlas", "borealis", "cinder", "delta")
)
_ROLES = {
    "approved_bom_revision",
    "approved_purchase_order_line",
    "accepted_supplier_quote",
    "supplier_confirmed_commitment",
}


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(
        isinstance(k, str) for k in cast(dict[object, object], value)
    ):
        raise CorpusAdmissionError("expected a JSON object")
    return cast(dict[str, object], value)


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise CorpusAdmissionError("expected a JSON array")
    return cast(list[object], value)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CorpusAdmissionError("expected a nonempty string")
    return value


def _time(value: object) -> datetime:
    result = datetime.fromisoformat(_text(value))
    if result.tzinfo is None:
        raise CorpusAdmissionError("source timestamp must be timezone-aware")
    return result


def _read(path: Path) -> dict[str, object]:
    return _object(json.loads(path.read_bytes()))


@dataclass(frozen=True)
class SyntheticCorpusReader:
    root: Path = DEFAULT_ROOT
    allowed_scopes: tuple[tuple[str, str, str], ...] = DEFAULT_SCOPES

    def _authorize(self, context: RequestContext, permission: Permission) -> None:
        context.require(permission)
        if (context.tenant_id, context.project_id, context.site_id) not in self.allowed_scopes:
            raise ScopeAuthorizationError("request is not authorized for corpus scope")

    def _path(self, value: object, expected_hash: object) -> Path:
        name = _text(value)
        candidate = self.root / name
        if Path(name).is_absolute() or ".." in Path(name).parts or candidate.is_symlink():
            raise CorpusAdmissionError("invalid admitted path")
        path = candidate.resolve()
        if not path.is_relative_to(self.root.resolve()) or path == self.root.resolve():
            raise CorpusAdmissionError("admitted path escapes corpus")
        if sha256(path.read_bytes()).hexdigest() != _text(expected_hash):
            raise CorpusAdmissionError("admitted source hash mismatch")
        return path

    def inventory(self, *, context: RequestContext) -> CorpusInventory:
        self._authorize(context, Permission.READ_STATE)
        return self._admit(context)[0]

    def _admit(
        self, context: RequestContext
    ) -> tuple[CorpusInventory, dict[str, CorpusSourceRow | CorpusSourceRecord]]:
        try:
            return self._load(context)
        except CorpusAdmissionError:
            raise
        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            InvalidOperation,
            BadZipFile,
            ParseError,
        ) as error:
            raise CorpusAdmissionError("invalid admitted corpus input") from error

    def _load(
        self, context: RequestContext
    ) -> tuple[CorpusInventory, dict[str, CorpusSourceRow | CorpusSourceRecord]]:
        manifest = _read(self.root / "manifest.json")
        if manifest.get("schema_version") != "procurement-demo-corpus/v1":
            raise CorpusAdmissionError("unsupported corpus schema")
        documents = _list(manifest.get("documents"))
        seen: set[str] = set()
        paths: set[str] = set()
        facts: list[CorpusFact] = []
        sources: dict[str, CorpusSourceRow | CorpusSourceRecord] = {}
        hashes = [sha256((self.root / "manifest.json").read_bytes()).hexdigest()]
        for value in documents:
            doc = _object(value)
            identity = _text(doc.get("artifact_id"))
            if identity in seen:
                raise CorpusAdmissionError("duplicate artifact identity")
            seen.add(identity)
            scope = StateScope(
                _text(doc.get("tenant_id")),
                _text(doc.get("project_id")),
                _text(doc.get("site_id")),
                identity,
            )
            if (scope.tenant_id, scope.project_id, scope.site_id) != (
                context.tenant_id,
                context.project_id,
                context.site_id,
            ):
                continue
            workbook = self._path(doc.get("path"), doc.get("content_hash"))
            authority = self._path(doc.get("metadata_path"), doc.get("metadata_hash"))
            for path in (workbook, authority):
                if str(path) in paths:
                    raise CorpusAdmissionError("duplicate artifact path")
                paths.add(str(path))
            role = _text(doc.get("role"))
            if role not in _ROLES:
                raise CorpusAdmissionError("unsupported source role")
            metadata = _read(authority)
            if metadata.get("schema_version") != 1:
                raise CorpusAdmissionError("unsupported authority schema")
            descriptor = _object(metadata.get("document"))
            for key in ("artifact_id", "tenant_id", "project_id", "site_id", "role"):
                if descriptor.get(key) != doc.get(key):
                    raise CorpusAdmissionError("authority scope or identity mismatch")
            records: dict[int, dict[str, object]] = {}
            for raw in _list(metadata.get("records")):
                record = _object(raw)
                row = record.get("row")
                if type(row) is not int or row < 2 or row in records:
                    raise CorpusAdmissionError("invalid or duplicate authority row")
                records[row] = record
            bom = read_bom(workbook, artifact_id=identity)
            if len(bom.lines) != len({line.evidence.row for line in bom.lines}):
                raise CorpusAdmissionError("duplicate source row coordinates")
            if set(records) != {line.evidence.row for line in bom.lines}:
                raise CorpusAdmissionError("authority records must cover exactly the parsed rows")
            hashes.extend((_text(doc["content_hash"]), _text(doc["metadata_hash"])))
            for line in bom.lines:
                if not line.quantity.is_finite() or line.quantity < 0 or not line.sku.strip():
                    raise CorpusAdmissionError("invalid source quantity or item")
                source = read_source_row(workbook, evidence=line.evidence)
                if (
                    source.headers != ("SKU", "Description", "Quantity", "Unit Price", "Unit")
                    or len(source.cells) != 5
                ):
                    raise CorpusAdmissionError("unsupported workbook columns")
                unit = _text(source.cells[4])
                record = records[line.evidence.row]
                approved = (
                    _time(record["approved_at"]) if record.get("approved_at") is not None else None
                )
                start = _time(record.get("effective_from"))
                end = (
                    _time(record["effective_until"])
                    if record.get("effective_until") is not None
                    else None
                )
                if end is not None and end <= start:
                    raise CorpusAdmissionError("invalid effective interval")
                supersedes = tuple(_text(v) for v in _list(record.get("supersedes")))
                if role == "approved_purchase_order_line" and (end is not None or supersedes):
                    raise CorpusAdmissionError("order replacement and expiry policy is unsupported")
                if len(set(supersedes)) != len(supersedes) or identity in supersedes:
                    raise CorpusAdmissionError("invalid supersession identities")
                ref = EvidenceRef(
                    identity + "-authority",
                    _text(doc["metadata_hash"]),
                    RecordLocation("records", str(line.evidence.row)),
                )
                facts.append(
                    CorpusFact(
                        line.sku,
                        line.quantity,
                        unit,
                        role,
                        scope,
                        identity,
                        supersedes,
                        approved,
                        start,
                        end,
                        _time(record.get("document_at")),
                        _time(record.get("ingested_at")),
                        _text(record.get("line_id")),
                        _text(record.get("assertion_id")),
                        line.evidence,
                        ref,
                    )
                )
                sources[line.evidence.evidence_id] = CorpusSourceRow(
                    line.evidence, source.headers, source.cells, source.highlighted_columns
                )
                sources[ref.evidence_id] = CorpusSourceRecord(
                    ref, json.dumps({"document": descriptor, "record": record}, sort_keys=True)
                )
        if not facts:
            raise CorpusAdmissionError("admitted scope has no source facts")
        return CorpusInventory(stable_id("corpus-snapshot", tuple(hashes)), tuple(facts)), sources

    def source(
        self, evidence: EvidenceRef, *, context: RequestContext
    ) -> CorpusSourceRow | CorpusSourceRecord:
        source = self.source_by_id(evidence.evidence_id, context=context)
        if source.evidence != evidence:
            raise CorpusNotFoundError("evidence not found in admitted scope")
        return source

    def source_by_id(
        self, evidence_id: str, *, context: RequestContext
    ) -> CorpusSourceRow | CorpusSourceRecord:
        """Resolve an admitted reference and original content in one fresh scoped load."""
        self._authorize(context, Permission.READ_EVIDENCE)
        source = self._admit(context)[1].get(evidence_id)
        if source is None:
            raise CorpusNotFoundError("evidence not found in admitted scope")
        return source
