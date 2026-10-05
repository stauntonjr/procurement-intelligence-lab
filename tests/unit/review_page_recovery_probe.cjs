// Unit simulation of the shipped event wiring. This is not a real browser.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2],'utf8'),script=html.split('<script nonce="{{nonce}}">')[1].split('</script>')[0];
class Element {constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.attributes={};this.listeners={};this.fields={};this.elements={token:{focus(){}}};this.value='';}append(...nodes){this.children.push(...nodes);for(const n of nodes)if(n&&typeof n==='object')n.parent=this;}prepend(...nodes){this.children.unshift(...nodes);for(const n of nodes)if(n&&typeof n==='object')n.parent=this;}replaceChildren(...nodes){this.children=[];this.append(...nodes);}addEventListener(kind,fn){this.listeners[kind]=fn;}setAttribute(name,value){this.attributes[name]=String(value);}getAttribute(name){return this.attributes[name];}focus(){this.focused=true;}reset(){this.fields={};}remove(){if(this.parent)this.parent.children=this.parent.children.filter(node=>node!==this);}querySelectorAll(selector){const descendants=[];const visit=node=>{for(const child of node.children||[]){if(child&&typeof child==='object'){descendants.push(child);visit(child);}}};visit(this);if(selector==='[data-candidate]')return descendants.filter(n=>n.dataset.candidate==='true');if(selector==='input')return descendants.filter(n=>n.tag==='input');throw Error('unexpected selector '+selector);}}
const ids=new Map(),all=[],stack=[];
for(const match of html.split('<script')[0].matchAll(/<(\/?)(\w+)([^>]*)>/g)){const [_,close,tag,attrs]=match;if(close){stack.pop();continue;}const node=new Element(tag);node.hidden=/\bhidden(?:\s|$)/.test(attrs);if(stack.length)stack.at(-1).append(node);all.push(node);const id=attrs.match(/\bid="([^"]+)"/);if(id)ids.set(id[1],node);if(!['input','meta','br','hr','link'].includes(tag))stack.push(node);}
const document={getElementById(id){assert(ids.has(id),'missing control '+id);return ids.get(id);},createElement(tag){const n=new Element(tag);all.push(n);return n;},querySelectorAll(selector){if(selector==='button')return all.filter(n=>n.tag==='button');throw Error('unexpected selector '+selector);},querySelector(selector){if(selector==='input[name="resolution"]:checked')return all.find(n=>n.tag==='input'&&n.name==='resolution'&&n.checked)||null;throw Error('unexpected selector '+selector);}};
class FormData {constructor(form){this.data={...form.fields};}get(name){return this.data[name];}[Symbol.iterator](){return Object.entries(this.data)[Symbol.iterator]();}}
const view={run_id:'recoverable-run',status:'awaiting_review',execution_kind:'fixture',saved:null,brief:{brief_id:'brief',version:1,digest:'exact-digest',item:'GPU-C',as_of:'2026-10-01T00:00:00Z',run:{versions:{}},snapshot_id:'snap',content_json:JSON.stringify({status:'not_assessed',required_quantity:null,ordered_quantity:null,evidence:[]})}};
const defect=process.argv[3],live=process.argv[4]==='live',calls=[];let failed=false,release;
async function fetch(path){calls.push(path);let ok=true,data;
if(path==='/api/runs')data={project:'atlas',execution_kind:'fixture',runs:[]};
else if(path==='/api/start'||path==='/api/ask'){
 if(failed){ok=false;data={error:'Injected unavailable',code:'pil.transient.probe'};if(defect.startsWith('success_')){ok=true;const corrupt=defect==='success_shape'?{run_id:'foreign-run'}:{...view,run_id:'foreign-run',brief:{...view.brief,content_json:'PRIVATE_RESPONSE_FRAGMENT'}};data=live?{interpretation:{run_id:'foreign-run',status:'investigate'},workflow:corrupt}:corrupt;}}
 else data=live?{interpretation:{run_id:view.run_id,status:'investigate'},workflow:view}:view;
 if(defect==='json'){ok=false;data={error:'PRIVATE_RESPONSE_FRAGMENT',code:'untrusted_reply'};}
 if(defect==='malformed')return {ok:false,json:async()=>{throw Error('PRIVATE_RESPONSE_FRAGMENT');}};
}else if(path.startsWith('/api/events?')){if(defect==='lock')await new Promise(resolve=>release=resolve);data={events:[]};}
else throw Error('unexpected public path');return {ok,json:async()=>data};}
const context={document,URLSearchParams,FormData,fetch};vm.createContext(context);vm.runInContext(script,context);
async function settle(){for(let i=0;i<40;i++)await Promise.resolve();}
(async()=>{
 const auth=ids.get('auth');auth.fields.token='public-test-only-capability';auth.listeners.submit({preventDefault(){},target:auth});await settle();
 const form=ids.get('investigate');form.fields=live?{question:'Compare GPU-A',as_of:'2026-10-01T00:00:00Z'}:{item:'GPU-A',as_of:'2026-10-01T00:00:00Z'};
 form.listeners.submit({preventDefault(){},target:form});await settle();
 if(defect==='retain'||defect.startsWith('success_')){
  failed=true;form.fields=live?{question:'Compare GPU-C',as_of:'2026-10-01T00:00:00Z'}:{item:'GPU-C',as_of:'2026-10-01T00:00:00Z'};
  form.listeners.submit({preventDefault(){},target:form});await settle();
  assert(!ids.get('error').hidden);assert(!ids.get('error').textContent.includes('PRIVATE_RESPONSE_FRAGMENT'),'private response fragment exposed');assert(!ids.get('review').hidden,'failed replacement erased exact draft');assert.equal(vm.runInContext('current.run_id',context),view.run_id,'malformed success replaced exact draft');assert.equal(vm.runInContext('selectedRun',context),view.run_id,'malformed success changed selected run');
  assert.equal(ids.get('recover').disabled,false,'failed replacement erased recovery');assert(ids.get('identity').textContent.includes('brief'));assert.equal(ids.get('approve').disabled,false);
 }else if(defect==='malformed'||defect==='json'){
  assert(!ids.get('error').hidden);assert(!ids.get('error').textContent.includes('PRIVATE_RESPONSE_FRAGMENT'),'private response fragment exposed');assert.equal(ids.get('approve').disabled,true);
 }else{
  assert(release,'event response must actually be pending');ids.get('logout').listeners.click();const before=calls.length;release();await settle();
  assert.equal(calls.length,before,'locked callback issued a new request');assert(ids.get('workspace').hidden);assert.equal(ids.get('approve').disabled,true);
 }
 console.log('public deterministic page oracle passed: '+defect+'; no browser/model quality claim');
})().catch(error=>{console.error(error);process.exitCode=1;});
