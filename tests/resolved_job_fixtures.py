"""Pinned synthetic six-stage job inputs; actual executors, no persistence side effects."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.domains.procurement.normalization import BomNormalizationPolicy
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.platform.execution.resolution_admission import (
    PreparedResolvedPrefix,
)
from procurement_intelligence_lab.platform.processing.contracts import ArtifactArrival
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    PinnedResolvedPrefixDefinition,
    ResolvedJobDefinition,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW
from tests.contract.test_bom_assertions import POLICY
from tests.local_prefix_job_fixtures import NOW
from tests.resolved_execution_fixtures import planned_resolved_inputs


def job_input(
    path: Path,
    *,
    key: str = "request-1",
    rows: str = HEADER + ROW,
    keys: tuple[str, ...] = ("GPU-A",),
    policy: BomNormalizationPolicy = POLICY,
):
    directory = path.parent if path.suffix else path
    directory.mkdir(parents=True, exist_ok=True)
    m, r, c, q, source = planned_resolved_inputs(directory, rows=rows, keys=keys)
    if path.suffix and path != source:
        from tests.contract.test_bom_stage_adapters import source as source_reference

        source.rename(path)
        source = path
        q = replace(q, prefix=replace(q.prefix, source=source_reference(path)))
    r = replace(
        r,
        implementations=tuple(
            replace(d, required_settings=(), optional_settings=()) for d in r.implementations
        ),
    )
    c = replace(c, selections=tuple(replace(s, settings=()) for s in c.selections))
    service = bootstrap.build_planned_resolved_bom_service(
        manifest=m,
        registry=r,
        config=c,
        normalization_policy=policy,
        resolution_policy=BomResolutionPolicy.from_parameters(q.policy.parameters),
        candidate_input=q.candidate_input,
        clock=lambda: NOW,
    )
    prepared = service.prepare(q)
    definition = PinnedResolvedPrefixDefinition.from_prepared(
        prepared,
        recipe_id="procurement.bom-local-resolved-prefix@1",
        normalization_parameters=tuple(sorted(policy.as_dict().items())),
    )
    content = source.read_bytes()
    arrival = ArtifactArrival(
        q.prefix.source.scope,
        "event-1",
        q.prefix.source,
        sha256(content).hexdigest(),
        len(content),
        AT,
    )
    return ResolvedJobDefinition(arrival, key, definition), prepared, content


def completed(job: ResolvedJobDefinition, prepared: PreparedResolvedPrefix):
    from procurement_intelligence_lab.platform.execution.resolution_archive import (
        CompletedResolvedPrefixSnapshot,
    )
    from procurement_intelligence_lab.platform.execution.resolution_runner import (
        run_resolved_prefix,
    )

    return CompletedResolvedPrefixSnapshot.from_execution(
        run_resolved_prefix(prepared, clock=lambda: NOW).receipt,
        job.definition.prefix.normalization_parameters,
    )
