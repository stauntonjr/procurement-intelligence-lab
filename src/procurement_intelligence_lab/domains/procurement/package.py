"""Side-effect-free procurement requirements, not implementation availability."""

from procurement_intelligence_lab.domains.procurement.source_schema import BOM_TABLE_SCHEMA
from procurement_intelligence_lab.platform.domain_packages.package import (
    DomainPackage,
    SourceProfile,
    StageBinding,
    StageId,
    StageMode,
)

BOM_PROFILE_ID = "bom-table"

PROCUREMENT_PACKAGE = DomainPackage(
    schema_version="1.0",
    domain_id="procurement",
    domain_version="0.1.0",
    source_profiles=(
        SourceProfile(
            profile_id=BOM_PROFILE_ID,
            profile_version="1.0.0",
            bindings=(
                StageBinding(
                    StageId.INGEST,
                    StageMode.EXECUTE,
                    eval_suite_ref="procurement.ingest/bom-capture@1",
                ),
                StageBinding(
                    StageId.STRUCTURE,
                    StageMode.EXECUTE,
                    requirements=("tables",),
                    eval_suite_ref="procurement.structure/bom-locations@1",
                ),
                StageBinding(
                    StageId.MAP,
                    StageMode.EXECUTE,
                    domain_config_ref=BOM_TABLE_SCHEMA.reference_id,
                    eval_suite_ref="procurement.mapping/bom-table@1",
                ),
                StageBinding(
                    StageId.NORMALIZE,
                    StageMode.EXECUTE,
                    policy_refs=("procurement.normalize/bom-decimal@1",),
                    eval_suite_ref="procurement.normalize/bom-values@1",
                ),
                StageBinding(
                    StageId.ASSERT,
                    StageMode.EXECUTE,
                    policy_refs=("procurement.assert/bom-claims@1",),
                    eval_suite_ref="procurement.assert/bom-evidence@1",
                ),
                StageBinding(
                    StageId.RESOLVE,
                    StageMode.EXECUTE,
                    requirements=("authoritative_ids", "abstention"),
                    policy_refs=("procurement.resolve/normalized-exact@1",),
                    eval_suite_ref="procurement.resolve/bom-identifiers@1",
                ),
                StageBinding(
                    StageId.RECONCILE,
                    StageMode.EXECUTE,
                    policy_refs=("procurement.reconcile/explicit-source-precedence@1",),
                    eval_suite_ref="procurement.reconcile/bom-conflicts@1",
                ),
                StageBinding(
                    StageId.DERIVE,
                    StageMode.EXECUTE,
                    policy_refs=("procurement.derive/bom-queries@1",),
                    eval_suite_ref="procurement.derive/bom-queries@1",
                ),
                StageBinding(
                    StageId.DETECT,
                    StageMode.EXECUTE,
                    requirements=("abstention",),
                    policy_refs=("procurement.detect/qualified-assessment@1",),
                    eval_suite_ref="procurement.detect/qualified-assessment@1",
                ),
                StageBinding(StageId.PREDICT, StageMode.EMPTY, neutral_semantics="no_predictions"),
                StageBinding(
                    StageId.DECIDE,
                    StageMode.EMPTY,
                    neutral_semantics="no_decisions_or_recommendations",
                ),
                StageBinding(StageId.ACT, StageMode.EMPTY, neutral_semantics="no_action_attempted"),
            ),
        ),
    ),
)
