import pytest

from procurement_intelligence_lab.platform.domain_packages.contract_registry import (
    CONTRACT_REGISTRY,
)
from procurement_intelligence_lab.platform.domain_packages.package import STAGE_CATALOG


@pytest.mark.regression
def test_catalog_never_names_an_unimplemented_semantic_contract() -> None:
    referenced = {
        name for stage in STAGE_CATALOG for name in (stage.input_contract, stage.output_contract)
    }

    assert referenced <= CONTRACT_REGISTRY.keys()
    assert {name: CONTRACT_REGISTRY[name].__name__ for name in referenced} == {
        name: name for name in referenced
    }
