"""Deterministic validation and compilation of declarative domain packages."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from procurement_intelligence_lab.domain.package import (
    STAGE_DEFINITIONS,
    STAGE_ORDER,
    DomainPackage,
    SourceProfile,
    StageBinding,
    StageId,
    StageMode,
)

SUPPORTED_SCHEMA_VERSION = "1.0"
SUPPORTED_CAPABILITIES = frozenset(
    {
        "abstention",
        "authoritative_ids",
        "bounding_boxes",
        "contextual_evidence",
        "human_review",
        "page_coordinates",
        "probabilistic_evidence",
        "reading_order",
        "tables",
    }
)
_VERSION = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$")
_SCHEMA_VERSION = re.compile(r"^[0-9]+\.[0-9]+$")
_REF = re.compile(r"^[a-z][a-z0-9_.-]*(?:/[a-z][a-z0-9_.-]+)?@[0-9]+(?:\.[0-9]+)*$")
_FORBIDDEN_TOKENS = (
    "aws",
    "azure",
    "credential",
    "deployment",
    "docling",
    "gcp",
    "model",
    "openai",
    "region",
    "secret",
    "semantica",
    "service",
    "splink",
    "textract",
    "vertex",
)
_INVALID_EMPTY_SEMANTICS = frozenset({"failed", "none", "skipped", "unknown", "unresolved"})


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class DomainPackageValidationError(ValueError):
    """Raised when a package cannot be compiled without semantic inference."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        detail = "; ".join(f"{issue.code} at {issue.path}: {issue.message}" for issue in issues)
        super().__init__(detail)


@dataclass(frozen=True)
class CompiledManifest:
    """Canonical manifest bytes and its content hash."""

    manifest: Mapping[str, object]
    canonical_json: bytes
    manifest_hash: str


def compile_domain_package(
    package: object,
    *,
    source_profile: str = "default",
) -> CompiledManifest:
    """Validate and compile a package into deterministic, provider-neutral JSON."""

    issues: list[ValidationIssue] = []
    if not isinstance(package, DomainPackage):
        raise DomainPackageValidationError(
            (
                ValidationIssue(
                    "invalid_package",
                    "package",
                    "expected DomainPackage",
                ),
            )
        )
    _validate_package_header(package, issues)
    profile = _select_profile(package, source_profile, issues)
    if profile is not None:
        _validate_profile(profile, issues)

    if issues:
        raise DomainPackageValidationError(tuple(issues))
    assert profile is not None

    stages = [_compile_binding(binding) for binding in profile.bindings]
    payload: dict[str, object] = {
        "domain_package_schema_version": package.schema_version,
        "domain": {"id": package.domain_id, "version": package.domain_version},
        "source_profile": {
            "id": profile.profile_id,
            "version": profile.profile_version,
        },
        "stages": stages,
    }
    canonical_json = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return CompiledManifest(
        MappingProxyType(payload),
        canonical_json,
        hashlib.sha256(canonical_json).hexdigest(),
    )


def _validate_package_header(
    package: DomainPackage,
    issues: list[ValidationIssue],
) -> None:
    if not _SCHEMA_VERSION.fullmatch(package.schema_version):
        issues.append(
            ValidationIssue(
                "invalid_schema_version",
                "schema_version",
                "must use MAJOR.MINOR syntax",
            )
        )
    elif package.schema_version != SUPPORTED_SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                "unsupported_schema_version",
                "schema_version",
                f"compiler supports {SUPPORTED_SCHEMA_VERSION}",
            )
        )
    if not package.domain_id:
        issues.append(ValidationIssue("missing_domain_id", "domain_id", "must not be empty"))
    if not _VERSION.fullmatch(package.domain_version):
        issues.append(
            ValidationIssue(
                "invalid_domain_version",
                "domain_version",
                "must use MAJOR.MINOR or MAJOR.MINOR.PATCH syntax",
            )
        )
    if not package.source_profiles:
        issues.append(
            ValidationIssue(
                "missing_source_profiles",
                "source_profiles",
                "at least one complete profile is required",
            )
        )


