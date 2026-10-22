import json
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.semantic_codec import (
    MAX_PAYLOAD_BYTES,
    canonical,
    digest,
)
from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.execution.identity import (
    canonical as execution_canonical,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
)
from tests.planned_execution_archive_fixtures import executed, parameters


def test_actual_completed_prefix_roundtrips_with_exact_plan_bytes_and_digests(tmp_path: Path):
    r, _ = executed(tmp_path / "source.xlsx")
    completed = CompletedPrefixSnapshot.from_execution(r, parameters())
    codec = bootstrap.archive_codec()
    loaded = codec.loads(codec.dumps(completed))
    assert execution_canonical(loaded) == execution_canonical(completed)
    assert loaded.execution.plan.canonical_json == r.plan.canonical_json
    assert loaded.execution.execution_digest == r.execution_digest
    assert loaded.execution.receipt_digest == r.receipt_digest
    assert loaded.snapshot.normalization_policy_parameters == parameters()


def test_old_snapshot_wire_is_literal_unchanged():
    folder = Path(__file__).parents[1] / "fixtures/planned-execution-archive"
    wire = (folder / "legacy-snapshot-v1.json").read_text()
    assert (
        sha256(wire.encode()).hexdigest()
        == (folder / "legacy-snapshot-v1.sha256").read_text().strip()
    )
    codec = bootstrap.archive_codec()
    assert codec.dumps(codec.loads(wire)) == wire


@pytest.mark.parametrize("value", [b"", bytes(range(256))])
def test_bytes_tag_roundtrips(value: Any):
    codec = bootstrap.archive_codec()
    raw = codec.dumps(value)
    assert json.loads(raw)["root"] == ["bytes-hex", value.hex()]
    assert codec.loads(raw) == value


@pytest.mark.parametrize(
    "tag",
    [
        ["bytes-hex", "A0"],
        ["bytes-hex", "a"],
        ["bytes-hex", "xz"],
        ["bytes-hex", 0],
        ["bytes-hex", "aa", "extra"],
        ["bytes", "aa"],
        ["bytes-hex", "aa bb"],
    ],
)
def test_bytes_tag_is_strict(tag: Any):
    with pytest.raises(ArchiveIntegrityError):
        bootstrap.archive_codec().loads(canonical({"schema": 1, "root": tag, "records": {}}))


def test_bytes_tag_is_bounded():
    codec = bootstrap.archive_codec()
    with pytest.raises(ArchiveContractError):
        codec.dumps(b"x" * (MAX_PAYLOAD_BYTES // 2))
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(
            canonical({"schema": 1, "root": ["bytes-hex", "00" * MAX_PAYLOAD_BYTES], "records": {}})
        )


@pytest.mark.parametrize("mode", ["plan", "references", "enum", "binding"])
def test_rehashed_invalid_persisted_execution_fails_typed(tmp_path: Path, mode: str):
    r, _ = executed(tmp_path / "source.xlsx")
    codec = bootstrap.archive_codec()
    graph = json.loads(codec.dumps(CompletedPrefixSnapshot.from_execution(r, parameters())))
    # Mutate then rehash every reference: integrity must come from constructors, not just hashes.
    target = {
        "plan": "PhysicalPlan",
        "references": "PrefixExecutionReceipt",
        "enum": "StageExecutionEntry",
        "binding": "CompletedPrefixSnapshot",
    }[mode]
    for node in graph["records"].values():
        if node["kind"] != target:
            continue
        fields = dict(node["fields"])
        if mode == "plan":
            fields["canonical_json"] = ["bytes-hex", b"{}".hex()]
        elif mode == "references":
            fields["references"] = ["tuple", []]
        elif mode == "enum":
            fields["status"] = ["enum", "ExecutionStatus", "INVENTED"]
        else:
            node["kind"] = "UnknownCompletedPrefix"
        node["fields"] = [[k, fields[k]] for k, _ in node["fields"]]
        break
    records = graph["records"]
    new = {}

    def rebuild(value: Any) -> Any:
        if not isinstance(value, list):
            return value
        if value and value[0] == "ref":
            node = records[value[1]]
            node = {"kind": node["kind"], "fields": [[k, rebuild(v)] for k, v in node["fields"]]}
            key = digest(node)
            new[key] = node
            return ["ref", key]
        return [rebuild(x) for x in cast(list[Any], value)]

    graph["root"] = rebuild(graph["root"])
    graph["records"] = new
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(canonical(graph))
