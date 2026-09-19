"""Dependency-free chat and evidence-inspector HTTP adapter."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import as_file, files
from urllib.parse import parse_qs, urlparse

from procurement_intelligence_lab.adapters.xlsx import read_bom, read_source_row
from procurement_intelligence_lab.application.chat import (
    UnsupportedQuestionError,
    answer_question,
)
from procurement_intelligence_lab.application.review import review_context_for_claim
from procurement_intelligence_lab.application.showcase import (
    ORDER_POLICY,
    ORDER_SCENARIOS,
    ShowcaseScenario,
    showcase_order_comparison,
    showcase_required_quantity,
)
from procurement_intelligence_lab.domains.procurement.bom import Bom
from procurement_intelligence_lab.domains.procurement.governance import (
    GoverningClaim,
    GoverningClaimDecision,
)
from procurement_intelligence_lab.platform.semantics.identity import stable_id
from procurement_intelligence_lab.platform.semantics.scope import (
    Permission,
    RequestContext,
    ScopeAuthorizationError,
)

_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Procurement Evidence Inspector</title>
<style>
:root{color-scheme:light;--ink:#172d34;--muted:#546b72;--line:#d9e2df;--green:#186750;--soft:#edf5ef}
*{box-sizing:border-box}body{margin:0;background:#f4f6f2;color:var(--ink);font:16px/1.5 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:30px 32px 50px}.masthead{display:flex;justify-content:space-between;gap:16px;font-size:12px;font-weight:700;letter-spacing:.1em}.tag{color:var(--green)}h1{font:48px/1.1 Georgia,serif;letter-spacing:-.03em;margin:32px 0 12px}h2{font-size:18px;margin:0 0 14px}p{color:var(--muted);margin:8px 0 18px}.intro{max-width:690px}.panel{background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px}.query{margin:26px 0 20px}label,.eyebrow{display:block;font-size:11px;font-weight:750;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}.input-row{display:flex;gap:10px}input{min-width:0;flex:1;padding:14px;border:1px solid #b6c7c0;border-radius:8px;font:inherit;color:var(--ink)}button{font:inherit;cursor:pointer;border:1px solid var(--line);border-radius:8px;padding:10px 14px;background:#fff;color:var(--ink)}button:hover{background:var(--soft)}button:disabled{cursor:wait;opacity:.65}button.primary{background:var(--green);color:#fff;border-color:var(--green);font-weight:650;padding:12px 22px}button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #c08c28;outline-offset:3px}.examples{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.examples button{font-size:12px;padding:5px 10px;border:0;background:#f1f4f1}.workspace{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}.result-value{font:54px/1.1 Georgia,serif;margin:10px 0;overflow-wrap:anywhere}.status{display:inline-block;background:var(--soft);color:var(--green);font-size:12px;font-weight:700;padding:5px 10px;border-radius:20px}.status.caution{background:#fff3dc;color:#855a10}.evidence-list{display:grid;gap:8px;margin-top:16px}.evidence-button{width:100%;text-align:left;display:flex;justify-content:space-between;gap:10px}.evidence-button[aria-pressed=true]{border-color:var(--green);background:var(--soft)}.small{font-size:13px}.trace{margin-top:20px}.stages{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stage{text-align:left;padding:14px;background:#f8faf7;font-size:13px}.stage small{display:block;color:var(--muted);margin-top:6px}.source-placeholder{min-height:175px;display:flex;flex-direction:column;justify-content:center}.location{font-weight:650;overflow-wrap:anywhere}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px;margin-top:14px}caption{text-align:left;font-size:12px;color:var(--muted);margin-bottom:8px}th,td{padding:10px;text-align:left;border-bottom:1px solid var(--line)}th{font-size:11px;color:var(--muted)}td{background:var(--soft)}details{margin-top:18px;font-size:12px}summary{cursor:pointer;color:var(--muted)}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;overflow:auto}.notice{font-size:14px;min-height:22px;margin:10px 0 0}.notice.error{color:#a13729}.footer{font-size:12px;margin-top:20px} [hidden]{display:none!important}@media(max-width:760px){main{padding:22px 16px}h1{font-size:38px}.workspace{grid-template-columns:1fr}.stages{grid-template-columns:1fr 1fr}.panel{padding:18px}.masthead{font-size:10px}.input-row{flex-direction:column}.result-value{font-size:44px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style><style>select{width:100%;padding:10px;border:1px solid #b6c7c0;border-radius:8px;font:inherit;color:var(--ink);background:#fff}td{background:#fff}.highlight{background:var(--soft);box-shadow:inset 0 0 0 1px #afd0bd}.decision{margin-top:16px;padding:14px;border:1px solid var(--line);border-radius:8px;background:#f8faf7}.decision p{margin:4px 0}</style></head><body><main>
<header class="masthead"><span>PROCUREMENT INTELLIGENCE LAB</span><span class="tag">SYNTHETIC DATA · READ ONLY</span></header>
<h1>Every answer has a trail.</h1><p class="intro">From a BOM question to the source row. Deterministic calculations, visible evidence, and no hidden assumptions.</p>
<section class="panel query" aria-label="Ask a BOM question"><form>
<input type="hidden" name="tenant_id" value="synthetic-tenant"><input type="hidden" name="project_id" value="synthetic-project"><input type="hidden" name="site_id" value="synthetic-site">
<label for="question">Your question</label><div class="input-row"><input id="question" name="q" value="How many GPUs are in the BOM?" required autocomplete="off"><button class="primary" id="ask">Ask</button></div>
<label for="scenario">Evidence scenario</label><select id="scenario" name="scenario"><option value="">Standard synthetic BOM</option><option value="order_mismatch">Compare requirement 4 with order 2</option><option value="order_matched">Compare requirement 4 with order 4</option><option value="order_missing">Order observation missing</option><option value="order_unresolved">Requirement unresolved with order 2</option><option value="conflict">Competing approved revisions: 4 versus 6 GPUs</option><option value="superseded">Explicitly superseded revision: 4 to 6 GPUs</option><option value="shared_value">Competing approved revisions: both 4 GPUs</option><option value="missing_approval">Newer revision lacks approval</option></select>
<div class="examples" aria-label="Example questions"><button type="button" data-question="How many GPUs are in the BOM?">GPU quantity</button><button type="button" data-question="What is the total BOM cost?">BOM cost</button><button type="button" data-question="Which SKUs are in the BOM?">Distinct SKUs</button><button type="button" data-scenario="conflict">Inspect conflict</button></div>
<div id="notice" class="notice" role="status" aria-live="polite">Ready to inspect the synthetic BOM.</div></form></section>
<div class="workspace"><section class="panel" aria-labelledby="answer-heading"><span class="eyebrow">01 / Answer</span><h2 id="answer-heading">A result you can inspect</h2><div id="answer"><p>Ask a question to see the calculated value and its evidence.</p></div><div id="evidence" class="evidence-list"></div></section>
<section class="panel" aria-labelledby="source-heading"><span class="eyebrow">02 / Source evidence</span><h2 id="source-heading">Follow the evidence</h2><div id="source" class="source-placeholder" aria-live="polite"><p>Select a source row beneath the answer to inspect its original cells and references.</p></div></section></div>
<section class="panel trace" aria-labelledby="trace-heading"><span class="eyebrow">03 / Execution trace</span><h2 id="trace-heading">How this claim was produced</h2><p class="small">Select a stage to see its linked source evidence. Stages retain the service's recorded order.</p><div id="trace" class="stages"></div><p id="stage-note" class="small"></p></section>
<details><summary>Inspect the full response</summary><pre id="raw">No query submitted.</pre></details>
<p class="footer">Local architecture demo · Standard BOM questions and policy-backed revision scenarios · No external actions</p>
</main><script>
const form=document.querySelector('form'), question=document.querySelector('#question'), notice=document.querySelector('#notice'), answer=document.querySelector('#answer'), evidenceList=document.querySelector('#evidence'), source=document.querySelector('#source'), trace=document.querySelector('#trace'), raw=document.querySelector('#raw'), stageNote=document.querySelector('#stage-note');
let queryVersion=0, sourceVersion=0;
function element(tag,text,className){
  const node=document.createElement(tag);
  if(text!==undefined)node.textContent=text;
  if(className)node.className=className;
  return node
}
function sourceReset(){
  source.replaceChildren(element('p','Select a source row beneath the answer to inspect its original cells and references.'));
  source.className='source-placeholder'
}
function scopeParams(){
  const params=new URLSearchParams(new FormData(form));
  params.delete('q');
  return params
}
async function request(path,params){
  const response=await fetch(path+'?'+params,{
    cache:'no-store'
  }
  );
  if(!response.ok){
    if(response.status===403)throw new Error('This evidence is not available in the current demo scope.');
    if(response.status===404)throw new Error('The requested evidence is unavailable.');
    if(response.status===422)throw new Error('Try a supported BOM question or select a listed evidence scenario.');
    throw new Error('The service is unavailable. Please try again.')
  }
  return response.json()
}
function displayValue(data){
  if(data.comparison)return data.status==='not_assessed'?'Not assessed':data.status==='matched'?'Quantities match':'Quantity mismatch';
  if(data.value===null||data.value===undefined)return 'Not established';
  if(data.claim==='gpu_quantity')return String(data.value)+' GPUs';
  if(data.claim==='required_quantity')return String(data.value)+' GPUs';
  if(Array.isArray(data.value))return data.value.join(', ')||'No SKUs';
  return String(data.value)
}
function locationText(ref){
  return ref.sheet+' · row '+ref.row+' · '+ref.cells.map(cell=>cell+ref.row).join(', ')
}
function showEvidence(refs,orderIds=null){
  evidenceList.replaceChildren();
  if(!refs.length)evidenceList.append(element('p','No linked source evidence is available.','small'));
  for(const ref of refs){
    const button=element('button',undefined,'evidence-button');
    button.type='button';
    button.setAttribute('aria-pressed','false');
    button.append(element('span',(orderIds===null?'':orderIds.includes(ref.evidence_id)?'Order · ':'Requirement · ')+locationText(ref)),element('span','View →'));
    button.addEventListener('click',()=>openSource(ref,button));
    evidenceList.append(button)
  }
}
async function openSource(ref,button){
  const version=++sourceVersion,current=queryVersion;
  source.className='';
  source.replaceChildren(element('p','Loading source evidence…'));
  for(const other of evidenceList.querySelectorAll('button'))other.setAttribute('aria-pressed',String(other===button));
  try{
    const params=scopeParams();
    params.set('evidence_id',ref.evidence_id);
    const data=await request('/api/source',params);
    if(version!==sourceVersion||current!==queryVersion)return;
    if(data.evidence.evidence_id!==ref.evidence_id)throw new Error('The returned source does not match this evidence reference.');
    const file=data.evidence.artifact_id.split(/[\\/]/).pop();
    source.replaceChildren(element('div',file,'location'),element('p',locationText(data.evidence),'small'));
    const wrap=element('div',undefined,'table-wrap'),table=element('table');
    table.append(element('caption','Original worksheet cells · highlighted cells support this claim'));
    const head=element('thead'),headRow=element('tr'),body=element('tbody'),row=element('tr');
    for(let index=0;index<data.source_grid.headers.length;index++){
      const column=String.fromCharCode('A'.charCodeAt(0)+index);
      const th=element('th',data.source_grid.headers[index]);
      th.scope='col';
      if(data.source_grid.highlighted_columns.includes(column))th.className='highlight';
      headRow.append(th);
      const cell=element('td',data.source_grid.cells[index]);
      if(data.source_grid.highlighted_columns.includes(column))cell.className='highlight';
      row.append(cell)
    }
    head.append(headRow);
    body.append(row);
    table.append(head,body);
    wrap.append(table);
    source.append(wrap,element('p','Source row status: '+data.line.status,'small'));
    const details=element('details');
    details.append(element('summary','Evidence identity'),element('pre',JSON.stringify(data.evidence,null,2)));
    source.append(details)
  }
  catch(error){
    if(version!==sourceVersion||current!==queryVersion)return;
    source.replaceChildren(element('p',error instanceof TypeError?'Could not reach the service. Select the source again to retry.':error.message,'notice error'))
  }
}
function render(data){
  answer.replaceChildren();
  answer.append(element('div',data.status,'status'+(data.status==='reconciled'||data.status==='governed'||data.status==='governed_shared_value'?'':' caution')),element('div',displayValue(data),'result-value'),element('p',data.comparison?'Synthetic required-versus-ordered quantity comparison.':data.claim==='bom_cost'?'BOM cost from recorded quantities and unit prices. Currency is not specified by this fixture.':data.claim==='required_quantity'?'Required GPU quantity under the selected policy and as-of context.':data.claim==='gpu_quantity'?'GPU quantity in the synthetic BOM.':'Distinct canonical identifiers in the synthetic BOM.','small'));
  if(data.value===null&&!data.comparison)answer.append(element('p','The service has not established a value. Inspect the evidence and status.','small'));
  if(data.decision){
    const details=element('div',undefined,'decision');
    details.append(element('p','Policy: '+data.decision.policy_id+' · as of '+data.decision.as_of,'small'));
    if(data.governed_state)details.append(element('p',data.governed_state.expected_quantity===null?'Expected state: not projected while this claim is unresolved.':'Expected state: '+data.governed_state.expected_quantity+' GPUs · '+data.governed_state.basis+' · '+data.governed_state.scope.version,'small'));
    for(const candidate of data.decision.candidates)details.append(element('p',candidate.revision_id+' · '+candidate.value+' '+candidate.unit+' · '+candidate.disposition,'small'));
    answer.append(details)
  }
  if(data.comparison){
    const c=data.comparison;
    answer.append(element('p','Required: '+(c.required_quantity===null?'Not established':c.required_quantity+' each')+' · Ordered: '+(c.ordered_quantity===null?'Not observed':c.ordered_quantity+' each')));
    answer.append(element('p','Comparison policy: '+c.policy_id+' · tolerance '+c.tolerance+' · as of '+c.as_of,'small'));
    if(c.reason)answer.append(element('p',c.reason==='missing_observation'?'No order observation is available; this is not a zero quantity or proof of a missing purchase order.':'The requirement is unresolved; order evidence cannot establish the required quantity.','small'));
  }
  showEvidence(data.evidence,data.comparison?data.comparison.order_evidence_ids:null);
  trace.replaceChildren();
  for(const node of data.execution_trace.nodes){
    const button=element('button',undefined,'stage');
    button.type='button';
    button.append(element('strong',node.label),element('small',node.status));
    button.addEventListener('click',()=>{
      ++sourceVersion;
      sourceReset();
      const ids=new Set(node.evidence_ids);
      showEvidence(data.evidence.filter(ref=>ids.has(ref.evidence_id)),data.comparison?data.comparison.order_evidence_ids:null);
      stageNote.textContent=node.label+' · '+node.status;
      const missing=node.evidence_ids.filter(id=>!data.evidence.some(ref=>ref.evidence_id===id));
      if(missing.length)stageNote.textContent+=' · Some source references are unavailable.'
    }
    );
    trace.append(button)
  }
  raw.textContent=JSON.stringify(data,null,2)
}
form.addEventListener('submit',async event=>{
  event.preventDefault();
  const version=++queryVersion;
  ++sourceVersion;
  sourceReset();
  answer.replaceChildren(element('p','Calculating from the synthetic BOM…'));
  evidenceList.replaceChildren();
  trace.replaceChildren();
  stageNote.textContent='';
  raw.textContent='No current result.';
  notice.className='notice';
  notice.textContent='Calculating…';
  form.setAttribute('aria-busy','true');
  try{
    const data=await request('/api/ask',new URLSearchParams(new FormData(form)));
    if(version!==queryVersion)return;
    render(data);
    notice.textContent='Calculation complete. Select a source row to inspect the evidence.'
  }
  catch(error){
    if(version!==queryVersion)return;
    answer.replaceChildren(element('p','No answer available.'));
    notice.className='notice error';
    notice.textContent=error instanceof TypeError?'Could not reach the service. Please try again.':error.message
  }
  finally{
    if(version===queryVersion)form.removeAttribute('aria-busy')
  }
}
);
for(const button of document.querySelectorAll('[data-question]'))button.addEventListener('click',()=>{
  document.querySelector('#scenario').value='';
  question.value=button.dataset.question;
  form.requestSubmit()
}
);
for(const button of document.querySelectorAll('[data-scenario]'))button.addEventListener('click',()=>{
  document.querySelector('#scenario').value=button.dataset.scenario;
  question.value='How many GPUs are required?';
  form.requestSubmit()
}
);
</script></body></html>"""


