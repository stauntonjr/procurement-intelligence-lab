"""The first procurement package declares the current BOM semantics without runtime claims."""

import json
import subprocess
import sys

import pytest

from procurement_intelligence_lab.platform.domain_packages.compiler import compile_domain_package
from procurement_intelligence_lab.platform.domain_packages.package import STAGE_ORDER, StageMode


@pytest.mark.contract
def test_procurement_package_is_complete_and_keeps_late_stages_empty() -> None:
    from procurement_intelligence_lab.domains.procurement.package import PROCUREMENT_PACKAGE

    (profile,) = PROCUREMENT_PACKAGE.source_profiles
    assert profile.profile_id == "bom-table"
    assert tuple(binding.stage for binding in profile.bindings) == STAGE_ORDER
    assert [binding.mode for binding in profile.bindings[:9]] == [StageMode.EXECUTE] * 9
    assert [(binding.mode, binding.neutral_semantics) for binding in profile.bindings[9:]] == [
        (StageMode.EMPTY, "no_predictions"),
        (StageMode.EMPTY, "no_decisions_or_recommendations"),
        (StageMode.EMPTY, "no_action_attempted"),
    ]
    manifest = compile_domain_package(PROCUREMENT_PACKAGE, source_profile=profile.profile_id)
    assert json.loads(manifest.canonical_json)["domain"] == {
        "id": "procurement",
        "version": "0.1.0",
    }
    assert b"procurement.mapping/bom-table@1" in manifest.canonical_json
    assert b"procurement.resolve/normalized-exact@1" in manifest.canonical_json
    assert all(
        b"EXECUTE" not in json.dumps(stage).encode()
        for stage in json.loads(manifest.canonical_json)["stages"][9:]
    )


@pytest.mark.contract
def test_procurement_package_import_has_no_io_or_ambient_configuration() -> None:
    script = """
from pathlib import Path
import os
import socket
import procurement_intelligence_lab.platform.domain_packages.package

def denied(*args, **kwargs):
    raise AssertionError("package import attempted external work")

Path.read_text = Path.read_bytes = Path.open = denied
os.getenv = denied
socket.socket = denied
from procurement_intelligence_lab.domains.procurement.package import PROCUREMENT_PACKAGE
print(PROCUREMENT_PACKAGE.domain_id)
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "procurement"


@pytest.mark.contract
@pytest.mark.parametrize(
    "headers,accepted",
    [
        ((), False),
        (("SKU", "Description", "Quantity", "Unit Price"), True),
        (("SKU", "Description", "Quantity", "Unit Price", "Notes"), True),
        (("Description", "SKU", "Quantity", "Unit Price"), False),
        (("SKU", "Description", "Quantity"), False),
        (("SKU", "Description", "Quantity", "Quantity"), False),
    ],
)
def test_bom_schema_preserves_the_existing_header_prefix_contract(
    headers: tuple[str, ...], accepted: bool
) -> None:
    from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA

    assert BOM_TABLE_SCHEMA.matches_headers(headers) is accepted
    assert BOM_TABLE_SCHEMA.schema_id == "bom-xlsx-v1"
    assert BOM_TABLE_SCHEMA.sheet_name == "BOM"


@pytest.mark.contract
@pytest.mark.parametrize(
    "changes",
    [
        {"schema_id": ""},
        {"sheet_name": " "},
        {"reference_id": ""},
        {"columns": ("SKU", "Description", "Quantity")},
        {"columns": ("SKU", "Description", "Quantity", "Quantity")},
        {"columns": ("SKU", "Description", "Quantity", "")},
    ],
)
def test_bom_schema_rejects_incomplete_or_ambiguous_declarations(
    changes: dict[str, object],
) -> None:
    from dataclasses import replace
    from typing import Any, cast

    from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA

    with pytest.raises(ValueError):
        replace(BOM_TABLE_SCHEMA, **cast(dict[str, Any], changes))
