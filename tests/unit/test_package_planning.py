from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, replace
from typing import cast

import pytest

from procurement_intelligence_lab.bootstrap import compile_procurement_manifest
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.planning.contracts import (
    ContractRef,
    ImplementationRegistry,
    PlanningError,
)
from procurement_intelligence_lab.platform.planning.inputs import (
    load_config,
    load_registry,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from tests.planning_fixtures import conformance_manifest, planning_inputs


def test_real_procurement_plan_retains_requirements_neutrals_versions_and_hashes() -> None:
    compiled = compile_procurement_manifest()
    registry, config = planning_inputs(compiled.canonical_json)
    result = plan_manifest(compiled.canonical_json, registry=registry, config=config)
    payload = json.loads(result.canonical_json)
    assert result.plan_hash == hashlib.sha256(result.canonical_json).hexdigest()
    assert payload["manifest_hash"] == compiled.manifest_hash
    assert payload["domain"] == {"id": "procurement", "version": "0.1.0"}
    assert payload["source_profile"] == {"id": "bom-table", "version": "1.0.0"}
    assert payload["application_version"] == "test-build"
    assert len(payload["stages"]) == 12
    assert payload["physical_steps"] == [x["stage"] for x in payload["stages"][:9]]
    assert payload["stages"][1]["capability_checks"] == [
        {"capability": "tables", "satisfied": True}
    ]
    assert payload["stages"][2]["domain_config_ref"] == "procurement.mapping/bom-table@1"
    assert payload["stages"][0]["implementation"]["input_contract"] == {
        "name": "SourceReference",
        "version": "1.0",
    }
    assert [x["disposition"] for x in payload["stages"][9:]] == ["TYPED_EMPTY"] * 3
    assert payload["stages"][-1]["neutral_semantics"] == "no_action_attempted"
    assert payload["stages"][-1]["implementation"] is None
    assert b"fixture://offline" not in result.canonical_json


def test_non_procurement_uses_same_planner_with_passthrough_and_empty() -> None:
    manifest = conformance_manifest()
    registry, config = planning_inputs(manifest)
    payload = json.loads(plan_manifest(manifest, registry=registry, config=config).canonical_json)
    assert payload["physical_steps"] == ["INGEST"]
    assert payload["stages"][1]["disposition"] == "VALIDATE_PASSTHROUGH"
    assert payload["stages"][1]["output_contract_verified"] is True
    assert payload["stages"][1]["implementation"] is None
    assert "procurement" not in json.dumps(payload)


def test_order_and_json_format_are_not_provider_selection_or_identity() -> None:
    manifest = compile_procurement_manifest().canonical_json
    registry, config = planning_inputs(manifest)
    selections = tuple(
        replace(s, settings=(("region", "local"), *s.settings)) for s in config.selections
    )
    config = replace(config, selections=selections)
    expected = plan_manifest(manifest, registry=registry, config=config)
    reordered = replace(
        config,
        selections=tuple(
            replace(s, settings=tuple(reversed(s.settings))) for s in reversed(config.selections)
        ),
    )
    actual = plan_manifest(
        json.dumps(json.loads(manifest), indent=2).encode(),
        registry=replace(registry, implementations=tuple(reversed(registry.implementations))),
        config=reordered,
    )
    assert actual == expected


@pytest.mark.parametrize(
    "change",
    ["descriptor", "implementation", "provider", "model", "config", "application", "manifest"],
)
def test_relevant_versions_and_settings_change_plan_identity(change: str) -> None:
    manifest = compile_procurement_manifest().canonical_json
    registry, config = planning_inputs(manifest)
    before = plan_manifest(manifest, registry=registry, config=config)
    first = registry.implementations[0]
    if change == "descriptor":
        first = replace(first, descriptor_version="1.0.1")
    elif change == "implementation":
        first = replace(first, implementation_version="fixture-only-2")
    elif change == "provider":
        first = replace(first, provider_version="provider-2")
    elif change == "model":
        first = replace(first, model_version="model-2")
    elif change == "config":
        selection = replace(config.selections[0], settings=(("endpoint_ref", "fixture://other"),))
        config = replace(config, selections=(selection, *config.selections[1:]))
    elif change == "application":
        config = replace(config, application_version="another-build")
    else:
        data = json.loads(manifest)
        data["domain"]["version"] = "0.1.1"
        manifest = json.dumps(data).encode()
    registry = replace(registry, implementations=(first, *registry.implementations[1:]))
    after = plan_manifest(manifest, registry=registry, config=config)
    assert before.plan_hash != after.plan_hash


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("missing_selection", "missing_implementation"),
        ("unknown_id", "unknown_implementation"),
        ("wrong_stage", "implementation_stage_mismatch"),
        ("capabilities", "insufficient_capabilities"),
        ("contract_name", "incompatible_contract"),
        ("contract_version", "incompatible_contract"),
        ("config_version", "incompatible_config_version"),
        ("missing_setting", "missing_setting"),
        ("unknown_setting", "unknown_setting"),
        ("profile", "source_profile_mismatch"),
        ("profile_version", "source_profile_mismatch"),
        ("neutral_selection", "unexpected_implementation"),
    ],
)
def test_incompatible_plan_fails_closed(change: str, code: str) -> None:
    manifest = compile_procurement_manifest().canonical_json
    registry, config = planning_inputs(manifest)
    descriptor = registry.implementations[0]
    selection = config.selections[0]
    if change == "missing_selection":
        config = replace(config, selections=config.selections[1:])
    elif change == "unknown_id":
        selection = replace(selection, implementation_id="missing")
    elif change == "wrong_stage":
        descriptor = replace(descriptor, stage=StageId.MAP)
    elif change == "capabilities":
        registry = replace(
            registry,
            implementations=tuple(replace(x, capabilities=()) for x in registry.implementations),
        )
    elif change == "contract_name":
        descriptor = replace(descriptor, input_contract=ContractRef("Artifact", "1.0"))
    elif change == "contract_version":
        descriptor = replace(descriptor, input_contract=ContractRef("SourceReference", "2.0"))
    elif change == "config_version":
        selection = replace(selection, config_schema_version="2.0")
    elif change == "missing_setting":
        selection = replace(selection, settings=())
    elif change == "unknown_setting":
        selection = replace(selection, settings=(*selection.settings, ("unknown", "hidden")))
    elif change == "profile":
        config = replace(config, source_profile="other")
    elif change == "profile_version":
        config = replace(config, source_profile_version="99.0.0")
    elif change == "neutral_selection":
        config = replace(
            config, selections=(*config.selections, replace(selection, stage=StageId.ACT))
        )
    if change not in ("missing_selection", "neutral_selection"):
        config = replace(config, selections=(selection, *config.selections[1:]))
    if change != "capabilities":
        registry = replace(registry, implementations=(descriptor, *registry.implementations[1:]))
    with pytest.raises(PlanningError) as caught:
        plan_manifest(manifest, registry=registry, config=config)
    assert code in {issue.code for issue in caught.value.issues}
    assert caught.value.as_dict()["code"] == "pil.input.package_planning_invalid"
    assert all(issue.path for issue in caught.value.issues)
    assert "hidden" not in str(caught.value)


