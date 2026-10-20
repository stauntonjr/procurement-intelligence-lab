from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from importlib.util import find_spec
from pathlib import Path

import pytest

from tests.bom_stage_fixtures import AT
from tests.contract.test_postgres_archive import inputs


def contract():
    assert find_spec("procurement_intelligence_lab.platform.semantics.document_reviews") is not None
    from procurement_intelligence_lab.platform.semantics import document_reviews

    return document_reviews


def proposal(tmp_path: Path):
    c = contract()
    snapshot, _ = inputs(tmp_path)
    previous = next(a for a in snapshot.assertions if a.predicate.value == "has_quantity")
    return c.ReviewProposal(
        snapshot.artifact.source.scope,
        "request-1",
        snapshot.snapshot_id,
        previous,
        Decimal("8.00"),
        "Correct interpretation at source cell",
        "human",
    )


def test_exact_task_digest_preserves_all_typed_content(tmp_path: Path):
    c = contract()
    p = proposal(tmp_path)
    task = c.DocumentReviewTask(p, AT + timedelta(seconds=2))
    assert len(task.digest) == 64 and task.digest == replace(task).digest
    for change in (
        {"proposed_value": Decimal("8.0")},
        {"proposed_value": "8.00"},
        {"reason": "different rationale"},
        {"proposer_id": "another human"},
    ):
        other = c.DocumentReviewTask(replace(p, **change), task.recorded_at)
        assert other.task_id == task.task_id and other.digest != task.digest
    assert replace(task, recorded_at=task.recorded_at + timedelta(seconds=1)).digest != task.digest
    assert task.proposal.previous.value == Decimal("0.5")


def test_approval_is_a_separate_prospective_correction(tmp_path: Path):
    c = contract()
    task = c.DocumentReviewTask(proposal(tmp_path), AT + timedelta(seconds=2))
    cmd = c.ReviewDecisionCommand(
        task.proposal.scope,
        "decision-1",
        task.task_id,
        task.digest,
        c.ReviewOutcome.APPROVE,
        "reviewer",
        "checked original evidence",
    )
    decision = c.DocumentReviewDecision(cmd, AT + timedelta(seconds=3))
    result = c.ReviewHistory(task, decision)
    assert decision.effective_at == decision.recorded_at
    assert result.correction_id and c.ReviewHistory(task, None).correction_id is None
    assert (
        c.ReviewHistory(
            task, replace(decision, command=replace(cmd, outcome=c.ReviewOutcome.REJECT))
        ).correction_id
        is None
    )
    assert result.task.proposal.previous.value == Decimal("0.5")
    with pytest.raises(ValueError):
        c.ReviewHistory(task, replace(decision, recorded_at=AT))
    with pytest.raises(ValueError):
        c.ReviewHistory(task, replace(decision, command=replace(cmd, task_digest="0" * 64)))


def test_invalid_construction_fails_before_storage(tmp_path: Path):
    c = contract()
    p = proposal(tmp_path)
    for changes in (
        {"request_id": ""},
        {"reason": " "},
        {"proposer_id": ""},
        {"scope": replace(p.scope, version="foreign")},
        {"proposed_value": 1.5},
        {"proposed_value": Decimal("NaN")},
        {"workflow": c.ReviewWorkflow.ENTITY},
        {"workflow": c.ReviewWorkflow.OPERATIONAL},
    ):
        with pytest.raises(ValueError):
            replace(p, **changes)
    for at in (AT - timedelta(seconds=1), AT.replace(tzinfo=None)):
        with pytest.raises(ValueError):
            c.DocumentReviewTask(p, at)
    for value in (None, Decimal(0), Decimal("-0.125"), Decimal("9" * 128 + ".50")):
        assert replace(p, proposed_value=value).proposed_value == value


def test_wrong_nested_contract_types_fail_typed(tmp_path: Path):
    from typing import Any, cast

    c = contract()
    task = c.DocumentReviewTask(proposal(tmp_path), AT + timedelta(seconds=2))
    for wrong in (None, "object", 1):
        with pytest.raises(ValueError):
            c.DocumentReviewTask(cast(Any, wrong), AT)
        with pytest.raises(ValueError):
            c.DocumentReviewDecision(cast(Any, wrong), AT)
        with pytest.raises(ValueError):
            c.ReviewHistory(cast(Any, wrong), None)
    with pytest.raises(ValueError):
        c.ReviewHistory(task, cast(Any, "decision"))


def test_domain_admission_preserves_predicates_units_and_typed_values(tmp_path: Path):
    from procurement_intelligence_lab.domains.procurement.document_reviews import (
        validate_bom_review,
    )

    c = contract()
    snapshot, _ = inputs(tmp_path)
    for previous in snapshot.assertions:
        value = (
            Decimal("2.25")
            if previous.predicate.value in ("has_quantity", "has_unit_price")
            else "Reviewed text"
        )
        p = c.ReviewProposal(
            snapshot.artifact.source.scope,
            previous.assertion_id,
            snapshot.snapshot_id,
            previous,
            value,
            "Human checked source",
            "human",
        )
        validate_bom_review(p)
        validate_bom_review(replace(p, proposed_value=None))
        invalid = True if isinstance(value, Decimal) else Decimal("2.25")
        with pytest.raises(ValueError):
            validate_bom_review(replace(p, proposed_value=invalid))
    from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate

    p = proposal(tmp_path)
    with pytest.raises(ValueError):
        validate_bom_review(
            replace(p, previous=replace(p.previous, predicate=AssertionPredicate.UNMAPPED_FIELD))
        )


def test_unicode_task_input_is_portable_before_any_write(tmp_path: Path):
    c = contract()
    p = proposal(tmp_path)
    invalid = "bad" + chr(0xD800) + "text"
    for changes in (
        {"reason": invalid},
        {"request_id": invalid},
        {"proposer_id": invalid},
        {"proposed_value": invalid},
    ):
        with pytest.raises(ValueError):
            replace(p, **changes)
    good = replace(p, reason="Source checked: résumé " + chr(0x1F4E6))
    assert c.DocumentReviewTask(good, AT + timedelta(seconds=2)).digest
