"""Actual sixth admission rejects metadata incompatibility before an absent source."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.identity import digest
from procurement_intelligence_lab.platform.execution.resolution_admission import (
    prepare_resolved_prefix,
)
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    ResolutionPolicyEvidence,
    load_candidate_input,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from tests.bom_stage_fixtures import AT
from tests.contract.test_planned_resolved_bom_execution import service
from tests.resolved_execution_fixtures import planned_resolved_inputs


@pytest.mark.parametrize("change", ["version", "descriptor", "settings", "policy", "code"])
def test_sixth_preflight_rejects_before_absent_source(tmp_path: Path, change: str):
    inputs = planned_resolved_inputs(tmp_path, source_exists=False)
    s = service(inputs)
    if change == "version":
        s = replace(
            s,
            resolution=replace(
                s.resolution,
                descriptor=replace(s.resolution.descriptor, implementation_version="changed"),
            ),
        )
    elif change == "descriptor":
        s = replace(
            s,
            resolution=replace(
                s.resolution,
                descriptor=replace(s.resolution.descriptor, provider_version="changed"),
            ),
        )
    elif change == "settings":
        s = replace(s, resolution=replace(s.resolution, settings=(("unknown", "x"),)))
    elif change == "policy":
        s = replace(s, resolution=replace(s.resolution, policy_version="unsupported"))
    else:
        s = replace(
            s,
            prefix=replace(s.prefix, config=replace(s.prefix.config, application_version="wrong")),
        )
    with pytest.raises(SemanticContractError) as error:
        s.execute(inputs[3])
    assert error.value.code.value != "pil.input.artifact_source_unavailable"


def test_non_procurement_fixture_uses_same_neutral_runner():
    from procurement_intelligence_lab.platform.execution.contracts import ResolvedReference
    from procurement_intelligence_lab.platform.execution.outputs import AssertedOutput
    from procurement_intelligence_lab.platform.execution.resolution_admission import (
        ResolveExecutorRegistration,
    )
    from procurement_intelligence_lab.platform.execution.resolution_contracts import (
        ResolveInvocation,
    )
    from procurement_intelligence_lab.platform.execution.resolution_outputs import ResolvedOutput
    from procurement_intelligence_lab.platform.execution.resolution_runner import (
        run_resolved_prefix,
    )
    from tests.execution_fixtures import executable_inputs
    from tests.planning_fixtures import planning_inputs
    from tests.resolved_execution_fixtures import catalog_wire

    m, _, _, executors, q, calls = executable_inputs()
    wire = json.loads(m)
    wire["stages"][5].update(
        mode="EXECUTE", neutral_semantics=None, policy_refs=["neutral.resolve/none@1"]
    )
    m = json.dumps(wire, sort_keys=True, separators=(",", ":")).encode()
    registry, config = planning_inputs(m)
    config = replace(config, application_version=q.context.code_revision)
    descriptor = next(d for d in registry.implementations if d.stage is StageId.RESOLVE)
    parameters = (("entity_type", "neutral_item"), ("identifier_namespace", "neutral_key"))
    policy = ResolutionPolicyEvidence(
        ResolvedReference("neutral.resolve/none@1", "neutral-policy@1", digest(dict(parameters))),
        "neutral_item",
        "neutral_key",
        parameters,
    )
    candidate = load_candidate_input(
        json.dumps(
            catalog_wire((), entity_type="neutral_item", identifier_namespace="neutral_key")
        ).encode()
    )
    request = ResolvedExecutionRequest(q, candidate, policy, StageId.RESOLVE)

    class Empty:
        def invoke(
            self, inputs: AssertedOutput, *, invocation: ResolveInvocation
        ) -> ResolvedOutput:
            calls.append(StageId.RESOLVE)
            return ResolvedOutput(
                inputs, candidate.snapshot, policy, (), (), (), invocation.provenance
            )

    registration = ResolveExecutorRegistration(
        descriptor,
        next(s.settings for s in config.selections if s.stage is StageId.RESOLVE),
        (policy.reference,),
        Empty(),
        policy.reference.reference_id,
    )
    prepared = prepare_resolved_prefix(
        m,
        registry=registry,
        config=config,
        executors=executors,
        resolution=registration,
        request=request,
        now=AT,
    )
    result = run_resolved_prefix(prepared, clock=lambda: AT)
    assert calls == list(StageId)[:6]
    assert not result.output.outcomes
    assert result.receipt.entries[5].event_id
