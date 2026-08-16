import pytest

import procurement_intelligence_lab.platform.domain_packages.compiler as compiler_module
from procurement_intelligence_lab.platform.domain_packages.compiler import (
    compile_domain_package,
)
from procurement_intelligence_lab.platform.domain_packages.contract_registry import (
    CONTRACT_REGISTRY,
)
from procurement_intelligence_lab.platform.domain_packages.package import (
    STAGE_CATALOG,
)
from tests.unit.test_domain_package_compiler import package


@pytest.mark.contract
def test_compiler_catalog_contract_names_are_backed_by_platform_types() -> None:
    result = compile_domain_package(package(domain_id="inventory"))

    assert result.manifest_hash
    for stage in STAGE_CATALOG:
        assert CONTRACT_REGISTRY[stage.input_contract].__name__ == stage.input_contract
        assert CONTRACT_REGISTRY[stage.output_contract].__name__ == stage.output_contract


@pytest.mark.contract
def test_compiler_revalidates_contract_registry_at_call_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def record_validation() -> None:
        calls.append(True)

    monkeypatch.setattr(
        compiler_module,
        "validate_stage_contract_registry",
        record_validation,
    )

    compiler_module.compile_domain_package(package(domain_id="inventory"))

    assert calls == [True]
