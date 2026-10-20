"""Initialize and read an explicitly configured local Postgres assertion archive."""

import argparse
import json
import os
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from procurement_intelligence_lab.application.archived_documents import receipt_payload
from procurement_intelligence_lab.bootstrap import build_archive_reader, build_assertion_archive
from procurement_intelligence_lab.interfaces.archive_config import configured_dsn, load_scope
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    SemanticContractError,
)


def export_content(output: Path, content: bytes) -> None:
    temporary: str | None = None
    try:
        with NamedTemporaryFile(dir=output.absolute().parent, delete=False) as file:
            temporary = file.name
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.link(temporary, output)
    except OSError:
        raise ArchiveContractError("content export requires a writable new output path") from None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Explicitly initialize the supported archive schema")
    for command in ("show", "history", "content"):
        sub = commands.add_parser(command)
        sub.add_argument(
            "--scope", type=Path, required=True, help="Exact tenant/project/site/version JSON"
        )
        if command != "history":
            sub.add_argument("--snapshot-id", required=True)
        if command == "content":
            sub.add_argument(
                "--output", type=Path, required=True, help="New output path; never overwrite"
            )
    args = parser.parse_args()
    try:
        dsn = configured_dsn()
        if args.command == "init":
            build_assertion_archive(dsn).initialize()
            payload = {"schema_version": 1, "initialized": True}
        else:
            scope = load_scope(args.scope)
            reader = build_archive_reader(dsn)
            if args.command == "history":
                payload = {"receipts": [receipt_payload(x) for x in reader.archive.history(scope)]}
            elif args.command == "show":
                payload = reader.show(scope, args.snapshot_id).as_dict()
            else:
                content = reader.archive.content(scope, args.snapshot_id)
                export_content(args.output, content)
                payload = {
                    "snapshot_id": args.snapshot_id,
                    "content_hash": sha256(content).hexdigest(),
                    "byte_length": len(content),
                    "output": str(args.output),
                }
    except SemanticContractError as exc:
        print(json.dumps(exc.as_dict()), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