@pytest.mark.parametrize(
    "data", [b"null", b"[]", b"{}", b'{"domain": 1, "domain":2}', b'{"x":NaN}', b"\xff"]
)
def test_malformed_manifest_has_typed_failure(data: bytes) -> None:
    registry, config = planning_inputs(conformance_manifest())
    with pytest.raises(PlanningError):
        plan_manifest(data, registry=registry, config=config)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("schema", "1.1"),
        ("profile", 7),
        ("stage_mode", "skip"),
        ("stages", []),
        ("stage_duplicate", None),
        ("stage_order", None),
        ("requirements", ["unknown"]),
        ("passthrough", False),
        ("neutral", "no_action_attempted"),
        ("extra", "callback"),
        ("bool", 1),
        ("policies", [1]),
        ("reference", "aws.region@1"),
    ],
)
def test_manifest_revalidation_does_not_trust_compiler_shaped_json(
    path: str, value: object
) -> None:
    data = json.loads(conformance_manifest())
    registry, config = planning_inputs(conformance_manifest())
    if path == "schema":
        data["domain_package_schema_version"] = value
    elif path == "profile":
        data["source_profile"]["version"] = value
    elif path == "stages":
        data["stages"] = value
    elif path == "stage_duplicate":
        data["stages"][1] = data["stages"][0]
    elif path == "stage_order":
        data["stages"].reverse()
    elif path == "extra":
        data["stages"][0]["execute"] = value
    elif path == "stage_mode":
        data["stages"][0]["mode"] = value
    elif path == "requirements":
        data["stages"][0]["requirements"] = value
    elif path == "passthrough" or path == "bool":
        data["stages"][1]["output_contract_verified"] = value
    elif path == "policies":
        data["stages"][0]["policy_refs"] = value
    elif path == "reference":
        data["stages"][0]["domain_config_ref"] = value
    else:
        data["stages"][2]["neutral_semantics"] = value
    with pytest.raises(PlanningError):
        plan_manifest(json.dumps(data).encode(), registry=registry, config=config)


