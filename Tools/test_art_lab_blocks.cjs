// Focused contract fixtures; no generated art or final release policies required.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto').webcrypto;
const source=fs.readFileSync(require('node:path').join(__dirname,'../Web/wwwroot/art-lab.js'),'utf8');
const code=source.slice(source.indexOf('const PRINCIPAL_VIEWS ='),source.indexOf('async function reuseImage('));
const context=vm.createContext({crypto,TextDecoder,Uint8Array,Map,Set,JSON,Error,assetUrl:p=>p,fetch:async()=>{throw Error('unexpected fetch');}});
vm.runInContext(code+'\nglobalThis.api={bindGenerationBlocks,loadGenerationBlocks,eligibleAsset,canonicalViewReferences};',context);
const api=context.api,dirs=['front','top','right','left','bottom','rear'];
const targets=[['pocket-knives',['top','bottom']],['ink-knives',['top','bottom']],['iron-sword',['top']],['hand-axe',['top','bottom']],['carl01',['bottom']],['carl02',['bottom']],['carl03',['bottom']],['brittany',['bottom']],['bow',dirs],['bomb-rack',['top']],['spear',['top','bottom']],['siege',['rear']],['shared-workbench',['top']],['shared-cannon',['top','rear']],['shared-cage',['top']]];
function fixture(){
 const index={assets:[],view_sets:[]},records=[];
 for(const [id,affected] of targets){const parent={id,object_id:id,image:{path:id+'.png'},views:{applicable:true,complete:false}};index.assets.push(parent);const views={},bindings={};for(const view of dirs){const aid=id+'-'+view;views[view]=aid;index.assets.push({id:aid,object_id:id,view,image:{path:aid+'.png'}});bindings[view]={asset_id:aid,path:aid+'.png',sha256:'a'.repeat(64)};}index.view_sets.push({object_id:id,complete:false,views});const approved=dirs.filter(v=>!affected.includes(v));records.push({object_id:id,primary_source:{asset_id:id,path:id+'.png',sha256:'b'.repeat(64)},status:'external-generation-blocked',complete:false,affected_views:affected,views:bindings,unaffected_review:{status:'independent-partial-review',approved_views:approved,views:Object.fromEntries(approved.map(v=>[v,bindings[v]]))}});}
 const statistics={recorded_blocked_sets:15,recorded_blocked_views:25};index.generation_blocks={path:'blocks.json',statistics};return {index,report:{schema_version:1,policy:'recorded-image-tool-block-release-v1',path_base:'library-root',statistics,records}};
}
test('15-set fixture retains references but rejects exactly 25 unavailable placements',()=>{const {index,report}=fixture();api.bindGenerationBlocks(index,report);const metadata=new Map(index.assets.map(a=>[a.id,a]));let blocked=0,approved=0;for(const [id,affected] of targets){const refs=api.canonicalViewReferences(metadata.get(id),index);for(const view of dirs){assert.equal(api.eligibleAsset(metadata.get(id+'-'+view),metadata,index),!affected.includes(view));assert.equal(refs[view].reviewed,!affected.includes(view));assert.equal(refs[view].blocked,affected.includes(view));affected.includes(view)?blocked++:approved++;}assert.equal(index.view_sets.find(s=>s.object_id===id).complete,false);}assert.equal(blocked,25);assert.equal(approved,65);});
test('matching catalog source byte and pixel hashes preserve partial approval',()=>{const f=fixture();f.index.assets[0].image.sha256=f.report.records[0].primary_source.sha256;f.index.assets[0].image.rgba_sha256='c'.repeat(64);f.report.records[0].primary_source.rgba_sha256='c'.repeat(64);api.bindGenerationBlocks(f.index,f.report);assert.equal(f.index.recordedBlocks.size,15);});
test('matching catalog leaf byte and pixel hashes preserve partial approval',()=>{const f=fixture(),binding=f.report.records[0].views.front;f.index.assets[1].image.sha256=binding.sha256;f.index.assets[1].image.rgba_sha256='e'.repeat(64);binding.rgba_sha256='e'.repeat(64);api.bindGenerationBlocks(f.index,f.report);assert.equal(f.index.recordedBlocks.size,15);});
test('ordinary library placement remains unchanged without a block policy',()=>{const {index}=fixture();delete index.generation_blocks;const metadata=new Map(index.assets.map(a=>[a.id,a]));assert.equal(api.eligibleAsset(metadata.get('bow-front'),metadata,index),true);});
test('shared-batch uncertainty remains visible on unavailable references without claiming individual attribution',()=>{const f=fixture(),reason='batch rejection; individual request attribution unavailable';f.report.records.find(row=>row.object_id==='shared-workbench').reason=reason;api.bindGenerationBlocks(f.index,f.report);const metadata=new Map(f.index.assets.map(a=>[a.id,a])),refs=api.canonicalViewReferences(metadata.get('shared-workbench'),f.index);assert.equal(refs.top.blockReason,reason);assert.equal(refs.top.status,'unapproved reference · generation unavailable');assert.equal(refs.front.blockReason,null);assert.equal(api.eligibleAsset(metadata.get('shared-workbench-top'),metadata,f.index),false);assert.equal(api.eligibleAsset(metadata.get('shared-workbench-front'),metadata,f.index),true);});
for(const [name,mutate] of [
 ['missing unaffected approval',f=>f.report.records[0].unaffected_review.approved_views.pop()],
 ['stale approved leaf',f=>f.report.records[0].unaffected_review.views.front={path:'stale.png'}],
 ['stale native source',f=>f.report.records[0].primary_source.path='other.png'],
 ['stale canonical source bytes',f=>f.index.assets[0].image.sha256='c'.repeat(64)],
 ['stale canonical source pixels',f=>f.index.assets[0].image.rgba_sha256='d'.repeat(64)],
 ['stale leaf bytes',f=>f.index.assets[1].image.sha256='c'.repeat(64)],
 ['stale leaf pixels',f=>{f.report.records[0].views.front.rgba_sha256='e'.repeat(64);f.index.assets[1].image.rgba_sha256='d'.repeat(64)}],
 ['wrong leaf binding',f=>f.report.records[0].views.top.asset_id='other'],
 ['falsely complete set',f=>f.index.view_sets[0].complete=true],
 ['duplicate target',f=>f.report.records.push(f.report.records[0])],
 ['wildcard direction',f=>f.report.records[0].affected_views=['*']],
 ['inaccurate counts',f=>f.report.statistics={recorded_blocked_sets:15,recorded_blocked_views:24}]
])test('reject '+name,()=>{const f=fixture();mutate(f);assert.throws(()=>api.bindGenerationBlocks(f.index,f.report));});
test('pinned report is fetched and hash checked before partial placement is enabled',async()=>{const f=fixture(),bytes=Buffer.from(JSON.stringify(f.report));f.index.generation_blocks.sha256=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');context.fetch=async()=>({ok:true,arrayBuffer:async()=>bytes});await api.loadGenerationBlocks(f.index,'/');assert.equal(f.index.recordedBlocks.size,15);f.index.generation_blocks.sha256='0'.repeat(64);await assert.rejects(api.loadGenerationBlocks(f.index,'/'),/hash mismatch/);assert.equal(f.index.recordedBlocks.size,0);});

test('byte-bound legacy view policies allow catalog-only supplemental RGBA hashes',()=>{const f=fixture();for(const a of f.index.assets)if(a.view)a.image.rgba_sha256='e'.repeat(64);api.bindGenerationBlocks(f.index,f.report);assert.equal(f.index.recordedBlocks.size,15);});
