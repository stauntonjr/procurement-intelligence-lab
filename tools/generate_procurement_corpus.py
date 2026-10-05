"""Render source facts deterministically; never import policy or evaluator gold."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "synthetic/specs/procurement-corpus-v1.json"
DEFAULT_OUTPUT = ROOT / "src/procurement_intelligence_lab/examples/corpus_v1"


def write_json(path: Path, value: object) -> str:
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def render(spec: Path, output: Path) -> None:
    source = json.loads(spec.read_text())
    output.mkdir(parents=True, exist_ok=True)
    documents = []
    for doc in source["documents"]:
        identity = doc["artifact_id"]
        values = [["SKU", "Description", "Quantity", "Unit Price", "Unit"]]
        values += [
            [r[k] for k in ("sku", "description", "quantity", "unit_price", "unit")]
            for r in doc["rows"]
        ]
        rows = []
        for index, row in enumerate(values, 1):
            cells = "".join(
                f'<c r="{chr(65 + c)}{index}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
                for c, v in enumerate(row)
            )
            rows.append(f'<row r="{index}">{cells}</row>')
        parts = {
            "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
            "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
            "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            "xl/worksheets/sheet1.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + "".join(rows)
            + "</sheetData></worksheet>",
        }
        workbook = output / f"{identity}.xlsx"
        with ZipFile(workbook, "w") as archive:
            for name, content in sorted(parts.items()):
                entry = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                entry.compress_type = ZIP_DEFLATED
                archive.writestr(entry, content)
        records = []
        for row_number, row in enumerate(doc["rows"], 2):
            records.append(
                {
                    k: v
                    for k, v in row.items()
                    if k not in ("sku", "description", "quantity", "unit_price", "unit")
                }
                | {"row": row_number}
            )
        metadata_path = f"{identity}.authority.json"
        metadata_hash = write_json(
            output / metadata_path,
            {
                "schema_version": 1,
                "document": {k: v for k, v in doc.items() if k != "rows"},
                "records": records,
            },
        )
        documents.append(
            {k: v for k, v in doc.items() if k != "rows"}
            | {
                "path": workbook.name,
                "content_hash": sha256(workbook.read_bytes()).hexdigest(),
                "metadata_path": metadata_path,
                "metadata_hash": metadata_hash,
            }
        )
    write_json(
        output / "manifest.json",
        {"schema_version": source["schema_version"], "documents": documents},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.spec, args.output)
