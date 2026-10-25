import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=path=>readFile(resolve(root,path),'utf8');
const moduleURL=source=>`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const {nativeProject,nativePick,serializeNativeVisuals,validateNativeVisuals,nativeSceneFromVisuals}=await import(moduleURL(await read('Web/wwwroot/native-map-visuals.js')));
const roomURL=moduleURL(await read('Web/wwwroot/room-kit.js'));
const {generateDungeon,getPlayableMap}=await import(moduleURL((await read('Web/wwwroot/procedural-map.js')).replace(/(['"])\.\/room-kit\.js\1/g,JSON.stringify(roomURL))));
const edgeURL=moduleURL(await read('Web/wwwroot/tile-edge-tags.js'));
const {buildArtScene}=await import(moduleURL((await read('Web/wwwroot/generator-art.js')).replace(/(['"])\.\/tile-edge-tags\.js\1/g,JSON.stringify(edgeURL))));
const kit=JSON.parse(await read('Web/wwwroot/assets/room-kit/manifest.json'));
const rules=JSON.parse(await read('Web/wwwroot/assets/map-generation-rules.json'));
const catalog=JSON.parse(await read('Web/wwwroot/assets/book-tiles/catalog.json'));
let picks=0,scenes=0;
for(const [width,height] of [[6,6],[10,8],[20,16]]) {
  for(let rotation=0;rotation<4;rotation++)for(let y=0;y<height;y++)for(let x=0;x<width;x++) {
    const point=nativeProject(x,y,rotation);
    assert.deepEqual(nativePick(point.x,point.y,width,height,rotation),{x,y});
    assert.deepEqual(nativePick(point.x+29,point.y-23,width,height,rotation),{x,y});
    picks+=2;
  }
  for(const rotation of [0,1,2,3]) {
    const outside=nativeProject(-1,0,rotation);
    assert.equal(nativePick(outside.x,outside.y,width,height,rotation),null);
  }
  for(const style of catalog.styles) {
    const variant=catalog.kits.find(k=>k.id==='starter-dungeon').variants[style.id];
    const manifest=JSON.parse(await read(`Web/wwwroot/assets/book-tiles/${variant.manifest}`));
    const art={manifest,images:new Map(manifest.assets.map(asset=>[asset.id,{}]))};
    for(const layout of ['chambers','cavern','hall']) {
      const room=generateDungeon(kit,{seed:`native-${layout}`,width,height,layout,biome:'stone',density:.4,roomCount:4},rules);
      const playable=getPlayableMap(room,kit);
      const scene=buildArtScene(room,art,true);
      const metadata={styleId:style.id,kitId:'starter-dungeon',width,height,tiles:playable.tiles};
      const visuals=serializeNativeVisuals(scene,metadata);
      const portable=JSON.parse(JSON.stringify({...playable,visuals}));
      const restored=nativeSceneFromVisuals(portable.visuals,art,width,height,portable.tiles);
      assert.deepEqual(serializeNativeVisuals(restored,metadata),visuals,'portable descriptor reconstructs exact preview placements, order and rotations');
      const floorCount=scene.floor.length;
      assert.equal(visuals.pieces.length,floorCount+scene.structures.length+scene.decorations.length);
      assert.ok(visuals.pieces.some(p=>p.x2%2!==0||p.y2%2!==0),'boundary half-cell positions retained');
      assert.ok(visuals.pieces.some(p=>p.rotation!==0),'wall orientation retained');
      const missing=structuredClone(visuals),blocked=new Set(playable.tiles.filter(t=>t.blocked).map(t=>`${t.x},${t.y}`));
      const walkableFloor=missing.pieces.findIndex(p=>p.layer==='ground'&&!blocked.has(`${p.x2/2},${p.y2/2}`));
      assert.ok(walkableFloor>=0);missing.pieces.splice(walkableFloor,1);
      assert.throws(()=>validateNativeVisuals(missing,width,height,playable.tiles),/cover every walkable/);
      for(const bad of [
        {...visuals,styleId:'../escape'}, {...visuals,kitId:'x'.repeat(65)},
        {...visuals,pieces:[{...visuals.pieces[0],cell:24}]},
        {...visuals,pieces:[{...visuals.pieces[0],x2:-2}]},
        {...visuals,pieces:[{...visuals.pieces[0],rotation:4}]},
        {...visuals,pieces:[{...visuals.pieces[0],layer:'unknown'}]},
      ])assert.throws(()=>validateNativeVisuals(bad,width,height));
      scenes++;
    }
  }
}
const ground={cell:0,x2:0,y2:0,rotation:0,layer:'ground'};
const minimal={schemaVersion:1,styleId:'pocket-dungeon',kitId:'starter-dungeon',pieces:[ground]};
assert.throws(()=>validateNativeVisuals(minimal,6,6,[]),/cover every walkable/,'implicit walkable cells also need art');
assert.throws(()=>validateNativeVisuals({...minimal,pieces:[ground,{...ground}]},6,6),/duplicate native floor/);
console.log(`PASS ${picks} native square rotated picks and ${scenes} real generated preview/portable-render scene roundtrips across all styles.`);
