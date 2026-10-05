"""Public application contract backed by independent source arithmetic."""

import json
from datetime import datetime
from pathlib import Path

from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext

CONTEXT = RequestContext(
    "demo",
    "synthetic-tenant",
    "atlas",
    "lab",
    frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE}),
    "test",
)


def test_independent_gold() -> None:
    from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
    from procurement_intelligence_lab.application.corpus_investigation import (
        CorpusInvestigationService,
        InvestigationRequest,
    )

    gold = json.loads(
        (Path(__file__).resolve().parents[2] / "evals/procurement_corpus/v1/gold.json").read_text()
    )
    service = CorpusInvestigationService(SyntheticCorpusReader())
    for case in gold["cases"]:
        result = service.investigate(
            InvestigationRequest(case["item"], datetime.fromisoformat(case["as_of"])),
            context=CONTEXT,
        )
        assert result.assessment.status.value == case["status"], case["id"]
        assert (result.assessment.reason.value if result.assessment.reason else None) == case[
            "reason"
        ], case["id"]
        assert (
            str(result.governed.expected.required_quantity) if result.governed.expected else None
        ) == case["required_quantity"], case["id"]
        assert result.evidence
        for ref in result.evidence:
            assert service.reader.source(ref, context=CONTEXT).evidence == ref


def test_order_identity_unit_and_scope_boundaries() -> None:
    from dataclasses import dataclass, replace

    import pytest

    from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
    from procurement_intelligence_lab.application.corpus_investigation import (
        CorpusInvestigationService,
        InvestigationRequest,
    )
    from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
    from procurement_intelligence_lab.platform.semantics.scope import ScopeAuthorizationError
    from procurement_intelligence_lab.ports.corpus import (
        CorpusInventory,
        CorpusSourceRecord,
        CorpusSourceRow,
    )

    reader = SyntheticCorpusReader()
    original = reader.inventory(context=CONTEXT)
    facts = tuple(f for f in original.facts if f.canonical_key == "GPU-A")
    orders = tuple(f for f in facts if f.role == "approved_purchase_order_line")
    others = tuple(f for f in facts if f.role != "approved_purchase_order_line")

    @dataclass(frozen=True)
    class ModifiedReader:
        inventory_value: CorpusInventory

        def inventory(self, *, context: RequestContext) -> CorpusInventory:
            return self.inventory_value

        def source(
            self, evidence: EvidenceRef, *, context: RequestContext
        ) -> CorpusSourceRow | CorpusSourceRecord:
            return reader.source(evidence, context=context)

    request = InvestigationRequest("GPU-A", datetime.fromisoformat("2026-10-01T00:00:00+00:00"))
    # Exact repeated assertion does not inflate 3 + 3 into 9.
    result = CorpusInvestigationService(
        ModifiedReader(replace(original, facts=facts + (orders[0],)))
    ).investigate(request, context=CONTEXT)
    assert str(result.ordered_quantity) == "6"
    conflict = others + (orders[0], replace(orders[1], line_id=orders[0].line_id))
    result = CorpusInvestigationService(
        ModifiedReader(replace(original, facts=conflict))
    ).investigate(request, context=CONTEXT)
    assert result.assessment.reason and result.assessment.reason.value == "conflicting_input"
    assert result.ordered_quantity is None
    incompatible = others + (orders[0], replace(orders[1], unit="ea"))
    result = CorpusInvestigationService(
        ModifiedReader(replace(original, facts=incompatible))
    ).investigate(request, context=CONTEXT)
    assert result.assessment.reason and result.assessment.reason.value == "incompatible_unit"
    foreign = others + (replace(orders[0], scope=replace(orders[0].scope, project_id="foreign")),)
    with pytest.raises(ScopeAuthorizationError):
        CorpusInvestigationService(ModifiedReader(replace(original, facts=foreign))).investigate(
            request, context=CONTEXT
        )


def test_cross_item_line_and_assertion_ownership_checked_before_filtering() -> None:
    from dataclasses import replace
    from unittest.mock import Mock

    import pytest

    from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
    from procurement_intelligence_lab.application.corpus_investigation import (
        CorpusInvestigationService,
        InvestigationRequest,
    )
    from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError

    inventory = SyntheticCorpusReader().inventory(context=CONTEXT)
    order = next(
        f
        for f in inventory.facts
        if f.canonical_key == "GPU-A" and f.role == "approved_purchase_order_line"
    )
    for field in ("line_id", "assertion_id"):
        foreign = replace(
            order, canonical_key="OTHER", line_id="other-line", assertion_id="other-assertion"
        )
        foreign = replace(foreign, **{field: getattr(order, field)})
        reader = Mock()
        reader.inventory.return_value = replace(inventory, facts=inventory.facts + (foreign,))
        with pytest.raises(CorpusAdmissionError, match="identity.*item"):
            CorpusInvestigationService(reader).investigate(
                InvestigationRequest("GPU-A", datetime.fromisoformat("2026-10-01T00:00:00Z")),
                context=CONTEXT,
            )


def test_distractor_permutation_does_not_change_assessment() -> None:
    from dataclasses import replace
    from unittest.mock import Mock

    from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
    from procurement_intelligence_lab.application.corpus_investigation import (
        CorpusInvestigationService,
        InvestigationRequest,
    )

    inventory = SyntheticCorpusReader().inventory(context=CONTEXT)
    reader = Mock()
    reader.inventory.return_value = inventory
    service = CorpusInvestigationService(reader)
    request = InvestigationRequest("GPU-A", datetime.fromisoformat("2026-10-01T00:00:00+00:00"))
    original = service.investigate(request, context=CONTEXT)
    reader.inventory.return_value = replace(inventory, facts=tuple(reversed(inventory.facts)))
    permuted = service.investigate(request, context=CONTEXT)
    assert permuted.assessment.status == original.assessment.status
    assert permuted.assessment.reason == original.assessment.reason
    assert permuted.assessment.assessment_id == original.assessment.assessment_id
    assert set(permuted.evidence) == set(original.evidence)
    assert permuted.ordered_quantity == original.ordered_quantity
    assert permuted.governed.expected == original.governed.expected
