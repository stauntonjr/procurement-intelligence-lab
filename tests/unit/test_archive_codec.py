from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.semantics import archive as ledger
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source


def test_complete_snapshot_roundtrips_without_losing_claim_identity(tmp_path: Path) -> None:
    assert hasattr(ledger, "DocumentSnapshot")
    assert hasattr(bootstrap, "archive_codec")
    result = bootstrap.build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    ).run(source(workbook(tmp_path / "source.xlsx", HEADER + ROW)))
    from procurement_intelligence_lab.application.archived_documents import result_for, snapshot_for

    snapshot = snapshot_for(result)
    codec = bootstrap.archive_codec()
    raw = codec.dumps(snapshot)
    restored = codec.loads(raw)
    assert restored == snapshot
    assert result_for(restored).as_dict() == result.as_dict()
    assert codec.dumps(restored) == raw
    assert [a.assertion_id for a in restored.assertions] == [
        a.assertion_id for a in result.assertions
    ]
    assert len(raw) < 100000


def test_codec_uses_typed_values_and_rejects_unsupported_types() -> None:
    assert hasattr(bootstrap, "archive_codec")
    codec = bootstrap.archive_codec()
    values = (
        None,
        True,
        1,
        "1",
        Decimal("-0.000"),
        Decimal("9" * 128 + ".50"),
        date(2026, 1, 1),
        datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    )
    for value in values:
        restored = codec.loads(codec.dumps(value))
        assert type(restored) is type(value) and restored == value
        assert str(restored) == str(value)
    for value in (1.5, Decimal("NaN"), AT.replace(tzinfo=None), {"arbitrary": "object"}):
        with pytest.raises(ValueError):
            codec.dumps(value)


@pytest.mark.parametrize(
    "root",
    [
        [],
        ["str", 1],
        ["int", True],
        ["decimal", "oops"],
        ["decimal", "NaN"],
        ["date", "invalid"],
        ["datetime", "2026-01-01T00:00:00"],
        ["enum", "missing", "x"],
        ["tuple", "wrong"],
        ["ref", "missing"],
        ["unknown"],
    ],
)
def test_corrupt_scalar_graphs_fail_typed(root: object) -> None:
    import json

    from procurement_intelligence_lab.platform.semantics.errors import ArchiveIntegrityError

    with pytest.raises(ArchiveIntegrityError):
        bootstrap.archive_codec().loads(json.dumps({"schema": 1, "root": root, "records": {}}))


def test_schema_duplicate_keys_orphans_unknown_record_fields_and_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    from procurement_intelligence_lab.adapters import semantic_codec as wire
    from procurement_intelligence_lab.platform.semantics.errors import (
        ArchiveContractError,
        ArchiveIntegrityError,
    )
    from procurement_intelligence_lab.platform.semantics.scope import StateScope

    codec = bootstrap.archive_codec()
    raw = codec.dumps(StateScope("tenant", "project", "site", "version"))
    graph = json.loads(raw)
    malformed = ["null", "[]", '{"schema":1,"schema":1}', raw.replace('"schema":1', '"schema":2')]
    orphan = json.loads(raw)
    orphan["root"] = ["null"]
    malformed.append(json.dumps(orphan))
    for mutation in ("kind", "fields", "type"):
        changed = json.loads(raw)
        node = changed["records"].pop(changed["root"][1])
        if mutation == "kind":
            node["kind"] = "unregistered"
        elif mutation == "fields":
            node["fields"].append(["extra", ["str", "x"]])
        else:
            node["fields"][0][1] = ["bool", True]
        key = wire.digest(node)
        changed["records"][key] = node
        changed["root"] = ["ref", key]
        malformed.append(json.dumps(changed))
    for item in malformed:
        with pytest.raises(ArchiveIntegrityError):
            codec.loads(item)
    monkeypatch.setattr(wire, "MAX_PAYLOAD_BYTES", 10)
    with pytest.raises(ArchiveContractError):
        codec.dumps("long string")
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(raw)
    assert graph["schema"] == 1


def test_source_event_mismatch_is_not_an_archive_snapshot(tmp_path: Path) -> None:
    from dataclasses import replace

    from procurement_intelligence_lab.application.archived_documents import snapshot_for
    from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError

    result = bootstrap.build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    ).run(source(workbook(tmp_path / "source.xlsx", HEADER)))
    snapshot = snapshot_for(result)
    events = list(snapshot.transformations)
    # Keep event identity coherent while making its declared output unrelated to capture.
    events[0] = replace(events[0], output_ids=("unrelated",))
    for i in range(1, len(events)):
        events[i] = replace(events[i], parent_event_ids=(events[i - 1].event_id,))
    origin = replace(snapshot.origin, normalization_event=events[3])
    with pytest.raises(ArchiveContractError):
        replace(snapshot, transformations=tuple(events), origin=origin)
