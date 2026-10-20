import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.memory_ledger import InMemoryAssertionLedger
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    CountUnit,
)
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_stage_adapters import source

pytestmark = pytest.mark.contract
POLICY = BomNormalizationPolicy(CountUnit.EACH, "USD", CountUnit.EACH)


def service():
    assert hasattr(bootstrap, "build_bom_assertion_service")
    return bootstrap.build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    )


def test_conflicting_rows_missing_sku_unmapped_and_zero_keep_all_claims(tmp_path: Path):
    rows = HEADER + ROW.replace("</row>", '<c r="E7"><v>uninterpreted</v></c></row>')
    rows += ROW.replace("7", "8").replace("<v>0.5</v>", "<v>-1.25</v>")
    rows += '<row r="9"><c r="C9"><v>0</v></c></row>'
    result = service().run(source(workbook(tmp_path / "source.xlsx", rows)))
    assert len(result.assertions) == 13
    assert len(result.mentions) == 2
    assert [x.text for x in result.mentions] == ["GPU-A", "GPU-A"]
    assert len({x.mention_id for x in result.mentions}) == 2
    assert len({x.subject_key for x in result.assertions}) == 3
    assert [x.value for x in result.assertions if x.predicate.value == "has_quantity"] == [
        Decimal("0.5"),
        Decimal("-1.25"),
        Decimal(0),
    ]
    for claim, observation in zip(result.assertions, result.normalized.observations, strict=True):
        assert claim.context is not None
        assert claim.context.observation is observation
        assert claim.evidence == observation.source_field.evidence
        assert claim.context.confidence_diagnostic == "not estimated"
        assert claim.transformation_event_id == result.normalized.transformation.event_id
        assert claim.context.origin.artifact == result.normalized.stages.artifact
    nulls = [x for x in result.assertions if x.value is None]
    assert len(nulls) == 6
    assert all(
        x.context is not None and x.context.observation.status.value == "unresolved" for x in nulls
    )
    extra = next(x for x in nulls if x.predicate.value == "unmapped_field")
    assert extra.context is not None
    assert extra.context.observation.source_field.raw_value == "uninterpreted"
    ledger = InMemoryAssertionLedger()
    entries = [ledger.append(x, observed_at=AT) for x in result.assertions]
    assert [x.assertion for x in entries] == list(result.assertions)
    payload = json.loads(json.dumps(result.as_dict()))
    assert payload["executed_stages"][-1] == "ASSERT"
    assert len(payload["assertion_batch"]["claims"]) == 13
    assert any(x["mention_diagnostic"] for x in payload["assertion_batch"]["claims"])
    assert result.transformation.parent_event_ids == (result.normalized.transformation.event_id,)
    assert result.transformation.output_ids == (
        result.batch_id,
        *(x.assertion_id for x in result.assertions),
        *(x.mention_id for x in result.mentions),
    )


def test_empty_has_real_receipt_and_replay_is_identical(tmp_path: Path):
    s = service()
    ref = source(workbook(tmp_path / "empty.xlsx", HEADER))
    r = s.run(ref)
    assert r.assertions == r.mentions == ()
    assert r.transformation.output_ids == (r.batch_id,)
    assert s.run(ref).as_dict() == r.as_dict()


def test_context_rejects_forged_lineage_and_changes_identity(tmp_path: Path):
    s = service()
    ref = source(workbook(tmp_path / "source.xlsx", HEADER + ROW))
    r = s.run(ref)
    c = r.assertions[0]
    context = c.context
    assert context is not None
    invalid = (
        {"value": "different"},
        {"subject_key": "other"},
        {"source_system": "other"},
        {"transformation_event_id": "other"},
        {"evidence": replace(c.evidence, content_hash="other")},
    )
    for changes in invalid:
        with pytest.raises(SemanticContractError):
            replace(c, **changes)
    for changes in (
        {"confidence_diagnostic": ""},
        {"observation": replace(context.observation, scope=replace(ref.scope, tenant_id="other"))},
        {"observation": replace(context.observation, effective_at=AT + timedelta(days=1))},
        {
            "observation": replace(
                context.observation,
                provenance=replace(provenance(), implementation_version="other"),
            )
        },
    ):
        with pytest.raises(SemanticContractError):
            replace(context, **changes)
    for changes in (
        {"recorded_at": AT.replace(tzinfo=None)},
        {"recorded_at": AT - timedelta(seconds=1)},
        {"normalization_batch_id": "other"},
        {"normalization_event": replace(context.origin.normalization_event, event_type="map")},
    ):
        with pytest.raises(SemanticContractError):
            replace(context.origin, **changes)
    later = replace(context.origin, recorded_at=AT + timedelta(seconds=1))
    assert replace(c, context=replace(context, origin=later)).assertion_id != c.assertion_id
    assert (
        replace(c, context=replace(context, confidence_diagnostic="no estimate")).assertion_id
        != c.assertion_id
    )
    changed = replace(
        s, assertion_provenance=replace(s.assertion_provenance, implementation_version="next")
    ).run(ref)
    assert changed.batch_id != r.batch_id
    assert changed.assertions[0].assertion_id != c.assertion_id
    assert changed.normalized.as_dict() == r.normalized.as_dict()


