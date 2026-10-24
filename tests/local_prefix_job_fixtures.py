"""Synthetic real-prefix job inputs and explicit clocks."""

from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.domains.procurement.normalization import BomNormalizationPolicy
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from procurement_intelligence_lab.platform.processing.contracts import (
    ArtifactArrival,
    JobDefinition,
    PinnedPrefixDefinition,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source
from tests.planned_bom_fixtures import planned_inputs

NOW = AT + timedelta(seconds=2)


def job_input(
    path: Path,
    *,
    key: str = "request-1",
    rows: str = HEADER + ROW,
    policy: BomNormalizationPolicy = POLICY,
):
    path = workbook(path, rows)
    manifest, registry, config = planned_inputs()
    registry = replace(
        registry,
        implementations=tuple(
            replace(d, required_settings=(), optional_settings=()) for d in registry.implementations
        ),
    )
    config = replace(config, selections=tuple(replace(s, settings=()) for s in config.selections))
    service = bootstrap.build_planned_bom_service(
        manifest=manifest, registry=registry, config=config, policy=policy, clock=lambda: NOW
    )
    prepared = service.prepare(
        ExecutionRequest(source(path), provenance().context, AT, StageId.ASSERT)
    )
    definition = PinnedPrefixDefinition.from_prepared(
        prepared,
        recipe_id="procurement.bom-local-prefix@1",
        normalization_parameters=tuple(sorted(policy.as_dict().items())),
    )
    content = path.read_bytes()
    arrival = ArtifactArrival(
        prepared.request.source.scope,
        "event-1",
        prepared.request.source,
        sha256(content).hexdigest(),
        len(content),
        AT,
    )
    return JobDefinition(arrival, key, definition), prepared, content
