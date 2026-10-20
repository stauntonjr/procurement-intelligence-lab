from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from procurement_intelligence_lab.adapters.local_artifacts import (
    LocalFileIngest,
    MemoryArtifactContent,
)
from procurement_intelligence_lab.adapters.xlsx_structure import XlsxStructure
from procurement_intelligence_lab.domains.procurement.mapping import BomTableMap
from procurement_intelligence_lab.platform.semantics.artifacts import SourceReference
from procurement_intelligence_lab.platform.semantics.epistemics import EpistemicStatus
from procurement_intelligence_lab.platform.semantics.errors import (
    ArtifactContentError,
    ArtifactSourceError,
    DocumentStructureError,
    SchemaMappingError,
    SourceReferenceError,
    TemporalContractError,
)
from procurement_intelligence_lab.platform.semantics.strategies import (
    IngestStrategy,
    MapStrategy,
    StructureStrategy,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, SCOPE, provenance, workbook

pytestmark = pytest.mark.contract


def adapters():
    store = MemoryArtifactContent()
    ingest: IngestStrategy = LocalFileIngest(store, AT)
    structure: StructureStrategy = XlsxStructure(store, "BOM")
    mapper: MapStrategy = BomTableMap()
    return store, ingest, structure, mapper


def source(path: Path) -> SourceReference:
    return SourceReference("local-file", path.as_uri(), SCOPE, AT, "fixture-v1")


def test_capture_is_snapshot_not_reopened_source_and_mapping_keeps_raw_values(
    tmp_path: Path,
) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    original = path.read_bytes()
    store, ingest, structure, mapper = adapters()
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    assert artifact.content_hash == sha256(original).hexdigest()
    assert store.get(artifact.content_hash) == original
    path.write_bytes(b"a different source")
    path.unlink()
    document = structure.structure(artifact, provenance=provenance())
    mapped = mapper.map_document(document, provenance=provenance())
    fields = {f.field_name: f for f in mapped.fields}
    assert fields["quantity"].raw_value == "0.5"
    assert fields["unit_price"].raw_value == "100.50"
    assert fields["description"].raw_value is None
    assert fields["description"].status is EpistemicStatus.UNRESOLVED
    assert fields["description"].diagnostic == "missing column B"
    assert fields["quantity"].evidence.row == 7
    assert fields["quantity"].evidence.cells == ("C",)
    assert fields["quantity"].evidence.artifact_id == artifact.artifact_id
    assert mapped.source_document is document


def test_empty_and_header_only_are_distinct_from_unreadable(tmp_path: Path) -> None:
    _, ingest, structure, mapper = adapters()
    path = workbook(tmp_path / "empty.xlsx", "")
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    document = structure.structure(artifact, provenance=provenance())
    assert document.elements == ()
    with pytest.raises(SchemaMappingError):
        mapper.map_document(document, provenance=provenance())
    workbook(path, HEADER)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    document = structure.structure(artifact, provenance=provenance())
    assert mapper.map_document(document, provenance=provenance()).fields == ()
    with pytest.raises(ArtifactSourceError):
        ingest.ingest(source(tmp_path / "absent.xlsx"), provenance=provenance())


@pytest.mark.parametrize("raw", [b"", b"not a zip archive"])
def test_invalid_captured_workbook_is_typed_not_empty(tmp_path: Path, raw: bytes) -> None:
    _, ingest, structure, _ = adapters()
    path = tmp_path / "bad.xlsx"
    path.write_bytes(raw)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    assert artifact.byte_length == len(raw)
    with pytest.raises(DocumentStructureError):
        structure.structure(artifact, provenance=provenance())


def test_missing_or_tampered_capture_is_never_repaired_by_source_reread(tmp_path: Path) -> None:
    _, ingest, _, _ = adapters()
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    empty = MemoryArtifactContent()
    with pytest.raises(ArtifactContentError):
        XlsxStructure(empty, "BOM").structure(artifact, provenance=provenance())

    class WrongContent:
        def put(self, content: bytes) -> str:
            return sha256(content).hexdigest()

        def get(self, content_hash: str) -> bytes:
            return b"changed"

    with pytest.raises(ArtifactContentError):
        XlsxStructure(WrongContent(), "BOM").structure(artifact, provenance=provenance())
    assert path.is_file()


@pytest.mark.parametrize(
    "scheme",
    [
        "https://example.org/source.xlsx",
        "file://remote/source.xlsx",
        "relative.xlsx",
        "file:///tmp/invalid%00.xlsx",
    ],
)
def test_unsupported_source_uris_fail_before_io(scheme: str) -> None:
    _, ingest, _, _ = adapters()
    with pytest.raises(SourceReferenceError):
        ingest.ingest(SourceReference("other", scheme, SCOPE, AT), provenance=provenance())


def test_capture_time_and_scope_are_explicit_identity_inputs(tmp_path: Path) -> None:
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    store, ingest, _, _ = adapters()
    original = source(path)
    (first,) = ingest.ingest(original, provenance=provenance())
    (again,) = ingest.ingest(original, provenance=provenance())
    assert first == again
    (other,) = ingest.ingest(
        replace(original, scope=replace(SCOPE, tenant_id="other")), provenance=provenance()
    )
    assert first.artifact_id != other.artifact_id
    (later,) = LocalFileIngest(store, AT + timedelta(seconds=1)).ingest(
        original, provenance=provenance()
    )
    assert first.artifact_id != later.artifact_id
    with pytest.raises(TemporalContractError):
        ingest.ingest(
            replace(original, observed_at=AT + timedelta(seconds=1)), provenance=provenance()
        )


@pytest.mark.parametrize(
    "rows",
    [
        HEADER + '<row r="7"><c r="A7"><v>x</v></c><c r="A7"><v>y</v></c></row>',
        HEADER + '<row r="7"><c r="A8"><v>x</v></c></row>',
        HEADER + ROW + ROW,
        HEADER + '<row r="0"><c r="A0"><v>x</v></c></row>',
        HEADER + '<row r="7"><c r="A7"><f>1+1</f><v>2</v></c></row>',
    ],
)
def test_conflicting_coordinates_and_formula_are_typed_failures(tmp_path: Path, rows: str) -> None:
    _, ingest, structure, _ = adapters()
    path = workbook(tmp_path / "source.xlsx", rows)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    with pytest.raises(DocumentStructureError):
        structure.structure(artifact, provenance=provenance())


def test_missing_sku_and_duplicate_sku_are_retained_with_unmapped_cells(tmp_path: Path) -> None:
    rows = (
        HEADER
        + ROW
        + '<row r="8"><c r="A8"><v>GPU-A</v></c><c r="C8"><v>-1</v></c><c r="E8"><v>raw extra</v></c></row>'
        + '<row r="9"><c r="C9"><v>0</v></c></row>'
    )
    _, ingest, structure, mapper = adapters()
    path = workbook(tmp_path / "source.xlsx", rows)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    mapped = mapper.map_document(
        structure.structure(artifact, provenance=provenance()), provenance=provenance()
    )
    assert len(mapped.fields) == 13
    by_key = {x.field_key: x for x in mapped.fields}
    assert by_key["BOM!C8"].raw_value == "-1"
    assert by_key["BOM!C9"].raw_value == "0"
    assert by_key["BOM!A9"].raw_value is None
    assert by_key["BOM!E8"].field_name == "unmapped.E"
    assert by_key["BOM!E8"].raw_value == "raw extra"
    assert by_key["BOM!E8"].diagnostic


@pytest.mark.parametrize(
    "header", [HEADER.replace("Quantity", "Description"), HEADER.replace("SKU", "Unknown")]
)
def test_mapping_rejects_invalid_headers(tmp_path: Path, header: str) -> None:
    _, ingest, structure, mapper = adapters()
    path = workbook(tmp_path / "source.xlsx", header + ROW)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    with pytest.raises(SchemaMappingError):
        mapper.map_document(
            structure.structure(artifact, provenance=provenance()), provenance=provenance()
        )


def test_merged_cells_and_unsupported_media_fail_explicitly(tmp_path: Path) -> None:
    _, ingest, structure, _ = adapters()
    path = workbook(
        tmp_path / "source.xlsx",
        HEADER + ROW,
        extra='<mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>',
    )
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    with pytest.raises(DocumentStructureError):
        structure.structure(artifact, provenance=provenance())
    with pytest.raises(DocumentStructureError):
        structure.structure(replace(artifact, media_type="text/plain"), provenance=provenance())


def test_invalid_numeric_text_is_not_normalized_or_treated_as_missing(tmp_path: Path) -> None:
    _, ingest, structure, mapper = adapters()
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW.replace("0.5", "not-a-number"))
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    mapped = mapper.map_document(
        structure.structure(artifact, provenance=provenance()), provenance=provenance()
    )
    quantity = next(f for f in mapped.fields if f.field_name == "quantity")
    assert quantity.raw_value == "not-a-number"
    assert quantity.status is EpistemicStatus.OBSERVED


