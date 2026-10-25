"""Strict public context/policy parsing and canonical deployment identity."""

import re
from dataclasses import asdict
from typing import Any

from procurement_intelligence_lab.domains.procurement.reconciliation_policy import (
    BomReconciliationPolicy,
    identifier,
    strict_json,
    timestamp,
)
from procurement_intelligence_lab.platform.execution.identity import digest
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    OperationAuthorityEvidence,
    ReconciliationPolicyEvidence,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationRegistry,
    PhysicalPlan,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope


def operation_context(data: bytes, *, config_digest: str) -> tuple[StateScope, ProvenanceContext]:
    value = strict_json(data, 32768)
    admit(set(value) == {"scope", "run_id", "code_revision", "started_at"})
    s = value["scope"]
    admit(type(s) is dict and set(s) == {"tenant_id", "project_id", "site_id", "version"})
    scope = StateScope(
        *(identifier(s[k]) for k in ("tenant_id", "project_id", "site_id", "version"))
    )
    revision = identifier(value["code_revision"])
    admit(re.fullmatch("[0-9a-f]{40}", revision) is not None)
    context = ProvenanceContext(
        identifier(value["run_id"]),
        "retained-resolution-reconciliation",
        "1",
        revision,
        "local-uncontainerized",
        config_digest,
        None,
        (),
        timestamp(value["started_at"]),
    )
    return scope, context


def reconciliation_policy(data: bytes) -> BomReconciliationPolicy:
    return BomReconciliationPolicy.from_data(data)


def deployment_digest(
    plan: PhysicalPlan,
    registry: ImplementationRegistry,
    policy: ReconciliationPolicyEvidence,
    authority: OperationAuthorityEvidence,
) -> str:
    descriptors: list[dict[str, Any]] = []
    for d in sorted(registry.implementations, key=lambda d: d.implementation_id):
        data = asdict(d)
        for key in ("capabilities", "required_settings", "optional_settings"):
            data[key] = sorted(data[key])
        descriptors.append(data)
    return digest(
        (
            "retained-reconciliation-deployment-v1",
            plan.plan_hash,
            tuple(descriptors),
            policy,
            authority.schema_id,
            authority.semantic_json,
        )
    )
