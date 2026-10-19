"""Plan a compiled package using explicit deployment files; never execute stages."""

import argparse
import json
import sys
from pathlib import Path

from procurement_intelligence_lab.platform.planning.contracts import PlanningError, reject
from procurement_intelligence_lab.platform.planning.inputs import (
    canonical,
    load_config,
    load_registry,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest


def _read(path: Path, name: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        reject("input_unreadable", name, "planning input could not be read")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate deployment choices and emit a plan (no execution)."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, required=True, help="Explicit TOML deployment config"
    )
    args = parser.parse_args()
    try:
        manifest = _read(args.manifest, "manifest")
        registry = load_registry(_read(args.registry, "registry"))
        config = load_config(_read(args.config, "config"))
        result = plan_manifest(manifest, registry=registry, config=config)
    except PlanningError as exc:
        print(
            json.dumps(
                {
                    **exc.as_dict(),
                    "issues": [
                        {"code": issue.code, "path": issue.path, "message": issue.message}
                        for issue in exc.issues
                    ],
                }
            ),
            file=sys.stderr,
        )
        return 2
    sys.stdout.buffer.write(
        canonical({"plan": json.loads(result.canonical_json), "plan_hash": result.plan_hash})
        + b"\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
