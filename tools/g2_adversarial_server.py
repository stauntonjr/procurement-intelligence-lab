"""Evaluator-only faults around an unchanged installed public reviewer; never packaged."""

import argparse
import json
import os
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from procurement_intelligence_lab.application.exact_brief_review import BriefReviewService
from procurement_intelligence_lab.interfaces.review_web import create_server, read_token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--flag", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--project", default="atlas")
    parser.add_argument(
        "--fault",
        choices=(
            "none",
            "tool_timeout",
            "expired_approval",
            "changed_snapshot",
            "review_crash_scope",
        ),
        default="none",
    )
    args = parser.parse_args()
    web = create_server(
        args.database,
        project=args.project,
        token=read_token(args.token_file),
        port=0,
        model_endpoint=args.endpoint,
    )
    service = web.composition.service
    if args.fault in ("tool_timeout", "changed_snapshot"):
        original = service.tools.investigator

        class InjectedInvestigator:
            def investigate(self, request: Any, *, context: Any) -> Any:
                if args.flag.exists() and args.fault == "tool_timeout":
                    raise TimeoutError("PRIVATE_INJECTED_TOOL_ERROR")
                result = original.investigate(request, context=context)
                if args.flag.exists():
                    return replace(result, snapshot_id="injected_changed_snapshot")
                return result

        service.tools = replace(service.tools, investigator=InjectedInvestigator())
    elif args.fault == "expired_approval":
        flagged_calls = 0

        def clock() -> datetime:
            nonlocal flagged_calls
            now = datetime.now(UTC)
            if args.flag.exists():
                flagged_calls += 1
                if flagged_calls > 1:
                    return now + timedelta(hours=2)
            return now

        service.clock = clock
    elif args.fault == "review_crash_scope":
        original_save = BriefReviewService.save

        def crashing_save(self: BriefReviewService, *fields: Any, **kwargs: Any) -> Any:
            saved = original_save(self, *fields, **kwargs)
            if args.flag.exists():
                os._exit(86)  # real death after durable save, before graph acknowledgment
            return saved

        BriefReviewService.save = crashing_save  # type: ignore[method-assign]
    print(
        json.dumps({"port": web.server_port, "versions": asdict(web.composition.runs.versions)}),
        flush=True,
    )
    try:
        web.serve_forever()
    finally:
        web.server_close()


if __name__ == "__main__":
    main()
