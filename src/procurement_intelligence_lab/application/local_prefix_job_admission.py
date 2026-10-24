"""Pin the admitted local profile without opening source or persistence."""

from datetime import datetime

from procurement_intelligence_lab.platform.execution.admission import PreparedPrefix
from procurement_intelligence_lab.platform.processing.contracts import (
    ArtifactArrival,
    JobDefinition,
    PinnedPrefixDefinition,
)
from procurement_intelligence_lab.platform.processing.lifecycle import submission_transition

RECIPE = "procurement.bom-local-prefix@1"


def pin_local_prefix_job(
    prepared: PreparedPrefix,
    arrival: ArtifactArrival,
    idempotency_key: str,
    *,
    normalization_parameters: tuple[tuple[str, str], ...],
    now: datetime,
) -> JobDefinition:
    job = JobDefinition(
        arrival,
        idempotency_key,
        PinnedPrefixDefinition.from_prepared(
            prepared, recipe_id=RECIPE, normalization_parameters=normalization_parameters
        ),
    )
    submission_transition(job, now=now)
    return job
