from datetime import UTC, datetime

import pytest

from procurement_intelligence_lab.domains.procurement.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)


def _context(config_digest: str = "config-a") -> ProvenanceContext:
    return ProvenanceContext(
        run_id="run-1",
        workflow_name="bom-pipeline",
        workflow_version="1",
        code_revision="git-sha",
        image_digest="sha256:image",
        config_digest=config_digest,
        dependency_lock_digest="sha256:lock",
        input_snapshot_ids=("artifact-1",),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_execution_context_identity_changes_with_effective_config() -> None:
    first = _context("config-a")
    second = _context("config-b")

    assert first.context_id != second.context_id


def test_model_decisions_require_resolved_model_identity() -> None:
    with pytest.raises(ValueError, match="model ID"):
        DecisionProvenance(
            _context(),
            "entity-resolver",
            ComponentKind.MODEL,
            "1",
            model_provider="provider",
            model_id="model",
        )


def test_decision_provenance_links_component_to_execution_context() -> None:
    provenance = DecisionProvenance(
        _context(),
        "normalized-exact-resolver",
        ComponentKind.DETERMINISTIC,
        "1",
        policy_version="policy-1",
    )

    assert provenance.context.context_id == _context().context_id
    assert provenance.provenance_id.startswith("decision-provenance:")


def test_transformation_event_identity_changes_with_implementation_version() -> None:
    first = TransformationEvent(
        "document-structuring",
        DecisionProvenance(
            _context(),
            "xlsx-bom-structurer",
            ComponentKind.DETERMINISTIC,
            "1",
            schema_version="bom-xlsx-v1",
        ),
        (ProvenanceEdge(ProvenanceRelation.USED_INPUT, "artifact:hash"),),
        ("structured-bom:hash:BOM",),
    )
    second = TransformationEvent(
        "document-structuring",
        DecisionProvenance(
            _context(),
            "xlsx-bom-structurer",
            ComponentKind.DETERMINISTIC,
            "2",
            schema_version="bom-xlsx-v1",
        ),
        (ProvenanceEdge(ProvenanceRelation.USED_INPUT, "artifact:hash"),),
        ("structured-bom:hash:BOM",),
    )

    assert first.event_id != second.event_id


def test_model_transformation_retains_resolved_model_and_schema_identity() -> None:
    event = TransformationEvent(
        "document-structuring",
        DecisionProvenance(
            _context(),
            "model-structurer",
            ComponentKind.MODEL,
            "1",
            model_provider="provider",
            model_id="model",
            model_revision="2026-01-01",
            prompt_version="prompt-v1",
            schema_version="bom-schema-v2",
        ),
        (ProvenanceEdge(ProvenanceRelation.USED_INPUT, "artifact:hash"),),
        ("structured-bom:hash",),
    )

    assert event.provenance.model_revision == "2026-01-01"
    assert event.provenance.schema_version == "bom-schema-v2"
