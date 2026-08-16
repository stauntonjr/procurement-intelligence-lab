"""Runtime strategy Protocols for the fixed logical stage topology."""

from datetime import datetime
from types import MappingProxyType
from typing import Protocol

from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.semantics.actions import (
    ActionResult,
    ApprovedDecision,
)
from procurement_intelligence_lab.platform.semantics.anomalies import Anomaly
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact, SourceReference
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.decisions import (
    Decision,
    FactsAnomaliesPredictions,
)
from procurement_intelligence_lab.platform.semantics.derivation import DerivedFact
from procurement_intelligence_lab.platform.semantics.documents import (
    MappedDocument,
    StructuredDocument,
)
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.prediction import EvidenceAndState, Prediction
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.reconciliation import (
    ReconciliationDecision,
)
from procurement_intelligence_lab.platform.semantics.resolution import (
    CanonicalizedAssertion,
    EntityMention,
    ResolutionDecision,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope
from procurement_intelligence_lab.platform.semantics.state import OperationalState


class IngestStrategy(Protocol):
    def ingest(
        self, source: SourceReference, *, provenance: DecisionProvenance
    ) -> tuple[Artifact, ...]: ...


class StructureStrategy(Protocol):
    def structure(
        self, artifact: Artifact, *, provenance: DecisionProvenance
    ) -> StructuredDocument: ...


class MapStrategy(Protocol):
    def map_document(
        self, document: StructuredDocument, *, provenance: DecisionProvenance
    ) -> MappedDocument: ...


class NormalizeStrategy(Protocol):
    def normalize(
        self, document: MappedDocument, *, provenance: DecisionProvenance
    ) -> tuple[NormalizedObservation, ...]: ...


class AssertStrategy(Protocol):
    def assert_observations(
        self,
        observations: tuple[NormalizedObservation, ...],
        *,
        provenance: DecisionProvenance,
    ) -> tuple[tuple[SourceAssertion, ...], tuple[EntityMention, ...]]: ...


class ResolveStrategy(Protocol):
    def resolve(
        self,
        mentions: tuple[EntityMention, ...],
        assertions: tuple[SourceAssertion, ...],
        *,
        provenance: DecisionProvenance,
    ) -> tuple[tuple[ResolutionDecision, ...], tuple[CanonicalizedAssertion, ...]]: ...


class ReconcileStrategy(Protocol):
    def reconcile(
        self,
        assertions: tuple[CanonicalizedAssertion, ...],
        *,
        scope: StateScope,
        as_of: datetime,
        provenance: DecisionProvenance,
    ) -> tuple[tuple[ReconciliationDecision, ...], tuple[OperationalState, ...]]: ...


class DeriveStrategy(Protocol):
    def derive(
        self,
        states: tuple[OperationalState, ...],
        *,
        as_of: datetime,
        provenance: DecisionProvenance,
    ) -> tuple[DerivedFact, ...]: ...


class DetectStrategy(Protocol):
    def detect(
        self,
        states: tuple[OperationalState, ...],
        facts: tuple[DerivedFact, ...],
        *,
        detected_at: datetime,
    ) -> tuple[Anomaly, ...]: ...


class PredictStrategy(Protocol):
    def predict(
        self, inputs: EvidenceAndState, *, provenance: DecisionProvenance
    ) -> tuple[Prediction, ...]: ...


class DecideStrategy(Protocol):
    def decide(
        self,
        inputs: FactsAnomaliesPredictions,
        *,
        provenance: DecisionProvenance,
    ) -> tuple[Decision, ...]: ...


class ActStrategy(Protocol):
    def act(
        self, decision: ApprovedDecision, *, provenance: DecisionProvenance
    ) -> ActionResult: ...


STAGE_STRATEGIES: MappingProxyType[StageId, type[object]] = MappingProxyType(
    {
        StageId.INGEST: IngestStrategy,
        StageId.STRUCTURE: StructureStrategy,
        StageId.MAP: MapStrategy,
        StageId.NORMALIZE: NormalizeStrategy,
        StageId.ASSERT: AssertStrategy,
        StageId.RESOLVE: ResolveStrategy,
        StageId.RECONCILE: ReconcileStrategy,
        StageId.DERIVE: DeriveStrategy,
        StageId.DETECT: DetectStrategy,
        StageId.PREDICT: PredictStrategy,
        StageId.DECIDE: DecideStrategy,
        StageId.ACT: ActStrategy,
    }
)
