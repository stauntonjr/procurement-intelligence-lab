"""Packaged local fixture reviewer page; no third-party scripts or credential storage."""

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Procurement review workflow</title>
<style nonce="{{nonce}}">
:root{font-family:system-ui;color:#17304a;background:#f3f6fa}body{max-width:1100px;margin:2rem auto;padding:0 1rem}h1{margin-bottom:.5rem}h2{font-size:1.2rem}section{background:white;border:1px solid #c6d3e0;border-radius:12px;padding:1.2rem;margin:1rem 0}label{display:block;margin:.7rem 0}input,button,select{font:inherit;padding:.6rem;border:1px solid #768ca3;border-radius:5px}button{cursor:pointer;background:#123f66;color:white}button:disabled{background:#607386;cursor:default}button.secondary{background:white;color:#17304a}input{max-width:100%;box-sizing:border-box}input:focus,button:focus,summary:focus,a:focus{outline:3px solid #946200;outline-offset:3px}.badge{display:inline-block;background:#e6eef8;padding:.4rem .7rem;border-radius:5px}.layout{display:grid;grid-template-columns:1fr 2fr;gap:1rem}.facts{font-size:1.3rem;background:#e9f1f8;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:25rem;overflow:auto}code,#digest,#identity,#selected-run,#saved{overflow-wrap:anywhere}li{margin:.7rem 0}table{border-collapse:collapse;width:100%;display:block;overflow:auto}th,td{text-align:left;border:1px solid #c6d3e0;padding:.5rem}td.highlight{background:#fff0b9;box-shadow:inset 0 0 0 2px #b76e00}.evidence-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.7rem;padding:0;list-style:none}.evidence-card{width:100%;min-height:4.5rem;text-align:left;background:#f7f9fc;color:#17304a;border:2px solid #9aafc1}.evidence-card[aria-pressed="true"]{background:#fff4cf;border-color:#946200;box-shadow:0 0 0 3px #f4cf72}.source-note{font-weight:650;color:#6d4900}.authority-card{border-left:5px solid #946200;background:#fff8e6;padding:.8rem 1rem}.authority-card p{margin:.35rem 0}#source{min-height:5rem}#error{color:#8b1824;background:#fff2f2;padding:.8rem}#status{min-height:1.5rem}[hidden]{display:none!important}@media(max-width:800px){.layout{display:block}}.muted{color:#435a72}
</style></head><body>
<h1>Evidence-backed procurement review</h1><p class="badge">Fixture execution · synthetic development corpus · no model calls</p>
<p>Compare governed requirements with recorded procurement activity, inspect the source evidence, and record an explicit scoped reconciliation decision.</p>
<section id="login"><h2>Local reviewer sign-in</h2><form id="auth" method="post" action="/auth-unavailable"><label>Local reviewer token <input name="token" type="password" autocomplete="off" required minlength="32" size="48"></label><button>Unlock review</button></form><p class="muted">Token stays in this page’s memory. Reloading requires sign-in. Loopback development access only.</p></section>
<p id="status" role="status" aria-live="polite">Sign in to inspect persisted review runs.</p><p id="error" role="alert" hidden></p>
<div id="workspace" hidden><button id="logout" class="secondary">Lock review</button><p id="scope"></p>
<div class="layout"><div><section><h2>Check procurement evidence</h2><form id="investigate"><label>Item to review <input name="item" value="GPU-A" required maxlength="100" id="request-input"></label><label>Evidence available through <input name="as_of" value="2026-10-01T00:00:00Z" required size="28"></label><button>Check for discrepancies</button></form><p class="muted">Compares governing requirements with recorded procurement activity using evidence available through this time.</p></section>
<details><summary>Prior investigations and recovery</summary><button id="refresh" class="secondary">Refresh investigations</button><ul id="runs"></ul><section id="run-controls" hidden><p id="selected-run"></p><button id="recover" class="secondary">Recover investigation</button></section></details></div>
<div><section id="review" hidden><h2 id="review-title" tabindex="-1">Discrepancy assessment</h2><p id="outcome" class="facts"></p>
<h2>Source evidence</h2><p class="muted">Select a cited document to inspect the admitted source and highlighted supporting cells.</p><ul id="evidence" class="evidence-grid"></ul><h3>Relevant source detail</h3><div id="source"></div>
<h2>Resolve or review</h2><p id="resolution-effect">A governing choice applies prospectively to this item, project, and site. Historical state is unchanged.</p><fieldset id="resolution"><label><input type="radio" name="resolution" value="keep_unresolved" data-action-label="Keep this item unresolved"> Keep this item unresolved</label><label><input type="radio" name="resolution" value="assessment_needs_correction" data-action-label="Record assessment correction"> Assessment needs correction</label></fieldset><label>Required rationale <textarea id="rationale" maxlength="2000"></textarea></label><button id="reconcile" disabled>Choose a reconciliation outcome</button><button id="approve" hidden></button><button id="reject" hidden></button><p id="saved"></p>
<details><summary>Technical details</summary><p id="identity"></p><p id="digest"></p><pre id="facts"></pre><pre id="versions"></pre></details></section>
<section><h2>Application execution timeline</h2><p class="muted">Persisted tool outcomes, separate from domain evidence provenance. Snapshot feed; no hidden reasoning or model stream.</p><ol id="events"></ol></section></div></div></div>
<section><h2>Trust boundary</h2><p>Authenticated human → scoped application → admitted corpus tools → deterministic brief → exact review receipt → idempotent saved result.</p><p class="muted">Optional LangGraph checkpoints coordinate execution. Application records own review and save authority. This local fixture prototype is not a production procurement system or a representation of Scale AI’s internal architecture. Live-model and deployed-browser acceptance remain separate gates.</p></section>
<script nonce="{{nonce}}">
const $=id=>document.getElementById(id);let token='',current=null,selectedRun=null,busy=false,epoch=0,evidenceButtons=[];
function message(text,error=false){$('status').textContent=error?'Operation unavailable. You can refresh history or recover the selected run.':text;$('error').hidden=!error;$('error').textContent=error?text:'';}
function enabled(){document.querySelectorAll('button').forEach(b=>{if(b.id!=='logout')b.disabled=busy||b.dataset.incompatible==='true';});$('approve').disabled=busy||!current||current.status==='rejected';$('reject').disabled=busy||!current||current.status!=='awaiting_review';$('recover').disabled=busy||!selectedRun;const choice=document.querySelector('input[name="resolution"]:checked');$('reconcile').textContent=choice?choice.dataset.actionLabel:'Choose a reconciliation outcome';$('reconcile').disabled=busy||!current||!choice||!$('rationale').value.trim();}
function clear(){current=null;selectedRun=null;evidenceButtons=[];$('run-controls').hidden=true;$('review').hidden=true;$('evidence').replaceChildren();$('source').replaceChildren();$('source').textContent='';$('events').replaceChildren();enabled();}
function selectRun(run){selectedRun=run;$('run-controls').hidden=false;$('selected-run').textContent=run;enabled();}
function pageFailure(text){const error=Error(text);error.pageSafe=true;return error;}
async function safeResponse(response){try{const result=await response.json();if(!result||typeof result!=='object'||Array.isArray(result))throw Error();return result;}catch{throw pageFailure('The server response could not be read. Refresh history or recover the selected run.');}}
async function api(path,data){let response;try{response=await fetch(path,{method:data?'POST':'GET',headers:{Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json'}:{})},...(data?{body:JSON.stringify(data)}:{}),cache:'no-store',redirect:'error'});}catch{throw pageFailure('The response was not received. Refresh history or recover the selected run before repeating an operation.');}const result=await safeResponse(response);if(!response.ok){const messages={401:'Authenticate with the local reviewer token.',403:'Request is outside the authorized local boundary.',404:'Run, item or evidence was not found in this review scope.',409:'Review conflicts with the exact brief, current evidence or run configuration.',422:'Supply exactly the documented fields and a timezone-aware cutoff.',503:'Workflow or admitted evidence is unavailable. Refresh or recover the run.'};throw pageFailure(messages[response.status]??'The server response is unavailable. Refresh history or recover the selected run.');}return result;}
async function action(work){if(busy)return;busy=true;enabled();const version=epoch;try{await work(version);}catch(error){if(version===epoch)message(error.pageSafe?error.message:'The server response could not be read. Refresh history or recover the selected run.',true);}finally{if(version===epoch){busy=false;enabled();}}}
async function history(version){if(version!==epoch)return;const data=await api('/api/runs');if(version!==epoch)return;$('scope').textContent='Authenticated local reviewer · project '+data.project+' · '+data.execution_kind;$('runs').replaceChildren();if(!data.runs.length){const li=document.createElement('li');li.textContent='No owned runs yet.';$('runs').append(li);}for(const run of data.runs){const li=document.createElement('li'),button=document.createElement('button');button.className='secondary';button.textContent=run.created_at+' · '+run.run_id.slice(0,8)+(run.compatible?'':' · incompatible version');button.dataset.incompatible=String(!run.compatible);button.disabled=!run.compatible;button.addEventListener('click',()=>action(async v=>{clear();selectRun(run.run_id);message('Loading persisted run…');const view=await api('/api/run?'+new URLSearchParams({run_id:run.run_id}));if(v!==epoch)return;await render(view);await timeline(v);if(v!==epoch)return;message('Persisted run loaded. Recover or review this finding.');}));li.append(button);$('runs').append(li);}}
function preparedView(view){try{const object=x=>x&&typeof x==='object'&&!Array.isArray(x),text=x=>typeof x==='string'&&x.length>0;if(!object(view)||!text(view.run_id)||!text(view.status)||!text(view.execution_kind)||!object(view.brief))throw Error();const brief=view.brief;if(!['brief_id','digest','item','as_of','snapshot_id','content_json'].every(k=>text(brief[k]))||!Number.isInteger(brief.version)||brief.version<1||!object(brief.run)||!object(brief.run.versions))throw Error();const facts=JSON.parse(brief.content_json);if(!object(facts)||!text(facts.status)||!Array.isArray(facts.evidence)||!facts.evidence.every(ref=>object(ref)&&text(ref.evidence_id)&&text(ref.artifact_id)))throw Error();const saved=view.saved;if(saved!==null&&(!object(saved)||!text(saved.saved_id)||!text(saved.saved_at)))throw Error();return {brief,facts};}catch{throw pageFailure('The server response could not be read. Refresh history or recover the selected run.');}}
async function selectEvidence(button,ref,view,version){const run=view.run_id;const source=await api('/api/source?'+new URLSearchParams({run_id:run,evidence_id:ref.evidence_id}));if(version!==epoch||!current||current.run_id!==run)return;renderSource(source);evidenceButtons.forEach(candidate=>candidate.setAttribute('aria-pressed',String(candidate===button)));message('Original admitted source loaded.');}
async function renderEvidence(view,facts){$('source').replaceChildren();$('source').textContent='';$('evidence').replaceChildren();evidenceButtons=[];if(!facts.evidence.length){$('source').textContent='No cited evidence is available for this assessment.';return;}for(const ref of facts.evidence){const li=document.createElement('li'),button=document.createElement('button');button.className='evidence-card';button.textContent=ref.artifact_id+' · '+(ref.row?'row '+ref.row:'authority '+ref.record_key);button.setAttribute('aria-pressed','false');button.addEventListener('click',()=>action(v=>selectEvidence(button,ref,view,v)));evidenceButtons.push(button);li.append(button);$('evidence').append(li);}await selectEvidence(evidenceButtons[0],facts.evidence[0],view,epoch);}
function renderResolution(facts){const box=$('resolution');box.querySelectorAll('[data-candidate]').forEach(node=>node.remove());const eligible=(facts.governance_candidates||[]).filter(item=>item.eligible);if(eligible.length===2)for(const item of eligible){const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name='resolution';input.value='select_governing_revision';input.dataset.claimId=item.claim_id;input.dataset.actionLabel='Use revision '+item.revision_id+' prospectively';input.addEventListener('change',enabled);label.dataset.candidate='true';label.append(input,' Use revision '+item.revision_id+' — '+item.value+' '+item.unit+' for this item');box.prepend(label);}box.querySelectorAll('input').forEach(input=>input.addEventListener('change',enabled));}
async function render(view){const {brief,facts}=preparedView(view);current=view;$('events').replaceChildren();selectRun(view.run_id);$('review').hidden=false;const required=facts.required_quantity??'cannot be determined';const ordered=facts.ordered_quantity??'not recorded';$('outcome').textContent='Required quantity: '+required+(facts.unit?' '+facts.unit:'')+'. Order observation: '+ordered+(facts.unit?' '+facts.unit:'')+'. Assessment: '+facts.status+(facts.reason?' ('+facts.reason.replaceAll('_',' ')+').':'.');renderResolution(facts);$('identity').textContent='Investigation '+view.run_id+' · '+view.status+' · assessment '+brief.brief_id+' · version '+brief.version+' · '+brief.item+' as of '+brief.as_of;$('digest').textContent='Verified assessment version: '+brief.digest;$('saved').textContent=view.saved?'Reviewed assessment '+view.saved.saved_id+' · '+view.saved.saved_at:'';$('facts').textContent=JSON.stringify(facts,null,2);$('versions').textContent=JSON.stringify({versions:brief.run.versions,snapshot_id:brief.snapshot_id,execution_kind:view.execution_kind},null,2);await renderEvidence(view,facts);enabled();$('review-title').focus();}
function renderSource(source){$('source').replaceChildren();$('source').textContent='';if(source.cells){const note=document.createElement('p');note.className='source-note';note.textContent='Highlighted cells support this assessment.';const table=document.createElement('table'),header=document.createElement('tr'),row=document.createElement('tr');source.headers.forEach((label,i)=>{const th=document.createElement('th');th.scope='col';th.textContent=label;header.append(th);const td=document.createElement('td');td.textContent=source.cells[i];if(source.highlighted_columns.includes(String.fromCharCode(65+i)))td.className='highlight';row.append(td);});table.append(header,row);$('source').append(note,table);}if(source.authority){const card=document.createElement('div'),heading=document.createElement('h3'),role=document.createElement('p'),approved=document.createElement('p');card.className='authority-card';heading.textContent='Governing authority record';role.textContent='Document role: '+(source.authority.document?.role??'recorded authority');approved.textContent='Approved or effective: '+(source.authority.record?.approved_at??source.authority.record?.effective_from??'recorded in source');card.append(heading,role,approved);$('source').append(card);}const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Complete source record';pre.textContent=JSON.stringify(source.authority??source.evidence,null,2);details.append(summary,pre);$('source').append(details);}
async function timeline(version){if(version!==epoch||!current)return;const run=current.run_id;const data=await api('/api/events?'+new URLSearchParams({run_id:run}));if(version!==epoch||!current||current.run_id!==run)return;$('events').replaceChildren();for(const e of data.events){const li=document.createElement('li');li.textContent=e.occurred_at+' · '+e.kind+(e.tool_name?' · '+e.tool_name:'')+(e.error_code?' · '+e.error_code:'');$('events').append(li);}}
$('auth').addEventListener('submit',event=>{event.preventDefault();if(busy)return;token=String(new FormData(event.target).get('token'));event.target.reset();action(async v=>{await history(v);if(v!==epoch)return;$('login').hidden=true;$('workspace').hidden=false;message('Authenticated. Start an investigation or recover a persisted run.');$('request-input').focus();});});
$('logout').addEventListener('click',()=>{++epoch;token='';busy=false;clear();$('runs').replaceChildren();$('workspace').hidden=true;$('login').hidden=false;message('Review locked. Sign in again.');$('auth').elements.token.focus();});
$('investigate').addEventListener('submit',event=>{event.preventDefault();const fields=Object.fromEntries(new FormData(event.target));action(async v=>{message('Executing scoped corpus tools…');const view=await api('/api/start',fields);if(v!==epoch)return;await render(view);await timeline(v);await history(v);if(v!==epoch)return;message('Finding persisted. Inspect its evidence before reviewing.');});});
$('refresh').addEventListener('click',()=>action(async v=>{await history(v);if(current)await timeline(v);if(v!==epoch)return;message('Owned history and application events refreshed.');}));
$('recover').addEventListener('click',()=>action(async v=>{const view=await api('/api/recover',{run_id:selectedRun});if(v!==epoch)return;await render(view);await timeline(v);if(v!==epoch)return;message('Durable workflow recovered. No duplicate result created.');}));
for(const decision of ['approve','reject'])$(decision).addEventListener('click',()=>action(async v=>{const brief=current.brief;const view=await api('/api/review',{run_id:current.run_id,brief_id:brief.brief_id,digest:brief.digest,decision});if(v!==epoch)return;await render(view);await timeline(v);if(v!==epoch)return;message(view.status==='completed'?'Finding saved. Repeated approval acknowledges the same result.':'Finding rejected. No result saved.');}));
$('rationale').addEventListener('input',enabled);$('reconcile').addEventListener('click',()=>action(async v=>{const choice=document.querySelector('input[name="resolution"]:checked'),brief=current.brief;const result=await api('/api/reconcile',{run_id:current.run_id,brief_id:brief.brief_id,digest:brief.digest,outcome:choice.value,selected_claim_id:choice.dataset.claimId||'',rationale:$('rationale').value.trim()});if(v!==epoch)return;$('saved').textContent='Reconciliation decision '+result.decision.decision_id+' effective '+result.decision.effective_at;$('outcome').textContent='Current assessment: '+result.current_assessment.status+' | Required: '+(result.current_assessment.required_quantity??'unresolved')+' | Order observation: '+(result.current_assessment.ordered_quantity??'not recorded');message('Reconciliation decision saved for this item, project, and site. Historical state is unchanged.');}));
</script></body></html>"""


def live_html() -> str:
    """Same exact-review controls with explicit model interpretation and abstention."""
    page = HTML.replace(
        "Fixture execution · synthetic development corpus · no model calls",
        "Local Qwen 3.6 inference · synthetic development corpus",
    )
    page = page.replace(
        'Item to review <input name="item" value="GPU-A" required maxlength="100"',
        'Procurement question <input name="question" value="Compare GPU-A with its governing requirement" required maxlength="1000" size="40"',
    )
    page = page.replace(
        "Compares governing requirements with recorded procurement activity using evidence available through this time.",
        "Interprets one procurement question, then compares admitted governing requirements with recorded activity.",
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
        "async function render(view)",
        "async function renderOutcome(outcome){const call=outcome.interpretation;if(!call||typeof call!=='object'||Array.isArray(call)||typeof call.run_id!=='string'||!call.run_id||!['investigate','clarify','unsupported','failed'].includes(call.status)||!Object.hasOwn(outcome,'workflow')||(outcome.workflow?call.status!=='investigate'||outcome.workflow.run_id!==call.run_id:call.status==='investigate'))throw pageFailure('The server response could not be read. Refresh history or recover the selected run.');if(outcome.workflow)preparedView(outcome.workflow);$('interpretation').textContent=JSON.stringify(call,null,2);if(outcome.workflow){await render(outcome.workflow);return true;}clear();$('interpretation').textContent=JSON.stringify(outcome.interpretation,null,2);selectRun(outcome.interpretation.run_id);$('review').hidden=true;enabled();message('Interpretation '+outcome.interpretation.status+' · '+outcome.interpretation.reason+'. No finding or approval available.');return false;}\nasync function render(view)",
    )
    page = page.replace(
        "const view=await api('/api/start',fields);if(v!==epoch)return;await render(view);",
        "const outcome=await api('/api/ask',fields);if(v!==epoch)return;const hasBrief=await renderOutcome(outcome);await history(v);if(!hasBrief)return;",
    )
    page = page.replace(
        "const view=await api('/api/run?'", "const outcome=await api('/api/interpretation?'"
    )
    page = page.replace(
        "if(v!==epoch)return;await render(view);await timeline(v);if(v!==epoch)return;message('Persisted run loaded.",
        "if(v!==epoch)return;if(!await renderOutcome(outcome))return;await timeline(v);if(v!==epoch)return;message('Persisted run loaded.",
    )
    page = page.replace(
        "const view=await api('/api/recover',{run_id:selectedRun});if(v!==epoch)return;await render(view);",
        "const outcome=await api('/api/recover',{run_id:selectedRun});if(v!==epoch)return;if(!await renderOutcome(outcome))return;",
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


def original_html(page: str, sources: str) -> str:
    """Server-configured original source context; never derive it from model output."""
    if sources not in ("showcase-a-order", "showcase-a-b-order", "showcase-a-only"):
        raise ValueError("unsupported original sources")
    import re

    page = re.sub(
        r"Compares governing requirements with recorded procurement activity using evidence available through this time\.</p>",
        "Original GPU-A XLSX sources: " + sources + ". Fixed January 15 cutoff. "
        "Order observation is recorded source data; not_assessed does not mean reconciled.</p>",
        page,
        count=1,
    )
    return (
        page.replace(
            "</style>",
            "#evidence button{max-width:100%;overflow-wrap:anywhere}</style>",
            1,
        )
        .replace("2026-10-01T00:00:00Z", "2026-01-15T00:00:00Z")
        .replace("Assessed ordered: ", "Order observation: ")
        .replace("synthetic development corpus", "original synthetic XLSX snapshot")
    )
