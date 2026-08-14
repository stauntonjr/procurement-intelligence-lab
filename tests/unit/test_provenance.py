from datetime import UTC, datetime

import pytest

from procurement_intelligence_lab.domain.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
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
