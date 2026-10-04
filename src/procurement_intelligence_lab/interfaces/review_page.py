"""Packaged local fixture reviewer page; no third-party scripts or credential storage."""

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Procurement review workflow</title>
<style nonce="{{nonce}}">
:root{font-family:system-ui;color:#17304a;background:#f3f6fa}body{max-width:1100px;margin:2rem auto;padding:0 1rem}h1{margin-bottom:.5rem}h2{font-size:1.2rem}section{background:white;border:1px solid #c6d3e0;border-radius:12px;padding:1.2rem;margin:1rem 0}label{display:block;margin:.7rem 0}input,button,select{font:inherit;padding:.6rem;border:1px solid #768ca3;border-radius:5px}button{cursor:pointer;background:#123f66;color:white}button:disabled{background:#607386;cursor:default}button.secondary{background:white;color:#17304a}input{max-width:100%;box-sizing:border-box}input:focus,button:focus,summary:focus,a:focus{outline:3px solid #e3a122;outline-offset:3px}.badge{display:inline-block;background:#e6eef8;padding:.4rem .7rem;border-radius:5px}.layout{display:grid;grid-template-columns:1fr 2fr;gap:1rem}.facts{font-size:1.3rem;background:#e9f1f8;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:25rem;overflow:auto}code{overflow-wrap:anywhere}li{margin:.7rem 0}table{border-collapse:collapse;width:100%;display:block;overflow:auto}th,td{text-align:left;border:1px solid #c6d3e0;padding:.5rem}td.highlight{background:#fff0b9}#error{color:#8b1824;background:#fff2f2;padding:.8rem}#status{min-height:1.5rem}[hidden]{display:none!important}@media(max-width:800px){.layout{display:block}}.muted{color:#435a72}
</style></head><body>
<h1>Evidence-backed procurement review</h1><p class="badge">Fixture execution · synthetic development corpus · no model calls</p>
<p>Independent interview reference demo. Deterministic policies own quantities and decisions. Approving saves a demo brief; it does not resolve source conflicts or submit an order.</p>
<section id="login"><h2>Local reviewer sign-in</h2><form id="auth" method="post" action="/auth-unavailable"><label>Local reviewer token <input name="token" type="password" autocomplete="off" required minlength="32" size="48"></label><button>Unlock review</button></form><p class="muted">Token stays in this page’s memory. Reloading requires sign-in. Loopback development access only.</p></section>
<p id="status" role="status" aria-live="polite">Sign in to inspect persisted review runs.</p><p id="error" role="alert" hidden></p>
<div id="workspace" hidden><button id="logout" class="secondary">Lock review</button><p id="scope"></p>
<div class="layout"><div><section><h2>Start an investigation</h2><form id="investigate"><label>Canonical item <input name="item" value="GPU-A" required maxlength="100"></label><label>As of (ISO 8601 with timezone) <input name="as_of" value="2026-10-01T00:00:00Z" required size="28"></label><button>Investigate and draft</button></form><p class="muted">Atlas examples: GPU-A mismatch, GPU-C unresolved requirement, GPU-D missing observation. Typed requests only.</p></section>
<section><h2>Recent owned runs</h2><button id="refresh" class="secondary">Refresh history</button><p class="muted">Newest 50 application records. Select a run, then recover after a restart.</p><ul id="runs"></ul></section></div>
<div><section id="run-controls" hidden><h2>Selected persisted run</h2><p id="selected-run"></p><button id="recover" class="secondary">Recover selected run</button></section><section id="review" hidden><h2 id="review-title" tabindex="-1">Exact persisted brief</h2><p id="outcome" class="facts"></p><p id="identity"></p><p id="digest"></p><p id="saved"></p>
<button id="approve">Approve exact brief</button> <button id="reject" class="secondary">Reject exact brief</button>
<details><summary>Complete immutable facts and policy evidence</summary><pre id="facts"></pre></details><details><summary>Run versions and snapshot</summary><pre id="versions"></pre></details>
<h2>Evidence provenance</h2><ul id="evidence"></ul><h2>Original source cells or authority record</h2><div id="source"></div></section>
<section><h2>Application execution timeline</h2><p class="muted">Persisted tool outcomes, separate from domain evidence provenance. Snapshot feed; no hidden reasoning or model stream.</p><ol id="events"></ol></section></div></div></div>
<section><h2>Trust boundary</h2><p>Authenticated human → scoped application → admitted corpus tools → deterministic brief → exact review receipt → idempotent saved result.</p><p class="muted">Optional LangGraph checkpoints coordinate execution. Application records own review and save authority. This local fixture prototype is not a production procurement system or a representation of Scale AI’s internal architecture. Live-model and deployed-browser acceptance remain separate gates.</p></section>
<script nonce="{{nonce}}">
const $=id=>document.getElementById(id);let token='',current=null,selectedRun=null,busy=false,epoch=0;
function message(text,error=false){$('status').textContent=error?'Operation unavailable. You can refresh history or recover the selected run.':text;$('error').hidden=!error;$('error').textContent=error?text:'';}
function enabled(){document.querySelectorAll('button').forEach(b=>{if(b.id!=='logout')b.disabled=busy||b.dataset.incompatible==='true';});$('approve').disabled=busy||!current||current.status==='rejected';$('reject').disabled=busy||!current||current.status!=='awaiting_review';$('recover').disabled=busy||!selectedRun;}
function clear(){current=null;selectedRun=null;$('run-controls').hidden=true;$('review').hidden=true;$('evidence').replaceChildren();$('source').replaceChildren();$('events').replaceChildren();enabled();}
function selectRun(run){selectedRun=run;$('run-controls').hidden=false;$('selected-run').textContent=run;enabled();}
async function api(path,data){const response=await fetch(path,{method:data?'POST':'GET',headers:{Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json'}:{})},...(data?{body:JSON.stringify(data)}:{}),cache:'no-store',redirect:'error'});const result=await response.json();if(!response.ok)throw Error(result.error+' ['+result.code+']');return result;}
async function action(work){if(busy)return;busy=true;enabled();const version=epoch;try{await work(version);}catch(error){if(version===epoch)message(error.message,true);}finally{if(version===epoch){busy=false;enabled();}}}
async function history(version){const data=await api('/api/runs');if(version!==epoch)return;$('scope').textContent='Authenticated local reviewer · project '+data.project+' · '+data.execution_kind;$('runs').replaceChildren();if(!data.runs.length){const li=document.createElement('li');li.textContent='No owned runs yet.';$('runs').append(li);}for(const run of data.runs){const li=document.createElement('li'),button=document.createElement('button');button.className='secondary';button.textContent=run.created_at+' · '+run.run_id.slice(0,8)+(run.compatible?'':' · incompatible version');button.dataset.incompatible=String(!run.compatible);button.disabled=!run.compatible;button.addEventListener('click',()=>action(async v=>{clear();selectRun(run.run_id);message('Loading persisted run…');const view=await api('/api/run?'+new URLSearchParams({run_id:run.run_id}));if(v!==epoch)return;render(view);await timeline(v);if(v!==epoch)return;message('Persisted run loaded. Recover or review the exact brief.');}));li.append(button);$('runs').append(li);}}
function render(view){current=view;selectRun(view.run_id);const brief=view.brief,facts=JSON.parse(brief.content_json);$('review').hidden=false;$('outcome').textContent=facts.status+(facts.reason?' · '+facts.reason:'')+' | Required: '+(facts.required_quantity??'unresolved')+' | Assessed ordered: '+(facts.ordered_quantity??'not established')+(facts.unit?' '+facts.unit:'');$('identity').textContent='Run '+view.run_id+' · '+view.status+' · brief '+brief.brief_id+' · version '+brief.version+' · '+brief.item+' as of '+brief.as_of;$('digest').textContent='Exact brief SHA-256: '+brief.digest;$('saved').textContent=view.saved?'Saved result '+view.saved.saved_id+' · '+view.saved.saved_at:'No saved result.';$('facts').textContent=JSON.stringify(facts,null,2);$('versions').textContent=JSON.stringify({versions:brief.run.versions,snapshot_id:brief.snapshot_id,execution_kind:view.execution_kind},null,2);$('source').replaceChildren();$('evidence').replaceChildren();for(const ref of facts.evidence){const li=document.createElement('li'),button=document.createElement('button');button.className='secondary';button.textContent=ref.artifact_id+' · '+(ref.row?'row '+ref.row:'authority '+ref.record_key);button.addEventListener('click',()=>action(async v=>{const run=view.run_id;const source=await api('/api/source?'+new URLSearchParams({run_id:run,evidence_id:ref.evidence_id}));if(v!==epoch||!current||current.run_id!==run)return;renderSource(source);message('Original admitted source loaded.');}));li.append(button);$('evidence').append(li);}enabled();$('review-title').focus();}
function renderSource(source){$('source').replaceChildren();if(source.cells){const table=document.createElement('table'),header=document.createElement('tr'),row=document.createElement('tr');source.headers.forEach((label,i)=>{const th=document.createElement('th');th.scope='col';th.textContent=label;header.append(th);const td=document.createElement('td');td.textContent=source.cells[i];if(source.highlighted_columns.includes(String.fromCharCode(65+i)))td.className='highlight';row.append(td);});table.append(header,row);$('source').append(table);}const pre=document.createElement('pre');pre.textContent=JSON.stringify(source.authority??source.evidence,null,2);$('source').append(pre);}
async function timeline(version){if(!current)return;const run=current.run_id;const data=await api('/api/events?'+new URLSearchParams({run_id:run}));if(version!==epoch||!current||current.run_id!==run)return;$('events').replaceChildren();for(const e of data.events){const li=document.createElement('li');li.textContent=e.occurred_at+' · '+e.kind+(e.tool_name?' · '+e.tool_name:'')+(e.error_code?' · '+e.error_code:'');$('events').append(li);}}
$('auth').addEventListener('submit',event=>{event.preventDefault();if(busy)return;token=String(new FormData(event.target).get('token'));event.target.reset();action(async v=>{await history(v);if(v!==epoch)return;$('login').hidden=true;$('workspace').hidden=false;message('Authenticated. Start an investigation or recover a persisted run.');});});
$('logout').addEventListener('click',()=>{++epoch;token='';busy=false;clear();$('runs').replaceChildren();$('workspace').hidden=true;$('login').hidden=false;message('Review locked. Sign in again.');$('auth').elements.token.focus();});
$('investigate').addEventListener('submit',event=>{event.preventDefault();const fields=Object.fromEntries(new FormData(event.target));action(async v=>{clear();message('Executing scoped corpus tools…');const view=await api('/api/start',fields);if(v!==epoch)return;render(view);await timeline(v);await history(v);if(v!==epoch)return;message('Draft persisted. Inspect its evidence before reviewing.');});});
$('refresh').addEventListener('click',()=>action(async v=>{await history(v);if(current)await timeline(v);if(v!==epoch)return;message('Owned history and application events refreshed.');}));
$('recover').addEventListener('click',()=>action(async v=>{const view=await api('/api/recover',{run_id:selectedRun});if(v!==epoch)return;render(view);await timeline(v);if(v!==epoch)return;message('Durable workflow recovered. No duplicate result created.');}));
for(const decision of ['approve','reject'])$(decision).addEventListener('click',()=>action(async v=>{const brief=current.brief;const view=await api('/api/review',{run_id:current.run_id,brief_id:brief.brief_id,digest:brief.digest,decision});if(v!==epoch)return;render(view);await timeline(v);if(v!==epoch)return;message(view.status==='completed'?'Exact brief saved. Repeated approval acknowledges the same result.':'Brief rejected. No result saved.');}));
</script></body></html>"""


def live_html() -> str:
    """Same exact-review controls with explicit model interpretation and abstention."""
    page = HTML.replace(
        "Fixture execution · synthetic development corpus · no model calls",
        "Local Qwen 3.6 inference · synthetic development corpus",
    )
    page = page.replace(
        'Canonical item <input name="item" value="GPU-A" required maxlength="100"',
        'Question <input name="question" value="Compare GPU-A with its governing requirement" required maxlength="1000" size="40"',
    )
    page = page.replace(
        "Typed requests only.",
        "One bounded model interpretation; quantities come from admitted evidence.",
    )
    page = page.replace("This local fixture prototype", "This local inference prototype")
    page = page.replace(
        "Live-model and deployed-browser acceptance remain separate gates.",
        "Live acceptance reports and deployed-browser acceptance remain separate gates.",
    )
    page = page.replace(
        "<h2>Application execution timeline</h2>",
        '<h2>Model interpretation</h2><pre id="interpretation"></pre><h2>Application execution timeline</h2>',
    )
    page = page.replace(
        "function render(view)",
        "function renderOutcome(outcome){$('interpretation').textContent=JSON.stringify(outcome.interpretation,null,2);if(outcome.workflow){render(outcome.workflow);return true;}current=null;selectRun(outcome.interpretation.run_id);$('review').hidden=true;enabled();message('Interpretation '+outcome.interpretation.status+' · '+outcome.interpretation.reason+'. No brief or approval available.');return false;}\nfunction render(view)",
    )
    page = page.replace(
        "const view=await api('/api/start',fields);if(v!==epoch)return;render(view);",
        "const outcome=await api('/api/ask',fields);if(v!==epoch)return;const hasBrief=renderOutcome(outcome);await history(v);if(!hasBrief)return;",
    )
    page = page.replace(
        "const view=await api('/api/run?'", "const outcome=await api('/api/interpretation?'"
    )
    page = page.replace(
        "if(v!==epoch)return;render(view);await timeline(v);if(v!==epoch)return;message('Persisted run loaded.",
        "if(v!==epoch)return;if(!renderOutcome(outcome))return;await timeline(v);if(v!==epoch)return;message('Persisted run loaded.",
    )
    page = page.replace(
        "const view=await api('/api/recover',{run_id:selectedRun});if(v!==epoch)return;render(view);",
        "const outcome=await api('/api/recover',{run_id:selectedRun});if(v!==epoch)return;if(!renderOutcome(outcome))return;",
    )
    page = page.replace(
        "message('Executing scoped corpus tools…')",
        "message('Interpreting with local Qwen, then executing scoped tools…')",
    )
    page = page.replace(
        "$('events').replaceChildren();enabled();}",
        "$('events').replaceChildren();$('interpretation').textContent='';enabled();}",
    )
    return page
