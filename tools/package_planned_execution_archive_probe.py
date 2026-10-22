"""Qualify installed planned-prefix retention using stdlib and public subprocess commands."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    original, context, policy, registry, config = (Path(x).absolute() for x in sys.argv[1:6])
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    with TemporaryDirectory(prefix="planned-archive-probe-", dir=Path.cwd()) as folder:
        root = Path(folder)
        source = root / "synthetic.xlsx"
        content = original.read_bytes()
        source.write_bytes(content)

        def run(module: str, args: list[str], code: str | None = None):
            done = subprocess.run(
                [sys.executable, "-m", "procurement_intelligence_lab.interfaces." + module, *args],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            if code is not None:
                if done.returncode != 2 or done.stdout or json.loads(done.stderr)["code"] != code:
                    raise RuntimeError(
                        "installed planned archive failed typed rejection: " + done.stderr
                    )
                return json.loads(done.stderr)
            if done.returncode or done.stderr:
                raise RuntimeError("installed planned archive command failed: " + done.stderr)
            return json.loads(done.stdout)

        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(run("domain_package", [])))
        args = [
            str(source),
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
            "--config",
            str(config),
            "--context",
            str(context),
            "--normalization-policy",
            str(policy),
            "--stop-after",
            "ASSERT",
            "--archive",
        ]
        if env.get("PIL_PLANNED_ARCHIVE_EXPECT_MISSING_DRIVER") == "1":
            source.unlink()
            env["PIL_ASSERTION_ARCHIVE_DSN"] = "postgresql://invalid.local/unused"
            error = run("execute_package", args, "pil.infrastructure.archive_unavailable")
            if "storage extra" not in error["message"]:
                raise RuntimeError("installed base wheel did not prove missing-driver boundary")
            print(json.dumps({"planned_execution_archive_missing_driver": "passed"}))
            return 0
        if not env.get("PIL_ASSERTION_ARCHIVE_DSN"):
            raise RuntimeError(
                "installed storage probe requires an explicitly isolated archive DSN"
            )
        run("assertion_archive", ["init"])
        run("execute_package", args, "pil.infrastructure.archive_unavailable")
        run("planned_execution_archive", ["init"])
        first = run("execute_package", args)
        again = run("execute_package", args)
        r = first["archive_receipt"]
        key = r["execution_digest"]
        if (
            again["archive_receipt"] != r
            or again["retained_execution_receipt"] != first["retained_execution_receipt"]
            or again["execution_receipt"]["receipt_digest"]
            == first["execution_receipt"]["receipt_digest"]
        ):
            raise RuntimeError("installed retry did not distinguish current and retained execution")
        er = first["execution_receipt"]
        if (
            len(first["transformations"]) != 5
            or len(er["entries"]) != 12
            or er["package_execution_complete"]
            or any(x["status"] != "NOT_EXECUTED" for x in er["entries"][5:])
        ):
            raise RuntimeError("installed retention lost prefix boundary")
        changed = root / "policy.json"
        data = json.loads(policy.read_text())
        data["currency"] = "GBP" if data["currency"] != "GBP" else "USD"
        changed.write_text(json.dumps(data))
        other = args.copy()
        other[other.index("--normalization-policy") + 1] = str(changed)
        variation = run("execute_package", other)
        if variation["archive_receipt"]["execution_digest"] == key:
            raise RuntimeError("altered policy reused computation identity")
        scope = root / "scope.json"
        scope.write_text(json.dumps(r["scope"]))
        source.unlink()
        shown = run(
            "planned_execution_archive", ["show", "--scope", str(scope), "--execution-digest", key]
        )
        if (
            shown["retained_execution_receipt"] != first["retained_execution_receipt"]
            or shown["assertion_batch"] != first["assertion_batch"]
        ):
            raise RuntimeError("installed restart changed retained evidence")
        page = run("planned_execution_archive", ["history", "--scope", str(scope), "--limit", "1"])
        if (
            page["receipts"] != [r]
            or not page["has_more"]
            or page["next_after_sequence"] != r["sequence"]
        ):
            raise RuntimeError("installed history did not evidence pagination")
        last = run(
            "planned_execution_archive",
            [
                "history",
                "--scope",
                str(scope),
                "--limit",
                "1",
                "--after-sequence",
                str(page["next_after_sequence"]),
            ],
        )
        if (
            last["has_more"]
            or last["next_after_sequence"] is not None
            or len(last["receipts"]) != 1
        ):
            raise RuntimeError("installed final history page fabricated completeness")
        output = root / "retained.xlsx"
        export = [
            "content",
            "--scope",
            str(scope),
            "--execution-digest",
            key,
            "--output",
            str(output),
        ]
        run("planned_execution_archive", export)
        if output.read_bytes() != content:
            raise RuntimeError("installed export changed captured bytes")
        run("planned_execution_archive", export, "pil.input.archive_contract_invalid")
        legacy = run(
            "assertion_archive", ["show", "--scope", str(scope), "--snapshot-id", r["snapshot_id"]]
        )
        if legacy["assertion_batch"] != first["assertion_batch"]:
            raise RuntimeError("installed legacy source reader changed assertions")
        print(
            json.dumps(
                {
                    "planned_execution_archive_smoke": "passed",
                    "actual_stages": 5,
                    "logical_stages": 12,
                    "source_deleted": True,
                    "retry_retains_first": True,
                    "export_equal": True,
                    "legacy_reader": True,
                    "policy_distinct": True,
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
