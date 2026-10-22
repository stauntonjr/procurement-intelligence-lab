from dataclasses import replace
from datetime import timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    CompletedPrefixSnapshot,
    ExecutionArchiveReceipt,
    ExecutionHistoryPage,
    same_computation,
)
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt
from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError
from tests.bom_stage_fixtures import HEADER, ROW
from tests.planned_execution_archive_fixtures import executed, parameters


def source_receipt(completed: CompletedPrefixSnapshot):
    s = completed.snapshot
    return ArchiveReceipt(
        1,
        s.snapshot_id,
        completed.scope,
        s.artifact.artifact_id,
        s.artifact.content_hash,
        len(s.assertions),
        s.origin.recorded_at,
    )


def archived(completed: CompletedPrefixSnapshot, sequence: Any = 1):
    return ArchivedPrefix(
        completed,
        ExecutionArchiveReceipt(
            sequence,
            completed.execution_digest,
            completed.execution.receipt_digest,
            source_receipt(completed),
        ),
    )


@pytest.mark.parametrize("rows", [HEADER, HEADER + ROW, HEADER + ROW + ROW.replace("7", "8")])
def test_actual_completed_binding_and_identity(tmp_path: Path, rows: str):
    receipt, _ = executed(tmp_path / "source.xlsx", rows)
    completed = CompletedPrefixSnapshot.from_execution(receipt, parameters())
    assert completed.snapshot.transformations == tuple(x.event for x in receipt.output.chain)
    assert len(completed.snapshot.assertions) == len(receipt.output.assertions)
    assert sha256(receipt.computation_payload).hexdigest() == receipt.execution_digest
    assert (
        canonical(
            (
                receipt.plan,
                receipt.context,
                receipt.source,
                receipt.references,
                receipt.output,
                receipt.entries,
            )
        )
        == receipt.computation_payload
    )
    assert archived(completed).receipt.snapshot_id == completed.snapshot.snapshot_id


def test_first_completion_is_the_only_ignored_computation_field(tmp_path: Path):
    r, _ = executed(tmp_path / "source.xlsx")
    first = CompletedPrefixSnapshot.from_execution(r, parameters())
    for at in (
        r.completed_at + timedelta(seconds=1),
        r.completed_at.astimezone(timezone(timedelta(hours=2))),
    ):
        later = CompletedPrefixSnapshot.from_execution(replace(r, completed_at=at), parameters())
        assert same_computation(first, later)
        assert first.execution.receipt_digest != later.execution.receipt_digest
    altered = replace(
        first,
        snapshot=replace(first.snapshot, normalization_policy_parameters=(("other", "value"),)),
    )
    assert not same_computation(first, altered)
    with pytest.raises(ArchiveContractError):
        replace(
            archived(first),
            completed=CompletedPrefixSnapshot.from_execution(
                replace(r, completed_at=r.completed_at + timedelta(seconds=1)), parameters()
            ),
        )


def test_completed_binding_rejects_foreign_snapshot_policy_and_mention_encoding(tmp_path: Path):
    r, _ = executed(tmp_path / "source.xlsx")
    c = CompletedPrefixSnapshot.from_execution(r, parameters())
    with pytest.raises(ArchiveContractError):
        replace(
            c,
            snapshot=replace(
                c.snapshot, normalization_policy_parameters=cast(Any, list(parameters()))
            ),
        )
    with pytest.raises(ArchiveContractError):
        CompletedPrefixSnapshot.from_execution(cast(Any, None), parameters())
    mention = c.snapshot.mentions[0]
    changed = replace(
        mention, observed_at=mention.observed_at.astimezone(timezone(timedelta(hours=2)))
    )
    with pytest.raises(ArchiveContractError):
        replace(c, snapshot=replace(c.snapshot, mentions=(changed, *c.snapshot.mentions[1:])))
    claim = mention.assertions[0]
    assert claim.context is not None
    p = claim.context.provenance
    changed_claim = replace(
        claim,
        context=replace(
            claim.context,
            provenance=replace(
                p,
                context=replace(
                    p.context,
                    started_at=p.context.started_at.astimezone(timezone(timedelta(hours=2))),
                ),
            ),
        ),
    )
    changed = replace(mention, assertions=(changed_claim, *mention.assertions[1:]))
    with pytest.raises(ArchiveContractError):
        replace(c, snapshot=replace(c.snapshot, mentions=(changed, *c.snapshot.mentions[1:])))


@pytest.mark.parametrize("sequence", [0, -1, True, 1.5, "1"])
def test_receipt_rejects_invalid_sequence(tmp_path: Path, sequence: Any):
    r, _ = executed(tmp_path / "source.xlsx")
    with pytest.raises(ArchiveContractError):
        archived(CompletedPrefixSnapshot.from_execution(r, parameters()), sequence)


@pytest.mark.parametrize("digest", ["", "A" * 64, "a" * 63, None])
def test_receipt_rejects_invalid_digest(tmp_path: Path, digest: Any):
    r, _ = executed(tmp_path / "source.xlsx")
    c = CompletedPrefixSnapshot.from_execution(r, parameters())
    with pytest.raises(ArchiveContractError):
        ExecutionArchiveReceipt(1, digest, r.receipt_digest, source_receipt(c))


def test_history_bounds_and_cursor(tmp_path: Path):
    r, _ = executed(tmp_path / "source.xlsx")
    c = CompletedPrefixSnapshot.from_execution(r, parameters())
    a = archived(c).receipt
    assert ExecutionHistoryPage(c.scope, 0, 1, (a,), True, 1).has_more
    assert not ExecutionHistoryPage(c.scope, 0, 1, (a,), False, None).has_more
    valid: dict[str, Any] = {
        "scope": c.scope,
        "after_sequence": 0,
        "limit": 1,
        "receipts": (a,),
        "has_more": False,
        "next_after_sequence": None,
    }
    for change in (
        {"limit": 0},
        {"limit": 201},
        {"limit": True},
        {"limit": 1.5},
        {"after_sequence": True},
        {"after_sequence": -1},
        {"receipts": (a, a)},
        {"has_more": 1},
        {"has_more": True},
        {"next_after_sequence": 1},
        {"after_sequence": 1},
        {"has_more": True, "next_after_sequence": True},
        {"receipts": (), "has_more": True, "next_after_sequence": 1},
    ):
        with pytest.raises(ArchiveContractError):
            ExecutionHistoryPage(**cast(Any, valid | change))


@pytest.mark.parametrize(
    "parameters",
    [
        None,
        1,
        [["currency", "USD"]],
        (("currency",),),
        ((1, "USD"),),
        (("a", ""),),
        (("z", "1"), ("a", "2")),
        (("a", "1"), ("a", "2")),
    ],
)
def test_projection_rejects_all_malformed_policy_parameters_typed(tmp_path: Path, parameters: Any):
    r, _ = executed(tmp_path / "source.xlsx")
    with pytest.raises(ArchiveContractError):
        CompletedPrefixSnapshot.from_execution(r, parameters)
