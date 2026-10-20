import json
from pathlib import Path

import pytest

from procurement_intelligence_lab.interfaces.bom_normalization_policy import load_policy
from procurement_intelligence_lab.platform.semantics.errors import NormalizationPolicyError


def test_policy_order_and_file_location_do_not_change_meaning_or_identity(tmp_path: Path) -> None:
    policy = {
        "profile": "bom-decimal@1",
        "quantity_unit": "dozen",
        "currency": "EUR",
        "price_unit": "each",
    }
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text(json.dumps(policy))
    second.write_text(json.dumps(dict(reversed(tuple(policy.items()))), indent=4))
    a, b = load_policy(first), load_policy(second)
    assert a == b and a.reference_id == b.reference_id
    assert a.as_dict() == {**policy, "reference_id": a.reference_id}


@pytest.mark.parametrize(
    "raw",
    [
        None,
        b"\xff",
        b"{",
        b"[]",
        b'{"currency":"USD","currency":"EUR"}',
        b'{"currency":"USD"}',
        b'{"profile":"other","quantity_unit":"each","currency":"USD","price_unit":"each"}',
        b'{"profile":"bom-decimal@1","quantity_unit":1,"currency":"USD","price_unit":"each"}',
        b'{"profile":"bom-decimal@1","quantity_unit":"unknown","currency":"USD","price_unit":"each"}',
    ],
)
def test_policy_file_failures_remain_typed(tmp_path: Path, raw: bytes | None) -> None:
    path = tmp_path / "policy.json"
    if raw is not None:
        path.write_bytes(raw)
    with pytest.raises(NormalizationPolicyError):
        load_policy(path)
