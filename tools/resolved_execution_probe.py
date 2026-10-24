"""Qualify installed six-stage commands from outside the checkout, without test imports."""

import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "source",
        "context",
        "normalization_policy",
        "registry",
        "config",
        "resolution_policy",
        "candidate_snapshot",
        "cases",
        "wheel",
    ):
        parser.add_argument(name, type=Path)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    calls: list[dict[str, object]] = []

    def run(module: str, args: list[str], *, error: str | None = None):
        argv = [sys.executable, "-m", "procurement_intelligence_lab.interfaces." + module, *args]
        before = perf_counter()
        done = subprocess.run(argv, env=env, text=True, capture_output=True, check=False)
        calls.append(
            {"argv": argv, "exit_code": done.returncode, "seconds": perf_counter() - before}
        )
        if error is not None:
            assert done.returncode == 2 and not done.stdout, done.stderr
            assert json.loads(done.stderr)["code"] == error, done.stderr
            return json.loads(done.stderr)
        assert done.returncode == 0 and not done.stderr, done.stderr
        return json.loads(done.stdout)

    with tempfile.TemporaryDirectory(prefix="resolved-probe-", dir=Path.cwd()) as work:
        root = Path(work)
        source = root / "source.xlsx"
        source.write_bytes(options.source.read_bytes())
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(run("domain_package", [])))
        pins = {}
        for name in (
            "context",
            "normalization_policy",
            "registry",
            "config",
            "resolution_policy",
            "candidate_snapshot",
        ):
            original = getattr(options, name)
            path = root / original.name
            path.write_bytes(original.read_bytes())
            pins[name] = path
        args = [str(source), "--manifest", str(manifest), "--stop-after", "RESOLVE"]
        for name, path in pins.items():
            args += ["--" + name.replace("_", "-"), str(path)]
        first = run("execute_resolved_package", args)
        receipt = first["execution_receipt"]
        assert len(first["transformations"]) == 6
        assert [e["status"] for e in receipt["entries"]] == ["SUCCEEDED"] * 6 + ["NOT_EXECUTED"] * 6
        assert receipt["requested_prefix_complete"] and not receipt["package_execution_complete"]
        assert first["artifact"]["content_hash"] == sha256(source.read_bytes()).hexdigest()
        assert (
            receipt["context"]["code_revision"]
            == json.loads(pins["context"].read_text())["code_revision"]
        )
        # The old public caller uses the identical plan, pins and first-five behavior.
        oldargs = args[:]
        for name in ("resolution-policy", "candidate-snapshot"):
            i = oldargs.index("--" + name)
            del oldargs[i : i + 2]
        oldargs[oldargs.index("--stop-after") + 1] = "ASSERT"
        old = run("execute_package", oldargs)
        assert (
            old["execution_receipt"]["execution_digest"]
            == first["prefix_execution_receipt"]["execution_digest"]
        )
        for key in ("artifact", "normalization", "assertion_batch"):
            assert old[key] == first[key]
        catalog = json.loads(pins["candidate_snapshot"].read_text())
        raw = pins["candidate_snapshot"].read_bytes()
        catalog["keys"].reverse()
        pins["candidate_snapshot"].write_text(json.dumps(catalog, indent=2))
        formatted = run("execute_resolved_package", args)
        assert formatted["execution_receipt"]["execution_digest"] == receipt["execution_digest"]
        assert (
            formatted["resolution"]["candidate_raw_sha256"]
            != first["resolution"]["candidate_raw_sha256"]
        )
        assert formatted["execution_receipt"]["receipt_digest"] != receipt["receipt_digest"]
        catalog["keys"] = []
        pins["candidate_snapshot"].write_text(json.dumps(catalog))
        empty = run("execute_resolved_package", args)
        assert empty["execution_receipt"]["execution_digest"] != receipt["execution_digest"]
        assert (
            empty["prefix_execution_receipt"]["execution_digest"]
            == first["prefix_execution_receipt"]["execution_digest"]
        )
        assert all(
            o["status"] == "unresolved" and not o["matched_keys"]
            for o in empty["resolution"]["outcomes"]
        )
        assert not empty["resolution"]["canonicalized_assertions"]
        pins["candidate_snapshot"].write_bytes(raw)
        # Every corpus example is an actual installed public execution over its explicit source.
        cases = json.loads(options.cases.read_text())
        examples = []
        tp = fp = fn = accepted = unresolved = 0
        for case in cases:
            variant = root / (case["id"] + ".xlsx")
            with ZipFile(source) as original, ZipFile(variant, "w") as output:
                for info in original.infolist():
                    data = original.read(info.filename)
                    if info.filename == "xl/worksheets/sheet1.xml":
                        xml = data.decode()
                        a = xml.index("<sheetData>") + len("<sheetData>")
                        b = xml.index("</sheetData>")
                        data = (xml[:a] + case["source_rows_xml"] + xml[b:]).encode()
                    output.writestr(info, data)
            pins["candidate_snapshot"].write_text(json.dumps(case["candidate_snapshot"]))
            actual = run("execute_resolved_package", [str(variant), *args[1:]])
            outcomes = actual["resolution"]["outcomes"]
            assert len(outcomes) == 1
            o = outcomes[0]
            assert (
                o["status"] == case["expected_status"]
                and o["canonical_key"] == case["expected_key"]
            )
            assert o["evidence"][0]["predicate"] == "has_sku"
            assert o["evidence"][0]["evidence"]["location"]["row"] == case["source_location"]["row"]
            is_accepted = o["status"] == "resolved"
            accepted += is_accepted
            unresolved += not is_accepted
            tp += is_accepted and o["canonical_key"] == case["expected_key"]
            fp += is_accepted and o["canonical_key"] != case["expected_key"]
            fn += case["expected_key"] is not None and (
                not is_accepted or o["canonical_key"] != case["expected_key"]
            )
            from procurement_intelligence_lab.domains.procurement.resolution import (
                resolve_identifier,
            )
            from procurement_intelligence_lab.interfaces.execute_package import request
            from procurement_intelligence_lab.platform.semantics.provenance import (
                ComponentKind,
                DecisionProvenance,
            )

            legacy = resolve_identifier(
                case["mention"],
                tuple(case["candidate_snapshot"]["keys"]),
                provenance=DecisionProvenance(
                    request(variant, pins["context"].read_bytes()).context,
                    "legacy-rule-corpus",
                    ComponentKind.DETERMINISTIC,
                    "1",
                ),
            )
            assert legacy.canonical_key == o["canonical_key"] and legacy.status.value == o["status"]
            examples.append(
                {
                    **case,
                    "actual": o,
                    "legacy": {
                        "canonical_key": legacy.canonical_key,
                        "status": legacy.status.value,
                    },
                }
            )
        pins["candidate_snapshot"].write_bytes(raw)
        storage: dict[str, object] = {
            "status": "not_requested",
            "reason": "No explicit disposable DSN",
        }
        if env.get("PIL_ASSERTION_ARCHIVE_DSN"):
            for module in (
                "assertion_archive",
                "planned_execution_archive",
                "resolved_execution_archive",
            ):
                run(module, ["init"])
            retained = run("execute_resolved_package", args + ["--archive"])
            key = retained["archive_receipt"]["execution_digest"]
            scope = root / "scope.json"
            scope.write_text(json.dumps(json.loads(pins["context"].read_text())["scope"]))
            source_bytes = source.read_bytes()
            source.unlink()
            manifest.unlink()
            for path in pins.values():
                path.unlink()
            base = ["--scope", str(scope), "--execution-digest", key]
            shown = run("resolved_execution_archive", ["show", *base])
            assert shown["resolution"] == retained["resolution"]
            page = run("resolved_execution_archive", ["history", "--scope", str(scope)])
            assert any(r["execution_digest"] == key for r in page["receipts"])
            for command in ("content", "export"):
                output = root / (command + ".bin")
                argv = [command, *base, "--output", str(output)]
                run("resolved_execution_archive", argv)
                if command == "content":
                    assert output.read_bytes() == source_bytes
                else:
                    from procurement_intelligence_lab.bootstrap import archive_codec
                    from procurement_intelligence_lab.platform.execution.resolution_archive import (
                        ArchivedResolvedPrefix,
                    )

                    graph = archive_codec().loads(output.read_text())
                    assert isinstance(graph, ArchivedResolvedPrefix)
                    assert graph.completed.execution.candidate_input.raw_json == raw
                run("resolved_execution_archive", argv, error="pil.input.archive_contract_invalid")
            run(
                "planned_execution_archive",
                [
                    "show",
                    "--scope",
                    str(scope),
                    "--execution-digest",
                    retained["prefix_execution_receipt"]["execution_digest"],
                ],
            )
            run(
                "assertion_archive",
                [
                    "show",
                    "--scope",
                    str(scope),
                    "--snapshot-id",
                    retained["archive_receipt"]["snapshot_id"],
                ],
            )
            storage = {
                "status": "passed",
                "source_deleted": True,
                "input_files_deleted": True,
                "source_and_catalog_exact": True,
            }
        elif importlib.util.find_spec("psycopg") is None:
            env["PIL_ASSERTION_ARCHIVE_DSN"] = "postgresql://unused.invalid/unavailable"
            run(
                "resolved_execution_archive",
                ["init"],
                error="pil.infrastructure.archive_unavailable",
            )
            storage["missing_extra_typed"] = True
        expected_unique = sum(c["expected_key"] is not None for c in cases)
        result = {
            "resolved_prefix_probe": "passed",
            "python": platform.python_version(),
            "wheel_sha256": sha256(options.wheel.read_bytes()).hexdigest(),
            "code_revision": receipt["context"]["code_revision"],
            "execution_digest": receipt["execution_digest"],
            "first_five_digest": first["prefix_execution_receipt"]["execution_digest"],
            "actual_stages": 6,
            "logical_stages": 12,
            "storage": storage,
            "corpus": {
                "population": "synthetic declared-namespace development mentions; rule-contract labels only",
                "eligible": len(cases),
                "accepted": accepted,
                "expected_unique": expected_unique,
                "true_positive": tp,
                "false_merge": fp,
                "false_negative": fn,
                "unresolved": unresolved,
                "precision": tp / accepted if accepted else None,
                "recall": tp / expected_unique if expected_unique else None,
                "false_merge_rate": fp / accepted if accepted else None,
                "abstention_review_load": unresolved / len(cases) if cases else None,
                "examples": examples,
            },
            "commands": calls,
        }
        if options.output:
            options.output.write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {k: v for k, v in result.items() if k not in ("commands", "corpus")}
                | {"corpus_counts": {k: v for k, v in result["corpus"].items() if k != "examples"}},
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
