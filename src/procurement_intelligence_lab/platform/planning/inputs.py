"""Strict, side-effect-free language-neutral deployment input loaders."""

from __future__ import annotations

import json
import tomllib
from typing import cast

from procurement_intelligence_lab.platform.domain_packages.compiler import (
    CompiledManifest,
    DomainPackageValidationError,
    ValidationIssue,
    compile_domain_package,
)
from procurement_intelligence_lab.platform.domain_packages.package import (
    DomainPackage,
    SourceProfile,
    StageBinding,
    StageId,
    StageMode,
)
from procurement_intelligence_lab.platform.planning.contracts import (
    ContractRef,
    ImplementationConfig,
    ImplementationDescriptor,
    ImplementationRegistry,
    PlanningError,
    StageSelection,
    reject,
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            reject("duplicate_key", "json", "duplicate object keys are forbidden")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    reject("invalid_json", "json", "non-finite numbers are forbidden")


def load_json(data: bytes, path: str) -> object:
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=_object_pairs, parse_constant=_invalid_constant
        )
    except PlanningError as exc:
        raise PlanningError(
            tuple(ValidationIssue(issue.code, path, issue.message) for issue in exc.issues)
        ) from None
    except (ValueError, UnicodeError, RecursionError):
        reject("invalid_json", path, "expected valid UTF-8 JSON")


def record(
    value: object, path: str, required: set[str], optional: set[str] | None = None
) -> dict[str, object]:
    if not isinstance(value, dict):
        reject("invalid_record", path, "expected an object")
    result = cast(dict[str, object], value)
    if not required <= result.keys() or result.keys() - required - (optional or set()):
        reject("invalid_fields", path, "missing required or unknown fields")
    return result


def string(value: object, path: str) -> str:
    if not isinstance(value, str):
        reject("invalid_type", path, "expected string")
    try:
        value.encode("utf-8")
    except UnicodeError:
        reject("invalid_text", path, "expected valid Unicode text")
    return value


