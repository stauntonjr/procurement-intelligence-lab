"""Authorized application boundary for deterministic anomaly assessment."""

from dataclasses import dataclass
from datetime import datetime

from procurement_intelligence_lab.domains.procurement.anomaly_assessment import (
    AnomalyAssessment,
    AnomalyAssessmentInput,
    AnomalyAssessmentPolicies,
    QuantityAssessmentPolicies,
    assess_anomalies,
    assess_quantity,
)
from procurement_intelligence_lab.platform.semantics.errors import ScopeAuthorizationError
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext


@dataclass(frozen=True)
class AnomalyService:
    policies: QuantityAssessmentPolicies | AnomalyAssessmentPolicies
    provenance: DecisionProvenance
    detected_at: datetime

    def assess(
        self,
        inputs: AnomalyAssessmentInput,
        *,
        request_context: RequestContext,
    ) -> tuple[AnomalyAssessment, ...]:
        request_context.require(Permission.READ_STATE)
        scope = inputs.scope
        if (
            request_context.tenant_id,
            request_context.project_id,
            request_context.site_id,
        ) != (scope.tenant_id, scope.project_id, scope.site_id):
            raise ScopeAuthorizationError("request is not authorized for assessment scope")
        if isinstance(self.policies, AnomalyAssessmentPolicies):
            return assess_anomalies(
                inputs,
                policies=self.policies,
                provenance=self.provenance,
                detected_at=self.detected_at,
            )
        return assess_quantity(
            inputs,
            policy=self.policies,
            provenance=self.provenance,
            detected_at=self.detected_at,
        )
