"""Explicit local Qwen natural-language review CLI; no paid provider fallback."""

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from procurement_intelligence_lab.adapters.local_qwen import (
    MODEL,
    PROMPT,
    SCHEMA,
    LocalQwenInterpreter,
)
from procurement_intelligence_lab.adapters.sqlite_interpretation import SqliteInterpretationStore
from procurement_intelligence_lab.application.question_review import (
    QuestionOutcome,
    QuestionReviewService,
)
from procurement_intelligence_lab.interfaces.review_sources import (
    REVIEW_PROJECTS,
    SOURCE_OPTIONS,
    compose_sources,
)
from procurement_intelligence_lab.interfaces.workflow import (
    WorkflowComposition,
    compose_services,
    view_dto,
)
from procurement_intelligence_lab.platform.semantics.interpretation import ModelFailure
from procurement_intelligence_lab.platform.semantics.scope import Permission, RequestContext
from procurement_intelligence_lab.ports.corpus import CorpusAdmissionError


def compose_live(
    database: Path, endpoint: str = "http://127.0.0.1:8000/v1", *, sources: str = "corpus"
) -> WorkflowComposition:
    config = {
        "prompt": PROMPT,
        "schema": SCHEMA,
        "endpoint": endpoint,
        "model": MODEL,
        "max_tokens": 256,
        "temperature": 0,
        "thinking": False,
        "timeout": 30,
    }
    return compose_services(
        database,
        sources=sources,
        live_prompt="question-review/v1:"
        + sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
    )


def compose_question(
    database: Path, endpoint: str = "http://127.0.0.1:8000/v1", *, sources: str = "corpus"
) -> QuestionReviewService:
    model = LocalQwenInterpreter(endpoint=endpoint)
    return QuestionReviewService(
        compose_live(database, endpoint, sources=sources),
        model,
        SqliteInterpretationStore(database),
    )


def outcome_dto(outcome: QuestionOutcome) -> dict[str, object]:
    return {
        "interpretation": asdict(outcome.call),
        "workflow": view_dto(outcome.view) if outcome.view else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--sources", choices=SOURCE_OPTIONS, default="corpus")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--project", required=True, choices=REVIEW_PROJECTS)
    parser.add_argument("operation", choices=("ask", "recover", "review", "events"))
    for field in ("question", "as-of", "run-id", "brief-id", "digest", "decision"):
        parser.add_argument("--" + field)
    args = parser.parse_args()
    try:
        fields = {"question", "as_of", "run_id", "brief_id", "digest", "decision"}
        required = {
            "ask": {"question", "as_of"},
            "recover": {"run_id"},
            "review": {"run_id", "brief_id", "digest", "decision"},
            "events": {"run_id"},
        }[args.operation]
        if {f for f in fields if getattr(args, f) is not None} != required:
            raise ValueError("provide exactly the operation fields")
        source_config = compose_sources(args.sources)
        if args.project not in source_config.projects:
            raise ValueError("project is not configured for sources")
        context = RequestContext(
            "local-demo",
            "synthetic-tenant",
            args.project,
            source_config.site,
            frozenset(Permission),
            "human-live-cli",
        )
        service = compose_question(args.database, args.endpoint, sources=args.sources)
        if args.operation == "ask":
            result = outcome_dto(
                service.ask(args.question, datetime.fromisoformat(args.as_of), context=context)
            )
        elif args.operation == "recover":
            result = outcome_dto(service.recover(args.run_id, context=context))
        elif args.operation == "review":
            result = view_dto(
                service.composition.runtime.review(
                    args.run_id, args.brief_id, args.digest, args.decision, context=context
                )
            )
        else:
            from procurement_intelligence_lab.platform.semantics.agent_runs import event_dto

            result = {
                "events": [
                    event_dto(e)
                    for e in service.composition.runs.events(args.run_id, context=context)
                ]
            }
        print(
            json.dumps(
                result, default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x)
            )
        )
        return 0
    except CorpusAdmissionError as error:
        result = {"code": error.code, "category": error.category}
    except ModelFailure as error:
        result = {
            "code": error.code.value,
            "category": error.category.value,
            "reason": error.reason,
        }
    except (ValueError, TypeError, RuntimeError, LookupError, PermissionError) as error:
        code = getattr(
            getattr(error, "code", None), "value", "pil.input.semantic_contract_violation"
        )
        category = getattr(getattr(error, "category", None), "value", "input")
        result = {"code": code, "category": category}
    print(json.dumps(result))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
