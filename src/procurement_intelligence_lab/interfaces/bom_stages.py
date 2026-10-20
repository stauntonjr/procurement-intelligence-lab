"""Inspect BOM stages with optional explicit-policy normalization and source claims."""

import argparse
import json
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

from procurement_intelligence_lab.bootstrap import (
    build_bom_assertion_service,
    build_bom_normalization_service,
    build_bom_stage_service,
)
from procurement_intelligence_lab.interfaces.bom_normalization_policy import load_policy
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import (
    DocumentStageError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DocumentStageError("execution context contains duplicate JSON keys")
        result[key] = value
    return result


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise DocumentStageError("context identities and timestamps require non-empty strings")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise DocumentStageError("context text must be valid Unicode") from None
    return value


def _time(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(_text(value))
    except ValueError:
        raise DocumentStageError("context timestamps must use timezone-aware ISO 8601") from None
    if parsed.tzinfo is None:
        raise DocumentStageError("context timestamps must be timezone-aware")
    return parsed


def _context(path: Path) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise DocumentStageError(
            "execution context must be readable, unambiguous UTF-8 JSON"
        ) from None
    if not isinstance(value, dict):
        raise DocumentStageError("execution context must be an object")
    data = cast(dict[str, object], value)
    required = {"scope", "observed_at", "captured_at", "run_id", "code_revision"}
    if not required <= data.keys() or data.keys() - required - {"source_version"}:
        raise DocumentStageError("execution context has missing or unsupported fields")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect BOM capture, structure and mapping, optional normalization and source assertions."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--context", type=Path, required=True, help="Explicit scope/time/run/code JSON context"
    )
    parser.add_argument(
        "--normalization-policy",
        type=Path,
        help="Opt in to NORMALIZE with explicit quantity/price units and currency JSON",
    )
    parser.add_argument(
        "--assertions",
        action="store_true",
        help="Opt in to ASSERT after NORMALIZE; requires --normalization-policy",
    )
    args = parser.parse_args()
    try:
        if args.assertions and args.normalization_policy is None:
            raise DocumentStageError("--assertions requires --normalization-policy")
        data = _context(args.context)
        scope_value = data["scope"]
        if not isinstance(scope_value, dict) or set(cast(dict[str, object], scope_value)) != {
            "tenant_id",
            "project_id",
            "site_id",
            "version",
        }:
            raise DocumentStageError(
                "context scope requires tenant_id, project_id, site_id and version"
            )
        scope_data = cast(dict[str, object], scope_value)
        scope = StateScope(
            *(_text(scope_data[key]) for key in ("tenant_id", "project_id", "site_id", "version"))
        )
        observed_at = _time(data["observed_at"])
        captured_at = _time(data["captured_at"])
        version = _text(data["source_version"]) if data.get("source_version") is not None else None
        context = ProvenanceContext(
            _text(data["run_id"]),
            "bom-stage-inspection",
            "1",
            _text(data["code_revision"]),
            "local-uncontainerized",
            sha256(
                json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            None,
            (),
            captured_at,
        )
        source = SourceReference(
            "local-file", args.source.absolute().as_uri(), scope, observed_at, version
        )
        if args.normalization_policy is None:
            result = (
                build_bom_stage_service(captured_at=captured_at, context=context)
                .run(source)
                .as_dict()
            )
        else:
            policy = load_policy(args.normalization_policy)
            result = (
                (
                    build_bom_assertion_service
                    if args.assertions
                    else build_bom_normalization_service
                )(captured_at=captured_at, context=context, policy=policy)
                .run(source)
                .as_dict()
            )
            result["normalization_policy"] = policy.as_dict()
    except SemanticContractError as exc:
        print(json.dumps(exc.as_dict()), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
