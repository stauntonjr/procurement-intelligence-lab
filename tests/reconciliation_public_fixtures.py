"""Real public producer execution and explicitly pinned synthetic authority input files."""

import json
from pathlib import Path
from typing import Any
from zipfile import ZIP_STORED, ZipFile

from tests.bom_stage_fixtures import AT, HEADER, ROW
from tests.integration.test_execute_package_cli import ROOT
from tests.integration.test_execute_resolved_package_cli import inputs as resolved_inputs
from tests.integration.test_planned_execution_archive_cli import run, success


def inputs(
    tmp_path: Path,
    dsn: str,
    rows: tuple[str, ...] = (HEADER + ROW,),
    *,
    identical: bool = False,
    padding: int = 0,
    candidate_keys: tuple[str, ...] | None = None,
):
    for module in ("assertion_archive", "planned_execution_archive", "resolved_execution_archive"):
        success(run(module, ["init"], dsn))
    producers: list[dict[str, Any]] = []
    original: bytes | None = None
    for i, row in enumerate(rows):
        folder = tmp_path / f"producer-{i}"
        folder.mkdir()
        source_args = resolved_inputs(folder, row)
        if original is not None and identical:
            Path(source_args[0]).write_bytes(original)
        if padding and i == 0:
            with ZipFile(source_args[0], "a") as archive:
                archive.writestr("synthetic-padding.bin", b"0" * padding, compress_type=ZIP_STORED)
        if candidate_keys is not None:
            path = Path(source_args[source_args.index("--candidate-snapshot") + 1])
            value = json.loads(path.read_text())
            value["keys"] = candidate_keys
            path.write_text(json.dumps(value))
        original = Path(source_args[0]).read_bytes()
        producers.append(success(run("execute_resolved_package", source_args + ["--archive"], dsn)))
    args: list[str] = []
    for name in ("context", "governing-policy", "registry", "config"):
        filename = {
            "registry": "procurement-registry.json",
            "config": "procurement-config.toml",
        }.get(name, name + ".json")
        path = tmp_path / filename
        path.write_bytes((ROOT / "tests/fixtures/retained-reconciliation" / filename).read_bytes())
        args += ["--" + name, str(path)]
    manifest = tmp_path / "operation-manifest.json"
    manifest.write_text(
        run(
            "domain_package", ["--source-profile", "retained-resolved-required-quantity"], dsn
        ).stdout
    )
    args += ["--manifest", str(manifest), "--as-of", AT.isoformat()]
    records: list[dict[str, Any]] = []
    for i, p in enumerate(producers):
        d = p["execution_receipt"]["execution_digest"]
        a = p["artifact"]
        args += ["--producer-digest", d]
        records.append(
            {
                "execution_digest": d,
                "artifact_id": a["artifact_id"],
                "content_hash": a["content_hash"],
                "revision_id": f"r{i}",
                "supersedes_revision_ids": [],
                "source_role": "approved_bom_revision",
                "approval": {
                    "record_ref": f"synthetic-approval-{i}",
                    "approved_at": AT.isoformat(),
                },
                "effective_from": AT.isoformat(),
                "effective_until": None,
                "document_at": AT.isoformat(),
            }
        )
    authority = tmp_path / "authority.json"
    authority.write_text(json.dumps({"schema_version": "1.0", "producers": records}))
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps(producers[0]["artifact"]["source"]["scope"]))
    args += ["--authority", str(authority)]
    return args, scope, producers
