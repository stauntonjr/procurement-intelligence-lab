from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import NoReturn

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.application.archived_planned_execution import (
    PlannedExecutionArchiveReader,
)
from procurement_intelligence_lab.domains.procurement.normalization import BomNormalizationPolicy
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.archive import (
    ArchivedPrefix,
    CompletedPrefixSnapshot,
    ExecutionArchiveReceipt,
    ExecutionHistoryPage,
    same_computation,
)
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from procurement_intelligence_lab.platform.semantics.archive import ArchiveReceipt
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
    ArchiveUnavailableError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source
from tests.contract.test_package_document_executors import CountingExecutor
from tests.planned_bom_fixtures import planned_inputs
from tests.planned_execution_archive_fixtures import parameters

pytestmark = pytest.mark.contract


class MemoryArchive:
    def __init__(self) -> None:
        self.retained: ArchivedPrefix | None = None
        self.bytes: bytes | None = None
        self.ready = True

    def check_ready(self) -> None:
        if not self.ready:
            raise ArchiveUnavailableError("capability unavailable")

    def append(self, completed: CompletedPrefixSnapshot, content: bytes):
        c = completed
        if self.retained is None:
            s = c.snapshot
            r = ArchiveReceipt(
                1,
                s.snapshot_id,
                c.scope,
                s.artifact.artifact_id,
                s.artifact.content_hash,
                len(s.assertions),
                s.origin.recorded_at,
            )
            self.retained = ArchivedPrefix(
                c, ExecutionArchiveReceipt(1, c.execution_digest, c.execution.receipt_digest, r)
            )
            self.bytes = content
        assert same_computation(c, self.retained.completed)
        return self.retained

    def load(self, scope: StateScope, execution_digest: str) -> ArchivedPrefix:
        assert self.retained is not None
        return self.retained

    def history(self, scope: StateScope, *, limit: int = 100, after_sequence: int = 0):
        assert self.retained is not None
        return ExecutionHistoryPage(
            scope, after_sequence, limit, (self.retained.receipt,), False, None
        )

    def content(self, scope: StateScope, execution_digest: str):
        assert self.bytes is not None
        return self.bytes


def setup(tmp_path: Path, rows: str = HEADER + ROW, policy: BomNormalizationPolicy = POLICY):
    m, r, c = planned_inputs()
    archive = MemoryArchive()
    service = bootstrap.build_planned_bom_archive_service(
        manifest=m,
        registry=r,
        config=c,
        policy=policy,
        clock=lambda: AT + timedelta(seconds=1),
        archive_factory=lambda: archive,
    )
    path = workbook(tmp_path / "source.xlsx", rows)
    q = ExecutionRequest(source(path), provenance().context, AT, StageId.ASSERT)
    return service, archive, q, path


