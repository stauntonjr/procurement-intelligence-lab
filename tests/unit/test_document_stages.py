from dataclasses import replace
from pathlib import Path

import pytest

from procurement_intelligence_lab.bootstrap import build_bom_stage_service
from procurement_intelligence_lab.platform.semantics.artifacts import Artifact
from procurement_intelligence_lab.platform.semantics.documents import StructuredDocument
from procurement_intelligence_lab.platform.semantics.errors import DocumentStageError
from procurement_intelligence_lab.platform.semantics.provenance import DecisionProvenance
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_stage_adapters import source


def test_service_rejects_foreign_artifact_and_ignored_injected_provenance(tmp_path: Path) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    service = build_bom_stage_service(captured_at=AT, context=provenance().context)

    class ForeignStructure:
        def structure(
            self, artifact: Artifact, *, provenance: DecisionProvenance
        ) -> StructuredDocument:
            return StructuredDocument(
                replace(
                    artifact,
                    source=replace(
                        artifact.source, scope=replace(artifact.source.scope, tenant_id="other")
                    ),
                ),
                (),
                provenance,
            )

    with pytest.raises(DocumentStageError):
        replace(service, structure=ForeignStructure()).run(source(path))
    actual = service.structure

    class WrongProvenance:
        def structure(
            self, artifact: Artifact, *, provenance: DecisionProvenance
        ) -> StructuredDocument:
            return actual.structure(
                artifact, provenance=replace(provenance, implementation_version="different")
            )

    with pytest.raises(DocumentStageError):
        replace(service, structure=WrongProvenance()).run(source(path))


@pytest.mark.parametrize("count", [0, 2])
def test_single_document_service_does_not_choose_first_of_many_or_invent_empty_success(
    tmp_path: Path, count: int
) -> None:
    from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference

    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    service = build_bom_stage_service(captured_at=AT, context=provenance().context)
    actual = service.ingest

    class CaptureMultiplicity:
        def ingest(
            self, source: SourceReference, *, provenance: DecisionProvenance
        ) -> tuple[Artifact, ...]:
            return actual.ingest(source, provenance=provenance) * count

    with pytest.raises(DocumentStageError):
        replace(service, ingest=CaptureMultiplicity()).run(source(path))
