import {bookOneSeedNumber} from './book-one-playable-floor.js';

/** Decide whether the direct game entry resumes Book 1 or starts a new floor. */
export function planBookOneEntry(serializedSave, requestedSeed = null) {
  if (requestedSeed !== null && (!requestedSeed.trim() || requestedSeed.length > 80)) {
    throw new Error('Floor seed must contain 1–80 characters.');
  }
  let saved;
  try { saved = serializedSave ? JSON.parse(serializedSave) : null; } catch { /* Preserve invalid storage until a confirmed replacement. */ }
  const floorPlan = saved?.generatedDungeon?.floorPlan;
  const isBookOne = isBookOneFloorPlan(floorPlan);
  const matchesSeed = requestedSeed === null || floorPlan?.seed === (bookOneSeedNumber(requestedSeed) & 0x7fffffff);
  if (isBookOne && matchesSeed) return {kind: 'resume'};
  return {
    kind: 'start', seed: requestedSeed ?? 'book-one-floor-one',
    needsConfirmation: Boolean(serializedSave),
  };
}

/** Generate the same canonical packet used by the optional atlas preview. */
export async function createBookOneEntry(seed, loadJSON = async path => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`First Floor content could not load: ${path}`);
  return response.json();
}) {
  const [{generateBookOneFloor}, {getBookOneFloorPlayable}, library, rules, manifest, catalog] = await Promise.all([
    import('./book-one-floor.js'), import('./book-one-playable-floor.js'),
    loadJSON('assets/top-down-object-kit/manifest.json'),
    loadJSON('data/procedural-object-room-rules.json'),
    loadJSON('assets/room-kit/manifest.json'), loadJSON('data/book-one-floor-one.json'),
  ]);
  const floor = generateBookOneFloor(library, {seed}, rules, manifest, catalog);
  return getBookOneFloorPlayable(floor, library);
}

/** Only leave a saved safe room; battle, victory and defeat resume their phase. */
export function shouldResumeBookOneFloor(view) {
  return view?.screen === 'camp'
    && isBookOneFloorPlan(view?.generatedDungeon?.floorPlan);
}

/** Mode identity comes from authored stable IDs, never the displayed map title. */
export function isBookOneFloorPlan(plan) {
  return Array.isArray(plan?.groups) && plan.groups.length > 0
    && plan.groups.every(group => typeof group.id === 'string' && group.id.startsWith('book1.'))
    && Array.isArray(plan.discoveries) && plan.discoveries.some(point => point.id === 'visit-entry');
}
