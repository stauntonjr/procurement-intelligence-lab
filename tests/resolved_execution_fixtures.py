"""Synthetic actual first-five results and explicit neutral resolution evidence."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from procurement_intelligence_lab.platform.domain_packages.package import StageId, StageMode
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionStatus,
    ResolvedReference,
    StageExecutionEntry,
)
from procurement_intelligence_lab.platform.execution.identity import digest
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedPrefixExecutionReceipt,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    ResolutionPolicyEvidence,
    load_candidate_input,
)
from procurement_intelligence_lab.platform.execution.resolution_outputs import (
    MentionResolution,
    ResolvedOutput,
    resolution_input_ids,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    CanonicalizedAssertion,
    ResolutionDecision,
    ResolutionStatus,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, SCOPE
from tests.planned_execution_archive_fixtures import executed


def catalog_wire(keys: Any = ("GPU-A",), **changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "catalog_id": "synthetic-items",
        "catalog_revision": "1",
        "scope": vars(SCOPE),
        "entity_type": "procurement_item",
        "identifier_namespace": "internal_sku",
        "effective_at": AT.isoformat(),
        "keys": list(cast(tuple[object, ...], keys)) if type(keys) is tuple else keys,
    }
    value.update(changes)
    return value


def catalog(keys: tuple[str, ...] = ("GPU-A",), **changes: Any):
    return load_candidate_input(
        json.dumps(catalog_wire(keys, **changes), ensure_ascii=False).encode()
    )


def policy_evidence():
    parameters = tuple(
        sorted(
            {
                "profile": "bom-normalized-exact@1",
                "entity_type": "procurement_item",
                "identifier_namespace": "internal_sku",
                "normalization": "casefold-alnum@1",
                "matching": "unique-normalized-match@1",
            }.items()
        )
    )
    value = digest(dict(parameters))
    return ResolutionPolicyEvidence(
        ResolvedReference(
            "procurement.resolve/normalized-exact@1", "bom-normalized-exact@1:" + value, value
        ),
        "procurement_item",
        "internal_sku",
        parameters,
    )


def resolved_parts(tmp_path: Path, *, rows: str = HEADER + ROW, keys: tuple[str, ...] = ("GPU-A",)):
    prefix, content = executed(tmp_path / "source.xlsx", rows)
    evidence = catalog(keys)
    policy = policy_evidence()
    metadata = json.loads(prefix.plan.canonical_json)["stages"][5]["implementation"]
    p = DecisionProvenance(
        replace(
            prefix.context,
            input_snapshot_ids=tuple(
                dict.fromkeys(
                    (
                        *prefix.context.input_snapshot_ids,
                        *resolution_input_ids(prefix.output, evidence.snapshot, policy),
                    )
                )
            ),
        ),
        metadata["implementation_id"],
        ComponentKind.DETERMINISTIC,
        metadata["implementation_version"],
        policy_version=policy.reference.reference_id,
    )
    outcomes: list[MentionResolution] = []
    links: list[CanonicalizedAssertion] = []
    for mention in prefix.output.mentions:
        sku = next(a for a in mention.assertions if a.value == mention.text)
        matches = ("GPU-A",) if "GPU-A" in keys else ()
        d = ResolutionDecision(
            mention.text,
            "GPU-A" if matches else None,
            ResolutionStatus.RESOLVED if matches else ResolutionStatus.UNRESOLVED,
            (sku,),
            "normalized exact identifier match" if matches else "no normalized candidate match",
            p,
        )
        outcomes.append(
            MentionResolution(
                mention, d, evidence.snapshot.snapshot_id, matches, policy.reference.reference_id
            )
        )
        if matches:
            links.extend(CanonicalizedAssertion(a, d, SCOPE, AT) for a in mention.assertions)
    linked = {a.assertion.assertion_id for a in links}
    output = ResolvedOutput(
        prefix.output,
        evidence.snapshot,
        policy,
        tuple(outcomes),
        tuple(links),
        tuple(a.assertion_id for a in prefix.output.assertions if a.assertion_id not in linked),
        p,
    )
    entries = list(prefix.entries)
    entries[5] = StageExecutionEntry(
        StageId.RESOLVE,
        StageMode.EXECUTE,
        ExecutionStatus.SUCCEEDED,
        None,
        p.component_name,
        output.input_ids,
        output.reference_ids,
        output.event.event_id,
    )
    receipt = ResolvedPrefixExecutionReceipt(
        prefix, evidence, policy, output, tuple(entries), AT + timedelta(seconds=2)
    )
    return receipt, content


def planned_resolved_inputs(
    tmp_path: Path,
    *,
    rows: str = HEADER + ROW,
    keys: tuple[str, ...] = ("GPU-A",),
    source_exists: bool = True,
):
    from procurement_intelligence_lab import bootstrap
    from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
    from procurement_intelligence_lab.platform.execution.resolution_contracts import (
        ResolvedExecutionRequest,
    )
    from procurement_intelligence_lab.platform.planning.contracts import (
        ImplementationRegistry,
        StageSelection,
    )
    from tests.bom_stage_fixtures import provenance, workbook
    from tests.contract.test_bom_stage_adapters import source
    from tests.planned_bom_fixtures import planned_inputs

    manifest, registry, config = planned_inputs()
    descriptor = bootstrap.bom_resolution_descriptor()
    registry = ImplementationRegistry(
        "1.0", (*registry.implementations[:5], descriptor, *registry.implementations[6:])
    )
    config = replace(
        config,
        selections=(
            *config.selections[:5],
            StageSelection(
                StageId.RESOLVE, descriptor.implementation_id, descriptor.config_schema_version
            ),
            *config.selections[6:],
        ),
    )
    path = tmp_path / "actual.xlsx"
    if source_exists:
        workbook(path, rows)
    request = ResolvedExecutionRequest(
        ExecutionRequest(source(path), provenance().context, AT, StageId.ASSERT),
        catalog(keys),
        policy_evidence(),
        StageId.RESOLVE,
    )
    return manifest, registry, config, request, path


def completed_resolved(tmp_path: Path):
    from procurement_intelligence_lab import bootstrap
    from procurement_intelligence_lab.domains.procurement.resolution_policy import (
        BomResolutionPolicy,
    )
    from procurement_intelligence_lab.platform.execution.resolution_archive import (
        CompletedResolvedPrefixSnapshot,
    )
    from tests.contract.test_bom_assertions import POLICY
    from tests.planned_execution_archive_fixtures import parameters

    m, r, c, q, path = planned_resolved_inputs(tmp_path)
    service = bootstrap.build_planned_resolved_bom_service(
        manifest=m,
        registry=r,
        config=c,
        normalization_policy=POLICY,
        resolution_policy=BomResolutionPolicy.from_parameters(q.policy.parameters),
        candidate_input=q.candidate_input,
        clock=lambda: AT + timedelta(seconds=1),
    )
    return CompletedResolvedPrefixSnapshot.from_execution(
        service.execute(q).execution.receipt, parameters()
    ), path.read_bytes()
