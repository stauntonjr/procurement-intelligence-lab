from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from procurement_intelligence_lab.bootstrap import build_bom_stage_service
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    BomNormalize,
    CountUnit,
)
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    NormalizationError,
    NormalizationPolicyError,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_stage_adapters import source

pytestmark = pytest.mark.contract


def mapped(tmp_path: Path, rows: str = HEADER + ROW):
    return (
        build_bom_stage_service(captured_at=AT, context=provenance().context)
        .run(source(workbook(tmp_path / "source.xlsx", rows)))
        .mapped
    )


def policy(quantity_unit: CountUnit = CountUnit.EACH) -> BomNormalizationPolicy:
    return BomNormalizationPolicy(quantity_unit, "USD", CountUnit.EACH)


def test_exact_numbers_keep_raw_evidence_and_ignore_ambient_decimal_context(tmp_path: Path) -> None:
    document = mapped(tmp_path, HEADER + ROW.replace("<v>0.5</v>", "<v>123456789.123456789</v>"))
    with localcontext() as context:
        context.prec = 2
        values = BomNormalize(policy(CountUnit.DOZEN)).normalize(document, provenance=provenance())
    fields = {x.source_field.field_name: x for x in values}
    quantity = fields["quantity"]
    assert quantity.value == Decimal("1481481469.481481468")
    assert quantity.unit == "each"
    assert quantity.source_field.raw_value == "123456789.123456789"
    assert quantity.source_field is document.fields[2]
    assert quantity.source_field.evidence.cells == ("C",)
    assert quantity.scope == document.source_document.artifact.source.scope
    assert quantity.effective_at == AT
    assert fields["unit_price"].value == Decimal("100.50")
    assert fields["unit_price"].unit == "USD/each"
    assert fields["description"].value is None
    assert fields["description"].status is EpistemicStatus.UNRESOLVED
    assert fields["description"].diagnostic == "missing column B"
    assert fields["sku"].value == "GPU-A"


@pytest.mark.parametrize("raw", ["0", "-0", "-1", "+1.25", "0004.50", " 0.5 ", "9" * 128])
def test_signed_fractional_and_boundary_values_remain_source_observations(
    tmp_path: Path, raw: str
) -> None:
    document = mapped(tmp_path, HEADER + ROW.replace("<v>0.5</v>", f"<v>{raw}</v>"))
    result = BomNormalize(policy()).normalize(document, provenance=provenance())
    quantity = next(x for x in result if x.source_field.field_name == "quantity")
    assert quantity.value == Decimal(raw)
    assert quantity.status is EpistemicStatus.OBSERVED
    assert quantity.source_field.raw_value == raw


@pytest.mark.parametrize(
    "raw", ["NaN", "Infinity", "1,000", "1e3", "$4", "1_0", ".5", "1.", "９", "9" * 129]
)
def test_ambiguous_invalid_and_overlong_numbers_fail_typed(tmp_path: Path, raw: str) -> None:
    document = mapped(tmp_path, HEADER + ROW.replace("<v>0.5</v>", f"<v>{raw}</v>"))
    with pytest.raises(NormalizationError, match="BOM!C7"):
        BomNormalize(policy()).normalize(document, provenance=provenance())


def test_missing_unmapped_duplicate_and_missing_sku_rows_are_not_dropped(tmp_path: Path) -> None:
    rows = HEADER + ROW.replace("</row>", '<c r="E7"><v>extra</v></c></row>')
    rows += ROW.replace("7", "8") + '<row r="9"><c r="C9"><v>0</v></c></row>'
    document = mapped(tmp_path, rows)
    observations = BomNormalize(policy()).normalize(document, provenance=provenance())
    assert len(observations) == 13
    assert len({x.subject_hint for x in observations}) == 3
    assert [x.source_field for x in observations] == list(document.fields)
    extra = next(x for x in observations if x.source_field.field_name == "unmapped.E")
    assert extra.value is None and extra.status is EpistemicStatus.UNRESOLVED
    assert extra.diagnostic and extra.source_field.raw_value == "extra"
    missing = next(x for x in observations if x.observation_key == "BOM!A9")
    assert missing.value is None and missing.status is EpistemicStatus.UNRESOLVED
    assert missing.source_field.evidence.row == 9
    zero = next(x for x in observations if x.observation_key == "BOM!C9")
    assert zero.value == Decimal(0) and zero.status is EpistemicStatus.OBSERVED