def string_list(value: object, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        reject("invalid_type", path, "expected array of strings")
    return tuple(string(x, path) for x in cast(list[object], value))


def array(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        reject("invalid_type", path, "expected array")
    return cast(list[object], value)


def _stage(value: object, path: str) -> StageId:
    try:
        return StageId(string(value, path))
    except ValueError:
        reject("unknown_stage", path, "expected a catalog stage")


def _contract(value: object, path: str) -> ContractRef:
    data = record(value, path, {"name", "version"})
    name = string(data["name"], path + ".name")
    version = string(data["version"], path + ".version")
    try:
        return ContractRef(name, version)
    except PlanningError as exc:
        raise PlanningError(
            tuple(
                ValidationIssue(
                    issue.code, path + "." + issue.path.removeprefix("contract."), issue.message
                )
                for issue in exc.issues
            )
        ) from None


def load_registry(data: bytes) -> ImplementationRegistry:
    root = record(load_json(data, "registry"), "registry", {"schema_version", "implementations"})
    descriptors: list[ImplementationDescriptor] = []
    required = {
        "implementation_id",
        "descriptor_version",
        "implementation_version",
        "stage",
        "input_contract",
        "output_contract",
        "capabilities",
        "config_schema_version",
    }
    optional = {"required_settings", "optional_settings", "provider_version", "model_version"}
    for index, value in enumerate(array(root["implementations"], "registry.implementations")):
        path = f"registry.implementations[{index}]"
        item = record(value, path, required, optional)
        descriptors.append(
            ImplementationDescriptor(
                implementation_id=string(item["implementation_id"], path + ".implementation_id"),
                descriptor_version=string(item["descriptor_version"], path + ".descriptor_version"),
                implementation_version=string(
                    item["implementation_version"], path + ".implementation_version"
                ),
                stage=_stage(item["stage"], path + ".stage"),
                input_contract=_contract(item["input_contract"], path + ".input_contract"),
                output_contract=_contract(item["output_contract"], path + ".output_contract"),
                capabilities=string_list(item["capabilities"], path + ".capabilities"),
                config_schema_version=string(
                    item["config_schema_version"], path + ".config_schema_version"
                ),
                required_settings=string_list(
                    item.get("required_settings", []), path + ".required_settings"
                ),
                optional_settings=string_list(
                    item.get("optional_settings", []), path + ".optional_settings"
                ),
                provider_version=None
                if item.get("provider_version") is None
                else string(item["provider_version"], path + ".provider_version"),
                model_version=None
                if item.get("model_version") is None
                else string(item["model_version"], path + ".model_version"),
            )
        )
    return ImplementationRegistry(
        string(root["schema_version"], "registry.schema_version"), tuple(descriptors)
    )


def load_config(data: bytes) -> ImplementationConfig:
    try:
        value = tomllib.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        reject("invalid_toml", "config", "expected valid UTF-8 TOML with unique keys")
    root = record(
        value,
        "config",
        {
            "schema_version",
            "source_profile",
            "source_profile_version",
            "application_version",
            "selections",
        },
    )
    selections: list[StageSelection] = []
    for index, value in enumerate(array(root["selections"], "config.selections")):
        path = f"config.selections[{index}]"
        item = record(
            value, path, {"stage", "implementation_id", "config_schema_version", "settings"}
        )
        if not isinstance(item["settings"], dict):
            reject("invalid_settings", path + ".settings", "expected a string-valued table")
        settings = cast(dict[str, object], item["settings"])
        selections.append(
            StageSelection(
                _stage(item["stage"], path + ".stage"),
                string(item["implementation_id"], path + ".implementation_id"),
                string(item["config_schema_version"], path + ".config_schema_version"),
                tuple((key, string(value, path + ".settings")) for key, value in settings.items()),
            )
        )
    return ImplementationConfig(
        string(root["schema_version"], "config.schema_version"),
        string(root["source_profile"], "config.source_profile"),
        string(root["source_profile_version"], "config.source_profile_version"),
        string(root["application_version"], "config.application_version"),
        tuple(selections),
    )


def validate_manifest(data: bytes) -> CompiledManifest:
    """Reconstruct only the exact ratified schema, then reuse semantic compilation."""
    root = record(
        load_json(data, "manifest"),
        "manifest",
        {"domain_package_schema_version", "domain", "source_profile", "stages"},
    )
    domain = record(root["domain"], "manifest.domain", {"id", "version"})
    profile = record(root["source_profile"], "manifest.source_profile", {"id", "version"})
    bindings: list[StageBinding] = []
    fields = {
        "stage",
        "mode",
        "requirements",
        "domain_config_ref",
        "policy_refs",
        "eval_suite_ref",
        "neutral_semantics",
        "output_contract_verified",
    }
    for index, value in enumerate(array(root["stages"], "manifest.stages")):
        path = f"manifest.stages[{index}]"
        item = record(value, path, fields)
        try:
            mode = StageMode(string(item["mode"], path + ".mode"))
        except ValueError:
            reject("invalid_mode", path + ".mode", "expected EXECUTE, PASSTHROUGH or EMPTY")
        if not isinstance(item["output_contract_verified"], bool):
            reject("invalid_type", path + ".output_contract_verified", "expected boolean")
        refs = {
            key: None if item[key] is None else string(item[key], path + "." + key)
            for key in ("domain_config_ref", "eval_suite_ref", "neutral_semantics")
        }
        bindings.append(
            StageBinding(
                _stage(item["stage"], path + ".stage"),
                mode,
                string_list(item["requirements"], path + ".requirements"),
                refs["domain_config_ref"],
                string_list(item["policy_refs"], path + ".policy_refs"),
                refs["eval_suite_ref"],
                refs["neutral_semantics"],
                item["output_contract_verified"],
            )
        )
    profile_id = string(profile["id"], "manifest.source_profile.id")
    package = DomainPackage(
        string(root["domain_package_schema_version"], "manifest.domain_package_schema_version"),
        string(domain["id"], "manifest.domain.id"),
        string(domain["version"], "manifest.domain.version"),
        (
            SourceProfile(
                profile_id,
                string(profile["version"], "manifest.source_profile.version"),
                tuple(bindings),
            ),
        ),
    )
    try:
        return compile_domain_package(package, source_profile=profile_id)
    except DomainPackageValidationError as exc:
        raise PlanningError(
            tuple(ValidationIssue(x.code, "manifest." + x.path, x.message) for x in exc.issues)
        ) from None