def test_strategy_rejects_drop_duplicate_foreign_and_wrong_bom_profile(tmp_path: Path):
    from procurement_intelligence_lab.domains.procurement.observation_assertions import BomAssert

    r = service().run(source(workbook(tmp_path / "source.xlsx", HEADER + ROW)))
    obs = r.normalized.observations
    assert r.assertions[0].context is not None
    origin = r.assertions[0].context.origin
    strategy = BomAssert(origin)
    for observations in (obs[1:], obs + obs[:1], (replace(obs[0], predicate="foreign"), *obs[1:])):
        with pytest.raises(SemanticContractError):
            strategy.assert_observations(observations, provenance=r.provenance)
    # Valid event membership does not authorize a foreign BOM predicate or unit.
    for changed in (replace(obs[2], unit="dozen"), replace(obs[0], predicate="foreign")):
        batch = tuple(changed if x is obs[2 if changed.unit == "dozen" else 0] else x for x in obs)
        event = replace(
            origin.normalization_event,
            output_ids=(origin.normalization_batch_id, *(x.observation_id for x in batch)),
        )
        with pytest.raises(SemanticContractError):
            BomAssert(replace(origin, normalization_event=event)).assert_observations(
                batch, provenance=r.provenance
            )


@pytest.mark.parametrize(
    "change",
    [
        "drop",
        "duplicate",
        "context",
        "provenance",
        "foreign_mention",
        "duplicate_mention",
        "fabricated_mention",
        "cross_row",
        "drop_mentions",
        "description_mention",
        "partial_row",
        "entity_type",
        "duplicate_attached",
        "wrong_predicate",
    ],
)
def test_application_rejects_invalid_assertion_producer(tmp_path: Path, change: str) -> None:
    from procurement_intelligence_lab.domains.procurement.observation_assertions import BomAssert
    from procurement_intelligence_lab.platform.semantics.assertions import AssertionOrigin
    from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
    from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance

    s = service()

    class Broken:
        def __init__(self, origin: AssertionOrigin):
            self.origin = origin

        def assert_observations(
            self, observations: tuple[NormalizedObservation, ...], *, provenance: DecisionProvenance
        ):
            claims, mentions = BomAssert(self.origin).assert_observations(
                observations, provenance=provenance
            )
            if change == "entity_type":
                return claims, (replace(mentions[0], entity_type="unrelated"), *mentions[1:])
            if change == "duplicate_attached":
                return claims, (
                    replace(mentions[0], assertions=mentions[0].assertions + claims[:1]),
                    *mentions[1:],
                )
            if change == "drop_mentions":
                return claims, ()
            if change == "description_mention":
                return claims, (replace(mentions[0], text="source description"), *mentions[1:])
            if change == "partial_row":
                return claims, (replace(mentions[0], assertions=claims[:1]), *mentions[1:])
            if change == "wrong_predicate":
                from procurement_intelligence_lab.domains.procurement.assertions import (
                    AssertionPredicate,
                )

                changed = replace(claims[0], predicate=AssertionPredicate.HAS_QUANTITY)
                return (changed, *claims[1:]), (
                    replace(mentions[0], assertions=(changed, *mentions[0].assertions[1:])),
                    *mentions[1:],
                )
            if change == "drop":
                return claims[1:], mentions
            if change == "duplicate":
                return claims + claims[:1], mentions
            if change == "context":
                return (replace(claims[0], context=None), *claims[1:]), mentions
            if change == "provenance":
                assert claims[0].context is not None
                claim = replace(
                    claims[0],
                    context=replace(
                        claims[0].context,
                        provenance=replace(provenance, implementation_version="wrong"),
                    ),
                )
                return (claim, *claims[1:]), mentions
            if change == "foreign_mention":
                return claims, (
                    replace(mentions[0], scope=replace(mentions[0].scope, tenant_id="foreign")),
                )
            if change == "duplicate_mention":
                return claims, mentions + mentions[:1]
            if change == "fabricated_mention":
                return claims, (replace(mentions[0], text="invented"),)
            return claims, (replace(mentions[0], assertions=claims),)

    ref = source(
        workbook(
            tmp_path / "source.xlsx",
            HEADER
            + ROW.replace("</row>", '<c r="B7"><v>source description</v></c></row>')
            + ROW.replace("7", "8"),
        )
    )
    with pytest.raises(SemanticContractError):
        replace(s, assertion_factory=Broken).run(ref)


def test_scope_source_version_and_time_are_retained_without_authority_selection(
    tmp_path: Path,
) -> None:
    s = service()
    ref = source(workbook(tmp_path / "source.xlsx", HEADER + ROW))
    variants = (
        ref,
        replace(ref, source_version="r2"),
        replace(ref, source_version=None),
        replace(ref, scope=replace(ref.scope, project_id="other")),
        replace(ref, observed_at=AT - timedelta(days=7)),
    )
    results = [s.run(x) for x in variants]
    assert len({r.assertions[0].assertion_id for r in results}) == len(variants)
    assert all(
        r.assertions[0].context is not None and r.assertions[0].context.origin.artifact.source == x
        for r, x in zip(results, variants, strict=True)
    )
    assert results[2].as_dict()["assertion_batch"]
    ledger = InMemoryAssertionLedger()
    for r in results[:2]:
        for claim in r.assertions:
            ledger.append(claim, observed_at=AT)
    assert len(ledger.entries()) == 8