_DEMO_SCOPE = ("synthetic-tenant", "synthetic-project", "synthetic-site")
_FIXTURE_RESOURCES = (
    "synthetic_bom.xlsx",
    "showcase_order_short.xlsx",
    "showcase_order_matched.xlsx",
    "showcase_bom_revision_a.xlsx",
    "showcase_bom_revision_b.xlsx",
    "showcase_bom_revision_b_equal.xlsx",
)


class EvidenceNotFoundError(LookupError):
    """Raised when an evidence ID is not present in the committed fixture."""


class ReviewContextNotFoundError(LookupError):
    """Raised when a claim ID is not present in the committed fixture."""


def _read_fixture_bom(resource_name: str = "synthetic_bom.xlsx") -> Bom:
    resource = files("procurement_intelligence_lab.examples").joinpath(resource_name)
    with as_file(resource) as path:
        artifact_id = None if resource_name == "synthetic_bom.xlsx" else f"showcase:{resource_name}"
        return read_bom(path, artifact_id=artifact_id)


def _request_context(
    query: dict[str, list[str]],
    permission: Permission,
) -> RequestContext:
    scope = tuple(query.get(name, [""])[0] for name in ("tenant_id", "project_id", "site_id"))
    if scope != _DEMO_SCOPE:
        raise ScopeAuthorizationError("missing or conflicting synthetic demo scope")
    return RequestContext(
        "demo-user",
        scope[0],
        scope[1],
        scope[2],
        frozenset({permission, Permission.READ_STATE}),
        "http-demo",
    )


