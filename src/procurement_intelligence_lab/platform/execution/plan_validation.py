"""Admit retained plan evidence, including direct receipt construction."""

import json
from hashlib import sha256
from typing import Any, cast

from procurement_intelligence_lab.platform.domain_packages.contract_registry import (
    CONTRACT_VERSIONS,
)
from procurement_intelligence_lab.platform.domain_packages.package import STAGE_CATALOG
from procurement_intelligence_lab.platform.execution.identity import canonical, digest_text, text
from procurement_intelligence_lab.platform.planning.contracts import PhysicalPlan
from procurement_intelligence_lab.platform.planning.inputs import load_registry, validate_manifest
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionError,
    SemanticContractError,
)

BINDING_FIELDS = frozenset(
    (
        "stage",
        "mode",
        "requirements",
        "domain_config_ref",
        "policy_refs",
        "eval_suite_ref",
        "neutral_semantics",
        "output_contract_verified",
    )
)
PLAN_FIELDS = frozenset(
    (
        "plan_schema_version",
        "domain_package_schema_version",
        "domain",
        "source_profile",
        "manifest_hash",
        "runtime_config_hash",
        "registry_schema_version",
        "runtime_config_schema_version",
        "application_version",
        "stages",
        "physical_steps",
    )
)
STAGE_FIELDS = BINDING_FIELDS | frozenset(
    ("input_contract", "output_contract", "disposition", "capability_checks", "implementation")
)


def plan_payload(plan: PhysicalPlan) -> dict[str, Any]:
    if type(plan) is not PhysicalPlan or type(plan.canonical_json) is not bytes:
        raise PackageExecutionError("receipt requires a typed canonical plan")
    if sha256(plan.canonical_json).hexdigest() != plan.plan_hash:
        raise PackageExecutionError("plan digest does not match retained bytes")
    try:
        raw: object = json.loads(plan.canonical_json)
        if not isinstance(raw, dict):
            raise TypeError
        data = cast(dict[str, Any], raw)
        if frozenset(data) != PLAN_FIELDS or canonical(data) != plan.canonical_json:
            raise ValueError
        if any(
            data[k] != "1.0"
            for k in (
                "plan_schema_version",
                "registry_schema_version",
                "runtime_config_schema_version",
            )
        ):
            raise ValueError
        text(data["application_version"])
        digest_text(data["runtime_config_hash"])
        raw_stages: object = data["stages"]
        if not isinstance(raw_stages, list):
            raise TypeError
        items = cast(list[object], raw_stages)
        if len(items) != 12:
            raise ValueError
        stages: list[dict[str, Any]] = []
        for item, d in zip(items, STAGE_CATALOG, strict=True):
            if not isinstance(item, dict):
                raise TypeError
            b = cast(dict[str, Any], item)
            if frozenset(b) != STAGE_FIELDS or b["stage"] != d.stage.value:
                raise ValueError
            stages.append(b)
        manifest = {
            k: data[k] for k in ("domain_package_schema_version", "domain", "source_profile")
        }
        manifest["stages"] = [{k: b[k] for k in BINDING_FIELDS} for b in stages]
        compiled = validate_manifest(canonical(manifest))
        if (
            canonical(manifest) != compiled.canonical_json
            or compiled.manifest_hash != data["manifest_hash"]
        ):
            raise ValueError
        descriptors = load_registry(
            canonical(
                {
                    "schema_version": "1.0",
                    "implementations": [
                        b["implementation"] for b in stages if b["mode"] == "EXECUTE"
                    ],
                }
            )
        )
        by_id = {d.implementation_id: d for d in descriptors.implementations}
        steps: list[str] = []
        for b, d in zip(stages, STAGE_CATALOG, strict=True):
            for direction in ("input_contract", "output_contract"):
                name = getattr(d, direction)
                if b[direction] != {"name": name, "version": CONTRACT_VERSIONS[name]}:
                    raise ValueError
            if b["mode"] == "EXECUTE":
                impl = b["implementation"]
                registered = by_id[impl["implementation_id"]]
                if registered.stage is not d.stage:
                    raise ValueError
                if (
                    registered.input_contract.name != d.input_contract
                    or registered.output_contract.name != d.output_contract
                ):
                    raise ValueError
                if (
                    registered.input_contract.version != b["input_contract"]["version"]
                    or registered.output_contract.version != b["output_contract"]["version"]
                ):
                    raise ValueError
                checks = [
                    {"capability": c, "satisfied": c in registered.capabilities}
                    for c in b["requirements"]
                ]
                if (
                    b["disposition"] != "EXECUTE"
                    or canonical(b["capability_checks"]) != canonical(checks)
                    or any(not c["satisfied"] for c in checks)
                ):
                    raise ValueError
                steps.append(d.stage.value)
            elif (
                b["implementation"] is not None
                or b["capability_checks"]
                or b["disposition"]
                != ("TYPED_EMPTY" if b["mode"] == "EMPTY" else "VALIDATE_PASSTHROUGH")
            ):
                raise ValueError
        if data["physical_steps"] != steps:
            raise ValueError
    except (ValueError, TypeError, KeyError, RecursionError, SemanticContractError):
        raise PackageExecutionError("invalid retained plan payload") from None
    return data
