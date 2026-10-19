"""Planning-only descriptor fixtures: no executor or operational authority."""

from procurement_intelligence_lab.platform.domain_packages.compiler import compile_domain_package
from procurement_intelligence_lab.platform.domain_packages.package import (
    STAGE_CATALOG,
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
    StageSelection,
)


def conformance_manifest() -> bytes:
    bindings = tuple(
        StageBinding(item.stage, StageMode.EXECUTE)
        if item.stage is StageId.INGEST
        else StageBinding(item.stage, StageMode.PASSTHROUGH, output_contract_verified=True)
        if item.stage is StageId.STRUCTURE
        else StageBinding(item.stage, StageMode.EMPTY, neutral_semantics=item.empty_result)
        for item in STAGE_CATALOG
    )
    return compile_domain_package(
        DomainPackage("1.0", "conformance", "0.1.0", (SourceProfile("events", "1.0.0", bindings),)),
        source_profile="events",
    ).canonical_json


def planning_inputs(
    manifest: bytes,
) -> tuple[ImplementationRegistry, ImplementationConfig]:
    import json

    data = json.loads(manifest)
    executable = {item["stage"] for item in data["stages"] if item["mode"] == "EXECUTE"}
    descriptors = tuple(
        ImplementationDescriptor(
            implementation_id=f"fixture.{item.stage.value.lower()}",
            descriptor_version="1.0.0",
            implementation_version="fixture-only-1",
            stage=item.stage,
            input_contract=ContractRef(item.input_contract, "1.0"),
            output_contract=ContractRef(item.output_contract, "1.0"),
            capabilities=("abstention", "authoritative_ids", "tables"),
            config_schema_version="1.0",
            required_settings=("endpoint_ref",),
            optional_settings=("region",),
        )
        for item in STAGE_CATALOG
        if item.stage.value in executable
    )
    selections = tuple(
        StageSelection(
            item.stage, item.implementation_id, "1.0", (("endpoint_ref", "fixture://offline"),)
        )
        for item in descriptors
    )
    return ImplementationRegistry("1.0", descriptors), ImplementationConfig(
        "1.0",
        data["source_profile"]["id"],
        data["source_profile"]["version"],
        "test-build",
        selections,
    )
