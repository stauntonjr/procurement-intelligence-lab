"""Qualify actual installed prefix execution without importing the source checkout."""

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile


def main() -> int:
    source, context, policy, registry, config = (Path(x).absolute() for x in sys.argv[1:6])
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}

    def run(module: str, args: list[str]):
        return subprocess.run(
            [sys.executable, "-m", "procurement_intelligence_lab.interfaces." + module, *args],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    compiled = run("domain_package", [])
    if compiled.returncode:
        raise RuntimeError("installed manifest command failed: " + compiled.stderr)
    manifest = Path("prefix-manifest.json").absolute()
    manifest.write_text(compiled.stdout)
    args = [
        str(source),
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        "--config",
        str(config),
        "--stop-after",
        "ASSERT",
        "--context",
        str(context),
        "--normalization-policy",
        str(policy),
    ]

    def execute(argv: list[str]):
        done = run("execute_package", argv)
        if done.returncode:
            raise RuntimeError("installed planned prefix failed: " + done.stderr)
        return json.loads(done.stdout)

    first = execute(args)
    r = first["execution_receipt"]
    if (
        first["executed_stages"] != ["INGEST", "STRUCTURE", "MAP", "NORMALIZE", "ASSERT"]
        or len(first["transformations"]) != 5
        or len(r["entries"]) != 12
    ):
        raise RuntimeError("installed prefix lost actual stage execution evidence")
    if (
        not r["requested_prefix_complete"]
        or r["package_execution_complete"]
        or len(r["resolved_references"]) != 3
    ):
        raise RuntimeError("installed prefix misstates completion or resolved input evidence")
    for entry in r["entries"][5:]:
        if (
            entry["status"] != "NOT_EXECUTED"
            or entry["output_ids"]
            or entry["event_id"] is not None
        ):
            raise RuntimeError("installed prefix fabricated later execution")
    claims = first["assertion_batch"]["claims"]
    quantity = next(c for c in claims if c["trace"]["mapped_field_key"] == "BOM!C2")
    if (
        quantity["value"] != "4"
        or quantity["unit"] != "each"
        or quantity["evidence"]["cells"] != ["C"]
    ):
        raise RuntimeError("installed prefix changed source quantity or location")
    source_hash = sha256(source.read_bytes()).hexdigest()
    if first["artifact"]["content_hash"] != source_hash:
        raise RuntimeError("installed capture changed source bytes")
    again = execute(args)["execution_receipt"]
    if again["execution_digest"] != r["execution_digest"]:
        raise RuntimeError("pinned repeat changed computation identity")
    if r["context"]["code_revision"] != json.loads(context.read_text())["code_revision"]:
        raise RuntimeError("installed receipt lost pinned revision")
    # Deterministic synthetic variation: two equal tokens plus a distinct unknown/zero row.
    variant = Path("prefix-source-variant.xlsx").absolute()
    with ZipFile(source) as original, ZipFile(variant, "w") as output:
        for info in original.infolist():
            content = original.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                xml = content.decode().replace("CPU-A", "GPU-A")
                xml = xml.replace(
                    "</sheetData>", '<row r="4"><c r="C4"><v>0</v></c></row></sheetData>'
                )
                content = xml.encode()
            output.writestr(info, content)
    variation = execute([str(variant), *args[1:]])
    vc = variation["assertion_batch"]["claims"]
    if [c["value"] for c in vc if c["predicate"] == "has_sku"] != ["GPU-A", "GPU-A", None] or len(
        {c["assertion_id"] for c in vc}
    ) != 12:
        raise RuntimeError("installed prefix lost duplicate rows or unknown source SKU")
    unknown = next(c for c in vc if c["trace"]["mapped_field_key"] == "BOM!A4")
    zero = next(c for c in vc if c["trace"]["mapped_field_key"] == "BOM!C4")
    if unknown["status"] != "unresolved" or zero["value"] != "0" or zero["status"] != "observed":
        raise RuntimeError("installed prefix conflated unknown with zero")
    unsupported = Path("prefix-unavailable-registry.json").absolute()
    data = json.loads(registry.read_text())
    data["implementations"][0]["implementation_id"] = "planning-only-capture"
    unsupported.write_text(json.dumps(data))
    unsupported_config = Path("prefix-unavailable-config.toml").absolute()
    unsupported_config.write_text(
        config.read_text().replace("local-file-capture", "planning-only-capture")
    )
    bad = args.copy()
    bad[0] = str(Path("prefix-absent-source.xlsx").absolute())
    bad[bad.index("--registry") + 1] = str(unsupported)
    bad[bad.index("--config") + 1] = str(unsupported_config)
    denied = run("execute_package", bad)
    if (
        denied.returncode != 2
        or denied.stdout
        or json.loads(denied.stderr)["code"] != "pil.input.package_execution_invalid"
    ):
        raise RuntimeError(
            "installed prefix did not fail unavailable executor before source access"
        )
    print(
        json.dumps(
            {
                "planned_prefix_smoke": "passed",
                "execution_digest": r["execution_digest"],
                "variation_digest": variation["execution_receipt"]["execution_digest"],
                "actual_stages": 5,
                "logical_stages": 12,
                "duplicates_and_unknown_preserved": True,
                "prefix_complete": True,
                "package_complete": False,
                "source_hash": source_hash,
                "code_revision": r["context"]["code_revision"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
