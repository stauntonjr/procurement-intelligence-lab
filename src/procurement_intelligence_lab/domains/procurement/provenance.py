"""Procurement composition helpers for platform provenance contracts."""

from datetime import UTC, datetime

from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)

__all__ = (
    "ComponentKind",
    "DecisionProvenance",
    "ProvenanceContext",
    "ProvenanceEdge",
    "ProvenanceRelation",
    "TransformationEvent",
    "local_provenance_context",
)


def local_provenance_context() -> ProvenanceContext:
    """Provide an explicit development context for the procurement demo."""

    return ProvenanceContext(
        run_id="local",
        workflow_name="bom-pipeline",
        workflow_version="dev",
        code_revision="working-tree",
        image_digest="local",
        config_digest="local",
        dependency_lock_digest=None,
        input_snapshot_ids=(),
        started_at=datetime.now(UTC),
    )
