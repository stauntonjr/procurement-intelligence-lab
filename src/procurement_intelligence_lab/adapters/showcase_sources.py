"""Hash-admitted original XLSX catalog/source mechanics; no decision policy."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from procurement_intelligence_lab.adapters.xlsx import read_bom, read_source_row
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.ports.corpus import (
    CorpusAdmissionError,
    CorpusNotFoundError,
    CorpusSourceRow,
)

A = "showcase_bom_revision_a.xlsx"
B = "showcase_bom_revision_b.xlsx"
ORDER = "showcase_order_short.xlsx"
SOURCE_SETS = {
    "showcase-a-order": (A, ORDER),
    "showcase-a-b-order": (A, B, ORDER),
    "showcase-a-only": (A,),
}
MANIFEST = "showcase_review_sources_v1.json"


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CorpusAdmissionError("duplicate manifest field")
        result[key] = value
    return result


@dataclass(frozen=True)
class ShowcaseSources:
    selection: str
    root: Path = Path(__file__).resolve().parents[1] / "examples"

    def __post_init__(self) -> None:
        if self.selection not in SOURCE_SETS:
            raise ValueError("unsupported original source set")

    def _admit(
        self, context: RequestContext, permission: Permission
    ) -> tuple[str, tuple[CorpusSourceRow, ...]]:
        context.require(permission)
        if (context.tenant_id, context.project_id, context.site_id) != (
            "synthetic-tenant",
            "synthetic-project",
            "synthetic-site",
        ):
            raise ScopeAuthorizationError("original source scope does not match request")
        try:
            manifest = self.root / MANIFEST
            if manifest.is_symlink():
                raise CorpusAdmissionError("manifest must not be a symlink")
            raw = manifest.read_bytes()
            payload: object = json.loads(raw, object_pairs_hook=_unique)
            if not isinstance(payload, dict):
                raise CorpusAdmissionError("invalid original source manifest")
            data = cast(dict[str, Any], payload)
            if set(data) != {"schema_version", "documents"}:
                raise CorpusAdmissionError("invalid original source manifest")
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                raise CorpusAdmissionError("unsupported original source manifest version")
            documents: object = data["documents"]
            if not isinstance(documents, list):
                raise CorpusAdmissionError("invalid document inventory")
            hashes: dict[str, str] = {}
            for raw_document in cast(list[object], documents):
                if not isinstance(raw_document, dict):
                    raise CorpusAdmissionError("invalid source declaration")
                document = cast(dict[str, Any], raw_document)
                if set(document) != {"path", "content_hash"}:
                    raise CorpusAdmissionError("invalid source declaration")
                name, digest = document["path"], document["content_hash"]
                if (
                    type(name) is not str
                    or name not in (A, B, ORDER)
                    or name in hashes
                    or type(digest) is not str
                    or not re.fullmatch(r"[0-9a-f]{64}", digest)
                ):
                    raise CorpusAdmissionError("invalid source identity/hash")
                hashes[name] = digest
            if set(hashes) != {A, B, ORDER}:
                raise CorpusAdmissionError("incomplete original source manifest")
            rows: list[CorpusSourceRow] = []
            selected = SOURCE_SETS[self.selection]
            for name in selected:
                path = self.root / name
                if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != hashes[name]:
                    raise CorpusAdmissionError("original source integrity failure")
                bom = read_bom(path, artifact_id="showcase:" + name)
                if len(bom.lines) != 1 or bom.lines[0].sku != "GPU-A":
                    raise CorpusAdmissionError("unsupported original item inventory")
                row = read_source_row(path, evidence=bom.lines[0].evidence)
                rows.append(
                    CorpusSourceRow(
                        bom.lines[0].evidence, row.headers, row.cells, row.highlighted_columns
                    )
                )
            return stable_id(
                "original-showcase-snapshot",
                (sha256(raw).hexdigest(), self.selection, *(hashes[name] for name in selected)),
            ), tuple(rows)
        except CorpusAdmissionError:
            raise
        except Exception as error:
            raise CorpusAdmissionError("original sources cannot be admitted") from error

    def items(self, *, context: RequestContext) -> tuple[str, ...]:
        self._admit(context, Permission.READ_STATE)
        return ("GPU-A",)

    def snapshot_id(self, *, context: RequestContext) -> str:
        return self._admit(context, Permission.READ_STATE)[0]

    def source_by_id(self, evidence_id: str, *, context: RequestContext) -> CorpusSourceRow:
        for source in self._admit(context, Permission.READ_EVIDENCE)[1]:
            if source.evidence.evidence_id == evidence_id:
                return source
        raise CorpusNotFoundError("source is not admitted in the original source set")

    def source_ids(self, *, context: RequestContext) -> frozenset[str]:
        return frozenset(
            row.evidence.evidence_id for row in self._admit(context, Permission.READ_EVIDENCE)[1]
        )
