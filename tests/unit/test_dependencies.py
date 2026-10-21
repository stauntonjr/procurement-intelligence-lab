from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from procurement_intelligence_lab.platform.semantics.dependencies import (
    ArchivedClaimRef,
    ClaimDependency,
    DependencyManifest,
    DependencySnapshot,
)
from procurement_intelligence_lab.platform.semantics.errors import DependencyContractError
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
    ProvenanceContext,
    ProvenanceEdge,
    ProvenanceRelation,
    TransformationEvent,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope

AT = datetime(2026, 10, 20, tzinfo=UTC)
SCOPE = StateScope("synthetic", "dependency-contract", "lab", "1")


def claim(ref: str, *inputs: str):
    context = ProvenanceContext(
        "fixture-run",
        "declared-producer-fixture",
        "1",
        "fixture",
        "fixture-image",
        "fixture-config",
        "fixture-lock",
        ("snapshot",),
        AT,
    )
    return ClaimDependency(
        ref,
        TransformationEvent(
            "declared-fixture",
            DecisionProvenance(context, "fixture-producer", ComponentKind.DETERMINISTIC, "1"),
            tuple(ProvenanceEdge(ProvenanceRelation.USED_INPUT, x) for x in inputs),
            (ref,),
        ),
    )


def manifest(*claims: ClaimDependency):
    return DependencyManifest(
        SCOPE,
        "request",
        (ArchivedClaimRef("snapshot", "source"),),
        tuple(sorted(claims, key=lambda c: c.reference_id)),
    )


def test_diamond_impact_preserves_links_and_explicit_coverage():
    m = manifest(
        claim("a", "source"), claim("b", "source"), claim("c", "a", "b"), claim("z", "source")
    )
    result = m.impact("source", 2)
    assert result.affected == (("a", 1), ("b", 1), ("c", 2), ("z", 1))
    assert ("a", "c") in result.links and ("b", "c") in result.links
    assert result.frontier == ()
    assert result.traversal_complete
    assert result.coverage == "registered_graph_only"
    assert result.global_completeness == "not_evaluated"
    bounded = m.impact("source", 1)
    assert bounded.frontier == ("c",)
    assert not bounded.traversal_complete
    assert "c" not in dict(bounded.affected)


def test_empty_graph_is_explicit_unknown_global_coverage():
    result = manifest().impact("source", 1)
    assert result.affected == () and result.traversal_complete
    assert result.global_completeness == "not_evaluated"


def test_schema_links_do_not_propagate_and_shared_descendant_uses_minimum_depth():
    a = claim("a", "source")
    b = claim("b", "a", "source")
    schema = ProvenanceEdge(ProvenanceRelation.USED_SCHEMA, "source")
    b = replace(b, event=replace(b.event, input_edges=(*b.event.input_edges, schema)))
    result = manifest(a, b).impact("source", 1)
    assert result.affected == (("a", 1), ("b", 1))
    assert result.traversal_complete
    assert result.links == (("a", "b"), ("source", "a"), ("source", "b"))


@pytest.mark.parametrize(
    "claims",
    [
        (claim("a", "missing"),),
        (claim("a", "a"),),
        (claim("a", "b"), claim("b", "a")),
        (claim("source", "source"),),
        (claim("a", "source"), claim("a", "source")),
    ],
)
def test_invalid_graph_cannot_be_registered(claims: tuple[ClaimDependency, ...]):
    with pytest.raises(DependencyContractError):
        manifest(*claims)


@pytest.mark.parametrize("depth", [0, 33, -1, True, 1.5])
def test_depth_bounds_are_intrinsic(depth: Any):
    with pytest.raises(DependencyContractError):
        manifest().impact("source", depth)


