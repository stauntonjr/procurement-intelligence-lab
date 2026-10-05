"""HTTP link decoration over validated application-owned result payloads."""

from urllib.parse import urlencode

from procurement_intelligence_lab.application.corpus_investigation import InvestigationResult
from procurement_intelligence_lab.application.corpus_payloads import (
    investigation_payload,
    source_payload,
)
from procurement_intelligence_lab.platform.semantics.scope import RequestContext
from procurement_intelligence_lab.ports.corpus import CorpusSourceRecord, CorpusSourceRow


def investigation_dto(result: InvestigationResult, context: RequestContext) -> dict[str, object]:
    data = investigation_payload(result, context)
    data["evidence"] = [
        ref.as_dict()
        | {
            "url": "/api/corpus/source?"
            + urlencode({"project": context.project_id, "evidence_id": ref.evidence_id})
        }
        for ref in result.evidence
    ]
    return data


def source_dto(source: CorpusSourceRow | CorpusSourceRecord) -> dict[str, object]:
    return source_payload(source)
