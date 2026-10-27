import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const source = await readFile(new URL('../Web/wwwroot/sprite-facing.js', import.meta.url), 'utf8');
const {rememberSpriteFacing, seedEnemyFacing, seedSpriteFacing, playerSpriteDirection, enemySpriteScaleX, drawFacingSprite} =
  await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

const facing = new Map();
const rat = {id:'rat.1',team:'enemy',x:4,y:2,hp:10};
seedEnemyFacing(facing,rat,[
  {team:'player',x:5,y:2,hp:0},
  {team:'enemy',x:4,y:3,hp:10},
  {team:'player',x:0,y:2,hp:10},
  {team:'player',x:4,y:4,hp:10},
]);
assert.deepEqual(facing.get(rat.id),{x:0,y:2},'initially face nearest living opponent');
rememberSpriteFacing(facing,rat.id,-1,0);
seedEnemyFacing(facing,rat,[{team:'player',x:8,y:2,hp:10}]);
assert.deepEqual(facing.get(rat.id),{x:-1,y:0},'movement persists during subsequent renders');
rememberSpriteFacing(facing,rat.id,0,0);
assert.deepEqual(facing.get(rat.id),{x:-1,y:0},'zero movement preserves facing');
rememberSpriteFacing(facing,rat.id,3,0);
assert.deepEqual(facing.get(rat.id),{x:3,y:0},'attack toward target overrides movement');

// Independently tabulated camera rotations for each cardinal grid direction.
const directions = [{x:1,y:0},{x:0,y:1},{x:-1,y:0},{x:0,y:-1}];
const nativeSigns = [[1,1,-1,-1],[1,-1,-1,1],[-1,-1,1,1],[-1,1,1,-1]];
const isoSigns = [[1,-1,-1,1],[-1,-1,1,1],[-1,1,1,-1],[1,1,-1,-1]];
const authoredSides = {rat:[1,1,1,1],guard:[1,1,1,1],boss:[1,1,1,1],
  'boss-hoarder':[-1,-1,1,1],'boss-juicer':[1,1,1,1],'boss-swine':[1,1,1,1],
  sludge:[-1,-1,-1,-1],cinder:[-1,-1,-1,-1],frost:[-1,-1,-1,-1],
  spore:[-1,-1,-1,-1],sentry:[-1,-1,-1,-1],mauler:[-1,-1,-1,-1],scatterer:[-1,-1,-1,-1]};
for (const [native, expected] of [[true,nativeSigns],[false,isoSigns]])
  for (let rotation=0;rotation<4;rotation++)
    for (let d=0;d<4;d++)
      for (const [key,sides] of Object.entries(authoredSides))
        for(let pose=0;pose<4;pose++)
          assert.equal(enemySpriteScaleX(key,pose,directions[d],rotation,native)*sides[pose],expected[rotation][d],
            `${key} pose ${pose}, view ${rotation}, direction ${d}, native=${native}`);

// Reflect only the painted art about its anchor; restoring also preserves FX/UI.
const calls=[];
const context=Object.fromEntries(['save','translate','scale','restore'].map(method=>[method,(...args)=>calls.push([method,...args])]));
drawFacingSprite(context,-1,120,240,()=>calls.push(['draw',-36,-90,100,100]));
assert.deepEqual(calls,[['save'],['translate',120,240],['scale',-1,1],['draw',-36,-90,100,100],['restore']]);
assert.throws(()=>drawFacingSprite(context,-1,0,0,()=>{throw Error('draw failed');}));
assert.equal(calls.at(-1)[0],'restore');
console.log('Enemy facing checks passed: nearest opponent, movement/attack transitions, 4 camera views, all art poses, anchors/context restoration.');

// Expected screen quadrants are independent of grid projection and camera rotation.
const vectors = [{x:1,y:0},{x:0,y:1},{x:-1,y:0},{x:0,y:-1},
  {x:1,y:1},{x:-1,y:1},{x:-1,y:-1},{x:1,y:-1}];
const square = [
 ['se','sw','sw','ne','se','sw','nw','ne'],
 ['sw','sw','ne','se','sw','nw','ne','se'],
 ['sw','ne','se','sw','nw','ne','se','sw'],
 ['ne','se','sw','sw','ne','se','sw','nw']];
