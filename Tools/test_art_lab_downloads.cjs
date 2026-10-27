const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('Web/wwwroot/art-lab.js','utf8');
class Node {
  constructor(tag,cls='',text=''){this.tag=tag;this.className=cls;this.textContent=text;this.children=[];}
  append(...children){this.children.push(...children);}
  removeAttribute(name){delete this[name];}
}
const context={URL,window:{location:{origin:'http://localhost'}},state:{manifestUrl:'http://localhost/assets/style-packs/pocket-dungeon/manifest.json'},make:(...args)=>new Node(...args),configureLink:(node,url)=>{node.href=url;},reuseUrl:path=>new URL(path,'http://localhost/assets/style-packs/pocket-dungeon/').href};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('const ART_ARCHIVE_REF ='),source.indexOf('async function fetchJson(')),context);
const all=node=>[node,...node.children.flatMap(all)];
test('ordinary archive remains a pinned ZIP link',()=>{
 const nodes=all(context.renderReuseDownload({label:'Complete library',path:'reusable/downloads/library.zip',format:'zip',bytes:1024}));
 const link=nodes.find(n=>n.tag==='a');
 assert.match(link.textContent,/Download ZIP/); assert.match(link.href,/\/AI-Art\/raw\/[0-9a-f]{40}\//); assert.ok(link.href.endsWith('/library.zip'));
});
test('multipart archive exposes manifest, ordered parts, helper and exact command',()=>{
 const nodes=all(context.renderReuseDownload({label:'Complete library',format:'multipart-zip',path:'reusable/downloads/library.zip.parts.json',file:'library.zip.parts.json',archive_bytes:200000000,parts:[{number:2,path:'reusable/downloads/library.zip.part-002',bytes:10},{number:1,path:'reusable/downloads/library.zip.part-001',bytes:10}],assembly_tool:{path:'reusable/downloads/assemble_archive_parts.py'}}));
 const links=nodes.filter(n=>n.tag==='a');
 assert.deepEqual(links.map(n=>n.textContent),['Download JSON manifest','Part 1 of 2 · 0.0 MiB','Part 2 of 2 · 0.0 MiB','Download assembly helper (Python)']);
 assert.ok(nodes.some(n=>n.textContent.startsWith('Multipart ZIP · 2 parts')));
 assert.equal(nodes.find(n=>n.tag==='code').textContent,'python assemble_archive_parts.py library.zip.parts.json --output library.zip');
 assert.equal(new Set(links.map(n=>n.href.match(/\/raw\/([0-9a-f]{40})\//)[1])).size,1);
 assert.ok(links.every(n=>!n.textContent.includes('Download ZIP')));
});
test('only canonical archive resources are accepted',()=>{
 for(const path of ['https://evil.test/assets/a.zip','javascript:alert(1)','https://github.com/other/repo/assets/a.zip','http://localhost/assets/evil.py']) assert.equal(context.canonicalDownloadUrl(path),null);
 for(const path of ['http://localhost/assets/a.zip.parts.json','http://localhost/assets/a.zip.part-001','http://localhost/assets/assemble_archive_parts.py']) assert.ok(context.canonicalDownloadUrl(path));
});
test('untrusted filenames never enter an assembly command',()=>{
 const nodes=all(context.renderReuseDownload({format:'multipart-zip',path:'reusable/downloads/library.zip.parts.json',file:'bad;touch.zip.parts.json',parts:[]}));
 assert.ok(!nodes.some(n=>n.tag==='code'));
});