@pytest.mark.parametrize(
    "rows",
    [
        HEADER + '<row r="1048577"><c r="A1048577"><v>x</v></c></row>',
        HEADER + '<row r="7"><c r="XFE7"><v>x</v></c></row>',
    ],
)
def test_xlsx_grid_boundary_is_rejected_before_dense_row_expansion(
    tmp_path: Path, rows: str
) -> None:
    _, ingest, structure, _ = adapters()
    path = workbook(tmp_path / "source.xlsx", rows)
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    with pytest.raises(DocumentStructureError):
        structure.structure(artifact, provenance=provenance())


def test_negative_shared_string_index_is_not_python_negative_indexing(tmp_path: Path) -> None:
    from zipfile import ZipFile

    path = workbook(
        tmp_path / "source.xlsx", HEADER + '<row r="7"><c r="A7" t="s"><v>-1</v></c></row>'
    )
    with ZipFile(path, "a") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>wrong last string</t></si></sst>',
        )
    _, ingest, structure, _ = adapters()
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    with pytest.raises(DocumentStructureError):
        structure.structure(artifact, provenance=provenance())


def test_last_valid_xlsx_grid_coordinate_is_supported(tmp_path: Path) -> None:
    _, ingest, structure, _ = adapters()
    path = workbook(
        tmp_path / "source.xlsx",
        HEADER + '<row r="1048576"><c r="XFD1048576"><v>boundary</v></c></row>',
    )
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    last = structure.structure(artifact, provenance=provenance()).elements[-1]
    assert (
        last.evidence.row == 1048576 and last.evidence.cells == ("XFD",) and last.text == "boundary"
    )


def test_duplicate_zip_members_are_not_selected_by_archive_order(tmp_path: Path) -> None:
    from zipfile import ZipFile

    path = workbook(tmp_path / "source.xlsx", HEADER + ROW)
    with ZipFile(path, "a") as archive, pytest.warns(UserWarning):
        archive.writestr("xl/worksheets/sheet1.xml", "another version")
    _, ingest, structure, _ = adapters()
    (artifact,) = ingest.ingest(source(path), provenance=provenance())
    with pytest.raises(DocumentStructureError):
        structure.structure(artifact, provenance=provenance())
