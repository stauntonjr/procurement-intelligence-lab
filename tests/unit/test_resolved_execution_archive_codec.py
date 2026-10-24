"""Allowlisted six-stage evidence must reject semantically invalid resealed graphs."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.semantic_codec import canonical, digest
from procurement_intelligence_lab.platform.execution.identity import (
    canonical as execution_canonical,
)
from procurement_intelligence_lab.platform.semantics.errors import ArchiveIntegrityError
from tests.resolved_execution_fixtures import completed_resolved


def test_actual_sixth_graph_round_trips_with_raw_catalog(tmp_path: Path):
    completed, _ = completed_resolved(tmp_path)
    codec = bootstrap.archive_codec()
    restored = codec.loads(codec.dumps(completed))
    assert execution_canonical(restored) == execution_canonical(completed)
    assert restored.execution.execution_digest == completed.execution.execution_digest
    assert (
        restored.execution.candidate_input.raw_json == completed.execution.candidate_input.raw_json
    )
    assert len(restored.prefix.snapshot.transformations) == 5


@pytest.mark.parametrize(
    "kind,field,value",
    cast(
        list[tuple[str, str, Any]],
        [
            ("CandidateInputEvidence", "raw_json", ["bytes-hex", b"{}".hex()]),
            ("ResolutionPolicyEvidence", "parameters", ["tuple", []]),
            ("MentionResolution", "matched_keys", ["tuple", []]),
            ("ResolvedOutput", "unlinked_assertion_ids", ["tuple", []]),
            ("ResolvedPrefixExecutionReceipt", "entries", ["tuple", []]),
        ],
    ),
)
def test_rehashed_resolution_substitution_is_integrity_failure(
    tmp_path: Path, kind: str, field: str, value: Any
):
    completed, _ = completed_resolved(tmp_path)
    # Make unlinked membership invalid for this otherwise fully resolved source.
    if kind == "ResolvedOutput":
        value = ["tuple", [["str", "foreign-claim"]]]
    codec = bootstrap.archive_codec()
    graph = json.loads(codec.dumps(completed))
    for node in graph["records"].values():
        if node["kind"] == kind:
            node["fields"] = [[k, value if k == field else v] for k, v in node["fields"]]
            break
    records = graph["records"]
    new: dict[str, Any] = {}

    def rebuild(v: Any) -> Any:
        if not isinstance(v, list):
            return v
        if v and v[0] == "ref":
            node = records[v[1]]
            node = {"kind": node["kind"], "fields": [[k, rebuild(x)] for k, x in node["fields"]]}
            key = digest(node)
            new[key] = node
            return ["ref", key]
        return [rebuild(x) for x in cast(list[Any], v)]

    graph["root"] = rebuild(graph["root"])
    graph["records"] = new
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(canonical(graph))