def test_snapshot_digest_binds_all_metadata_and_rejects_future_execution():
    m = manifest(claim("a", "source"))
    snap = DependencySnapshot(m, "recorder", AT)
    c = m.claims[0]
    changed = replace(
        c,
        event=replace(
            c.event,
            provenance=replace(
                c.event.provenance,
                context=replace(c.event.provenance.context, parent_run_id="other"),
            ),
        ),
    )
    altered = DependencySnapshot(replace(m, claims=(changed,)), "recorder", AT)
    assert snap.snapshot_id == altered.snapshot_id
    assert snap.digest != altered.digest
    with pytest.raises(DependencyContractError):
        DependencySnapshot(m, "recorder", AT - timedelta(seconds=1))


@pytest.mark.parametrize("value", ["", "bad\ud800text", "x" * 501])
def test_bad_recording_identity_is_rejected_before_storage(value: str):
    with pytest.raises(DependencyContractError):
        DependencySnapshot(manifest(), value, AT)


def test_typed_receipts_and_roots_are_required():
    m = manifest(claim("a", "source"))
    c = m.claims[0]
    with pytest.raises(DependencyContractError):
        replace(m, roots=())
    with pytest.raises(DependencyContractError):
        replace(m, roots=("source",))
    with pytest.raises(DependencyContractError):
        replace(c, event="event")
    with pytest.raises(DependencyContractError):
        replace(c, reference_id="not-an-output")
    with pytest.raises(DependencyContractError):
        replace(
            m,
            claims=(
                replace(
                    c,
                    event=replace(
                        c.event,
                        provenance=replace(
                            c.event.provenance,
                            context=replace(
                                c.event.provenance.context, input_snapshot_ids=("foreign",)
                            ),
                        ),
                    ),
                ),
            ),
        )
    with pytest.raises(DependencyContractError):
        replace(
            c,
            event=replace(
                c.event, input_edges=(ProvenanceEdge(ProvenanceRelation.OVERRIDES, "source"),)
            ),
        )
    with pytest.raises(DependencyContractError):
        replace(
            c,
            event=replace(
                c.event,
                provenance=replace(
                    c.event.provenance,
                    context=replace(
                        c.event.provenance.context, environment=(("raw", "unsupported"),)
                    ),
                ),
            ),
        )


def test_duplicate_data_input_is_intrinsically_invalid():
    with pytest.raises(DependencyContractError):
        claim("a", "source", "source")


def test_conflicting_output_receipts_cannot_assign_two_producers():
    a = claim("a", "source")
    a = replace(a, event=replace(a.event, output_ids=("a", "b")))
    with pytest.raises(DependencyContractError):
        manifest(a, claim("b", "source"))
    a = replace(a, event=replace(a.event, output_ids=("a", "source")))
    with pytest.raises(DependencyContractError):
        manifest(a)


def test_shared_multi_output_receipt_is_retained_without_inventing_edges():
    a = claim("a", "source")
    event = replace(a.event, output_ids=("a", "b"))
    result = manifest(replace(a, event=event), ClaimDependency("b", event)).impact("source", 1)
    assert result.affected == (("a", 1), ("b", 1))


def test_equal_python_receipts_with_different_time_encoding_do_not_alias():
    from datetime import timezone

    a = claim("a", "source")
    event = replace(a.event, output_ids=("a", "b"))
    shifted = replace(
        event,
        provenance=replace(
            event.provenance,
            context=replace(
                event.provenance.context,
                started_at=event.provenance.context.started_at.astimezone(
                    timezone(timedelta(hours=1))
                ),
            ),
        ),
    )
    assert shifted == event and shifted.event_id == event.event_id
    with pytest.raises(DependencyContractError):
        manifest(ClaimDependency("a", event), ClaimDependency("b", shifted))


def test_graph_size_and_noncanonical_roots_fail_before_storage():
    many = tuple(claim(f"c{i:03d}", "source") for i in range(257))
    with pytest.raises(DependencyContractError):
        manifest(*many)
    with pytest.raises(DependencyContractError):
        replace(manifest(), roots=(ArchivedClaimRef("snapshot", "source"),) * 2)
    with pytest.raises(DependencyContractError):
        replace(manifest(), claims=list(many[:1]))
