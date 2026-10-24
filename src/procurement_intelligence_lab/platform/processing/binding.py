"""Full pinned input/actual output binding, independent of deployment technologies."""

from hashlib import sha256

from procurement_intelligence_lab.platform.execution.archive import (
    CompletedPrefixSnapshot,
    _parameters,  # pyright: ignore[reportPrivateUsage]
)
from procurement_intelligence_lab.platform.execution.contracts import (
    PREFIX,
    ExecutionRequest,
    plan_payload,
)
from procurement_intelligence_lab.platform.execution.identity import same, text
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationRegistry,
    PhysicalPlan,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.processing.contracts import (
    JobDefinition,
    PinnedPrefixDefinition,
    PinnedStageMetadata,
    require,
    validate_graph,
)
from procurement_intelligence_lab.platform.processing.errors import JobContractError
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError


def validate_definition(definition: PinnedPrefixDefinition) -> None:
    d = definition
    try:
        text(d.recipe_id)
        require(type(d.manifest) is bytes and len(d.manifest) <= 1048576)
        require(
            type(d.registry) is ImplementationRegistry
            and type(d.config) is ImplementationConfig
            and type(d.request) is ExecutionRequest
            and type(d.plan) is PhysicalPlan
        )
        require(all(not s.settings for s in d.config.selections))
        require(not d.request.context.environment)
        require(d.request.context.code_revision == d.config.application_version)
        require(same(plan_manifest(d.manifest, registry=d.registry, config=d.config), d.plan))
        _parameters(d.normalization_parameters)
        require(
            type(d.stage_metadata) is tuple and tuple(m.stage for m in d.stage_metadata) == PREFIX
        )
        payload = plan_payload(d.plan)
        for metadata, binding in zip(d.stage_metadata, payload["stages"][:5], strict=True):
            require(type(metadata) is PinnedStageMetadata and binding["mode"] == "EXECUTE")
            keys = tuple(
                sorted(
                    (
                        *binding["policy_refs"],
                        *((binding["domain_config_ref"],) if binding["domain_config_ref"] else ()),
                    )
                )
            )
            require(tuple(r.declaration_ref for r in metadata.references) == keys)
        validate_graph(d)
    except (SemanticContractError, TypeError, ValueError, KeyError, AttributeError):
        raise JobContractError("invalid pinned prefix definition") from None


def validate_completion(
    job: JobDefinition, completed: CompletedPrefixSnapshot, content: bytes
) -> None:
    require(type(job) is JobDefinition and type(completed) is CompletedPrefixSnapshot)
    d = job.definition
    r = completed.execution
    require(
        same(r.source, d.request.source)
        and same(r.plan, d.plan)
        and same(r.context, d.effective_context)
    )
    for actual, metadata in zip(r.output.chain, d.stage_metadata, strict=True):
        provenance = actual.event.provenance
        require(same(provenance.policy_version, metadata.policy_version))
        require(same(provenance.schema_version, metadata.schema_version))
    expected_refs = {r.declaration_ref: r for m in d.stage_metadata for r in m.references}
    require(same(r.references, tuple(expected_refs[k] for k in sorted(expected_refs))))
    require(same(completed.snapshot.normalization_policy_parameters, d.normalization_parameters))
    require(
        type(content) is bytes
        and len(content) == job.arrival.expected_byte_length
        and sha256(content).hexdigest() == job.arrival.expected_content_hash
    )
    a = completed.snapshot.artifact
    require(
        a.content_hash == job.arrival.expected_content_hash
        and a.byte_length == job.arrival.expected_byte_length
        and same(a.captured_at, d.request.captured_at)
    )
