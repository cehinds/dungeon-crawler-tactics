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