def _select_profile(
    package: DomainPackage,
    profile_id: str,
    issues: list[ValidationIssue],
) -> SourceProfile | None:
    matches = tuple(
        profile for profile in package.source_profiles if profile.profile_id == profile_id
    )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        issues.append(
            ValidationIssue(
                "unknown_source_profile",
                "source_profile",
                f"profile {profile_id!r} is not declared",
            )
        )
    else:
        issues.append(
            ValidationIssue(
                "duplicate_source_profile",
                "source_profiles",
                f"profile {profile_id!r} is declared more than once",
            )
        )
    return None


def _validate_profile(profile: object, issues: list[ValidationIssue]) -> None:
    if not isinstance(profile, SourceProfile):
        issues.append(
            ValidationIssue(
                "invalid_source_profile",
                "source_profiles",
                "expected SourceProfile",
            )
        )
        return
    path = f"source_profiles[{profile.profile_id!r}]"
    if not profile.profile_id:
        issues.append(ValidationIssue("missing_source_profile_id", path, "must not be empty"))
    if not _VERSION.fullmatch(profile.profile_version):
        issues.append(
            ValidationIssue(
                "invalid_source_profile_version",
                f"{path}.profile_version",
                "must use MAJOR.MINOR or MAJOR.MINOR.PATCH syntax",
            )
        )
    bindings_value: object = cast(object, profile.bindings)
    if not isinstance(bindings_value, tuple):
        issues.append(
            ValidationIssue(
                "invalid_bindings",
                f"{path}.bindings",
                "must be a tuple of StageBinding records",
            )
        )
        return
    bindings = profile.bindings
    stages_list: list[object] = []
    for binding in bindings:
        binding_value: object = cast(object, binding)
        if isinstance(binding_value, StageBinding):
            stages_list.append(binding.stage)
    stages = tuple(stages_list)
    if len(stages) != len(set(stages)):
        issues.append(
            ValidationIssue(
                "duplicate_stage",
                f"{path}.bindings",
                "exactly one binding per stage is required",
            )
        )
    if stages != STAGE_ORDER:
        missing = tuple(stage.value for stage in STAGE_ORDER if stage not in stages)
        unknown = tuple(str(stage) for stage in stages if stage not in STAGE_DEFINITIONS)
        if missing:
            issues.append(
                ValidationIssue(
                    "missing_stage",
                    f"{path}.bindings",
                    f"missing stages: {', '.join(missing)}",
                )
            )
        if unknown:
            issues.append(
                ValidationIssue(
                    "unknown_stage",
                    f"{path}.bindings",
                    f"unknown stages: {', '.join(unknown)}",
                )
            )
        if not missing and not unknown:
            issues.append(
                ValidationIssue(
                    "reordered_stage",
                    f"{path}.bindings",
                    "bindings must follow the platform stage order",
                )
            )
    for index, binding in enumerate(bindings):
        _validate_binding(binding, f"{path}.bindings[{index}]", issues)


