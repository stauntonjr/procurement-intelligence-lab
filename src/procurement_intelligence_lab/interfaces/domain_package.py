"""Compile the shipped procurement declaration; execution planning is a separate boundary."""

import argparse
import json
import sys

from procurement_intelligence_lab.bootstrap import compile_procurement_manifest
from procurement_intelligence_lab.domains.procurement.package import BOM_PROFILE_ID
from procurement_intelligence_lab.platform.domain_packages.compiler import (
    DomainPackageValidationError,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile the procurement DomainPackage manifest.")
    parser.add_argument("--source-profile", default=BOM_PROFILE_ID)
    args = parser.parse_args()
    try:
        compiled = compile_procurement_manifest(source_profile=args.source_profile)
    except DomainPackageValidationError as exc:
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
    print(compiled.canonical_json.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
