"""The real row-grounded ASSERT output must remain the source of identity evidence."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab.domains.procurement.planned_resolution import (
    BomResolve,
    validate_bom_resolution_inputs,
    validate_bom_resolved_output,
)
from procurement_intelligence_lab.domains.procurement.resolution import resolve_identifier
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.platform.execution.resolution_outputs import (
    ResolvedOutput,
    resolution_input_ids,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, SCOPE
from tests.planned_execution_archive_fixtures import executed
from tests.resolved_execution_fixtures import catalog, policy_evidence


def supported_policy() -> BomResolutionPolicy:
    return BomResolutionPolicy.from_parameters(policy_evidence().parameters)


def run_output(
    tmp_path: Path, *, rows: str = HEADER + ROW, keys: tuple[str, ...] = ("GPU-A",)
) -> ResolvedOutput:
    prefix, _ = executed(tmp_path / "source.xlsx", rows)
    candidates, policy = catalog(keys), supported_policy()
    validate_bom_resolution_inputs(candidates, policy, scope=SCOPE, as_of=AT)
    context = replace(
        prefix.context,
        input_snapshot_ids=tuple(
            dict.fromkeys(
                (
                    *prefix.context.input_snapshot_ids,
                    *resolution_input_ids(prefix.output, candidates.snapshot, policy.evidence),
                )
            )
        ),
    )
    p = DecisionProvenance(
        context,
        "bom-normalized-exact-resolve",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version=policy.reference_id,
    )
    strategy = BomResolve(candidates.snapshot, policy)
    decisions, links = strategy.resolve(
        prefix.output.mentions, prefix.output.assertions, provenance=p
    )
    outcomes = strategy.audit_decisions(prefix.output.mentions, decisions)
    linked = {c.assertion.assertion_id for c in links}
    output = ResolvedOutput(
        prefix.output,
        candidates.snapshot,
        policy.evidence,
        outcomes,
        links,
        tuple(a.assertion_id for a in prefix.output.assertions if a.assertion_id not in linked),
        p,
    )
    validate_bom_resolved_output(output)
    return output


def test_actual_assert_rows_bind_resolution_evidence(tmp_path: Path):
    o = run_output(tmp_path)
    d = o.outcomes[0].decision
    assert d.canonical_key == "GPU-A"
    assert len(d.evidence) == 1 and d.evidence[0].value == "GPU-A"
    assert d.evidence[0] in o.previous.mentions[0].assertions
    assert d.evidence[0].subject_key != "GPU-A"
    assert all(c.assertion in o.previous.mentions[0].assertions for c in o.canonicalized)


def test_duplicate_mention_text_retains_distinct_rows(tmp_path: Path):
    o = run_output(tmp_path, rows=HEADER + ROW + ROW.replace("7", "8"))
    assert len(o.outcomes) == 2
    assert o.outcomes[0].decision.decision_id != o.outcomes[1].decision.decision_id
    assert o.outcomes[0].decision.evidence[0].evidence.row == 7
    assert o.outcomes[1].decision.evidence[0].evidence.row == 8


def test_null_sku_remains_unlinked(tmp_path: Path):
    no_sku = ROW.replace('<c r="A7"><v>GPU-A</v></c>', "").replace("7", "8")
    o = run_output(tmp_path, rows=HEADER + ROW + no_sku)
    assert len(o.outcomes) == 1
    assert len(o.unlinked_assertion_ids) == 4
    assert all(a.assertion_id in o.unlinked_assertion_ids for a in o.previous.assertions[4:])


@pytest.mark.parametrize(
    ("mention", "keys", "expected", "rationale"),
    [
        ("gpu a", ("GPU-A",), "GPU-A", "normalized exact identifier match"),
        ("GPU-A", ("GPU-A", "GPU A"), None, "ambiguous normalized candidate match"),
        ("GPU-A", (), None, "no normalized candidate match"),
        ("unknown", ("GPU-A",), None, "no normalized candidate match"),
        ("---", ("GPU-A",), None, "invalid normalized identifier"),
        ("Straße", ("STRASSE",), "STRASSE", "normalized exact identifier match"),
    ],
)
def test_unique_none_collision_and_invalid_identifier(
    tmp_path: Path, mention: str, keys: tuple[str, ...], expected: str | None, rationale: str
):
    o = run_output(tmp_path, rows=HEADER + ROW.replace("GPU-A", mention), keys=keys)
    d = o.outcomes[0].decision
    assert d.canonical_key == expected and d.rationale == rationale
    assert bool(o.canonicalized) == (expected is not None)
    assert len(o.outcomes[0].matched_keys) == (
        2 if rationale.startswith("ambiguous") else (1 if expected else 0)
    )


def test_namespace_scope_policy_and_future_catalog_reject():
    from datetime import timedelta

    for c in [
        catalog(entity_type="vendor"),
        catalog(identifier_namespace="vendor_sku"),
        catalog(scope={**vars(SCOPE), "version": "2"}),
        catalog(effective_at=(AT + timedelta(seconds=1)).isoformat()),
        catalog(("---",)),
    ]:
        with pytest.raises(PackageExecutionError):
            validate_bom_resolution_inputs(c, supported_policy(), scope=SCOPE, as_of=AT)
    p = supported_policy()
    for changes in [
        {"normalization": "fuzzy"},
        {"entity_type": "vendor"},
        {"matching": "first-match"},
    ]:
        with pytest.raises(PackageExecutionError):
            replace(p, **changes)
    assert p.evidence == policy_evidence()


@pytest.mark.parametrize("raw", ["0", "-2", "0.125"])
def test_zero_negative_fractional_unknown_values_are_preserved(tmp_path: Path, raw: str):
    o = run_output(tmp_path, rows=HEADER + ROW.replace("<v>0.5</v>", f"<v>{raw}</v>"))
    quantity = next(c for c in o.canonicalized if c.assertion.predicate.value == "has_quantity")
    assert str(quantity.assertion.value) == raw
    description = next(
        c for c in o.canonicalized if c.assertion.predicate.value == "has_description"
    )
    assert description.assertion.value is None


def test_domain_validator_rejects_fabricated_matched_subset(tmp_path: Path):
    o = run_output(tmp_path)
    p = supported_policy()
    new = catalog(("GPU-A", "GPU A"))
    # All neutral identities are internally consistent, but hiding one matching candidate is invalid.
    outcomes = tuple(replace(x, candidate_snapshot_id=new.snapshot.snapshot_id) for x in o.outcomes)
    changed = replace(o, candidates=new.snapshot, outcomes=outcomes)
    with pytest.raises(PackageExecutionContractError):
        validate_bom_resolved_output(changed)
    with pytest.raises(PackageExecutionError):
        BomResolve(new.snapshot, p).resolve((), o.previous.assertions, provenance=o.provenance)


def test_matching_outcomes_equal_legacy_rule_for_supported_inputs(tmp_path: Path):
    case_path = Path("tests/fixtures/resolved-execution/cases.json")
    manifest = json.loads(case_path.with_name("cases-manifest.json").read_text())
    assert sha256(case_path.read_bytes()).hexdigest() == manifest["cases_sha256"]
    cases: list[dict[str, Any]] = json.loads(
        Path("tests/fixtures/resolved-execution/cases.json").read_text()
    )
    for case in cases:
        o = run_output(
            tmp_path, rows=case["source_rows_xml"], keys=tuple(case["candidate_snapshot"]["keys"])
        )
        d = o.outcomes[0].decision
        assert d.canonical_key == case["expected_key"]
        assert d.status.value == case["expected_status"]
        legacy = resolve_identifier(
            case["mention"], tuple(case["candidate_snapshot"]["keys"]), provenance=o.provenance
        )
        assert d.canonical_key == legacy.canonical_key
        assert d.status == legacy.status
        assert d.evidence and not legacy.evidence


def test_empty_document_and_unmapped_claims_are_retained(tmp_path: Path):
    empty = run_output(tmp_path, rows=HEADER)
    assert not empty.outcomes and not empty.canonicalized and not empty.unlinked_assertion_ids
    extra = ROW.replace("</row>", '<c r="E7"><v>not interpreted</v></c></row>')
    output = run_output(tmp_path, rows=HEADER + extra)
    assert len(output.canonicalized) == 5
    unmapped = next(
        c for c in output.canonicalized if c.assertion.predicate.value == "unmapped_field"
    )
    assert unmapped.assertion.value is None


def test_policy_parameters_reject_unhashable_or_duplicate_names():
    bad: Any = (([], "value"),)
    with pytest.raises(PackageExecutionError):
        BomResolutionPolicy.from_parameters(bad)
    valid = policy_evidence().parameters
    with pytest.raises(PackageExecutionError):
        BomResolutionPolicy.from_parameters(valid + (valid[0],))
