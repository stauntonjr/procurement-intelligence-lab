"""Immutable, deployment-owned planning inputs and content-addressed output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NoReturn, cast

from procurement_intelligence_lab.platform.domain_packages.compiler import (
    SUPPORTED_CAPABILITIES,
    ValidationIssue,
)
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.semantics.errors import ErrorCode, SemanticContractError

PLANNING_SCHEMA_VERSION = "1.0"
_VERSION = re.compile(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?")
_KEY = re.compile(r"[a-z][a-z0-9_]*")


class PlanningError(SemanticContractError):
    """Stable admission/planning failure, without configuration values or tracebacks."""

    code = ErrorCode.PACKAGE_PLANNING_INVALID

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{x.code} at {x.path}: {x.message}" for x in issues))


def reject(code: str, path: str, message: str) -> NoReturn:
    raise PlanningError((ValidationIssue(code, path, message),))


def text(value: object, path: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        reject("invalid_text", path, "expected non-empty text without surrounding whitespace")
    try:
        value.encode("utf-8")
    except UnicodeError:
        reject("invalid_text", path, "expected valid Unicode text")


def version(value: object, path: str) -> None:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        reject("invalid_version", path, "expected MAJOR.MINOR or MAJOR.MINOR.PATCH")


def schema(value: object, path: str) -> None:
    if value != PLANNING_SCHEMA_VERSION:
        reject("unsupported_schema_version", path, "planning supports schema 1.0 only")


def strings(value: object, path: str, *, keys: bool = False) -> None:
    if not isinstance(value, tuple):
        reject("invalid_sequence", path, "expected immutable tuple")
    assert isinstance(value, tuple)
    items = cast(tuple[object, ...], value)
    for item in items:
        text(item, path)
        if keys and not _KEY.fullmatch(cast(str, item)):
            reject("invalid_setting_name", path, "settings use lowercase identifier keys")
    if len(set(items)) != len(items):
        reject("duplicate_value", path, "values must be unique")


@dataclass(frozen=True)
class ContractRef:
    name: str
    version: str

    def __post_init__(self) -> None:
        text(self.name, "contract.name")
        version(self.version, "contract.version")


@dataclass(frozen=True)
class ImplementationDescriptor:
    """Advertisement, never a callback or proof that a provider is available."""

    implementation_id: str
    descriptor_version: str
    implementation_version: str
    stage: StageId
    input_contract: ContractRef
    output_contract: ContractRef
    capabilities: tuple[str, ...]
    config_schema_version: str
    required_settings: tuple[str, ...] = ()
    optional_settings: tuple[str, ...] = ()
    provider_version: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        path = "registry.implementations"
        text(self.implementation_id, path + ".implementation_id")
        version(self.descriptor_version, path + ".descriptor_version")
        text(self.implementation_version, path + ".implementation_version")
        if not isinstance(cast(object, self.stage), StageId):
            reject("unknown_stage", path + ".stage", "expected a catalog stage")
        for direction in ("input_contract", "output_contract"):
            if not isinstance(getattr(self, direction), ContractRef):
                reject("invalid_contract", path + "." + direction, "expected ContractRef")
        version(self.config_schema_version, path + ".config_schema_version")
        strings(self.capabilities, path + ".capabilities")
        if not set(self.capabilities) <= SUPPORTED_CAPABILITIES:
            reject("unsupported_capability", path + ".capabilities", "capability is not catalogued")
        strings(self.required_settings, path + ".required_settings", keys=True)
        strings(self.optional_settings, path + ".optional_settings", keys=True)
        if set(self.required_settings) & set(self.optional_settings):
            reject("ambiguous_settings", path, "required and optional settings must be disjoint")
        for field in ("provider_version", "model_version"):
            value = getattr(self, field)
            if value is not None:
                text(value, path + "." + field)


@dataclass(frozen=True)
class ImplementationRegistry:
    schema_version: str
    implementations: tuple[ImplementationDescriptor, ...]

    def __post_init__(self) -> None:
        schema(self.schema_version, "registry.schema_version")
        if not isinstance(cast(object, self.implementations), tuple) or any(
            not isinstance(cast(object, x), ImplementationDescriptor) for x in self.implementations
        ):
            reject("invalid_registry", "registry.implementations", "expected descriptor tuple")
        ids = tuple(x.implementation_id for x in self.implementations)
        if len(ids) != len(set(ids)):
            reject("duplicate_implementation", "registry.implementations", "IDs must be unique")


@dataclass(frozen=True)
class StageSelection:
    stage: StageId
    implementation_id: str
    config_schema_version: str
    settings: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        path = "config.selections"
        if not isinstance(cast(object, self.stage), StageId):
            reject("unknown_stage", path + ".stage", "expected a catalog stage")
        text(self.implementation_id, path + ".implementation_id")
        version(self.config_schema_version, path + ".config_schema_version")
        if not isinstance(cast(object, self.settings), tuple):
            reject("invalid_settings", path + ".settings", "expected immutable string pairs")
        for item in self.settings:
            if not isinstance(cast(object, item), tuple) or len(item) != 2:
                reject("invalid_settings", path + ".settings", "expected immutable string pairs")
            text(item[0], path + ".settings.key")
            # Values are opaque references/options. Empty strings are rejected, never defaulted.
            text(item[1], path + ".settings.value")
        strings(tuple(item[0] for item in self.settings), path + ".settings", keys=True)


@dataclass(frozen=True)
class ImplementationConfig:
    schema_version: str
    source_profile: str
    source_profile_version: str
    application_version: str
    selections: tuple[StageSelection, ...]

    def __post_init__(self) -> None:
        schema(self.schema_version, "config.schema_version")
        text(self.source_profile, "config.source_profile")
        version(self.source_profile_version, "config.source_profile_version")
        text(self.application_version, "config.application_version")
        if not isinstance(cast(object, self.selections), tuple) or any(
            not isinstance(cast(object, x), StageSelection) for x in self.selections
        ):
            reject("invalid_selections", "config.selections", "expected StageSelection tuple")
        stages = tuple(x.stage for x in self.selections)
        if len(set(stages)) != len(stages):
            reject("duplicate_selection", "config.selections", "select each stage at most once")


@dataclass(frozen=True)
class PhysicalPlan:
    """Canonical UTF-8 JSON payload and SHA-256; no mutable projection or run status."""

    canonical_json: bytes
    plan_hash: str
