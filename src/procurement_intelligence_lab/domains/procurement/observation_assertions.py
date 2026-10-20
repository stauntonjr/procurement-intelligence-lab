"""BOM claims retain normalized evidence; entity resolution remains a later stage."""

import re
from dataclasses import dataclass
from decimal import Decimal

from procurement_intelligence_lab.domains.procurement.assertions import AssertionPredicate
from procurement_intelligence_lab.platform.semantics.assertions import (
    AssertionOrigin,
    SourceAssertion,
    SourceAssertionContext,
)
from procurement_intelligence_lab.platform.semantics.errors import SourceAssertionError
from procurement_intelligence_lab.platform.semantics.observations import NormalizedObservation
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from procurement_intelligence_lab.platform.semantics.resolution import EntityMention

_PREDICATES = {
    "sku": AssertionPredicate.HAS_SKU,
    "description": AssertionPredicate.HAS_DESCRIPTION,
    "quantity": AssertionPredicate.HAS_QUANTITY,
    "unit_price": AssertionPredicate.HAS_UNIT_PRICE,
}


@dataclass(frozen=True)
class BomAssert:
    origin: AssertionOrigin

    def assert_observations(
        self, observations: tuple[NormalizedObservation, ...], *, provenance: DecisionProvenance
    ) -> tuple[tuple[SourceAssertion, ...], tuple[EntityMention, ...]]:
        if self.origin.normalization_event.output_ids != (
            self.origin.normalization_batch_id,
            *(x.observation_id for x in observations),
        ) or len({x.observation_id for x in observations}) != len(observations):
            raise SourceAssertionError("assertion input must retain the exact normalization batch")
        claims: list[SourceAssertion] = []
        rows: dict[str, list[SourceAssertion]] = {}
        for observation in observations:
            name = observation.source_field.field_name
            unmapped = re.fullmatch(r"unmapped\.[A-Z]{1,3}", name) is not None
            if (
                name not in _PREDICATES and not unmapped
            ) or observation.predicate != f"procurement.bom.{name}":
                raise SourceAssertionError("assertion requires the BOM observation profile")
            value, unit = observation.value, observation.unit
            if name in ("quantity", "unit_price"):
                if value is not None and type(value) is not Decimal:
                    raise SourceAssertionError(
                        "BOM numeric claims require exact Decimal observations"
                    )
                if (name == "quantity" and unit != "each") or (
                    name == "unit_price"
                    and (unit is None or re.fullmatch(r"[A-Z]{3}/(each|dozen)", unit) is None)
                ):
                    raise SourceAssertionError("BOM numeric claim unit is missing or unsupported")
            elif (
                unit is not None
                or (unmapped and value is not None)
                or (value is not None and not isinstance(value, str))
            ):
                raise SourceAssertionError("BOM text/unmapped claim value or unit is invalid")
            claim = SourceAssertion(
                observation.subject_hint,
                _PREDICATES.get(name, AssertionPredicate.UNMAPPED_FIELD),
                value,
                observation.source_field.evidence,
                self.origin.artifact.source.source_system,
                self.origin.normalization_event.event_id,
                SourceAssertionContext(observation, self.origin, provenance, "not estimated"),
            )
            claims.append(claim)
            rows.setdefault(claim.subject_key, []).append(claim)
        mentions: list[EntityMention] = []
        for row in rows.values():
            sku = [x for x in row if x.predicate.value == AssertionPredicate.HAS_SKU.value]
            if len(sku) != 1:
                raise SourceAssertionError("BOM assertion rows require exactly one SKU field")
            text = sku[0].value
            if isinstance(text, str) and text.strip():
                mentions.append(
                    EntityMention(
                        text,
                        "procurement_item",
                        tuple(row),
                        self.origin.artifact.source.scope,
                        self.origin.artifact.source.observed_at,
                    )
                )
        return tuple(claims), tuple(mentions)
