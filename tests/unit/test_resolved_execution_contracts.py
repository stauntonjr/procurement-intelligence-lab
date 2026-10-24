"""Positive sixth invocation evidence and exact source-row membership."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import load_candidate_input
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    PackageExecutionError,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW
from tests.resolved_execution_fixtures import catalog_wire, resolved_parts


def test_resolution_output_exact_row_coverage(tmp_path: Path):
    r, _ = resolved_parts(tmp_path, rows=HEADER + ROW + ROW.replace("7", "8"))
    o = r.output
    assert len(o.outcomes) == 2
    assert o.outcomes[0].mention.text == o.outcomes[1].mention.text == "GPU-A"
    assert o.outcomes[0].outcome_id != o.outcomes[1].outcome_id
    assert len(o.canonicalized) == len(o.previous.assertions)
    assert not o.unlinked_assertion_ids
    for kwargs in [
        {"outcomes": o.outcomes[:1]},
        {"canonicalized": o.canonicalized[:-1]},
        {"outcomes": (o.outcomes[1], o.outcomes[0])},
        {"unlinked_assertion_ids": (o.previous.assertions[0].assertion_id,)},
    ]:
        with pytest.raises(PackageExecutionContractError):
            replace(o, **kwargs)
    with pytest.raises(PackageExecutionContractError):
        replace(o.outcomes[0], decision=o.outcomes[1].decision)


def test_empty_and_abstaining_output_retain_real_batch(tmp_path: Path):
    r, _ = resolved_parts(tmp_path, rows=HEADER)
    assert r.output.outcomes == ()
    assert r.output.reference_ids == (r.output.batch_id,)
    assert len(r.entries) == 12
    assert [e.status.value for e in r.entries] == ["SUCCEEDED"] * 6 + ["NOT_EXECUTED"] * 6
    assert r.requested_prefix_complete and not r.package_execution_complete
    r, _ = resolved_parts(tmp_path, keys=())
    assert not r.output.canonicalized
    assert len(r.output.unlinked_assertion_ids) == len(r.output.previous.assertions)


def test_sixth_receipt_identity_excludes_completion_and_raw_format(tmp_path: Path):
    r, _ = resolved_parts(tmp_path)
    raw = json.dumps(catalog_wire(), indent=2).encode()
    changed = replace(
        r,
        prefix=replace(r.prefix, completed_at=AT + timedelta(seconds=2)),
        candidate_input=load_candidate_input(raw),
        completed_at=AT + timedelta(seconds=3),
    )
    assert changed.execution_digest == r.execution_digest
    assert changed.receipt_digest != r.receipt_digest
    with pytest.raises(PackageExecutionContractError):
        replace(r, completed_at=AT)
    with pytest.raises(PackageExecutionContractError):
        replace(r, entries=r.prefix.entries)
    with pytest.raises(PackageExecutionContractError):
        replace(
            r, candidate_input=load_candidate_input(json.dumps(catalog_wire(("CPU-A",))).encode())
        )


def test_request_scope_namespace_and_future_catalog_rejected(tmp_path: Path):
    r, _ = resolved_parts(tmp_path)
    prefix = ExecutionRequest(r.prefix.source, r.prefix.context, AT, StageId.ASSERT)
    q = ResolvedExecutionRequest(prefix, r.candidate_input, r.policy, StageId.RESOLVE)
    assert q.stop_after is StageId.RESOLVE
    for value in [StageId.ASSERT, StageId.RECONCILE]:
        with pytest.raises(PackageExecutionError):
            replace(q, stop_after=value)
    for wire in [
        catalog_wire(effective_at=(AT + timedelta(seconds=1)).isoformat()),
        catalog_wire(entity_type="vendor"),
        catalog_wire(scope={**vars(prefix.source.scope), "version": "2"}),
    ]:
        with pytest.raises(PackageExecutionError):
            replace(q, candidate_input=load_candidate_input(json.dumps(wire).encode()))
