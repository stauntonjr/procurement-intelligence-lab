"""Synthetic completed records produced by the real admitted five-stage runner."""

from datetime import timedelta
from pathlib import Path

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source
from tests.planned_bom_fixtures import planned_inputs


def executed(path: Path, rows: str = HEADER + ROW):
    manifest, registry, config = planned_inputs()
    path = workbook(path, rows)
    service = bootstrap.build_planned_bom_service(
        manifest=manifest,
        registry=registry,
        config=config,
        policy=POLICY,
        clock=lambda: AT + timedelta(seconds=1),
    )
    return service.execute(
        ExecutionRequest(source(path), provenance().context, AT, StageId.ASSERT)
    ).execution.receipt, path.read_bytes()


def parameters():
    return tuple(sorted(POLICY.as_dict().items()))
