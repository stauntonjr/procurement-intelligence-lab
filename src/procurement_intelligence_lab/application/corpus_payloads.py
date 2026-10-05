"""Serializable application payloads validated before audited tool completion."""

import json

from procurement_intelligence_lab.application.corpus_investigation import InvestigationResult
from procurement_intelligence_lab.platform.semantics.scope import RequestContext
from procurement_intelligence_lab.ports.corpus import CorpusSourceRecord, CorpusSourceRow


def investigation_payload(
    result: InvestigationResult, context: RequestContext
) -> dict[str, object]:
    decision = result.governed.decision
    data: dict[str, object] = {
        "project": context.project_id,
        "item": decision.canonical_key,
        "as_of": decision.as_of.isoformat(),
        "snapshot_id": result.snapshot_id,
        "ordered_quantity": str(result.ordered_quantity)
        if result.ordered_quantity is not None
        else None,
        "governance_policy_id": decision.policy_id,
        "governance_decision_id": decision.decision_id,
        "evidence_by_role": {
            role: [ref.evidence_id for ref in refs]
            for role, refs in result.assessment.evidence_by_role
        },
        "assessment_id": result.assessment.assessment_id,
        "status": result.assessment.status.value,
        "reason": result.assessment.reason.value if result.assessment.reason else None,
        "required_quantity": str(result.governed.expected.required_quantity)
        if result.governed.expected
        else None,
        "unit": decision.unit,
        "governance_status": decision.status.value,
        "governance_dispositions": dict(decision.dispositions),
        "input_dispositions": dict(result.assessment.input_dispositions),
        "policy_id": result.assessment.policy_id,
        "policy_digest": result.assessment.policy_digest,
        "evidence": [ref.as_dict() for ref in result.evidence],
    }
    return data


def source_payload(source: CorpusSourceRow | CorpusSourceRecord) -> dict[str, object]:
    data: dict[str, object] = {"evidence": source.evidence.as_dict()}
    if isinstance(source, CorpusSourceRecord):
        authority = json.loads(source.record_json)
        if not isinstance(authority, dict):
            raise TypeError("authority record must be a JSON object")
        data["authority"] = authority
    else:
        data.update(
            {
                "headers": source.headers,
                "cells": source.cells,
                "highlighted_columns": source.highlighted_columns,
            }
        )
    return data
