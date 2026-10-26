"""Bind full six-stage input and actual result independently of persistence/runtime I/O."""

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.archive import CompletedPrefixSnapshot
from procurement_intelligence_lab.platform.execution.identity import same, text
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    CompletedResolvedPrefixSnapshot,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import (
    CandidateInputEvidence,
    ResolutionPolicyEvidence,
)
from procurement_intelligence_lab.platform.processing.binding import (
    validate_completion as validate_prefix_completion,
)
from procurement_intelligence_lab.platform.processing.contracts import (
    JobDefinition,
    PinnedPrefixDefinition,
)
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    PinnedResolutionMetadata,
    PinnedResolvedPrefixDefinition,
    ResolvedJobDefinition,
    require,
    validate_graph,
)
from procurement_intelligence_lab.platform.processing.resolved_errors import (
    ResolvedJobContractError,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError


def validate_definition(d: PinnedResolvedPrefixDefinition) -> None:
    try:
        text(d.recipe_id)
        require(type(d.prefix) is PinnedPrefixDefinition and d.prefix.recipe_id == d.recipe_id)
        require(
            type(d.candidate_input) is CandidateInputEvidence
            and type(d.policy) is ResolutionPolicyEvidence
        )
        require(type(d.resolution_metadata) is PinnedResolutionMetadata)
        q = d.resolved_request
        require(same(q.prefix, d.prefix.request))
        r = d.resolution_metadata
        selection = next(s for s in d.prefix.config.selections if s.stage is StageId.RESOLVE)
        descriptor = next(
            v
            for v in d.prefix.registry.implementations
            if v.implementation_id == selection.implementation_id
        )
        require(same(descriptor, r.descriptor) and not r.settings and not selection.settings)
        require(r.descriptor.provider_version is None and r.descriptor.model_version is None)
        require(
            r.references == (d.policy.reference,)
            and r.policy_version == d.policy.reference.reference_id
        )
        from procurement_intelligence_lab.platform.execution.contracts import plan_payload

        b = plan_payload(d.prefix.plan)["stages"][5]
        require(
            b["mode"] == "EXECUTE"
            and b["domain_config_ref"] is None
            and b["policy_refs"] == [d.policy.reference.declaration_ref]
        )
        validate_graph(d)
    except (SemanticContractError, TypeError, ValueError, KeyError, AttributeError, StopIteration):
        raise ResolvedJobContractError("invalid pinned resolved prefix definition") from None


def validate_completion(
    job: ResolvedJobDefinition, completed: CompletedResolvedPrefixSnapshot, content: bytes
) -> None:
    try:
        require(
            type(job) is ResolvedJobDefinition
            and type(completed) is CompletedResolvedPrefixSnapshot
        )
        d = job.definition
        prefix_job = JobDefinition(job.arrival, job.idempotency_key, d.prefix)
        require(type(completed.prefix) is CompletedPrefixSnapshot)
        validate_prefix_completion(prefix_job, completed.prefix, content)
        r = completed.execution
        require(same(r.candidate_input, d.candidate_input) and same(r.policy, d.policy))
        metadata = d.resolution_metadata
        p = r.output.provenance
        require(
            p.component_name == metadata.descriptor.implementation_id
            and p.implementation_version == metadata.descriptor.implementation_version
        )
        require(p.policy_version == metadata.policy_version and p.schema_version is None)
    except (SemanticContractError, TypeError, ValueError, KeyError, AttributeError):
        raise ResolvedJobContractError(
            "resolved completion disagrees with pinned job evidence"
        ) from None
