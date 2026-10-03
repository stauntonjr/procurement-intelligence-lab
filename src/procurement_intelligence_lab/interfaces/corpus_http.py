"""Corpus HTTP boundary and visible composition root for the synthetic demo."""

import json
from datetime import datetime
from urllib.parse import urlencode

from procurement_intelligence_lab.adapters.synthetic_corpus import SyntheticCorpusReader
from procurement_intelligence_lab.application.corpus_investigation import (
    CorpusInvestigationService,
    InvestigationRequest,
)
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)
from procurement_intelligence_lab.ports.corpus import (
    CorpusAdmissionError,
    CorpusNotFoundError,
    CorpusSourceRecord,
)

_HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Corpus investigation</title>
<style>body{font:17px system-ui;max-width:1000px;margin:3rem auto;padding:0 1rem;color:#17304a}label{display:block;margin:1rem 0}input,select,button{font:inherit;padding:.5rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf3f8;padding:1rem}li{margin:.4rem}a{color:#0758aa}#sources{display:grid;grid-template-columns:1fr 1fr;gap:.4rem}#comparison{font-size:1.35rem;padding:1rem;background:#edf3f8;border-radius:8px}pre{max-height:22rem;overflow:auto}details{margin:1rem 0}table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{text-align:left;padding:.6rem;border-bottom:1px solid #cad6e2}[hidden]{display:none!important}@media(max-width:650px){#sources{grid-template-columns:1fr}}</style>
<h1>Procurement corpus investigation</h1><p>Synthetic development corpus: one project, six workbooks, 240 source-row occurrences. Deterministic policy; no model calls.</p>
<a href="/">Legacy evidence inspector</a>
<form id="investigation"><label>Project <select name="project"><option value="atlas">Atlas</option></select></label>
<label>Canonical item <input name="item" value="GPU-A" required></label>
<label>As of (ISO 8601 with timezone) <input name="as_of" value="2026-10-01T00:00:00+00:00" size="32" required></label>
<button>Investigate</button></form>
<p>Try GPU-A (mismatch), GPU-B (agreement), GPU-C (conflicting requirements), GPU-D (missing observation), GPU-F (fractional), or GPU-G (zero).</p>
<p id="status" role="status"></p><p id="comparison" hidden></p><details><summary>Inspect the complete audit response</summary><pre id="result" hidden></pre></details><h2>Quantity and authority evidence</h2><ul id="sources"></ul><h2>Original source</h2><table id="cells" hidden></table><pre id="source">Select a quantity or authority reference.</pre>
<script>
const form=document.querySelector('form'),status=document.querySelector('#status'),result=document.querySelector('#result'),sources=document.querySelector('#sources'),source=document.querySelector('#source');
const comparison=document.querySelector('#comparison'),cells=document.querySelector('#cells');
let queryVersion=0,sourceVersion=0;
function renderCells(data){cells.replaceChildren();cells.hidden=!data.cells;if(!data.cells)return;for(const values of [data.headers,data.cells]){const row=document.createElement('tr');for(const value of values){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}cells.append(row);}}
form.addEventListener('submit',async event=>{event.preventDefault();const version=++queryVersion;++sourceVersion;status.textContent='Investigating…';result.hidden=true;comparison.hidden=true;cells.hidden=true;sources.replaceChildren();source.textContent='Select a quantity or authority reference.';
try{const response=await fetch('/api/corpus/investigate?'+new URLSearchParams(new FormData(form)));const data=await response.json();if(version!==queryVersion)return;if(!response.ok)throw Error(data.error);status.textContent=data.status+(data.reason?' — '+data.reason:'');comparison.textContent='Required: '+(data.required_quantity??'unresolved')+' · Assessed ordered: '+(data.ordered_quantity??'not established')+(data.unit?' '+data.unit:'');comparison.hidden=false;result.textContent=JSON.stringify(data,null,2);result.hidden=false;
for(const ref of data.evidence){const li=document.createElement('li'),a=document.createElement('a');a.href=ref.url;a.textContent=ref.artifact_id+' · '+(ref.row?'row '+ref.row:'authority record '+ref.record_key);a.addEventListener('click',async e=>{e.preventDefault();const clicked=++sourceVersion;cells.hidden=true;source.textContent='Loading original source…';try{const r=await fetch(a.href),d=await r.json();if(clicked!==sourceVersion||version!==queryVersion)return;if(!r.ok)throw Error(d.error);renderCells(d);source.textContent=JSON.stringify(d.authority??d.evidence,null,2);}catch(err){if(clicked!==sourceVersion||version!==queryVersion)return;source.textContent='Source unavailable: '+err.message;}});li.append(a);sources.append(li);}}
catch(err){if(version!==queryVersion)return;status.textContent='Investigation unavailable: '+err.message;}});
</script></html>"""


def corpus_response(path: str, query: dict[str, list[str]]) -> tuple[int, str, bytes]:
    if path == "/corpus":
        return 200, "text/html; charset=utf-8", _HTML.encode()
    try:
        allowed = (
            {"project", "item", "as_of"}
            if path.endswith("/investigate")
            else {"project", "evidence_id"}
        )
        if set(query) != allowed or any(len(v) != 1 or not v[0] for v in query.values()):
            raise ValueError("provide each required query parameter exactly once")
        if query["project"][0] != "atlas":
            raise ScopeAuthorizationError("project is not authorized for this demo")
        context = RequestContext(
            "public-synthetic-demo",
            "synthetic-tenant",
            "atlas",
            "lab",
            frozenset({Permission.READ_STATE, Permission.READ_EVIDENCE}),
            "corpus-http",
        )
        reader = SyntheticCorpusReader()
        if path.endswith("/investigate"):
            result = CorpusInvestigationService(reader).investigate(
                InvestigationRequest(query["item"][0], datetime.fromisoformat(query["as_of"][0])),
                context=context,
            )
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
                "evidence": [
                    ref.as_dict()
                    | {
                        "url": "/api/corpus/source?"
                        + urlencode({"project": context.project_id, "evidence_id": ref.evidence_id})
                    }
                    for ref in result.evidence
                ],
            }
        else:
            identifier = query["evidence_id"][0]
            inventory = reader.inventory(context=context)
            ref = next(
                (
                    ref
                    for fact in inventory.facts
                    for ref in (fact.evidence, fact.authority)
                    if ref.evidence_id == identifier
                ),
                None,
            )
            if ref is None:
                raise CorpusNotFoundError("evidence not found in admitted scope")
            source = reader.source(ref, context=context)
            data = {"evidence": ref.as_dict()}
            if isinstance(source, CorpusSourceRecord):
                data["authority"] = json.loads(source.record_json)
            else:
                data.update(
                    {
                        "headers": source.headers,
                        "cells": source.cells,
                        "highlighted_columns": source.highlighted_columns,
                    }
                )
        return 200, "application/json", json.dumps(data).encode()
    except ScopeAuthorizationError:
        status = 403
    except CorpusNotFoundError:
        status = 404
    except CorpusAdmissionError:
        status = 503
    except ValueError:
        status = 422
    # Python clears the exception variable at the end of an except clause.
    return (
        status,
        "application/json",
        json.dumps(
            {"error": _MESSAGES[status], "code": _CODES[status], "category": _CATEGORIES[status]}
        ).encode(),
    )


_MESSAGES = {
    403: "project is not authorized for this demo",
    404: "item or evidence not found in admitted scope",
    422: "invalid or repeated query parameter; supply item and timezone-aware as_of",
    503: "admitted corpus source validation failed",
}

_CODES = {
    403: "forbidden_scope",
    404: "not_found",
    422: "invalid_request",
    503: "corpus_admission_failed",
}

_CATEGORIES = {403: "authorization", 404: "input", 422: "input", 503: "infrastructure"}
