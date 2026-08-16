from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from procurement_intelligence_lab.adapters.xlsx import (
    read_bom,
    read_bom_with_provenance,
)
from procurement_intelligence_lab.domains.procurement.bom import bom_cost, gpu_quantity
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceRelation


def _write_bom(path: Path) -> None:
    content = '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c><v>SKU</v></c><c><v>Description</v></c><c><v>Quantity</v></c><c><v>Unit Price</v></c></row><row r="2"><c><v>GPU-A</v></c><c><v>GPU accelerator</v></c><c><v>4</v></c><c><v>100</v></c></row></sheetData></worksheet>'
    workbook = '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", content)


def test_reads_synthetic_xlsx_with_cell_provenance(tmp_path: Path) -> None:
    path = tmp_path / "bom.xlsx"
    _write_bom(path)

    bom = read_bom(path)

    assert gpu_quantity(bom).value == Decimal(4)
    assert bom_cost(bom).value == Decimal(400)
    assert bom.lines[0].evidence.row == 2


def test_xlsx_structuring_records_event_and_carries_it_into_assertions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bom.xlsx"
    _write_bom(path)

    result = read_bom_with_provenance(path)
    assertions = result.source_assertions()

    assert result.transformation.provenance.component_name == "xlsx-bom-structurer"
    assert result.transformation.provenance.schema_version == "bom-xlsx-v1"
    assert any(
        edge.relation is ProvenanceRelation.USED_INPUT
        and edge.target_id == f"artifact:{result.bom.lines[0].evidence.content_hash}"
        for edge in result.transformation.input_edges
    )
    assert {item.transformation_event_id for item in assertions} == {result.transformation.event_id}
