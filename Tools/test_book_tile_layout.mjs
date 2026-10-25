import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../Web/wwwroot/book-tile-layout.js', import.meta.url), 'utf8');
const { composeKit, worldContacts } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const anchor = { x: 128, y: 192 };
for (const projection of ['isometric', 'orthogonal']) {
  const iso = projection === 'isometric';
  const points = iso ? [[128,160],[192,192],[128,224],[64,192]] : [[64,128],[192,128],[192,256],[64,256]];
  const floor = { id:'floor',role:'ground',anchor,placement:{kind:'floor',points} };
  const wall = axis => ({ id:axis,role:'wall',anchor,placement:{kind:'wall',axis,points:iso ? (axis==='x'?[[96,176],[160,208]]:[[160,176],[96,208]]) : [[64,192],[192,192]]} });
  const manifest = { grid:{projection,tileWidth:128,tileHeight:iso?64:128}, assets:[floor,wall('x'),...(iso?[wall('y')]:[])] };
  manifest.assets.splice(1,0,{ id:'manual-piece',role:'ground',anchor });
  const placements = composeKit(manifest,1);
  assert.ok(placements.every(p=>p.asset.id!=='manual-piece'),'manual floor pieces are not mixed into registered previews');
  const floors = placements.filter(p=>p.layer===0);
  assert.equal(floors.length,25);
  const floorVertices = new Set(floors.flatMap(p=>worldContacts(p).map(v=>JSON.stringify(v))));
  for (const axis of iso?['x','y']:['x']) {
    const edge = placements.filter(p=>p.asset.id===axis).sort((a,b)=>a.py-b.py||a.px-b.px);
    assert.equal(edge.length,5);
    const contacts = edge.map(worldContacts);
    for (const pair of contacts) for (const point of pair) assert.ok(floorVertices.has(JSON.stringify(point)), 'wall endpoints land on floor vertices');
    for (let i=1;i<contacts.length;i++) assert.deepEqual(contacts[i-1][1],contacts[i][0], 'adjacent wall endpoints meet exactly');
  }
  if (iso) {
    const x=placements.find(p=>p.asset.id==='x');const y=placements.find(p=>p.asset.id==='y');
    assert.deepEqual(worldContacts(x)[0],worldContacts(y)[0],'two back walls share the same room corner');
  }
  assert.deepEqual(composeKit(manifest,1),placements,'layout is deterministic');
}
console.log('Book tile layout: floor vertices, shared wall endpoints, room corners and determinism passed.');
