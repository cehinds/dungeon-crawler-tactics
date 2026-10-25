import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const url = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const edgesURL = url(await readFile(new URL('../Web/wwwroot/tile-edge-tags.js', import.meta.url), 'utf8'));
const { fitFloorTiles } = await import(url((await readFile(new URL('../Web/wwwroot/tile-edge-solver.js', import.meta.url), 'utf8')).replace("'./tile-edge-tags.js'", JSON.stringify(edgesURL))));
const { validateFloorConnections } = await import(edgesURL);
const asset = (id, sides) => ({ id, role: 'ground', edges: Object.fromEntries(['north','east','south','west'].map((side, i) => [side, [`join.${sides[i]}`]])) });
const tile = (a, x, y, angle = 0) => ({ asset: a, px: x * 128, py: y * 128, angle });
const a = asset('a', ['a','a','a','a']), b = asset('b', ['b','b','b','b']);
const preferred = [tile(a,0,0), tile(a,1,0)];
assert.equal(fitFloorTiles(preferred,[a,b]).floor, preferred);
const mixed = [tile(a,0,0),tile(b,1,0)], snapshot = JSON.stringify(mixed);
const fitted = fitFloorTiles(mixed,[a,b],{seed:'repeat'});
assert.equal(fitted.adjustedTiles,1);
assert.deepEqual(validateFloorConnections(fitted.floor),[]);
assert.deepEqual(fitFloorTiles(mixed,[a,b],{seed:'repeat'}),fitted);
assert.equal(JSON.stringify(mixed),snapshot);
const asymmetric = asset('corner',['a','a','b','b']);
const rotated = fitFloorTiles([tile(asymmetric,0,0),tile(asymmetric,1,0)],[asymmetric]);
assert(rotated.rotatedTiles > 0);
assert.deepEqual(validateFloorConnections(rotated.floor),[]);
// The three locally preferred placements trap a greedy fourth-cell choice:
// its north/west connectors would have to be f/g, absent in every rotation.
const branchA = asset('branch-a',['a','b','c','d']);
const branchB = asset('branch-b',['c','e','f','b']);
const branchC = asset('branch-c',['c','g','h','i']);
const branchFloor = [tile(branchA,0,0),tile(branchB,1,0),tile(branchC,0,1),tile(branchA,1,1)];
const branchResult = fitFloorTiles(branchFloor,[branchA,branchB,branchC],{seed:'branch'});
assert.deepEqual(validateFloorConnections(branchResult.floor),[]);
assert(branchResult.floor.slice(0,3).some((piece,i)=>piece.asset.id !== branchFloor[i].asset.id || piece.angle !== 0), 'Reconsider earlier locally valid preferences when fourth cell has no candidate');
// Odd cycles cannot occur in the grid; an isolated manual connector still cannot be auto-selected.
const manual = asset('manual',['manual','manual','manual','manual']);
assert.throws(()=>fitFloorTiles(mixed,[manual]),/unsatisfiable/);
for (const excluded of [manual, asset('overlay',['overlay','overlay','overlay','overlay'])]) {
  const replaced = fitFloorTiles([tile(excluded,0,0)],[excluded,a]);
  assert.equal(replaced.floor[0].asset.id,'a', 'An isolated manual/overlay floor must be replaced');
  assert.throws(()=>fitFloorTiles([tile(excluded,0,0)],[excluded]),/unsatisfiable/);
}
assert.throws(()=>fitFloorTiles(mixed,[a,b],{maxSearchSteps:0}),/budget exhausted/);
assert.throws(()=>fitFloorTiles(mixed,[{id:'missing',role:'ground'}]),/edge metadata/);
const wall = { ...asset('wall',['a','b','c','d']), role: 'wall' };
const bounded = fitFloorTiles([tile(a,0,0)],[a,b], { boundaries: [{x:0,y:0,side:'east',asset:wall,rotation:2}] });
assert.equal(bounded.floor[0].asset.id,'b', 'Wall rotation exposes its original east connector on its world west side');
assert.equal(bounded.checkedBoundaries,1);
assert.throws(()=>fitFloorTiles([tile(a,0,0)],[a,b], { boundaries: [{x:0,y:0,side:'east',asset:wall,rotation:0}] }),/unsatisfiable/, 'Eligible floor pool cannot match wall connector d');
const preservedBoundary = fitFloorTiles(preferred,[a,b], { boundaries: [{x:0,y:0,side:'north',asset:wall,rotation:2}] });
assert.equal(preservedBoundary.floor,preferred, 'Compatible wall boundaries preserve fast-path references');
const wallA = {...a, id:'wall-a', role:'wall'}, wallB = {...b, id:'wall-b', role:'wall'};
const flexibleBoundaries = [
  {x:0,y:0,side:'north',asset:wallA,rotation:0,candidates:[{asset:wallB,rotation:0}]},
  {x:0,y:0,side:'east',asset:wallB,rotation:0}
];
const flexibleSnapshot = JSON.stringify(flexibleBoundaries);
const jointFit = fitFloorTiles([tile(a,0,0)],[a,b],{boundaries:flexibleBoundaries});
assert.equal(jointFit.floor[0].asset.id,'b', 'Both boundaries must be satisfied together');
assert.equal(jointFit.boundaries[0].asset.id,'wall-b', 'Select alternate wall instead of rejecting a valid floor arrangement');
assert.equal(jointFit.adjustedWalls,1);
assert.equal(JSON.stringify(flexibleBoundaries),flexibleSnapshot, 'Wall input remains immutable');
assert(!('candidates' in jointFit.boundaries[0]), 'Resolved scene boundaries contain only the placed wall');
const retained = [tile(b,0,0)];
assert.equal(fitFloorTiles(retained,[a,b],{boundaries:flexibleBoundaries}).floor,retained, 'Compatible alternate walls preserve floor references');
const bridge = asset('transition',['a','b','a','a']);
const transitioned = fitFloorTiles([tile(a,0,0),tile(a,1,0),tile(b,2,0)],[a,b,bridge],{boundaries:[
  {x:0,y:0,side:'west',asset:wallA,rotation:0}, {x:2,y:0,side:'east',asset:wallB,rotation:0}
]});
assert(transitioned.floor.some(piece=>piece.asset.id==='transition'), 'Authored transition connects distinct material tags');
assert.deepEqual(validateFloorConnections(transitioned.floor),[]);
assert.throws(()=>fitFloorTiles([tile(a,0,0)],[a],{boundaries:[{x:0,y:0,side:'north',asset:wallA,candidates:{}}]}),/must be an array/);
const large = Array.from({length:320},(_,i)=>tile(i%2?a:b,i%20,Math.floor(i/20)));
const result = fitFloorTiles(large,[a,b],{seed:'large',maxSearchSteps:20000});
assert.deepEqual(validateFloorConnections(result.floor),[]);
assert(result.searchSteps < 20000);
assert.equal(result.checkedJoins,604);
assert.equal(large[0].asset,b);
console.log(`PASS floor fitting: preferences, rotations, alternatives, failures, budget, determinism, immutability, and 320 cells (${result.searchSteps} steps).`);