def test_duplicate_ambiguous_and_mutable_records_are_rejected() -> None:
    registry, config = planning_inputs(conformance_manifest())
    with pytest.raises(PlanningError):
        replace(registry, implementations=registry.implementations * 2)
    with pytest.raises(PlanningError):
        replace(config, selections=config.selections * 2)
    with pytest.raises(PlanningError):
        replace(config.selections[0], settings=(("x", "a"), ("x", "b")))
    with pytest.raises(PlanningError):
        replace(registry.implementations[0], capabilities=cast(tuple[str, ...], ["tables"]))
    with pytest.raises(PlanningError):
        replace(registry, schema_version="2.0")
    with pytest.raises(PlanningError):
        replace(config, schema_version="1.1")
    with pytest.raises(FrozenInstanceError):
        setattr(registry.implementations[0], "implementation_id", "changed")  # noqa: B010
    with pytest.raises(PlanningError):
        replace(registry.implementations[0], required_settings=("x",), optional_settings=("x",))
    with pytest.raises(PlanningError):
        replace(registry.implementations[0], capabilities=("tables", "tables"))
    with pytest.raises(PlanningError):
        replace(config.selections[0], settings=(("x", cast(str, 0)),))


def test_loaders_reject_ambiguous_or_invalid_unused_descriptors() -> None:
    registry, _ = planning_inputs(conformance_manifest())
    payload = json.loads(json.dumps(asdict(registry)))
    assert load_registry(json.dumps(payload).encode()) == registry
    bad = asdict(registry.implementations[0])
    bad["implementation_id"] = "unused"
    bad["capabilities"] = ["unknown"]
    payload["implementations"].append(bad)
    with pytest.raises(PlanningError):
        load_registry(json.dumps(payload).encode())
    with pytest.raises(PlanningError):
        load_registry(b'{"schema_version":"1.0","schema_version":"1.0","implementations":[]}')
    with pytest.raises(PlanningError):
        load_config(b'schema_version="1.0"\nschema_version="1.0"')
    with pytest.raises(PlanningError):
        load_config(b"\xff")


def test_all_empty_manifest_needs_no_registry_or_selection() -> None:
    data = json.loads(conformance_manifest())
    from procurement_intelligence_lab.platform.domain_packages.package import STAGE_CATALOG

    for item, definition in zip(data["stages"], STAGE_CATALOG, strict=True):
        item.update(
            mode="EMPTY", output_contract_verified=False, neutral_semantics=definition.empty_result
        )
    _, config = planning_inputs(conformance_manifest())
    result = plan_manifest(
        json.dumps(data).encode(),
        registry=ImplementationRegistry("1.0", ()),
        config=replace(config, selections=()),
    )
    assert json.loads(result.canonical_json)["physical_steps"] == []


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("implementation_id", ""),
        ("descriptor_version", "future"),
        ("implementation_version", None),
        ("stage", "UNKNOWN"),
        ("input_contract", {"name": "SourceReference"}),
        ("output_contract", []),
        ("capabilities", None),
        ("required_settings", ["endpoint_ref", "endpoint_ref"]),
        ("optional_settings", ["endpoint_ref"]),
        ("provider_version", 0),
        ("model_version", False),
        ("config_schema_version", 0.5),
    ],
)
def test_registry_boundary_rejects_malformed_descriptor_fields(field: str, bad: object) -> None:
    registry, _ = planning_inputs(conformance_manifest())
    payload = json.loads(json.dumps(asdict(registry)))
    payload["implementations"][0][field] = bad
    with pytest.raises(PlanningError):
        load_registry(json.dumps(payload).encode())


@pytest.mark.parametrize("value", [0, -1, 0.5, True, [], {}, None])
def test_toml_settings_do_not_coerce_numeric_missing_or_container_values(value: object) -> None:
    registry, config = planning_inputs(conformance_manifest())
    with pytest.raises(PlanningError):
        replace(config.selections[0], settings=(("endpoint_ref", cast(str, value)),))
    # String-valued options stay opaque; the planner invents no business numeric policy.
    assert plan_manifest(
        conformance_manifest(),
        registry=registry,
        config=replace(
            config, selections=(replace(config.selections[0], settings=(("endpoint_ref", "0.5"),)),)
        ),
    ).plan_hash


def test_invalid_unused_contract_is_rejected_and_unused_compatible_choice_is_not_selected() -> None:
    manifest = conformance_manifest()
    registry, config = planning_inputs(manifest)
    baseline = plan_manifest(manifest, registry=registry, config=config)
    unused = replace(registry.implementations[0], implementation_id="other")
    assert (
        plan_manifest(
            manifest,
            registry=replace(registry, implementations=(*registry.implementations, unused)),
            config=config,
        )
        == baseline
    )
    with pytest.raises(PlanningError) as caught:
        plan_manifest(
            manifest,
            registry=replace(
                registry,
                implementations=(
                    *registry.implementations,
                    replace(unused, output_contract=ContractRef("Artifact", "2.0")),
                ),
            ),
            config=config,
        )
    assert caught.value.issues[0].code == "incompatible_contract"


@pytest.mark.parametrize("field", ["id", "version"])
def test_unrepresentable_unicode_has_typed_failure(field: str) -> None:
    data = json.loads(conformance_manifest())
    data["domain"][field] = "\ud800"
    registry, config = planning_inputs(conformance_manifest())
    with pytest.raises(PlanningError):
        plan_manifest(json.dumps(data).encode(), registry=registry, config=config)
