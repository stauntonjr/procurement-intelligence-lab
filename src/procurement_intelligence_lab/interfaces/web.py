"""Dependency-free chat and evidence-inspector HTTP adapter."""

from __future__ import annotations

import json
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from procurement_intelligence_lab.adapters.xlsx import read_bom
from procurement_intelligence_lab.application.chat import (
    UnsupportedQuestionError,
    answer_question,
)
from procurement_intelligence_lab.application.review import review_context_for_claim

_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Procurement Evidence Inspector</title>
<style>
body{font:16px system-ui;margin:0;background:#f6f7fb;color:#17223b}main{max-width:1000px;margin:auto;padding:32px}
h1{font:42px Georgia;margin:12px 0}p{color:#68738a}.chat,.panel{background:white;border:1px solid #dce1ea;border-radius:14px;padding:22px;margin-top:24px}
form{display:flex;gap:10px}input{flex:1;padding:13px;border:1px solid #ccd3df;border-radius:8px}button{padding:13px 18px;border:0;border-radius:8px;background:#285ea7;color:white}
#answer{margin-top:20px;white-space:pre-wrap}.trace{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.stage{padding:12px;background:#eef4ff;border-radius:8px}.stage small{display:block;color:#68738a;margin-top:5px}
@media(max-width:700px){.trace{grid-template-columns:1fr 1fr}h1{font-size:34px}}
</style></head><body><main><p>PROCUREMENT INTELLIGENCE LAB · READ-ONLY INVESTIGATION</p>
<h1>Every answer has a trail.</h1><p>Ask an approved BOM question. The answer is computed deterministically and remains linked to its source evidence.</p>
<section class="chat"><form><input name="q" value="How many GPUs are in the BOM?" aria-label="Question"><button>Ask</button></form><div id="answer"></div></section>
<section class="panel"><p>EXECUTION TRACE</p><div class="trace" id="trace"><div class="stage">Source assertions</div><div class="stage">Entity resolution</div><div class="stage">Operational state</div><div class="stage">Reconciliation</div></div></section>
<script>
const form=document.querySelector("form"),answer=document.querySelector("#answer"),trace=document.querySelector("#trace");
form.addEventListener("submit",async event=>{event.preventDefault();const q=new URLSearchParams(new FormData(form));const response=await fetch("/api/ask?"+q);const data=await response.json();if(!response.ok){answer.textContent=data.error;return}answer.textContent=JSON.stringify(data,null,2);trace.innerHTML=data.execution_trace.nodes.map(n=>'<div class="stage"><b>'+n.label+'</b><small>'+n.status+'</small></div>').join("")});
</script></main></body></html>"""


class EvidenceNotFoundError(LookupError):
    """Raised when an evidence ID is not present in the committed fixture."""


class ReviewContextNotFoundError(LookupError):
    """Raised when a claim ID is not present in the committed fixture."""


def _fixture() -> Path:
    return Path(__file__).resolve().parents[3] / "examples" / "synthetic_bom.xlsx"


def claim_payload(question: str) -> dict[str, object]:
    bom = read_bom(_fixture())
    claim = answer_question(question, bom, tuple(line.sku for line in bom.lines))
    value = str(claim.value) if isinstance(claim.value, Decimal) else claim.value
    return {
        "question": question,
        "claim": claim.kind,
        "claim_id": claim.claim_id,
        "value": value,
        "status": claim.status,
        "evidence": [{**ref.__dict__, "evidence_id": ref.evidence_id} for ref in claim.evidence],
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


def source_payload(evidence_id: str) -> dict[str, object]:
    bom = read_bom(_fixture())
    for line in bom.lines:
        evidence = line.evidence
        if evidence.evidence_id == evidence_id:
            return {
                "evidence": {**evidence.__dict__, "evidence_id": evidence.evidence_id},
                "line": {
                    "sku": line.sku,
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price) if line.unit_price is not None else None,
                    "status": line.status,
                },
            }
    raise EvidenceNotFoundError(f"unknown evidence ID: {evidence_id}")


def review_context_payload(claim_id: str) -> dict[str, object]:
    bom = read_bom(_fixture())
    try:
        context = review_context_for_claim(
            claim_id, bom, tuple(line.sku for line in bom.lines)
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
        if parsed.path == "/":
            body = _HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif parsed.path == "/api/ask":
            question = parse_qs(parsed.query).get("q", [""])[0]
            try:
                body = json.dumps(claim_payload(question)).encode()
                self.send_response(200)
            except UnsupportedQuestionError as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(422)
            self.send_header("Content-Type", "application/json")
        elif parsed.path == "/api/source":
            evidence_id = parse_qs(parsed.query).get("evidence_id", [""])[0]
            try:
                body = json.dumps(source_payload(evidence_id)).encode()
                self.send_response(200)
            except EvidenceNotFoundError as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(404)
            self.send_header("Content-Type", "application/json")
        elif parsed.path == "/api/review-context":
            claim_id = parse_qs(parsed.query).get("claim_id", [""])[0]
            try:
                body = json.dumps(review_context_payload(claim_id)).encode()
                self.send_response(200)
            except ReviewContextNotFoundError as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(404)
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


if __name__ == "__main__":
    run_server()
