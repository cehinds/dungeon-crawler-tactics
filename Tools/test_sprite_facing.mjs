import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../Web/wwwroot/sprite-facing.js', import.meta.url), 'utf8');
const {rememberSpriteFacing, seedEnemyFacing, enemySpriteScaleX, drawFacingSprite} =
  await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

const facing = new Map();
const rat = {id:'rat.1',team:'enemy',x:4,y:2,hp:10};
seedEnemyFacing(facing,rat,[
  {team:'player',x:5,y:2,hp:0},
  {team:'enemy',x:4,y:3,hp:10},
  {team:'player',x:0,y:2,hp:10},
  {team:'player',x:4,y:4,hp:10},
]);
assert.deepEqual(facing.get(rat.id),{x:0,y:1},'initially face nearest living opponent');
rememberSpriteFacing(facing,rat.id,-1,0);
seedEnemyFacing(facing,rat,[{team:'player',x:8,y:2,hp:10}]);
assert.deepEqual(facing.get(rat.id),{x:-1,y:0},'movement persists during subsequent renders');
rememberSpriteFacing(facing,rat.id,0,0);
assert.deepEqual(facing.get(rat.id),{x:-1,y:0},'zero movement preserves facing');
rememberSpriteFacing(facing,rat.id,3,0);
assert.deepEqual(facing.get(rat.id),{x:1,y:0},'attack toward target overrides movement');

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
