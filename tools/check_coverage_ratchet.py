"""Enforce the repository's checked-in branch-coverage baseline."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


@dataclass(frozen=True)
class CoverageRates:
    line_rate: Decimal
    branch_rate: Decimal


def read_rates(path: Path) -> CoverageRates:
    try:
        root = ET.parse(path).getroot()
        line_rate = Decimal(root.attrib["line-rate"])
        branch_rate = Decimal(root.attrib["branch-rate"])
    except (OSError, ET.ParseError, KeyError, InvalidOperation) as error:
        raise ValueError(f"coverage XML is missing valid line-rate/branch-rate: {path}") from error

    if not (line_rate.is_finite() and branch_rate.is_finite()):
        raise ValueError(f"coverage XML has non-finite line-rate/branch-rate: {path}")
    if not (Decimal("0") <= line_rate <= Decimal("1") and Decimal("0") <= branch_rate <= Decimal("1")):
        raise ValueError(f"coverage XML has out-of-range line-rate/branch-rate: {path}")

    return CoverageRates(line_rate, branch_rate)

def read_baseline(path: Path) -> CoverageRates:
    try:
        data = json.loads(path.read_text())
        return CoverageRates(
            Decimal(str(data["line_rate"])),
            Decimal(str(data["branch_rate"])),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"coverage baseline is invalid: {path}") from error


def validate(current: CoverageRates, baseline: CoverageRates) -> tuple[str, ...]:
    errors: list[str] = []
    if current.line_rate < baseline.line_rate:
        errors.append(
            f"line coverage regressed from {baseline.line_rate:.4f} to {current.line_rate:.4f}"
        )
    if current.branch_rate < baseline.branch_rate:
        errors.append(
            f"branch coverage regressed from {baseline.branch_rate:.4f} to {current.branch_rate:.4f}"
        )
    return tuple(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-xml", type=Path, default=Path("coverage.xml"))
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(".github/coverage-baseline.json"),
    )
    args = parser.parse_args(argv)
    try:
        errors = validate(read_rates(args.coverage_xml), read_baseline(args.baseline))
    except ValueError as error:
        print(f"coverage ratchet error: {error}", file=sys.stderr)
        return 2
    if errors:
        print("Coverage ratchet failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("coverage ratchet passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
