from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from procurement_intelligence_lab.adapters.xlsx import read_bom


@pytest.mark.contract
def test_sparse_cells_use_xlsx_coordinates_instead_of_xml_position(tmp_path: Path) -> None:
    path = tmp_path / "sparse.xlsx"
    worksheet = """<?xml version="1.0"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1"><v>SKU</v></c><c r="B1"><v>Description</v></c><c r="C1"><v>Quantity</v></c><c r="D1"><v>Unit Price</v></c></row>
<row r="7"><c r="A7"><v>GPU-A</v></c><c r="C7"><v>4</v></c><c r="D7"><v>100</v></c></row>
</sheetData></worksheet>"""
    workbook = """<?xml version="1.0"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets></workbook>"""
    relationships = """<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)

    line = read_bom(path).lines[0]

    assert line.sku == "GPU-A"
    assert line.description == ""
    assert line.quantity == Decimal(4)
    assert line.unit_price == Decimal(100)
    assert line.evidence.row == 7
    assert line.evidence.cells == ("A", "C", "D")