const iso = [
 ['se','sw','nw','ne','sw','sw','ne','se'],
 ['sw','nw','ne','se','sw','ne','se','sw'],
 ['nw','ne','se','sw','ne','se','sw','sw'],
 ['ne','se','sw','nw','se','sw','sw','ne']];
for (const [native, expected] of [[true,square],[false,iso]])
 for(let rotation=0;rotation<4;rotation++)
  for(let i=0;i<vectors.length;i++) {
   assert.equal(playerSpriteDirection(vectors[i],rotation,native),expected[rotation][i],
    `player direction ${i}, view ${rotation}, square=${native}`);
   const state = new Map();
   seedSpriteFacing(state,{id:'ally',team:'player',x:0,y:0},[{team:'enemy',hp:10,...vectors[i]}]);
   assert.deepEqual(state.get('ally'),vectors[i]);
   rememberSpriteFacing(state,'ally',vectors[(i+1)%vectors.length].x,vectors[(i+1)%vectors.length].y);
   seedSpriteFacing(state,{id:'ally',team:'player',x:0,y:0},[{team:'enemy',hp:10,...vectors[i]}]);
   assert.equal(playerSpriteDirection(state.get('ally'),rotation,native),expected[rotation][(i+1)%vectors.length]);
   rememberSpriteFacing(state,'ally',vectors[i].x,vectors[i].y);
   assert.equal(playerSpriteDirection(state.get('ally'),rotation,native),expected[rotation][i]);
  }
rememberSpriteFacing(facing,'diagonal',-1,-4);
assert.deepEqual(facing.get('diagonal'),{x:-1,y:-4},'unequal diagonal target vector is retained');
assert.equal(playerSpriteDirection(facing.get('diagonal'),0,false),'ne','project actual target, not a sign-normalized diagonal');
// Visually inspected PNG fixture: every sheet has columns front-right, front-left,
// rear-right, rear-left, each with idle/walk1/walk2. Hashes pin that observation
// to actual pixels; replacing source art requires rechecking its painted orientation.
const inspectedSheets = {
  "directional/carl.png": "cc86160a13e02014e1e52c666ad67c5b807928ab9021b622ab7273ca577bab21",
  "directional/donut.png": "89ad08a17ca187bf73b1a66d4bd24209090adf7304563244d999af1978a2808a",
  "directional/katia.png": "f52383c4124ea1935779c361d24cbef1f70d913cfe0e5fb4af623c5cff3a3881",
  "directional/mongo.png": "c639e4b4c57f175b70ff359accc2839b0436c3348eb3a03473ce09f67ac8a729",
  "forms/bulwark.png": "1ea1fb9756fb8dbc860ce695999574e5909cd3722d3cb4a8c5746154c8a43e01",
  "forms/strider.png": "17b1dad6b36bce631212cc41b682901226f8272e47f80ce372a18879e070d6b3",
  "forms/focused.png": "0f86d4283fbba229f9f54348c195ba288098689854f53ea49e734b0561e2b430"
};
for (const [path, hash] of Object.entries(inspectedSheets)) {
 const bytes=await readFile(new URL('../Web/wwwroot/assets/'+path,import.meta.url));
 assert.equal(createHash('sha256').update(bytes).digest('hex'),hash,`reinspect painted facing: ${path}`);
 const folder=path.split('/')[0];
 const manifest=JSON.parse(await readFile(new URL('../Web/wwwroot/assets/'+folder+'/manifest.json',import.meta.url)));
 const sheet=Object.values(manifest.characters??manifest.forms).find(sheet=>sheet.file===path.split('/')[1]);
 for(const [column,direction] of ['se','sw','ne','nw'].entries())
  for(const [row,pose] of ['idle','walk1','walk2'].entries()) {
   assert.equal(sheet.frames[direction][pose].x,column*128);
   assert.equal(sheet.frames[direction][pose].y,row*144);
  }
}
const renderer=await readFile(new URL('../Web/wwwroot/battlefield.js',import.meta.url),'utf8');
assert.match(renderer,/const useDirectional=Boolean\(directionalFrame\)/,'attacks and hits preserve directional art');
console.log('Player facing checks passed: square/isometric, 4 rotations, 8 target directions, movement persistence, source-art orientation fixtures.');
