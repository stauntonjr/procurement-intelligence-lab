from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from tools.check_coverage_ratchet import CoverageRates, read_baseline, read_rates, validate


def test_validate_rejects_line_or_branch_regressions() -> None:
    baseline = CoverageRates(Decimal("0.9000"), Decimal("0.7200"))

    assert validate(CoverageRates(Decimal("0.9000"), Decimal("0.7200")), baseline) == ()
    assert validate(CoverageRates(Decimal("0.8999"), Decimal("0.7200")), baseline)
    assert validate(CoverageRates(Decimal("0.9000"), Decimal("0.7199")), baseline)


def test_read_rates_and_baseline(tmp_path: Path) -> None:
    xml = tmp_path / "coverage.xml"
    xml.write_text('<coverage line-rate="0.9" branch-rate="0.7" />')
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"line_rate": 0.9, "branch_rate": 0.7}))

    assert read_rates(xml) == CoverageRates(Decimal("0.9"), Decimal("0.7"))
    assert read_baseline(baseline) == CoverageRates(Decimal("0.9"), Decimal("0.7"))


def test_read_rates_rejects_missing_attributes(tmp_path: Path) -> None:
    xml = tmp_path / "coverage.xml"
    xml.write_text("<coverage />")

    with pytest.raises(ValueError, match="missing valid"):
        read_rates(xml)
