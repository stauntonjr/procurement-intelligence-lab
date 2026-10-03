"""Admission failures must never become a successful absence."""

import json
import shutil
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from procurement_intelligence_lab.adapters.synthetic_corpus import (
    DEFAULT_ROOT,
    SyntheticCorpusReader,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError, CorpusNotFoundError
from tests.contract.test_corpus_investigation import CONTEXT


def copied(tmp_path: Path) -> SyntheticCorpusReader:
    root = tmp_path / "corpus"
    shutil.copytree(DEFAULT_ROOT, root)
    return SyntheticCorpusReader(root)


def test_authorization_precedes_io(tmp_path: Path) -> None:
    reader = SyntheticCorpusReader(tmp_path / "missing")
    for context in (
        replace(CONTEXT, project_id="foreign"),
        replace(CONTEXT, permissions=frozenset()),
    ):
        with pytest.raises(ScopeAuthorizationError):
            reader.inventory(context=context)


def test_source_requires_evidence_permission_and_known_identity() -> None:
    reader = SyntheticCorpusReader()
    ref = reader.inventory(context=CONTEXT).facts[0].evidence
    with pytest.raises(ScopeAuthorizationError):
        reader.source(ref, context=replace(CONTEXT, permissions=frozenset({Permission.READ_STATE})))
    with pytest.raises(CorpusNotFoundError):
        reader.source(replace(ref, artifact_id="unknown"), context=CONTEXT)


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "duplicate",
        "path",
        "tamper",
        "scope",
        "records",
        "expiry",
        "supersedes",
        "date",
        "unit",
        "quantity",
        "nan",
    ],
)
def test_admission_rejects_corruption(tmp_path: Path, mutation: str) -> None:
    reader = copied(tmp_path)
    path = reader.root / "manifest.json"
    manifest = json.loads(path.read_text())
    doc = manifest["documents"][2]
    if mutation == "schema":
        manifest["schema_version"] = "future"
    elif mutation == "duplicate":
        manifest["documents"].append(doc)
    elif mutation == "path":
        doc["path"] = "../escape.xlsx"
    elif mutation == "tamper":
        (reader.root / doc["path"]).write_bytes(b"corrupt")
    elif mutation in {"quantity", "nan", "unit"}:
        from tools.generate_procurement_corpus import DEFAULT_SPEC, render

        spec = json.loads(DEFAULT_SPEC.read_text())
        spec["documents"][0]["rows"][0]["quantity"] = (
            "NaN" if mutation == "nan" else "-1" if mutation == "quantity" else "4"
        )
        if mutation == "unit":
            spec["documents"][0]["rows"][0]["unit"] = ""
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(json.dumps(spec))
        render(spec_path, reader.root)
        with pytest.raises(CorpusAdmissionError):
            reader.inventory(context=CONTEXT)
        return
    else:
        metadata_path = reader.root / doc["metadata_path"]
        metadata = json.loads(metadata_path.read_text())
        record = metadata["records"][0]
        if mutation == "scope":
            metadata["document"]["project_id"] = "foreign"
        elif mutation == "records":
            metadata["records"].pop()
        elif mutation == "expiry":
            record["effective_until"] = "2026-11-01T00:00:00+00:00"
        elif mutation == "supersedes":
            record["supersedes"] = ["prior-order"]
        elif mutation == "date":
            record["approved_at"] = "2026-01-01"
        metadata_path.write_text(json.dumps(metadata))
        doc["metadata_hash"] = sha256(metadata_path.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(CorpusAdmissionError):
        reader.inventory(context=CONTEXT)


def test_metadata_change_changes_snapshot(tmp_path: Path) -> None:
    reader = copied(tmp_path)
    before = reader.inventory(context=CONTEXT)
    path = reader.root / "manifest.json"
    manifest = json.loads(path.read_text())
    doc = manifest["documents"][0]
    meta = reader.root / doc["metadata_path"]
    value = json.loads(meta.read_text())
    value["records"][0]["document_at"] = "2026-07-01T00:00:00+00:00"
    meta.write_text(json.dumps(value))
    doc["metadata_hash"] = sha256(meta.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    after = reader.inventory(context=CONTEXT)
    assert after.snapshot_id != before.snapshot_id
    assert after.facts[0].evidence == before.facts[0].evidence
    assert after.facts[0].authority != before.facts[0].authority


def test_deterministic_regeneration(tmp_path: Path) -> None:
    from tools.generate_procurement_corpus import DEFAULT_SPEC, render

    render(DEFAULT_SPEC, tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == {
        p.name: p.read_bytes() for p in DEFAULT_ROOT.iterdir()
    }


def test_duplicate_source_coordinate_rejected(tmp_path: Path) -> None:
    from zipfile import ZipFile

    reader = copied(tmp_path)
    path = reader.root / "manifest.json"
    manifest = json.loads(path.read_text())
    doc = manifest["documents"][0]
    workbook = reader.root / doc["path"]
    with ZipFile(workbook) as archive:
        parts = {n: archive.read(n) for n in archive.namelist()}
    xml = parts["xl/worksheets/sheet1.xml"].decode()
    start = xml.index('<row r="2">')
    end = xml.index("</row>", start) + len("</row>")
    duplicate = xml[start:end].replace("<t>4</t>", "<t>99</t>")
    parts["xl/worksheets/sheet1.xml"] = xml.replace(
        "</sheetData>", duplicate + "</sheetData>"
    ).encode()
    with ZipFile(workbook, "w") as archive:
        for name, raw in parts.items():
            archive.writestr(name, raw)
    doc["content_hash"] = sha256(workbook.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(CorpusAdmissionError, match="duplicate source row"):
        reader.inventory(context=CONTEXT)


def test_corrupt_shared_string_is_typed_admission_failure(tmp_path: Path) -> None:
    from zipfile import ZipFile

    reader = copied(tmp_path)
    path = reader.root / "manifest.json"
    manifest = json.loads(path.read_text())
    doc = manifest["documents"][0]
    workbook = reader.root / doc["path"]
    with ZipFile(workbook) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    xml = parts["xl/worksheets/sheet1.xml"].decode()
    start = xml.index('<c r="A2"')
    end = xml.index("</c>", start) + 4
    parts["xl/worksheets/sheet1.xml"] = (
        xml[:start] + '<c r="A2" t="s"><v>999</v></c>' + xml[end:]
    ).encode()
    with ZipFile(workbook, "w") as archive:
        for name, raw in parts.items():
            archive.writestr(name, raw)
    doc["content_hash"] = sha256(workbook.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(CorpusAdmissionError):
        reader.inventory(context=CONTEXT)


def test_admitted_values_follow_actual_workbook(tmp_path: Path) -> None:
    from tools.generate_procurement_corpus import DEFAULT_SPEC, render

    spec = json.loads(DEFAULT_SPEC.read_text())
    spec["documents"][0]["rows"][0]["quantity"] = "7"
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    directory = tmp_path / "corpus"
    render(path, directory)
    fact = next(
        f
        for f in SyntheticCorpusReader(directory).inventory(context=CONTEXT).facts
        if f.revision_id == "atlas-bom-r1" and f.canonical_key == "GPU-A"
    )
    assert str(fact.quantity) == "7"
