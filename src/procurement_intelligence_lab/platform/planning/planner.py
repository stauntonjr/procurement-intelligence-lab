"""Deterministic logical-to-physical planning, without invoking implementations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import cast

from procurement_intelligence_lab.platform.domain_packages.compiler import ValidationIssue
from procurement_intelligence_lab.platform.domain_packages.contract_registry import (
    CONTRACT_VERSIONS,
    validate_stage_contract_registry,
)
from procurement_intelligence_lab.platform.domain_packages.package import (
    STAGE_DEFINITIONS,
    StageId,
    StageMode,
)
from procurement_intelligence_lab.platform.planning.contracts import (
    PLANNING_SCHEMA_VERSION,
    ImplementationConfig,
    ImplementationDescriptor,
    ImplementationRegistry,
    PhysicalPlan,
    PlanningError,
    reject,
)
from procurement_intelligence_lab.platform.planning.inputs import canonical, validate_manifest


def _descriptor_payload(item: ImplementationDescriptor) -> dict[str, object]:
    result = asdict(item)
    for key in ("capabilities", "required_settings", "optional_settings"):
        result[key] = sorted(result[key])
    return result


def _config_hash(config: ImplementationConfig) -> str:
    result = asdict(config)
    result["selections"] = [
        {**asdict(item), "settings": dict(sorted(item.settings))}
        for item in sorted(config.selections, key=lambda x: x.stage.value)
    ]
    return hashlib.sha256(canonical(result)).hexdigest()


def plan_manifest(
    manifest: bytes,
    *,
    registry: ImplementationRegistry,
    config: ImplementationConfig,
) -> PhysicalPlan:
    """Validate explicit deployment choices and retain every logical disposition.

    Registry metadata is a compatibility advertisement. It neither proves availability
    nor grants authority to execute, materialize data, or perform an action.
    """
    if not isinstance(cast(object, manifest), bytes):
        reject("invalid_manifest", "manifest", "expected UTF-8 JSON bytes")
    if not isinstance(cast(object, registry), ImplementationRegistry) or not isinstance(
        cast(object, config), ImplementationConfig
    ):
        reject(
            "invalid_planning_input", "planning", "expected immutable registry and config records"
        )
    validate_stage_contract_registry()
    compiled = validate_manifest(manifest)
    payload = json.loads(compiled.canonical_json)
    if payload["source_profile"] != {
        "id": config.source_profile,
        "version": config.source_profile_version,
    }:
        reject(
            "source_profile_mismatch",
            "config.source_profile",
            "selected profile ID/version does not match manifest",
        )

    issues: list[ValidationIssue] = []
    for item in sorted(registry.implementations, key=lambda x: x.implementation_id):
        definition = STAGE_DEFINITIONS[item.stage]
        for direction in ("input_contract", "output_contract"):
            reference = getattr(item, direction)
            expected = getattr(definition, direction)
            if reference.name != expected or reference.version != CONTRACT_VERSIONS[expected]:
                issues.append(
                    ValidationIssue(
                        "incompatible_contract",
                        f"registry.implementations[{item.implementation_id}].{item.stage.value}.{direction}",
                        "descriptor must match the catalog name and supported semantic-contract version",
                    )
                )
    by_id = {item.implementation_id: item for item in registry.implementations}
    selections = {item.stage: item for item in config.selections}
    planned: list[dict[str, object]] = []
    physical_steps: list[str] = []
    for binding in cast(list[dict[str, object]], payload["stages"]):
        stage = StageId(cast(str, binding["stage"]))
        definition = STAGE_DEFINITIONS[stage]
        mode = StageMode(cast(str, binding["mode"]))
        path = f"source_profiles[{config.source_profile}].stages[{stage.value}]"
        selection = selections.get(stage)
        implementation: dict[str, object] | None = None
        checks: list[dict[str, object]] = []
        if mode is StageMode.EXECUTE:
            disposition = "EXECUTE"
            if selection is None:
                issues.append(
                    ValidationIssue(
                        "missing_implementation", path, "EXECUTE requires an explicit selection"
                    )
                )
            elif selection.implementation_id not in by_id:
                issues.append(
                    ValidationIssue("unknown_implementation", path, "selected ID is not registered")
                )
            else:
                descriptor = by_id[selection.implementation_id]
                if descriptor.stage is not stage:
                    issues.append(
                        ValidationIssue(
                            "implementation_stage_mismatch",
                            path,
                            "selected descriptor belongs to another stage",
                        )
                    )
                required = cast(list[str], binding["requirements"])
                checks = [
                    {"capability": capability, "satisfied": capability in descriptor.capabilities}
                    for capability in required
                ]
                if any(not check["satisfied"] for check in checks):
                    issues.append(
                        ValidationIssue(
                            "insufficient_capabilities",
                            path,
                            "selected descriptor lacks required capabilities",
                        )
                    )
                if selection.config_schema_version != descriptor.config_schema_version:
                    issues.append(
                        ValidationIssue(
                            "incompatible_config_version",
                            path,
                            "selection and descriptor config-schema versions must match",
                        )
                    )
                keys = {key for key, _ in selection.settings}
                if set(descriptor.required_settings) - keys:
                    issues.append(
                        ValidationIssue(
                            "missing_setting", path, "required deployment setting is absent"
                        )
                    )
                if keys - set(descriptor.required_settings) - set(descriptor.optional_settings):
                    issues.append(
                        ValidationIssue(
                            "unknown_setting", path, "deployment settings contain unsupported keys"
                        )
                    )
                implementation = _descriptor_payload(descriptor)
                physical_steps.append(stage.value)
        else:
            disposition = "TYPED_EMPTY" if mode is StageMode.EMPTY else "VALIDATE_PASSTHROUGH"
            if selection is not None:
                issues.append(
                    ValidationIssue(
                        "unexpected_implementation",
                        path,
                        "neutral stages cannot select an implementation",
                    )
                )
        planned.append(
            {
                **binding,
                "input_contract": {
                    "name": definition.input_contract,
                    "version": CONTRACT_VERSIONS[definition.input_contract],
                },
                "output_contract": {
                    "name": definition.output_contract,
                    "version": CONTRACT_VERSIONS[definition.output_contract],
                },
                "disposition": disposition,
                "capability_checks": checks,
                "implementation": implementation,
            }
        )
    if issues:
        raise PlanningError(tuple(issues))
    result = canonical(
        {
            "plan_schema_version": PLANNING_SCHEMA_VERSION,
            "domain_package_schema_version": payload["domain_package_schema_version"],
            "domain": payload["domain"],
            "source_profile": payload["source_profile"],
            "manifest_hash": compiled.manifest_hash,
            "runtime_config_hash": _config_hash(config),
            "registry_schema_version": registry.schema_version,
            "runtime_config_schema_version": config.schema_version,
            "application_version": config.application_version,
            "stages": planned,
            "physical_steps": physical_steps,
        }
    )
    return PhysicalPlan(result, hashlib.sha256(result).hexdigest())
