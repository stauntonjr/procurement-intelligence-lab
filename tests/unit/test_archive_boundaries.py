import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from procurement_intelligence_lab.application.archived_documents import snapshot_for
from procurement_intelligence_lab.bootstrap import archive_codec, build_bom_assertion_service
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn, load_scope
from procurement_intelligence_lab.interfaces.assertion_archive import export_content
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt
from procurement_intelligence_lab.platform.semantics.errors import ArchiveContractError
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source


def test_scope_and_export_are_explicit_and_fail_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.bom_stage_fixtures import SCOPE

    scope = tmp_path / "scope.json"
    for raw in (
        "[]",
        "{}",
        '{"tenant_id":"one","tenant_id":"two"}',
        json.dumps({"tenant_id": "", "project_id": "p", "site_id": "s", "version": "v"}),
    ):
        scope.write_text(raw)
        with pytest.raises(ArchiveContractError):
            load_scope(scope)
    scope.write_text(
        json.dumps(
            {
                "tenant_id": SCOPE.tenant_id,
                "project_id": SCOPE.project_id,
                "site_id": SCOPE.site_id,
                "version": SCOPE.version,
            }
        )
    )
    assert load_scope(scope) == SCOPE
    scope.unlink()
    with pytest.raises(ArchiveContractError):
        load_scope(scope)
    monkeypatch.delenv("PIL_ASSERTION_ARCHIVE_DSN", raising=False)
    with pytest.raises(ArchiveContractError):
        configured_dsn()
    monkeypatch.setenv("PIL_ASSERTION_ARCHIVE_DSN", "configured privately")
    assert configured_dsn() == "configured privately"
    output = tmp_path / "source.bin"
    export_content(output, b"original")
    with pytest.raises(ArchiveContractError):
        export_content(output, b"replacement")
    assert output.read_bytes() == b"original"
    with pytest.raises(ArchiveContractError):
        export_content(tmp_path / "absent" / "source.bin", b"content")
    assert not list(tmp_path.glob("tmp*"))


def test_snapshot_rejects_incomplete_foreign_or_reordered_source_graph(tmp_path: Path) -> None:
    result = build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    ).run(source(workbook(tmp_path / "source.xlsx", HEADER + ROW)))
    s = snapshot_for(result)
    variants = (
        {"normalization_policy_parameters": (("z", "1"), ("a", "2"))},
        {"normalization_policy_parameters": (("a", "1"), ("a", "2"))},
        {"normalization_policy_reference": ""},
        {
            "structured": replace(
                s.structured,
                provenance=replace(s.structured.provenance, implementation_version="other"),
            )
        },
        {"transformations": s.transformations[:-1]},
        {
            "transformations": (
                replace(s.transformations[0], parent_event_ids=("foreign",)),
                *s.transformations[1:],
            )
        },
        {"assertions": s.assertions[:-1]},
        {"observations": s.observations[:-1]},
        {"assertions": tuple(reversed(s.assertions))},
        {
            "mentions": (
                replace(s.mentions[0], scope=replace(s.mentions[0].scope, tenant_id="foreign")),
            )
        },
    )
    for changes in variants:
        with pytest.raises(ArchiveContractError):
            replace(s, **changes)
    for sequence, count, time in ((0, 4, AT), (1, -1, AT), (1, 4, AT.replace(tzinfo=None))):
        with pytest.raises(ArchiveContractError):
            ArchiveReceipt(
                sequence,
                s.snapshot_id,
                s.artifact.source.scope,
                s.artifact.artifact_id,
                s.artifact.content_hash,
                count,
                time,
            )
    receipt = ArchiveReceipt(
        1,
        s.snapshot_id,
        s.artifact.source.scope,
        s.artifact.artifact_id,
        s.artifact.content_hash,
        4,
        AT,
    )
    assert archive_codec().loads(archive_codec().dumps(receipt)) == receipt


def test_codec_records_are_immutable_and_object_sharing_does_not_change_wire_identity() -> None:
    from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
    from procurement_intelligence_lab.platform.semantics.scope import StateScope

    @dataclass
    class Mutable:
        value: str

    with pytest.raises(ArchiveContractError):
        SemanticCodec((Mutable,), ())
    scope = StateScope("t", "p", "s", "1")
    codec = archive_codec()
    assert codec.dumps((scope, scope)) == codec.dumps((replace(scope), replace(scope)))


def test_codec_limits_and_retained_policy_declarations_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from procurement_intelligence_lab.adapters import semantic_codec as wire
    from procurement_intelligence_lab.domains.procurement.normalization import (
        validate_bom_policy_declaration,
    )
    from procurement_intelligence_lab.platform.semantics.errors import (
        ArchiveIntegrityError,
        NormalizationPolicyError,
    )
    from tests.bom_stage_fixtures import SCOPE

    codec = archive_codec()
    raw = codec.dumps(SCOPE)
    nested: object = None
    for _ in range(70):
        nested = (nested,)
    with pytest.raises(ArchiveContractError):
        codec.dumps(nested)
    with pytest.raises(ArchiveContractError):
        wire.SemanticCodec((type(SCOPE), type(SCOPE)), ())
    monkeypatch.setattr(wire, "MAX_NODES", 0)
    with pytest.raises(ArchiveContractError):
        codec.dumps(SCOPE)
    with pytest.raises(ArchiveIntegrityError):
        codec.loads(raw)
    declaration = tuple(sorted(POLICY.as_dict().items()))
    validate_bom_policy_declaration(declaration, POLICY.reference_id)
    for parameters, reference in (
        ((), POLICY.reference_id),
        (declaration, "wrong"),
        (tuple(sorted({**POLICY.as_dict(), "currency": "EUR"}.items())), POLICY.reference_id),
    ):
        with pytest.raises(NormalizationPolicyError):
            validate_bom_policy_declaration(parameters, reference)
