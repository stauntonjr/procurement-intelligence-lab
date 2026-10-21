"""Executable domain-neutral empty-document fixture; no procurement imports."""

from dataclasses import dataclass, replace
from hashlib import sha256

from procurement_intelligence_lab.platform.domain_packages.compiler import compile_domain_package
from procurement_intelligence_lab.platform.domain_packages.package import (
    STAGE_CATALOG,
    DomainPackage,
    SourceProfile,
    StageBinding,
    StageId,
    StageMode,
)
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionRequest,
    ResolvedReference,
    StageInvocation,
)
from procurement_intelligence_lab.platform.execution.executors import (
    ExecutorRegistration,
    ExecutorRegistry,
)
from procurement_intelligence_lab.platform.execution.identity import digest
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    CapturedOutput,
    MappedOutput,
    NormalizedOutput,
    StageInput,
    StageOutput,
    StructuredOutput,
    event,
)
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationRegistry,
)
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import AssertionOrigin
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from tests.bom_stage_fixtures import AT, SCOPE, provenance
from tests.planning_fixtures import planning_inputs


@dataclass
class EmptyExecutor:
    stage: StageId
    calls: list[StageId]
    substitute: bool = False

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> StageOutput:
        self.calls.append(self.stage)
        p = invocation.provenance
        if self.substitute:
            p = replace(p, implementation_version="substituted")
        if self.stage is StageId.INGEST:
            assert type(inputs) is SourceReference
            a = Artifact(
                inputs, sha256(b"empty").hexdigest(), "text/plain", 5, invocation.captured_at, p
            )
            return CapturedOutput(
                a, event("artifact-capture", p, (inputs.reference_id,), (a.artifact_id,))
            )
        if self.stage is StageId.STRUCTURE:
            assert type(inputs) is CapturedOutput
            d = StructuredDocument(inputs.artifact, (), p)
            return StructuredOutput(
                inputs,
                d,
                event(
                    "document-structuring",
                    p,
                    inputs.reference_ids,
                    (d.document_id,),
                    (inputs.event.event_id,),
                ),
            )
        if self.stage is StageId.MAP:
            assert type(inputs) is StructuredOutput
            schema = invocation.references[0].reference_id
            d = MappedDocument(inputs.document, schema, (), p)
            return MappedOutput(
                inputs,
                d,
                event(
                    "schema-mapping",
                    p,
                    inputs.reference_ids,
                    (d.mapped_document_id,),
                    (inputs.event.event_id,),
                    schema,
                ),
            )
        if self.stage is StageId.NORMALIZE:
            assert type(inputs) is MappedOutput
            return NormalizedOutput(inputs, (), p, invocation.references[0].reference_id)
        assert type(inputs) is NormalizedOutput
        origin = AssertionOrigin(
            inputs.previous.previous.previous.artifact,
            inputs.batch_id,
            inputs.event,
            invocation.captured_at,
        )
        return AssertedOutput(inputs, (), (), origin, p)


def executable_inputs():
    refs = {
        StageId.MAP: "neutral.mapping/document@1",
        StageId.NORMALIZE: "neutral.normalize/values@1",
        StageId.ASSERT: "neutral.assert/claims@1",
    }
    bindings = tuple(
        StageBinding(
            d.stage,
            StageMode.EXECUTE,
            domain_config_ref=refs[d.stage] if d.stage is StageId.MAP else None,
            policy_refs=(refs[d.stage],) if d.stage in (StageId.NORMALIZE, StageId.ASSERT) else (),
        )
        if i < 5
        else StageBinding(d.stage, StageMode.EMPTY, neutral_semantics=d.empty_result)
        for i, d in enumerate(STAGE_CATALOG)
    )
    manifest = compile_domain_package(
        DomainPackage("1.0", "neutral", "1.0.0", (SourceProfile("documents", "1.0.0", bindings),)),
        source_profile="documents",
    ).canonical_json
    registry, config = planning_inputs(manifest)
    config = replace(config, application_version=provenance().context.code_revision)
    calls: list[StageId] = []
    registrations: list[ExecutorRegistration] = []
    for d in registry.implementations:
        r = (
            (ResolvedReference(refs[d.stage], refs[d.stage], digest(refs[d.stage])),)
            if d.stage in refs
            else ()
        )
        registrations.append(
            ExecutorRegistration(
                d,
                next(s.settings for s in config.selections if s.stage is d.stage),
                r,
                EmptyExecutor(d.stage, calls),
                policy_version=refs[d.stage]
                if d.stage in (StageId.NORMALIZE, StageId.ASSERT)
                else None,
                schema_version="neutral-document@1" if d.stage is StageId.MAP else None,
            )
        )
    request = ExecutionRequest(
        SourceReference("fixture", "fixture://empty", SCOPE, AT),
        provenance().context,
        AT,
        StageId.ASSERT,
    )
    return manifest, registry, config, ExecutorRegistry(tuple(registrations)), request, calls


type ExecutionInputs = tuple[
    bytes,
    ImplementationRegistry,
    ImplementationConfig,
    ExecutorRegistry,
    ExecutionRequest,
    list[StageId],
]
