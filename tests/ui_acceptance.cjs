// Synthetic source fixtures; real local HTTP API, persistence, DOM and application JS.
const {JSDOM,VirtualConsole}=require('jsdom');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const server=spawn(process.env.PYTHON||'python',[path.join(__dirname,'serve_fixture.py')],{cwd:root,stdio:['ignore','pipe','pipe']});
let logs='';server.stderr.on('data',x=>logs+=x);
const errors=[];let dom;
const wait=async(fn)=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,30));}throw Error('Timed out: '+fn.toString()+' '+logs)};
async function open(){const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 dom=await JSDOM.fromURL('http://127.0.0.1:8765/',{resources:'usable',runScripts:'dangerously',virtualConsole:vc,beforeParse(w){w.fetch=(url,options)=>fetch(new URL(url,w.location.href),options);w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};}});
 await wait(()=>dom.window.document.getElementById('active').textContent==='آماده');return dom.window;}
(async()=>{
 await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{if(d.toString().includes('ACCEPTANCE_READY'))resolve()});server.on('exit',code=>reject(Error('Server exited '+code+' '+logs)))});
 let w=await open(),d=w.document;const set=(id,v)=>d.getElementById(id).value=v;
 set('hours',12);set('capital',0);set('skills','dashboard');set('targetCountries','Iran, UAE');set('maxResults',2);set('maxAge',90);await w.saveProfile();
 set('feedName','Acceptance fixture (synthetic)');set('feedUrl','https://fixture.example/feed');await w.addFeed();
 assert.equal(d.querySelectorAll('[data-select-source]').length,1);
 set('topic','dashboard');set('sector','retail');set('businessModel','service');set('sourceMode','feeds');
 await w.post('/mission-draft',w.missionForm());dom.window.close();w=await open();d=w.document;
 assert.equal(d.getElementById('topic').value,'dashboard');assert.equal(d.getElementById('sourceMode').value,'feeds');assert.equal(d.getElementById('capital').value,'0');assert.equal(d.getElementById('maxAge').value,'90');assert.equal(d.querySelector('[data-select-source]').checked,true);
 await w.startScan();await w.poll();await wait(()=>d.querySelectorAll('tr[data-lead-id]').length===2);
 d.getElementById('rankSort').value='market';w.renderRun();assert.ok(d.querySelector('tr[data-lead-id]').textContent.includes('customer request'));
 const checked=[...d.querySelectorAll('[data-lead]')];checked.forEach(x=>x.checked=true);w.compareSelected();assert.equal(d.getElementById('screenDetail').open,true);assert.ok(d.getElementById('screenContent').textContent.includes('screening-2.1'));
 d.getElementById('dateFilter').value='unknown';w.renderRun();assert.equal(d.querySelectorAll('tr[data-lead-id]').length,1);assert.ok(d.querySelector('tr[data-lead-id]').textContent.includes('supplier'));
 d.getElementById('dateFilter').value='all';w.renderRun();
 const leadIds=[...d.querySelectorAll('tr[data-lead-id]')].map(x=>x.dataset.leadId);
 for(const [index,id] of leadIds.entries()){const answers=[index===0?'5':'1','Explicit synthetic acceptance review'];w.prompt=()=>answers.shift();await w.labelPriority(id)}
 w.showCalibration();assert.ok(d.getElementById('screenContent').textContent.includes('insufficient_comparable_labels'));assert.ok(d.getElementById('screenContent').textContent.includes('user_self_reported'));
 const research=await w.post('/research',{run_id:w.current().id,selected:[leadIds[0]]});
 const reportResponse=await fetch('http://127.0.0.1:8765/report/'+research.analyses[0].id);assert.equal(reportResponse.status,200);const reportHTML=await reportResponse.text();
 const reportDom=new JSDOM(reportHTML,{runScripts:'dangerously'});const reportDoc=reportDom.window.document;reportDoc.querySelector('[data-tab="economics"]').click();assert.equal(reportDoc.querySelector('[data-view="economics"]').hidden,false);assert.equal(reportDoc.querySelector('[data-view="summary"]').hidden,true);reportDom.window.close();
 const sourceId=d.querySelector('[data-select-source]').dataset.selectSource;await w.post('/source-test',{source_id:sourceId});assert.ok(d.getElementById('feedRows').textContent.includes('دریافت موفق'));
 await w.archiveFeed(sourceId);assert.equal(d.querySelectorAll('[data-select-source]').length,0);assert.equal(d.querySelectorAll('tr[data-lead-id]').length,2);
 assert.deepEqual(errors,[]);console.log('PASS: profile/reload, mission/reload, source registration/probe/archive, direct scan, ranking/filter/comparison and historical run retention. DOM only; no visual browser verification.');
})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>{dom?.window.close();server.kill()});
