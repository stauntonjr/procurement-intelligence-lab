from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from procurement_intelligence_lab.bootstrap import build_bom_normalization_service
from procurement_intelligence_lab.domains.procurement.normalization import (
    BomNormalizationPolicy,
    CountUnit,
)
from procurement_intelligence_lab.platform.semantics.documents import MappedDocument
from procurement_intelligence_lab.platform.semantics.errors import DocumentStageError
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_stage_adapters import source


@pytest.mark.parametrize(
    "change", ["drop", "duplicate", "foreign_scope", "time", "provenance", "source_field"]
)
def test_service_rejects_broken_normalization_lineage(tmp_path: Path, change: str) -> None:
    service = build_bom_normalization_service(
        captured_at=AT,
        context=provenance().context,
        policy=BomNormalizationPolicy(CountUnit.EACH, "USD", CountUnit.EACH),
    )
    normalizer = service.normalizer

    class Broken:
        def normalize(self, document: MappedDocument, *, provenance: DecisionProvenance):
            result = normalizer.normalize(document, provenance=provenance)
            if change == "drop":
                return ()
            if change == "duplicate":
                return result + result[:1]
            first = result[0]
            if change == "foreign_scope":
                first = replace(first, scope=replace(first.scope, tenant_id="foreign"))
            elif change == "time":
                first = replace(first, effective_at=AT + timedelta(days=1))
            elif change == "provenance":
                first = replace(
                    first, provenance=replace(provenance, implementation_version="wrong")
                )
            else:
                first = replace(
                    first, source_field=replace(first.source_field, raw_value="different")
                )
            return (first, *result[1:])

    with pytest.raises(DocumentStageError):
        replace(service, normalizer=Broken()).run(
            source(workbook(tmp_path / "source.xlsx", HEADER + ROW))
        )
