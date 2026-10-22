"""Explicit planned-prefix archive initialization and scoped source-free recovery."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import NoReturn

from procurement_intelligence_lab.application.archived_planned_execution import (
    execution_archive_receipt_payload,
)
from procurement_intelligence_lab.bootstrap import (
    build_planned_execution_archive,
    build_planned_execution_archive_reader,
)
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn
from procurement_intelligence_lab.interfaces.assertion_archive import export_content
from procurement_intelligence_lab.interfaces.execute_package import read, record
from procurement_intelligence_lab.platform.execution.archive import (
    execution_key,
    history_bounds,
    scope_contract,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    SemanticContractError,
)
from procurement_intelligence_lab.platform.semantics.scope import StateScope


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ArchiveContractError("invalid planned archive arguments; use --help")


def limit_value(raw: str) -> int:
    try:
        value = int(raw)
        if not 1 <= value <= 200:
            raise ValueError()
        return value
    except ValueError:
        raise ArchiveContractError("history limit must be an integer from1 to200") from None


def cursor_value(raw: str) -> int:
    try:
        value = int(raw)
        if value < 0:
            raise ValueError()
        return value
    except ValueError:
        raise ArchiveContractError("history cursor must be a nonnegative integer") from None


def scope_file(path: Path) -> StateScope:
    try:
        data = record(read(path, 32768))
        if set(data) != {"tenant_id", "project_id", "site_id", "version"}:
            raise ValueError()
        scope = StateScope(**data)
        scope_contract(scope)
        return scope
    except (ValueError, TypeError):
        raise ArchiveContractError(
            "scope requires bounded UTF-8 JSON with four exact identity strings"
        ) from None


def main() -> int:
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    for command in ("show", "history", "content"):
        sub = commands.add_parser(command)
        sub.add_argument("--scope", type=Path, required=True)
        if command == "history":
            sub.add_argument("--limit", type=limit_value, default=100)
            sub.add_argument("--after-sequence", type=cursor_value, default=0)
        else:
            sub.add_argument("--execution-digest", required=True)
        if command == "content":
            sub.add_argument("--output", type=Path, required=True)
    try:
        args = parser.parse_args()
        if args.command == "init":
            build_planned_execution_archive(configured_dsn()).initialize()
            payload = {"capability": "planned_prefix_archive/v1", "initialized": True}
        else:
            if args.command != "history":
                execution_key(args.execution_digest)
            scope = scope_file(args.scope)
            if args.command == "history":
                history_bounds(scope, args.limit, args.after_sequence)
            reader = build_planned_execution_archive_reader(configured_dsn())
            if args.command == "show":
                payload = reader.show(scope, args.execution_digest).as_dict()
            elif args.command == "history":
                page = reader.history(scope, limit=args.limit, after_sequence=args.after_sequence)
                payload = {
                    "receipts": [execution_archive_receipt_payload(r) for r in page.receipts],
                    "has_more": page.has_more,
                    "next_after_sequence": page.next_after_sequence,
                }
            else:
                content = reader.content(scope, args.execution_digest)
                export_content(args.output, content)
                payload = {
                    "execution_digest": args.execution_digest,
                    "content_hash": sha256(content).hexdigest(),
                    "byte_length": len(content),
                    "output": str(args.output),
                }
    except SemanticContractError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
