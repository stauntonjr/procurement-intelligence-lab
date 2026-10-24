"""Strict explicit resolution policy and catalog boundary."""

from procurement_intelligence_lab.domains.procurement.planned_resolution import (
    validate_bom_resolution_inputs,
)
from procurement_intelligence_lab.domains.procurement.resolution_policy import BomResolutionPolicy
from procurement_intelligence_lab.interfaces.execute_package import record, string
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import ExecutionRequest
from procurement_intelligence_lab.platform.execution.resolution_contracts import (
    ResolvedExecutionRequest,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import load_candidate_input
from procurement_intelligence_lab.platform.semantics.errors import PackageExecutionError


def resolution_policy(data: bytes) -> BomResolutionPolicy:
    value = record(data)
    if set(value) != {
        "profile",
        "entity_type",
        "identifier_namespace",
        "normalization",
        "matching",
    }:
        raise PackageExecutionError("resolution requires the exact supported policy fields")
    return BomResolutionPolicy.from_parameters(
        tuple(sorted((k, string(v)) for k, v in value.items()))
    )


def resolved_request(
    prefix: ExecutionRequest, candidate_data: bytes, policy: BomResolutionPolicy
) -> ResolvedExecutionRequest:
    candidate = load_candidate_input(candidate_data)
    validate_bom_resolution_inputs(
        candidate, policy, scope=prefix.source.scope, as_of=prefix.captured_at
    )
    return ResolvedExecutionRequest(prefix, candidate, policy.evidence, StageId.RESOLVE)