def claim_payload(
    question: str,
    *,
    request_context: RequestContext,
    scenario: str | None = None,
) -> dict[str, object]:
    if scenario:
        try:
            parsed_scenario = ShowcaseScenario(scenario)
        except ValueError as error:
            raise UnsupportedQuestionError("unknown showcase scenario") from error
        return _showcase_claim_payload(parsed_scenario, request_context=request_context)
    bom = _read_fixture_bom()
    claim = answer_question(
        question,
        bom,
        tuple(line.sku for line in bom.lines),
        request_context=request_context,
    )
    value = str(claim.value) if isinstance(claim.value, Decimal) else claim.value
    return {
        "question": question,
        "claim": claim.kind,
        "claim_id": claim.claim_id,
        "value": value,
        "status": claim.status,
        "evidence": [ref.as_dict() for ref in claim.evidence],
        "execution_trace": {
            "claim": claim.execution_trace.claim,
            "claim_id": claim.execution_trace.claim_id,
            "chain_id": claim.execution_trace.chain_id,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind,
                    "label": node.label,
                    "status": node.status,
                    "evidence_ids": [ref.evidence_id for ref in node.evidence],
                }
                for node in claim.execution_trace.nodes
            ],
        },
    }


def _showcase_claim_payload(
    scenario: ShowcaseScenario,
    *,
    request_context: RequestContext,
) -> dict[str, object]:
    comparison = (
        showcase_order_comparison(scenario, request_context=request_context)
        if scenario in ORDER_SCENARIOS
        else None
    )
    result = (
        comparison.requirement
        if comparison
        else showcase_required_quantity(scenario, request_context=request_context)
    )
    decision = result.decision
    expected = result.governed_state.expected
    evidence = tuple(item.evidence for item in result.candidates) + (
        comparison.order_evidence if comparison else ()
    )
    claim_id = stable_id(
        "showcase-required-quantity",
        scenario.value,
        decision.status.value,
        decision.value,
        tuple(item.claim_id for item in result.candidates),
    )
    if comparison:
        claim_id = stable_id(
            "order-comparison",
            claim_id,
            ORDER_POLICY.policy_id,
            tuple(ref.evidence_id for ref in evidence),
        )
    nodes = (
        ("source candidates", "observed"),
        ("canonical identity", "fixture-pinned"),
        ("governing policy", decision.policy_id),
        ("reconciliation", decision.status.value),
        ("governed expected state", "projected" if expected is not None else "not projected"),
    )
    trace_nodes: list[dict[str, object]] = [
        {
            "node_id": stable_id("showcase-node", claim_id, label),
            "kind": label.replace(" ", "_"),
            "label": label,
            "status": status,
            "evidence_ids": [item.evidence.evidence_id for item in result.candidates],
        }
        for label, status in nodes
    ]
    payload: dict[str, object] = {
        "question": "Required GPU quantity under the selected discrepancy scenario",
        "claim": "required_quantity",
        "claim_id": claim_id,
        "value": str(decision.value) if decision.value is not None else None,
        "status": decision.status.value,
        "evidence": [ref.as_dict() for ref in evidence],
        "decision": {
            "policy_id": decision.policy_id,
            "as_of": result.as_of.isoformat(),
            "governing_claim_ids": [item.claim_id for item in decision.governing],
            "candidates": [_candidate_payload(item, decision) for item in result.candidates],
        },
        "governed_state": {
            "expected_quantity": str(expected.required_quantity) if expected is not None else None,
            "basis": expected.basis.value if expected is not None else None,
            "scope": {
                "tenant_id": expected.scope.tenant_id,
                "project_id": expected.scope.project_id,
                "site_id": expected.scope.site_id,
                "version": expected.scope.version,
            }
            if expected is not None
            else None,
        },
        "execution_trace": {
            "claim": "order_quantity_comparison" if comparison else "required_quantity",
            "claim_id": claim_id,
            "chain_id": stable_id("showcase-chain", claim_id),
            "nodes": trace_nodes,
        },
    }

    if comparison:
        payload.update(
            {
                "question": "Does the observed order quantity match the governed requirement?",
                "claim": "order_quantity_comparison",
                "status": comparison.status,
                "value": None,
                "comparison": {
                    "required_quantity": str(expected.required_quantity) if expected else None,
                    "ordered_quantity": str(comparison.ordered_quantity)
                    if comparison.ordered_quantity is not None
                    else None,
                    "order_evidence_ids": [ref.evidence_id for ref in comparison.order_evidence],
                    "policy_id": ORDER_POLICY.policy_id,
                    "tolerance": str(ORDER_POLICY.tolerance),
                    "as_of": result.as_of.isoformat(),
                    "reason": comparison.reason,
                    "anomalies": [
                        {
                            "anomaly_id": a.anomaly_id,
                            "kind": a.kind.value,
                            "expected": str(a.expected),
                            "observed": str(a.observed),
                            "severity": a.severity.value,
                            "status": a.status.value,
                            "policy_id": a.policy_id,
                            "provenance_id": a.provenance.provenance_id,
                            "evidence_ids": [ref.evidence_id for ref in a.evidence],
                        }
                        for a in comparison.anomalies
                    ],
                },
            }
        )
        trace_nodes.append(
            {
                "node_id": stable_id("order-comparison", claim_id),
                "kind": "quantity_comparison",
                "label": "Required versus ordered quantity",
                "status": comparison.status,
                "evidence_ids": [ref.evidence_id for ref in evidence],
            }
        )
    return payload


