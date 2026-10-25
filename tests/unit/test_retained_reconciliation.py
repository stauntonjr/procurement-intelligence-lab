"""Actual source quantities become policy-backed state only with eligible evidence."""

import json
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    load_bom_authority,
)
from procurement_intelligence_lab.domains.procurement.reconciliation_validation import (
    validate_bom_reconciliation_inputs,
    validate_bom_reconciliation_output,
)
from procurement_intelligence_lab.domains.procurement.retained_reconciliation import (
    BomRetainedReconcileStrategy,
    build_reconciliation_audit,
    quantity_assertions,
)
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
    UnsupportedReconciliationInputError,
)
from procurement_intelligence_lab.platform.semantics.reconciliation import ReconciliationStatus
from procurement_intelligence_lab.platform.semantics.state import StateFreshness
from tests.bom_stage_fixtures import AT, HEADER, ROW, SCOPE, provenance
from tests.reconciliation_fixtures import metadata, policy, producer


def inputs(ps: Any, wire: Any = None, as_of: datetime = AT):
    authority = load_bom_authority(
        json.dumps(metadata(ps) if wire is None else wire).encode()
    ).evidence
    return RetainedReconciliationInputs(
        SCOPE,
        as_of,
        tuple(sorted(ps, key=lambda p: p.completed.execution_digest)),
        authority,
        policy(),
    )


def output(q: RetainedReconciliationInputs):
    validate_bom_reconciliation_inputs(q, started_at=AT + timedelta(days=1))
    p = replace(
        provenance(),
        context=replace(
            provenance().context, input_snapshot_ids=q.input_ids, started_at=AT + timedelta(days=1)
        ),
        policy_version=q.policy.reference.reference_id,
    )
    d, s = BomRetainedReconcileStrategy(q).reconcile(
        quantity_assertions(q), scope=q.scope, as_of=q.as_of, provenance=p
    )
    consumed = {a.assertion.assertion_id for d0 in d for a in (*d0.governing, *d0.losing)}
    outside = tuple(
        sorted(
            a.assertion_id
            for x in q.recorded_producers
            for a in x.completed.execution.output.previous.assertions
            if a.assertion_id not in consumed
        )
    )
    return ReconciledOutput(q, d, s, outside, build_reconciliation_audit(q, d, s, provenance=p), p)


def test_shared_equal_quantity_retains_all_distinct_source_paths(tmp_path: Path):
    p, _ = producer(tmp_path / "one")
    q, _ = producer(tmp_path / "two", HEADER + ROW.replace("100.50", "101.50"))
    got = output(inputs((p, q)))
    assert len(got.decisions[0].governing) == 2
    assert got.decisions[0].status is ReconciliationStatus.RECONCILED
    assert got.states[0].attributes[0].value == Decimal("0.5")
    assert got.states[0].attributes[0].status is EpistemicStatus.OBSERVED
    assert len(got.states[0].evidence) == 2 and got.states[0].freshness is StateFreshness.UNKNOWN
    assert got.states[0].scope.version != SCOPE.version
    validate_bom_reconciliation_output(got)
    assert json.loads(got.domain_audit)["items"][0]["decision"]["status"] == "governed_shared_value"


def test_identical_content_relabel_rejected(tmp_path: Path):
    p, data = producer(tmp_path / "one")
    q, _ = producer(tmp_path / "two", content=data)
    with pytest.raises(PackageExecutionError):
        inputs((p, p))
    assert (
        p.completed.prefix.snapshot.artifact.content_hash
        == q.completed.prefix.snapshot.artifact.content_hash
    )
    with pytest.raises(UnsupportedReconciliationInputError):
        inputs((p, q))


def test_selected_supersession_omission_and_empty_successor_rejected(tmp_path: Path):
    p, _ = producer(tmp_path / "one")
    q, _ = producer(tmp_path / "two", HEADER)
    w = metadata((p, q))
    w["producers"][1]["supersedes_revision_ids"] = ["revision-0"]
    with pytest.raises(UnsupportedReconciliationInputError):
        output(inputs((p, q), w))


@pytest.mark.parametrize(
    "rows,keys",
    [
        (HEADER + ROW + ROW.replace("7", "8"), ("GPU-A",)),
        (HEADER + ROW, ()),
        (HEADER + ROW.replace('<c r="C7"><v>0.5</v></c>', ""), ("GPU-A",)),
        (HEADER + ROW.replace("<v>0.5</v>", "<v>-1</v>"), ("GPU-A",)),
    ],
)
def test_unresolved_identity_or_repeated_item_quantity_rejected(
    tmp_path: Path, rows: str, keys: tuple[str, ...]
):
    p, _ = producer(tmp_path, rows, keys)
    with pytest.raises(UnsupportedReconciliationInputError):
        output(inputs((p,)))


