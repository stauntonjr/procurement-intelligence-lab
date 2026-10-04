// Unit simulation of the shipped event wiring. This is not a real browser.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2],'utf8'),script=html.split('<script nonce="{{nonce}}">')[1].split('</script>')[0];
class Element {constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.listeners={};this.fields={};this.elements={token:{focus(){}}};}append(...nodes){this.children.push(...nodes);for(const n of nodes)n.parent=this;}replaceChildren(...nodes){this.children=[];this.append(...nodes);}addEventListener(kind,fn){this.listeners[kind]=fn;}focus(){this.focused=true;}reset(){this.fields={};}}
const ids=new Map(),all=[],stack=[];
for(const match of html.split('<script')[0].matchAll(/<(\/?)(\w+)([^>]*)>/g)){const [_,close,tag,attrs]=match;if(close){stack.pop();continue;}const node=new Element(tag);node.hidden=/\bhidden(?:\s|$)/.test(attrs);if(stack.length)stack.at(-1).append(node);all.push(node);const id=attrs.match(/\bid="([^"]+)"/);if(id)ids.set(id[1],node);if(!['input','meta','br','hr','link'].includes(tag))stack.push(node);}
const document={getElementById(id){assert(ids.has(id),'missing control '+id);return ids.get(id);},createElement(tag){const n=new Element(tag);all.push(n);return n;},querySelectorAll(selector){assert.equal(selector,'button');return all.filter(n=>n.tag==='button');}};
class FormData {constructor(form){this.data={...form.fields};}get(name){return this.data[name];}[Symbol.iterator](){return Object.entries(this.data)[Symbol.iterator]();}}
const view={run_id:'recoverable-run',status:'awaiting_review',execution_kind:'fixture',saved:null,brief:{brief_id:'brief',version:1,digest:'exact-digest',item:'GPU-C',as_of:'2026-10-01T00:00:00Z',run:{versions:{}},snapshot_id:'snap',content_json:JSON.stringify({status:'not_assessed',required_quantity:null,ordered_quantity:null,evidence:[]})}};
const calls=[];async function fetch(path,options){calls.push({path,options});let ok=true,data;if(path==='/api/runs')data={project:'atlas',execution_kind:'fixture',runs:[{run_id:'recoverable-run',created_at:'now',compatible:true}]};else if(path.startsWith('/api/run?')){ok=false;data={error:'No brief yet',code:'workflow_unavailable'};}else if(path==='/api/recover')data=view;else if(path.startsWith('/api/events?'))data={events:[]};else throw Error('unexpected request '+path);return {ok,json:async()=>data};}
const context={document,URLSearchParams,FormData,fetch};vm.createContext(context);vm.runInContext(script,context);
async function settle(){for(let i=0;i<20;i++)await Promise.resolve();}
function visible(node){for(let p=node;p;p=p.parent)if(p.hidden)return false;return true;}
(async()=>{
const auth=ids.get('auth');auth.fields.token='test-only-capability-not-a-real-secret';auth.listeners.submit({preventDefault(){},target:auth});await settle();
const select=ids.get('runs').children[0].children[0];select.listeners.click();await settle();assert(!ids.get('error').hidden,'failed status should be shown');
const recover=ids.get('recover');assert.equal(recover.disabled,false,'a selected persisted run must remain recoverable after failed status');assert(visible(recover),'recovery must be visible without a brief');assert.equal(ids.get('approve').disabled,true,'approval must require a loaded exact brief');
recover.listeners.click();await settle();const call=calls.find(c=>c.path==='/api/recover');assert(call,'recovery should invoke the public endpoint');assert.deepEqual(JSON.parse(call.options.body),{run_id:'recoverable-run'});assert(!ids.get('review').hidden);assert(ids.get('digest').textContent.includes('exact-digest'));assert(ids.get('outcome').textContent.includes('Required: unresolved'));assert(ids.get('outcome').textContent.includes('Assessed ordered: not established'));assert.equal(ids.get('approve').disabled,false);assert(ids.get('review-title').focused);
// Lock removes the selected identity and exact review authority from the page.
ids.get('logout').listeners.click();assert.equal(recover.disabled,true);assert.equal(ids.get('approve').disabled,true);assert(ids.get('workspace').hidden);
console.log('shipped page recovery wiring, exact approval gating and null rendering passed; no browser acceptance claimed');
})().catch(error=>{console.error(error);process.exitCode=1;});