def _candidate_payload(item: GoverningClaim, decision: GoverningClaimDecision) -> dict[str, object]:
    disposition = dict(decision.dispositions)[item.claim_id]
    return {
        "claim_id": item.claim_id,
        "revision_id": item.revision_id,
        "value": str(item.value),
        "unit": item.unit,
        "source_type": item.source_type.value,
        "disposition": disposition,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "effective_from": item.effective_from.isoformat(),
        "effective_until": item.effective_until.isoformat() if item.effective_until else None,
        "document_at": item.document_at.isoformat(),
        "ingested_at": item.ingested_at.isoformat(),
    }


def source_payload(
    evidence_id: str,
    *,
    request_context: RequestContext,
) -> dict[str, object]:
    request_context.require(Permission.READ_EVIDENCE)
    for resource_name in _FIXTURE_RESOURCES:
        bom = _read_fixture_bom(resource_name)
        for line in bom.lines:
            evidence = line.evidence
            if evidence.evidence_id != evidence_id:
                continue
            resource = files("procurement_intelligence_lab.examples").joinpath(resource_name)
            with as_file(resource) as path:
                source_row = read_source_row(path, evidence=evidence)
            return {
                "evidence": evidence.as_dict(),
                "line": {
                    "sku": line.sku,
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price) if line.unit_price is not None else None,
                    "status": line.status,
                },
                "source_grid": {
                    "sheet": source_row.sheet,
                    "row": source_row.row,
                    "headers": list(source_row.headers),
                    "cells": list(source_row.cells),
                    "highlighted_columns": list(source_row.highlighted_columns),
                },
            }
    raise EvidenceNotFoundError(f"unknown evidence ID: {evidence_id}")


