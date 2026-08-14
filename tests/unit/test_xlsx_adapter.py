from decimal import Decimal
from zipfile import ZIP_DEFLATED, ZipFile

from procurement_intelligence_lab.adapters.xlsx import read_bom
from procurement_intelligence_lab.domain.bom import bom_cost, gpu_quantity


def test_reads_synthetic_xlsx_with_cell_provenance(tmp_path):
    path = tmp_path / "bom.xlsx"
    content = '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c><v>SKU</v></c><c><v>Description</v></c><c><v>Quantity</v></c><c><v>Unit Price</v></c></row><row r="2"><c><v>GPU-A</v></c><c><v>GPU accelerator</v></c><c><v>4</v></c><c><v>100</v></c></row></sheetData></worksheet>'
    workbook = '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", content)
    bom = read_bom(path)
    assert gpu_quantity(bom).value == Decimal(4)
    assert bom_cost(bom).value == Decimal(400)
    assert bom.lines[0].evidence.row == 2