def test_empty_valid_revision_has_no_candidates(tmp_path: Path):
    p, _ = producer(tmp_path, HEADER)
    got = output(inputs((p,)))
    assert not got.decisions and not got.states and got.event.event_id
    validate_bom_reconciliation_output(got)


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"approval": None}, "unapproved"),
        (
            {
                "approval": {
                    "record_ref": "future",
                    "approved_at": (AT + timedelta(seconds=1)).isoformat(),
                }
            },
            "approval_after_as_of",
        ),
        ({"effective_from": (AT + timedelta(seconds=1)).isoformat()}, "not_yet_effective"),
        (
            {
                "effective_from": (AT - timedelta(days=1)).isoformat(),
                "effective_until": AT.isoformat(),
            },
            "expired",
        ),
        ({"source_role": "receipt"}, "wrong_source_role"),
    ],
)
def test_future_approval_has_explicit_audit_reason(
    tmp_path: Path, change: dict[str, Any], reason: str
):
    p, _ = producer(tmp_path)
    got = output(inputs((p,), metadata((p,), **change)))
    assert not got.states and got.decisions[0].status is ReconciliationStatus.UNRESOLVED
    assert json.loads(got.domain_audit)["items"][0]["decision"]["dispositions"][0][1] == reason


def test_policy_time_and_derived_scope_do_not_follow_ingestion(tmp_path: Path):
    p, _ = producer(tmp_path)
    before = AT - timedelta(days=1)
    w = metadata(
        (p,),
        approval={"record_ref": "historical", "approved_at": before.isoformat()},
        effective_from=before.isoformat(),
    )
    got = output(inputs((p,), w, before))
    assert got.states[0].as_of == before and got.states[0].attributes[0].value == Decimal("0.5")
    w["producers"][0]["supersedes_revision_ids"] = ["not-selected"]
    assert output(inputs((p,), w, before)).states
    with pytest.raises(PackageExecutionError):
        validate_bom_reconciliation_inputs(got.inputs, started_at=before)


def test_conflict_abstains_with_all_losing_paths(tmp_path: Path):
    p, _ = producer(tmp_path / "one")
    q, _ = producer(tmp_path / "two", HEADER + ROW.replace("0.5", "2.5"))
    got = output(inputs((p, q)))
    assert not got.states and not got.decisions[0].governing and len(got.decisions[0].losing) == 2
    validate_bom_reconciliation_output(got)


def test_postconditions_reject_resealed_metadata_and_projection(tmp_path: Path):
    p, _ = producer(tmp_path)
    got = output(inputs((p,)))
    state = replace(
        got.states[0], attributes=(replace(got.states[0].attributes[0], value=Decimal(99)),)
    )
    with pytest.raises(PackageExecutionContractError):
        validate_bom_reconciliation_output(replace(got, states=(state,)))
    with pytest.raises(PackageExecutionContractError):
        validate_bom_reconciliation_output(replace(got, domain_audit=b"{}"))


@pytest.mark.parametrize("value", ["0", "0.25", "10.500"])
def test_zero_fractional_and_supersession(tmp_path: Path, value: str):
    p, _ = producer(tmp_path / "one")
    q, _ = producer(
        tmp_path / "two",
        HEADER + ROW.replace("<v>0.5</v>", f"<v>{value}</v>").replace("100.50", "102.00"),
    )
    wire = metadata((p, q))
    wire["producers"][1]["supersedes_revision_ids"] = ["revision-0"]
    got = output(inputs((p, q), wire))
    assert got.states[0].attributes[0].value == Decimal(value)
    assert len(got.decisions[0].governing) == len(got.decisions[0].losing) == 1
    reasons = json.loads(got.domain_audit)["items"][0]["decision"]["dispositions"]
    assert {r[1] for r in reasons} == {"governing", "superseded"}
    validate_bom_reconciliation_output(got)


def test_offsets_are_preserved_without_becoming_authority(tmp_path: Path):
    p, _ = producer(tmp_path)
    wire = metadata(
        (p,),
        approval={"record_ref": "offset-approval", "approved_at": "2026-10-18T20:00:00-04:00"},
        effective_from="2026-10-18T20:00:00-04:00",
    )
    got = output(inputs((p,), wire))
    assert got.states[0].attributes[0].value == Decimal("0.5")
    assert b"-04:00" in got.domain_audit


def test_catalog_mismatch_and_source_metadata_substitution(tmp_path: Path):
    p, _ = producer(tmp_path / "one")
    q, _ = producer(tmp_path / "two", keys=("GPU-A", "CPU-A"))
    with pytest.raises(PackageExecutionError):
        inputs((p, q))
    wire = metadata((p,), artifact_id="foreign-artifact")
    with pytest.raises(PackageExecutionError):
        output(inputs((p,), wire))
