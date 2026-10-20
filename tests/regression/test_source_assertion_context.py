from dataclasses import replace
from decimal import Decimal

import pytest

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.platform.semantics.assertions import SourceAssertion
from procurement_intelligence_lab.platform.semantics.errors import SemanticContractError
from procurement_intelligence_lab.platform.semantics.evidence import EvidenceRef
from procurement_intelligence_lab.platform.semantics.identity import stable_id

pytestmark = pytest.mark.regression


def test_null_without_context_is_not_a_source_claim():
    with pytest.raises(SemanticContractError, match="null.*unresolved context"):
        SourceAssertion(
            "row-1",
            AssertionPredicate.HAS_QUANTITY,
            None,
            EvidenceRef("artifact", "hash", "BOM", 2, ("C",)),
        )


def test_legacy_assertion_identity_is_unchanged():
    claim = SourceAssertion(
        "GPU",
        AssertionPredicate.HAS_QUANTITY,
        Decimal(0),
        EvidenceRef("artifact", "hash", "BOM", 2, ("C",)),
    )
    assert claim.assertion_id == stable_id(
        "assertion", "GPU", "has_quantity", "0", claim.evidence.evidence_id, "document", None
    )
    assert replace(claim).assertion_id == claim.assertion_id
