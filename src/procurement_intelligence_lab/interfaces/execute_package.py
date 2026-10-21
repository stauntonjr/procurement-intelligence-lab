"""Execute the explicitly requested source-assertion prefix using pinned deployment files."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn, cast

from procurement_intelligence_lab.bootstrap import build_planned_bom_service
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    CountUnit,
)
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from procurement_intelligence_lab.platform.execution.identity import aware, digest, text
from procurement_intelligence_lab.platform.planning.contracts import PlanningError
from procurement_intelligence_lab.platform.planning.inputs import load_config, load_registry
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionError,
    SemanticContractError,
    SemanticTypeContractError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise PackageExecutionError("invalid execution arguments; use --help")


def read(path: Path, limit: int) -> bytes:
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except (OSError, ValueError):
        raise PackageExecutionError("execution input file is unavailable") from None
    if len(data) > limit:
        raise PackageExecutionError("execution input file exceeds its supported bound")
    return data


def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for k, v in items:
        if k in out:
            raise PackageExecutionError("execution JSON keys must be unique")
        out[k] = v
    return out


def invalid_constant(value: str) -> None:
    raise PackageExecutionError("execution JSON must contain finite values")


def record(data: bytes) -> dict[str, Any]:
    try:
        raw: object = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant
        )
    except (ValueError, UnicodeError, RecursionError):
        raise PackageExecutionError("execution input requires unambiguous UTF-8 JSON") from None
    if not isinstance(raw, dict):
        raise PackageExecutionError("execution input requires a JSON object")
    return cast(dict[str, Any], raw)


def string(value: object) -> str:
    text(value)
    return cast(str, value)


def time(value: object) -> datetime:
    try:
        result = datetime.fromisoformat(string(value))
    except ValueError:
        raise PackageExecutionError("execution time requires aware ISO8601") from None
    aware(result)
    return result


def policy(data: bytes) -> BomNormalizationPolicy:
    value = record(data)
    if (
        set(value) != {"profile", "quantity_unit", "currency", "price_unit"}
        or value["profile"] != "bom-decimal@1"
    ):
        raise PackageExecutionError(
            "execution requires the explicit supported normalization policy"
        )
    for v in value.values():
        string(v)
    try:
        quantity, price = CountUnit(value["quantity_unit"]), CountUnit(value["price_unit"])
    except ValueError:
        raise PackageExecutionError("execution normalization units must be each or dozen") from None
    return BomNormalizationPolicy(quantity, value["currency"], price)


def request(source: Path, data: bytes) -> ExecutionRequest:
    value = record(data)
    required = {"scope", "observed_at", "captured_at", "run_id", "code_revision"}
    if not required <= value.keys() or value.keys() - required - {"source_version"}:
        raise PackageExecutionError("execution context has missing or unsupported fields")
    raw: object = value["scope"]
    if not isinstance(raw, dict):
        raise PackageExecutionError("execution scope requires an object")
    scope = cast(dict[str, object], raw)
    if set(scope) != {"tenant_id", "project_id", "site_id", "version"}:
        raise PackageExecutionError("execution scope requires all four identity fields")
    parsed = StateScope(
        *(string(scope[k]) for k in ("tenant_id", "project_id", "site_id", "version"))
    )
    captured = time(value["captured_at"])
    context = ProvenanceContext(
        string(value["run_id"]),
        "planned-source-assertion-prefix",
        "1",
        string(value["code_revision"]),
        "local-uncontainerized",
        digest(value),
        None,
        (),
        captured,
    )
    string(str(source))
    ref = SourceReference(
        "local-file",
        source.absolute().as_uri(),
        parsed,
        time(value["observed_at"]),
        string(value["source_version"]) if value.get("source_version") is not None else None,
    )
    return ExecutionRequest(ref, context, captured, StageId.ASSERT)


def main() -> int:
    parser = Parser(
        description="Execute an explicit five-stage prefix; later stages remain not executed."
    )
    parser.add_argument("source", type=Path)
    for name in ("manifest", "registry", "config", "context", "normalization-policy"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--stop-after", choices=("ASSERT",), required=True)
    try:
        args = parser.parse_args()
        manifest = read(args.manifest, 1048576)
        registry = load_registry(read(args.registry, 1048576))
        config = load_config(read(args.config, 1048576))
        q = request(args.source, read(args.context, 32768))
        parameters = policy(read(args.normalization_policy, 32768))
        service = build_planned_bom_service(
            manifest=manifest,
            registry=registry,
            config=config,
            policy=parameters,
            clock=lambda: datetime.now(UTC),
        )
        result = service.execute(q).as_dict()
    except (SemanticContractError, SemanticTypeContractError) as exc:
        error: dict[str, object] = dict(exc.as_dict())
        if isinstance(exc, PlanningError):
            error["issues"] = [
                {"code": i.code, "path": i.path, "message": i.message} for i in exc.issues
            ]
        print(json.dumps(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
