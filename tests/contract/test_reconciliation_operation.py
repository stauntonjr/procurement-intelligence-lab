"""Application admission happens before storage and current executor construction."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn

import pytest

from procurement_intelligence_lab.adapters.package_reconciliation_executor import (
    PackageReconciliationExecutor,
)
from procurement_intelligence_lab.application.archived_resolved_execution import (
    ResolvedExecutionArchiveReader,
)
from procurement_intelligence_lab.application.retained_reconciliation import (
    RetainedReconciliationService,
)
from procurement_intelligence_lab.bootstrap import (
    archive_codec,
    bom_reconciliation_descriptor,
    validate_completed_resolved_bom_prefix,
)
from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    load_bom_authority,
)
from procurement_intelligence_lab.domains.procurement.reconciliation_validation import (
    validate_bom_reconciliation_inputs,
    validate_bom_reconciliation_output,
    validate_bom_reconciliation_static,
)
from procurement_intelligence_lab.domains.procurement.retained_reconciliation import (
    BomRetainedReconcileStrategy,
)
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.reconciliation_admission import (
    ReconcileExecutorRegistration,
)
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionError,
    UnsupportedReconciliationInputError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from tests.bom_stage_fixtures import AT, HEADER, SCOPE, provenance
from tests.reconciliation_fixtures import metadata, policy, producer
from tests.unit.test_reconciliation_runner import runtime


def forbidden(*args: Any, **kwargs: Any) -> NoReturn:
    raise AssertionError("unexpected executor/storage/source access")


def service(tmp_path: Path, *, empty: bool = True):
    p, data = producer(tmp_path, HEADER) if empty else producer(tmp_path)

    class Archive:
        def check_ready(self):
            pass

        def load(self, scope: StateScope, execution_digest: str):
            return p

        def content(self, scope: StateScope, execution_digest: str):
            return data

        append = history = forbidden

    m, r, c = runtime()
    calls: list[Any] = []

    def factory(inputs: Any):
        calls.append(inputs)
        executor = PackageReconciliationExecutor(
            BomRetainedReconcileStrategy(inputs), validate_bom_reconciliation_output
        )
        return ReconcileExecutorRegistration(
            bom_reconciliation_descriptor(),
            (),
            (inputs.policy.reference,),
            executor,
            inputs.policy.reference.reference_id,
        )

    reader = ResolvedExecutionArchiveReader(
        Archive(),
        validate_completed_resolved_bom_prefix,
        lambda x: archive_codec().dumps(x).encode(),
    )
    authority = load_bom_authority(json.dumps(metadata((p,))).encode()).evidence
    s = RetainedReconciliationService(
        m,
        r,
        c,
        policy(),
        authority,
        lambda: reader,
        lambda p: (
            len(archive_codec().dumps(p).encode()),
            len(json.loads(archive_codec().dumps(p))["records"]),
        ),
        factory,
        lambda i, t: validate_bom_reconciliation_inputs(i, started_at=t),
        validate_bom_reconciliation_output,
        lambda: AT + timedelta(seconds=4),
        validate_bom_reconciliation_static,
        bom_reconciliation_descriptor(),
    )
    args: dict[str, Any] = {
        "scope": SCOPE,
        "as_of": AT,
        "context": replace(
            provenance().context, code_revision="test-build", started_at=AT + timedelta(seconds=3)
        ),
        "producer_digests": (p.completed.execution_digest,),
    }
    return s, args, calls


def test_invalid_runtime_metadata_fails_before_storage(tmp_path: Path):
    s, args, calls = service(tmp_path)
    with pytest.raises(PackageExecutionError):
        replace(
            s,
            producer_reader_factory=forbidden,
            config=replace(s.config, application_version="foreign"),
        ).execute(**args)
    assert calls == []


def test_all_producers_validated_before_reconcile_construction(tmp_path: Path):
    s, args, calls = service(tmp_path)
    assert s.execute(**args).requested_operation_complete and len(calls) == 1
    invalid_args: dict[str, Any] = {**args, "as_of": AT + timedelta(days=1)}
    with pytest.raises(PackageExecutionError):
        replace(s, validate_inputs=forbidden, executor_factory=forbidden).execute(**invalid_args)


def test_catalog_or_aggregate_budget_rejects(tmp_path: Path):
    s, args, calls = service(tmp_path)
    for measurement in [(4 * 1024 * 1024 + 1, 1), (1, 12501)]:

        def measured(
            _: ArchivedResolvedPrefix, bound: tuple[int, int] = measurement
        ) -> tuple[int, int]:
            return bound

        with pytest.raises(UnsupportedReconciliationInputError):
            replace(s, measure_producer=measured).execute(**args)
    assert not calls


def test_supersession_omission_fails_before_invoke(tmp_path: Path):
    s, args, calls = service(tmp_path)

    def invalid(*args: Any):
        raise UnsupportedReconciliationInputError("test unsupported input")

    with pytest.raises(UnsupportedReconciliationInputError):
        replace(s, validate_inputs=invalid, executor_factory=forbidden).execute(**args)
    assert not calls


def test_unsupported_descriptor_fails_before_storage(tmp_path: Path):
    s, args, _ = service(tmp_path)
    from procurement_intelligence_lab.platform.planning.contracts import ImplementationRegistry

    descriptors = tuple(
        replace(d, implementation_version="2") if d.stage is StageId.RECONCILE else d
        for d in s.registry.implementations
    )
    with pytest.raises(PackageExecutionError):
        replace(
            s,
            registry=ImplementationRegistry("1.0", descriptors),
            producer_reader_factory=forbidden,
            executor_factory=forbidden,
        ).execute(**args)


def test_future_operation_context_fails_before_storage(tmp_path: Path):
    s, args, _ = service(tmp_path)
    with pytest.raises(PackageExecutionError):
        replace(s, clock=lambda: AT, producer_reader_factory=forbidden).execute(**args)