def _validate_binding(
    binding: object,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(binding, StageBinding):
        issues.append(ValidationIssue("invalid_binding", path, "expected StageBinding"))
        return
    stage_value: object = cast(object, binding.stage)
    if not isinstance(stage_value, StageId):
        issues.append(ValidationIssue("unknown_stage", f"{path}.stage", "must be a catalog stage"))
        return
    mode_value: object = cast(object, binding.mode)
    if not isinstance(mode_value, StageMode):
        issues.append(ValidationIssue("invalid_mode", f"{path}.mode", "must be a catalog mode"))
        return
    requirements_value: object = cast(object, binding.requirements)
    requirements_items = cast(tuple[object, ...], requirements_value)
    if not isinstance(requirements_value, tuple) or any(
        not isinstance(item, str) or not item for item in requirements_items
    ):
        issues.append(
            ValidationIssue(
                "invalid_requirements",
                f"{path}.requirements",
                "must contain non-empty capability IDs",
            )
        )
    else:
        requirements = tuple(cast(str, item) for item in requirements_items)
        duplicate_requirements = len(requirements) != len(set(requirements))
        if duplicate_requirements:
            issues.append(
                ValidationIssue(
                    "duplicate_requirement",
                    f"{path}.requirements",
                    "capability IDs must be unique",
                )
            )
        for capability in requirements:
            if capability not in SUPPORTED_CAPABILITIES:
                issues.append(
                    ValidationIssue(
                        "unsupported_capability",
                        f"{path}.requirements",
                        f"unsupported capability {capability!r}",
                    )
                )
    if binding.domain_config_ref is not None:
        _validate_reference(binding.domain_config_ref, f"{path}.domain_config_ref", issues)
    for index, reference in enumerate(binding.policy_refs):
        _validate_reference(reference, f"{path}.policy_refs[{index}]", issues)
    if binding.eval_suite_ref is not None:
        _validate_reference(binding.eval_suite_ref, f"{path}.eval_suite_ref", issues)
    _validate_provider_neutrality(binding, path, issues)

    stage = stage_value
    mode = mode_value
    definition = STAGE_DEFINITIONS.get(stage)
    if definition is None:
        return
    if mode is StageMode.EMPTY:
        if not binding.neutral_semantics:
            issues.append(
                ValidationIssue(
                    "missing_neutral_semantics",
                    f"{path}.neutral_semantics",
                    f"EMPTY requires {definition.empty_result!r}",
                )
            )
        elif binding.neutral_semantics != definition.empty_result:
            issues.append(
                ValidationIssue(
                    "invalid_neutral_semantics",
                    f"{path}.neutral_semantics",
                    f"must be {definition.empty_result!r} for {stage.value}",
                )
            )
    elif binding.neutral_semantics is not None:
        issues.append(
            ValidationIssue(
                "unexpected_neutral_semantics",
                f"{path}.neutral_semantics",
                "only EMPTY bindings may declare neutral semantics",
            )
        )
    if mode is StageMode.PASSTHROUGH and not binding.output_contract_verified:
        issues.append(
            ValidationIssue(
                "unverified_passthrough",
                f"{path}.output_contract_verified",
                "PASSTHROUGH requires explicit output-contract verification",
            )
        )
    if mode is not StageMode.PASSTHROUGH and binding.output_contract_verified:
        issues.append(
            ValidationIssue(
                "unexpected_contract_verification",
                f"{path}.output_contract_verified",
                "only PASSTHROUGH may set output-contract verification",
            )
        )


def _validate_reference(
    reference: object,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(reference, str) or not _REF.fullmatch(reference):
        issues.append(
            ValidationIssue(
                "invalid_reference",
                path,
                "must be a versioned namespace reference such as procurement.policy@1",
            )
        )
    elif any(token in reference.casefold() for token in _FORBIDDEN_TOKENS):
        issues.append(
            ValidationIssue(
                "provider_leakage",
                path,
                "portable references must not contain provider/runtime selections",
            )
        )


def _validate_provider_neutrality(
    binding: StageBinding,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    values = (
        binding.domain_config_ref,
        *binding.policy_refs,
        binding.eval_suite_ref,
    )
    for value in values:
        if isinstance(value, str) and any(token in value.casefold() for token in _FORBIDDEN_TOKENS):
            issues.append(
                ValidationIssue(
                    "provider_leakage",
                    path,
                    "portable bindings must not select providers, models, services, regions, or deployment",
                )
            )


def _compile_binding(binding: StageBinding) -> dict[str, object]:
    return {
        "stage": binding.stage.value,
        "mode": binding.mode.value,
        "requirements": sorted(binding.requirements),
        "domain_config_ref": binding.domain_config_ref,
        "policy_refs": sorted(binding.policy_refs),
        "eval_suite_ref": binding.eval_suite_ref,
        "neutral_semantics": binding.neutral_semantics,
        "output_contract_verified": binding.output_contract_verified,
    }