def test_header_only_is_successful_empty_normalization(tmp_path: Path) -> None:
    assert BomNormalize(policy()).normalize(mapped(tmp_path, HEADER), provenance=provenance()) == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "usd"},
        {"currency": ""},
        {"currency": " USD"},
        {"quantity_unit": "each"},
        {"price_unit": None},
    ],
)
def test_policy_construction_requires_explicit_typed_units_and_currency(
    changes: dict[str, object],
) -> None:
    with pytest.raises(NormalizationPolicyError):
        replace(policy(), **changes)


def test_profile_mismatch_and_nontext_values_fail_before_coercion(tmp_path: Path) -> None:
    document = mapped(tmp_path)
    invalid = (
        replace(document, mapping_schema="other@1"),
        replace(
            document,
            fields=tuple(
                replace(f, raw_value=4) if f.field_name == "quantity" else f
                for f in document.fields
            ),
        ),
        replace(
            document,
            fields=tuple(
                replace(f, field_name="unit_price") if f.field_name == "quantity" else f
                for f in document.fields
            ),
        ),
        replace(document, fields=document.fields[1:]),
    )
    for candidate in invalid:
        with pytest.raises(NormalizationError):
            BomNormalize(policy()).normalize(candidate, provenance=provenance())


def test_policy_content_identity_and_price_denominator_are_explicit(tmp_path: Path) -> None:
    original = policy()
    changed = replace(original, currency="EUR", price_unit=CountUnit.DOZEN)
    assert original.reference_id != changed.reference_id
    assert replace(original).reference_id == original.reference_id
    observations = BomNormalize(changed).normalize(mapped(tmp_path), provenance=provenance())
    price = next(x for x in observations if x.source_field.field_name == "unit_price")
    assert price.value == Decimal("100.50") and price.unit == "EUR/dozen"


def test_scope_revision_and_observation_time_are_retained_in_identity(tmp_path: Path) -> None:
    from datetime import timedelta

    original = source(workbook(tmp_path / "source.xlsx", HEADER + ROW))
    later = AT + timedelta(days=1)
    service = build_bom_stage_service(captured_at=later, context=provenance().context)
    variants = (
        original,
        replace(original, scope=replace(original.scope, tenant_id="other")),
        replace(original, source_version="revision-2"),
        replace(original, observed_at=later),
    )
    observations = [
        BomNormalize(policy()).normalize(service.run(s).mapped, provenance=provenance())
        for s in variants
    ]
    for s, batch in zip(variants, observations, strict=True):
        assert all(x.scope == s.scope and x.effective_at == s.observed_at for x in batch)
    assert len({batch[0].subject_hint for batch in observations}) == 4
    assert len({batch[0].observation_id for batch in observations}) == 4


@pytest.mark.parametrize(
    "key", ["other!C7", "BOM!C8", "BOM!C" + "9" * 5000], ids=["sheet", "row", "overlong"]
)
def test_malformed_field_location_fails_typed(tmp_path: Path, key: str) -> None:
    document = mapped(tmp_path)
    fields = tuple(
        replace(f, field_key=key) if f.field_name == "quantity" else f for f in document.fields
    )
    with pytest.raises(NormalizationError):
        BomNormalize(policy()).normalize(replace(document, fields=fields), provenance=provenance())


def test_maximum_decimal_conversion_is_exact_even_with_inexact_traps(tmp_path: Path) -> None:
    from decimal import Inexact

    raw = "9" * 128
    document = mapped(tmp_path, HEADER + ROW.replace("<v>0.5</v>", f"<v>{raw}</v>"))
    with localcontext() as context:
        context.prec = 1
        context.traps[Inexact] = True
        result = BomNormalize(policy(CountUnit.DOZEN)).normalize(document, provenance=provenance())
    quantity = next(x for x in result if x.source_field.field_name == "quantity")
    assert quantity.value == Decimal(str(int(raw) * 12))
