from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import cast

import pytest

from procurement_intelligence_lab.domain.compiler import (
    DomainPackageValidationError,
    compile_domain_package,
)
from procurement_intelligence_lab.domain.package import (
    STAGE_ORDER,
    DomainPackage,
    SourceProfile,
    StageBinding,
    StageMode,
)


def package(
    *,
    bindings: tuple[StageBinding, ...] | None = None,
    profiles: tuple[SourceProfile, ...] | None = None,
    schema_version: str = "1.0",
    domain_id: str = "procurement",
) -> DomainPackage:
    selected = bindings or tuple(
        StageBinding(
            stage,
            StageMode.EMPTY,
            neutral_semantics=_empty_semantics(stage),
        )
        for stage in STAGE_ORDER
    )
    return DomainPackage(
        schema_version,
        domain_id,
        "0.3.0",
        profiles or (SourceProfile("default", "1.0.0", selected),),
    )


def _empty_semantics(stage: object) -> str:
    return {
        "INGEST": "no_captured_artifacts",
        "STRUCTURE": "no_structured_documents",
        "MAP": "no_mapped_documents",
        "NORMALIZE": "no_normalized_observations",
        "ASSERT": "no_assertions_or_mentions",
        "RESOLVE": "no_resolution_decisions",
        "RECONCILE": "no_governed_state_records",
        "DERIVE": "no_derived_facts",
        "DETECT": "no_anomalies",
        "PREDICT": "no_predictions",
        "DECIDE": "no_decisions_or_recommendations",
        "ACT": "no_action_attempted",
    }[str(stage)]


def codes(error: DomainPackageValidationError) -> set[str]:
    return {issue.code for issue in error.issues}


Mutator = Callable[[tuple[StageBinding, ...]], tuple[StageBinding, ...]]


def drop_last(bindings: tuple[StageBinding, ...]) -> tuple[StageBinding, ...]:
    return bindings[:-1]


def duplicate_first(bindings: tuple[StageBinding, ...]) -> tuple[StageBinding, ...]:
    return bindings[:1] + (bindings[0],) + bindings[1:]


def reorder_first_two(bindings: tuple[StageBinding, ...]) -> tuple[StageBinding, ...]:
    return (bindings[1], bindings[0], *bindings[2:])


def test_compile_is_deterministic_and_provider_neutral() -> None:
    first = compile_domain_package(package())
    second = compile_domain_package(package())

    assert first.canonical_json == second.canonical_json
    assert first.manifest_hash == second.manifest_hash
    assert first.manifest_hash
    assert b"procurement" in first.canonical_json
    assert b"provider" not in first.canonical_json.lower()


def test_compile_is_vertical_neutral() -> None:
    result = compile_domain_package(package(domain_id="inventory"))

    assert result.manifest["domain"] == {"id": "inventory", "version": "0.3.0"}
    stages = cast(list[dict[str, object]], result.manifest["stages"])
    assert [cast(str, stage["stage"]) for stage in stages] == [stage.value for stage in STAGE_ORDER]
    assert b"procurement" not in result.canonical_json


def test_compile_accepts_execute_and_verified_passthrough() -> None:
    bindings = list(package().source_profiles[0].bindings)
    bindings[0] = StageBinding(
        STAGE_ORDER[0],
        StageMode.EXECUTE,
        requirements=("authoritative_ids",),
    )
    bindings[1] = StageBinding(
        STAGE_ORDER[1],
        StageMode.PASSTHROUGH,
        output_contract_verified=True,
    )

    result = compile_domain_package(package(bindings=tuple(bindings)))

    stages = result.manifest["stages"]
    assert isinstance(stages, list)
    assert stages[0]["mode"] == "EXECUTE"
    assert stages[1]["output_contract_verified"] is True


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (drop_last, "missing_stage"),
        (duplicate_first, "duplicate_stage"),
        (reorder_first_two, "reordered_stage"),
    ],
)
def test_compile_rejects_stage_shape(mutator: Mutator, expected: str) -> None:
    bindings = tuple(
        StageBinding(
            stage,
            StageMode.EMPTY,
            neutral_semantics=_empty_semantics(stage),
        )
        for stage in STAGE_ORDER
    )

    with pytest.raises(DomainPackageValidationError) as caught:
        compile_domain_package(package(bindings=mutator(bindings)))

    assert expected in codes(caught.value)


@pytest.mark.parametrize(
    ("binding", "expected"),
    [
        (
            StageBinding(STAGE_ORDER[0], StageMode.EMPTY),
            "missing_neutral_semantics",
        ),
        (
            StageBinding(
                STAGE_ORDER[0],
                StageMode.EMPTY,
                neutral_semantics="unresolved",
            ),
            "invalid_neutral_semantics",
        ),
        (
            StageBinding(STAGE_ORDER[0], StageMode.PASSTHROUGH),
            "unverified_passthrough",
        ),
        (
            StageBinding(
                STAGE_ORDER[0],
                StageMode.EXECUTE,
                neutral_semantics="no_captured_artifacts",
            ),
            "unexpected_neutral_semantics",
        ),
    ],
)
def test_compile_rejects_invalid_mode_semantics(
    binding: StageBinding,
    expected: str,
) -> None:
    bindings = list(package().source_profiles[0].bindings)
    bindings[0] = binding

    with pytest.raises(DomainPackageValidationError) as caught:
        compile_domain_package(package(bindings=tuple(bindings)))

    assert expected in codes(caught.value)


def test_compile_rejects_unknown_capability_and_provider_leakage() -> None:
    bindings = list(package().source_profiles[0].bindings)
    bindings[0] = StageBinding(
        STAGE_ORDER[0],
        StageMode.EXECUTE,
        requirements=("not-a-capability",),
        domain_config_ref="procurement.model/gpt@1",
    )

    with pytest.raises(DomainPackageValidationError) as caught:
        compile_domain_package(package(bindings=tuple(bindings)))

    assert {"unsupported_capability", "provider_leakage"} <= codes(caught.value)


def test_compile_rejects_invalid_schema_and_reference() -> None:
    bindings = list(package().source_profiles[0].bindings)
    bindings[0] = replace(
        bindings[0],
        domain_config_ref="not-versioned",
    )

    with pytest.raises(DomainPackageValidationError) as caught:
        compile_domain_package(
            package(bindings=tuple(bindings), schema_version="2.0"),
        )

    assert {"unsupported_schema_version", "invalid_reference"} <= codes(caught.value)


def test_compile_rejects_unknown_profile() -> None:
    with pytest.raises(DomainPackageValidationError) as caught:
        compile_domain_package(package(), source_profile="erp")

    assert "unknown_source_profile" in codes(caught.value)


def test_compile_rejects_duplicate_profile_ids() -> None:
    profile = package().source_profiles[0]
    duplicate_profiles = (profile, profile)

    with pytest.raises(DomainPackageValidationError) as caught:
        compile_domain_package(package(profiles=duplicate_profiles))

    assert "duplicate_source_profile" in codes(caught.value)