def forbidden(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError("forbidden source/executor/factory access")


def test_actual_five_stages_run_on_every_invocation_and_recovery_is_source_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from procurement_intelligence_lab.application.asserted_document_stages import (
        AssertedDocumentStages,
    )
    from procurement_intelligence_lab.application.document_stages import DocumentStages
    from procurement_intelligence_lab.application.normalized_document_stages import (
        NormalizedDocumentStages,
    )

    service, archive, q, path = setup(tmp_path)
    content = path.read_bytes()
    calls: list[StageId] = []
    factory = service.executions.executor_factory

    def counting(at: datetime):
        r = factory(at)
        return replace(
            r,
            registrations=tuple(
                replace(x, executor=CountingExecutor(x.executor, calls)) for x in r.registrations
            ),
        )

    service = replace(service, executions=replace(service.executions, executor_factory=counting))
    for cls in (DocumentStages, NormalizedDocumentStages, AssertedDocumentStages):
        monkeypatch.setattr(cls, "run", forbidden)
    first = service.execute(q)
    assert calls == list(StageId)[:5]
    later = replace(
        service, executions=replace(service.executions, clock=lambda: AT + timedelta(seconds=2))
    ).execute(q)
    assert calls == list(StageId)[:5] * 2
    assert (
        first.current.execution.receipt.receipt_digest
        != later.current.execution.receipt.receipt_digest
    )
    assert later.retained == first.retained
    body = later.as_dict()
    assert (
        body["execution_receipt"]["execution_digest"]
        == body["retained_execution_receipt"]["execution_digest"]
    )
    assert (
        body["execution_receipt"]["receipt_digest"]
        != body["retained_execution_receipt"]["receipt_digest"]
    )
    assert (
        body["archive_receipt"]["source_receipt"]["receipt_id"]
        == first.retained.receipt.source_receipt.receipt_id
    )
    path.unlink()
    monkeypatch.setattr(type(service.executions), "prepare", forbidden)
    reader = PlannedExecutionArchiveReader(archive, service.validate_completed)
    assert (
        reader.show(q.source.scope, first.retained.receipt.execution_digest).as_dict()[
            "retained_execution_receipt"
        ]
        == first.as_dict()["retained_execution_receipt"]
    )
    assert reader.history(q.source.scope).receipts == (first.retained.receipt,)
    assert reader.content(q.source.scope, first.retained.receipt.execution_digest) == content


@pytest.mark.parametrize(
    "rows",
    [
        HEADER,
        HEADER + ROW + ROW.replace("7", "8"),
        HEADER + ROW.replace("0.5", "0"),
        HEADER + ROW.replace("<v>0.5</v>", "<v>-2</v>"),
        HEADER + ROW.replace('<c r="C7"><v>0.5</v></c>', ""),
    ],
)
def test_empty_duplicate_unknown_zero_negative_and_fractional_values_preserved(
    tmp_path: Path, rows: str
):
    service, _, q, _ = setup(tmp_path, rows)
    result = service.execute(q)
    expected = (
        bootstrap.build_bom_assertion_service(captured_at=AT, context=q.context, policy=POLICY)
        .run(q.source)
        .as_dict()
    )
    assert result.as_dict()["assertion_batch"] == expected["assertion_batch"]
    assert result.retained.completed.snapshot.normalization_policy_parameters == parameters()


def test_runtime_admission_precedes_storage_factory_and_storage_precedes_source(tmp_path: Path):
    service, archive, q, path = setup(tmp_path)
    path.unlink()
    r = service.executions.registry
    first = r.implementations[0]
    bad = replace(
        r, implementations=(replace(first, implementation_version="2"), *r.implementations[1:])
    )
    with pytest.raises(SemanticContractError):
        replace(
            service, archive_factory=forbidden, executions=replace(service.executions, registry=bad)
        ).execute(q)
    archive.ready = False
    with pytest.raises(ArchiveUnavailableError):
        service.execute(q)


def test_candidate_and_retained_validation_have_distinct_typed_failures(tmp_path: Path):
    service, archive, q, _ = setup(tmp_path)

    def invalid(c: CompletedPrefixSnapshot):
        raise ValueError("private sensitive detail")

    with pytest.raises(ArchiveContractError, match="completed"):
        replace(service, validate_completed=invalid).execute(q)
    assert archive.retained is None
    result = service.execute(q)
    reader = PlannedExecutionArchiveReader(archive, invalid)
    for read in (reader.show, reader.content):
        with pytest.raises(ArchiveIntegrityError) as e:
            read(q.source.scope, result.retained.receipt.execution_digest)
        assert "private" not in str(e.value)
    with pytest.raises(ArchiveIntegrityError):
        reader.history(q.source.scope)


def test_retained_policy_full_content_digest_and_declaration_are_verified(tmp_path: Path):
    service, _, q, _ = setup(tmp_path)
    result = service.execute(q)
    c = result.retained.completed
    # Intrinsically valid snapshot parameters are still required to match actual policy content.
    for p in (
        (("profile", "unsupported"),),
        tuple(sorted(dict(parameters(), currency="GBP").items())),
    ):
        changed = replace(c, snapshot=replace(c.snapshot, normalization_policy_parameters=p))
        with pytest.raises(SemanticContractError):
            service.validate_completed(changed)
