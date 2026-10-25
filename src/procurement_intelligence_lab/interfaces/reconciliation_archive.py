"""Explicit reconciliation capability initialization and scoped historical evidence reads."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import NoReturn

from procurement_intelligence_lab.application.archived_reconciliation import archive_receipt_payload
from procurement_intelligence_lab.bootstrap import (
    build_reconciliation_archive,
    build_reconciliation_archive_reader,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn
from procurement_intelligence_lab.interfaces.assertion_archive import export_content
from procurement_intelligence_lab.interfaces.planned_execution_archive import (
    cursor_value,
    limit_value,
    scope_file,
)
from procurement_intelligence_lab.platform.execution.archive import execution_key, history_bounds
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    SemanticContractError,
)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ArchiveContractError("invalid reconciliation archive arguments; use --help")


def main() -> int:
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    for command in ("show", "history", "content-manifest", "export"):
        p = commands.add_parser(command)
        p.add_argument("--scope", type=Path, required=True)
        if command == "history":
            p.add_argument("--limit", type=limit_value, default=100)
            p.add_argument("--after-sequence", type=cursor_value, default=0)
        else:
            p.add_argument("--execution-digest", required=True)
        if command == "export":
            p.add_argument("--output", type=Path, required=True)
    try:
        args = parser.parse_args()
        if args.command == "init":
            build_reconciliation_archive(configured_dsn()).initialize()
            payload = {"capability": "retained_resolution_reconciliation/v1", "initialized": True}
        else:
            if args.command != "history":
                execution_key(args.execution_digest)
            scope = scope_file(args.scope)
            if args.command == "history":
                history_bounds(scope, args.limit, args.after_sequence)
            reader = build_reconciliation_archive_reader(configured_dsn())
            if args.command == "show":
                payload = reader.show(scope, args.execution_digest).as_dict()
            elif args.command == "history":
                page = reader.history(scope, limit=args.limit, after_sequence=args.after_sequence)
                payload = {
                    "receipts": [archive_receipt_payload(r) for r in page.receipts],
                    "has_more": page.has_more,
                    "next_after_sequence": page.next_after_sequence,
                }
            elif args.command == "content-manifest":
                payload = reader.content_manifest(scope, args.execution_digest)
            else:
                data = reader.export(scope, args.execution_digest)
                export_content(args.output, data)
                payload = {
                    "execution_digest": args.execution_digest,
                    "content_hash": sha256(data).hexdigest(),
                    "byte_length": len(data),
                    "output": str(args.output),
                }
    except SemanticContractError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
