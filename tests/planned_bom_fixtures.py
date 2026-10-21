"""Real first-five executor metadata, with explicitly planning-only later advertisements."""

from dataclasses import replace

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationRegistry,
    StageSelection,
)
from tests.bom_stage_fixtures import provenance
from tests.planning_fixtures import planning_inputs


def planned_inputs():
    assert hasattr(bootstrap, "bom_execution_descriptors"), (
        "real executor descriptors are not implemented"
    )
    m = bootstrap.compile_procurement_manifest().canonical_json
    r, c = planning_inputs(m)
    real = bootstrap.bom_execution_descriptors()
    r = ImplementationRegistry("1.0", (*real, *r.implementations[5:]))
    c = replace(
        c,
        application_version=provenance().context.code_revision,
        selections=tuple(
            StageSelection(d.stage, d.implementation_id, d.config_schema_version) for d in real
        )
        + c.selections[5:],
    )
    return m, r, c
