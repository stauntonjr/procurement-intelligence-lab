"""Immutable execution and decision provenance contracts."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from procurement_intelligence_lab.domain.identity import stable_id


class ComponentKind(StrEnum):
    DETERMINISTIC = "deterministic"
    MODEL = "model"
    HUMAN = "human"


@dataclass(frozen=True)
class ProvenanceContext:
    """Effective execution manifest resolved at an application boundary."""

    run_id: str
    workflow_name: str
    workflow_version: str
    code_revision: str
    image_digest: str
    config_digest: str
    dependency_lock_digest: str | None
    input_snapshot_ids: tuple[str, ...]
    started_at: datetime
    environment: tuple[tuple[str, str], ...] = ()
    parent_run_id: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")

    @property
    def context_id(self) -> str:
        return stable_id(
            "run",
            self.run_id,
            self.workflow_name,
            self.workflow_version,
            self.code_revision,
            self.image_digest,
            self.config_digest,
            self.dependency_lock_digest,
            self.input_snapshot_ids,
        )


@dataclass(frozen=True)
class DecisionProvenance:
    """Component-level provenance attached to an auditable decision."""

    context: ProvenanceContext
    component_name: str
    component_kind: ComponentKind
    implementation_version: str
    policy_version: str | None = None
    model_provider: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None

    def __post_init__(self) -> None:
        if not self.component_name or not self.implementation_version:
            raise ValueError("component name and implementation version are required")
        if self.component_kind is ComponentKind.MODEL and not (
            self.model_provider and self.model_id and self.model_revision
        ):
            raise ValueError(
                "model decisions require provider, model ID, and model revision"
            )

    @property
    def provenance_id(self) -> str:
        return stable_id(
            "decision-provenance",
            self.context.context_id,
            self.component_name,
            self.component_kind.value,
            self.implementation_version,
            self.policy_version,
            self.model_provider,
            self.model_id,
            self.model_revision,
            self.prompt_version,
            self.schema_version,
        )


def local_provenance_context() -> ProvenanceContext:
    """Provide an explicit development context when no orchestrator is configured."""

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