def review_context_payload(
    claim_id: str,
    *,
    request_context: RequestContext,
) -> dict[str, object]:
    request_context.require(Permission.REVIEW)
    bom = _read_fixture_bom()
    try:
        context = review_context_for_claim(
            claim_id,
            bom,
            tuple(line.sku for line in bom.lines),
            request_context=request_context,
        )
    except LookupError as error:
        raise ReviewContextNotFoundError(str(error)) from error
    value = (
        str(context.claim_value)
        if isinstance(context.claim_value, Decimal)
        else context.claim_value
    )
    return {
        "claim_id": context.claim_id,
        "claim_kind": context.claim_kind,
        "claim_value": value,
        "claim_status": context.claim_status,
        "evidence_ids": context.evidence_ids,
        "chain_id": context.chain_id,
        "node_ids": context.node_ids,
        "allowed_reasons": [reason.value for reason in context.allowed_reasons],
    }


class InspectorHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/":
            body = _HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif parsed.path == "/healthz":
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif parsed.path == "/api/ask":
            question = query.get("q", [""])[0]
            scenario = query.get("scenario", [""])[0] or None
            try:
                body = json.dumps(
                    claim_payload(
                        question,
                        request_context=_request_context(query, Permission.READ_STATE),
                        scenario=scenario,
                    )
                ).encode()
                self.send_response(200)
            except (UnsupportedQuestionError, ScopeAuthorizationError) as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(422 if isinstance(error, UnsupportedQuestionError) else 403)
            self.send_header("Content-Type", "application/json")
        elif parsed.path == "/api/source":
            evidence_id = query.get("evidence_id", [""])[0]
            try:
                body = json.dumps(
                    source_payload(
                        evidence_id,
                        request_context=_request_context(query, Permission.READ_EVIDENCE),
                    )
                ).encode()
                self.send_response(200)
            except (EvidenceNotFoundError, ScopeAuthorizationError) as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(404 if isinstance(error, EvidenceNotFoundError) else 403)
            self.send_header("Content-Type", "application/json")
        elif parsed.path == "/api/review-context":
            claim_id = query.get("claim_id", [""])[0]
            try:
                body = json.dumps(
                    review_context_payload(
                        claim_id,
                        request_context=_request_context(query, Permission.REVIEW),
                    )
                ).encode()
                self.send_response(200)
            except (ReviewContextNotFoundError, ScopeAuthorizationError) as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(404 if isinstance(error, ReviewContextNotFoundError) else 403)
            self.send_header("Content-Type", "application/json")
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    ThreadingHTTPServer((host, port), InspectorHandler).serve_forever()


def main() -> None:
    parser = ArgumentParser(description="Run the Procurement Evidence Inspector HTTP server.")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Interface to bind (default: %(default)s)."
    )
    parser.add_argument(
        "--port", default=8000, type=int, help="TCP port to bind (default: %(default)s)."
    )
    arguments = parser.parse_args()
    run_server(host=arguments.host, port=arguments.port)


if __name__ == "__main__":
    main()
