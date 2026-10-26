"""Pin the admitted local profile without opening source or persistence."""

from datetime import datetime

from procurement_intelligence_lab.platform.execution.resolution_admission import (
    PreparedResolvedPrefix,
)
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    ArtifactArrival,
    PinnedResolvedPrefixDefinition,
    ResolvedJobDefinition,
)
from procurement_intelligence_lab.platform.processing.resolved_lifecycle import (
    submission_transition,
)

RECIPE = "procurement.bom-local-resolved-prefix@1"


def pin_resolved_prefix_job(
    prepared: PreparedResolvedPrefix,
    arrival: ArtifactArrival,
    idempotency_key: str,
    *,
    normalization_parameters: tuple[tuple[str, str], ...],
    now: datetime,
) -> ResolvedJobDefinition:
    job = ResolvedJobDefinition(
        arrival,
        idempotency_key,
        PinnedResolvedPrefixDefinition.from_prepared(
            prepared, recipe_id=RECIPE, normalization_parameters=normalization_parameters
        ),
    )
    submission_transition(job, now=now)
    return job
