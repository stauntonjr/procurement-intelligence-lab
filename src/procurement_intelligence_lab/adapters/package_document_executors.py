"""One injected strategy call per actual document-stage execution."""

from collections.abc import Callable
from dataclasses import dataclass

from procurement_intelligence_lab.platform.execution.contracts import StageInvocation
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    CapturedOutput,
    MappedOutput,
    NormalizedOutput,
    StageInput,
    StructuredOutput,
    event,
    require,
)
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import (
    AssertionOrigin,
    SourceAssertion,
)
from procurement_intelligence_lab.platform.semantics.document_lineage import validate_capture
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    DocumentStageError,
    PackageExecutionContractError,
)
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention
from procurement_intelligence_lab.platform.semantics.strategies import (
    AssertStrategy,
    IngestStrategy,
    MapStrategy,
    NormalizeStrategy,
    StructureStrategy,
)


@dataclass(frozen=True)
class CaptureExecutor:
    strategy: IngestStrategy

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> CapturedOutput:
        require(type(inputs) is SourceReference)
        assert type(inputs) is SourceReference
        captured = self.strategy.ingest(inputs, provenance=invocation.provenance)
        require(type(captured) is tuple and all(type(a) is Artifact for a in captured))
        try:
            artifact = validate_capture(inputs, captured, invocation.provenance)
        except DocumentStageError:
            raise PackageExecutionContractError(
                "capture must return exactly the requested source"
            ) from None
        return CapturedOutput(
            artifact,
            event(
                "artifact-capture",
                invocation.provenance,
                (inputs.reference_id,),
                (artifact.artifact_id,),
            ),
        )


@dataclass(frozen=True)
class StructureExecutor:
    strategy: StructureStrategy

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> StructuredOutput:
        require(type(inputs) is CapturedOutput)
        assert type(inputs) is CapturedOutput
        d = self.strategy.structure(inputs.artifact, provenance=invocation.provenance)
        require(type(d) is StructuredDocument)
        return StructuredOutput(
            inputs,
            d,
            event(
                "document-structuring",
                invocation.provenance,
                inputs.reference_ids,
                (d.document_id,),
                (inputs.event.event_id,),
            ),
        )


@dataclass(frozen=True)
class MapExecutor:
    strategy: MapStrategy
    schema_reference: str

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> MappedOutput:
        require(type(inputs) is StructuredOutput)
        assert type(inputs) is StructuredOutput
        d = self.strategy.map_document(inputs.document, provenance=invocation.provenance)
        require(type(d) is MappedDocument and d.mapping_schema == self.schema_reference)
        return MappedOutput(
            inputs,
            d,
            event(
                "schema-mapping",
                invocation.provenance,
                inputs.reference_ids,
                (d.mapped_document_id,),
                (inputs.event.event_id,),
                self.schema_reference,
            ),
        )


@dataclass(frozen=True)
class NormalizeExecutor:
    strategy: NormalizeStrategy
    policy_reference: str

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> NormalizedOutput:
        require(
            type(inputs) is MappedOutput
            and invocation.provenance.policy_version == self.policy_reference
        )
        assert type(inputs) is MappedOutput
        observations = self.strategy.normalize(inputs.document, provenance=invocation.provenance)
        return NormalizedOutput(inputs, observations, invocation.provenance, self.policy_reference)


@dataclass(frozen=True)
class AssertExecutor:
    factory: Callable[[AssertionOrigin], AssertStrategy]
    validator: Callable[
        [tuple[NormalizedObservation, ...], tuple[SourceAssertion, ...], tuple[EntityMention, ...]],
        None,
    ]

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> AssertedOutput:
        require(type(inputs) is NormalizedOutput)
        assert type(inputs) is NormalizedOutput
        origin = AssertionOrigin(
            inputs.previous.previous.previous.artifact,
            inputs.batch_id,
            inputs.event,
            invocation.captured_at,
        )
        assertions, mentions = self.factory(origin).assert_observations(
            inputs.observations, provenance=invocation.provenance
        )
        output = AssertedOutput(inputs, assertions, mentions, origin, invocation.provenance)
        self.validator(inputs.observations, assertions, mentions)
        return output
