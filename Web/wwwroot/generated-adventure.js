import { generateDungeon, getPlayableMap } from './procedural-map.js';
import { fetchJSON, loadArtKit, buildArtScene } from './generator-art.js';
import { serializeNativeVisuals } from './native-map-visuals.js';

// The in-game expedition uses the same layout, tile fitting and portable art as Foundry.
export async function createGeneratedAdventure({ seed, styleId = 'pocket-dungeon', kitId = 'starter-dungeon', layout = 'chambers' } = {}) {
  const catalogURL = new URL('assets/book-tiles/catalog.json', location.href);
  const [manifest, rules, catalog] = await Promise.all([
    fetchJSON('assets/room-kit/manifest.json'), fetchJSON('assets/map-generation-rules.json'), fetchJSON(catalogURL)
  ]);
  const chosenSeed = seed?.trim() || `crawl-${crypto.randomUUID().slice(0, 8)}`;
  const room = generateDungeon(manifest, { seed: chosenSeed, width: 16, height: 12, layout, biome: 'stone', roomCount: 4, density: .25 }, rules);
  const art = await loadArtKit(catalog, catalogURL, kitId, styleId);
  const scene = buildArtScene(room, art, true);
  const customMap = getPlayableMap(room, manifest);
  customMap.visuals = serializeNativeVisuals(scene, { styleId, kitId, width: room.width, height: room.height, tiles: customMap.tiles });
  return { customMap, entrance: room.entrance || room.start, exit: room.exit };
}

// Continuous exploration keeps the proven square tile/tag fitter and native renderer.
export async function createExplorationFloor({ seed, styleId = 'pocket-dungeon', kitId = 'starter-dungeon' } = {}) {
  const catalogURL = new URL('assets/book-tiles/catalog.json', location.href);
  const [manifest, rules, catalog] = await Promise.all([
    fetchJSON('assets/room-kit/manifest.json'), fetchJSON('assets/exploration-floor-rules.json'), fetchJSON(catalogURL)
  ]);
  const chosenSeed = seed?.trim() || `floor-${crypto.randomUUID().slice(0, 8)}`;
  const { generateExplorationFloor } = await import('./exploration-floor.js');
  const { room, floorPlan } = generateExplorationFloor(manifest, rules, chosenSeed);
  const art = await loadArtKit(catalog, catalogURL, kitId, styleId);
  // Only environmental landmarks belong on this abandoned works floor.
  // Props never acquire collision; canonical walls alone define impassable cells.
  const allowed = new RegExp(rules.propLabelPattern, 'i');
  const floorArt = { ...art, manifest: { ...art.manifest, assets: art.manifest.assets.filter(a => a.role !== 'prop' || allowed.test(a.label)) } };
  const scene = buildArtScene(room, floorArt, true);
  const landmarkAssets = floorArt.manifest.assets.filter(a => a.role === 'prop');
  const reserved = new Set([...room.generation.protectedCells,...floorPlan.groups,...floorPlan.discoveries].map(p=>`${p.x},${p.y}`));
  if (landmarkAssets.length) for (const [index, zone] of room.rooms.entries()) {
    if (!index) continue;
    const p = {x:zone.x+zone.width-2,y:zone.y+1};
    if (!reserved.has(`${p.x},${p.y}`)) scene.decorations.push({asset:landmarkAssets[(index-1)%landmarkAssets.length],px:p.x*128,py:p.y*128,angle:0,kind:'environment-landmark'});
  }
  floorPlan.map.visuals = serializeNativeVisuals(scene, {styleId,kitId,width:room.width,height:room.height,tiles:floorPlan.map.tiles});
  return { customMap: floorPlan.map, floorPlan, entrance: floorPlan.entrance, exit: floorPlan.exit };
}
