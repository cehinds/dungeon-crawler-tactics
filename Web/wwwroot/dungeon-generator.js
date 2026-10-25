import { drawFloorLayer } from './tile-surface-renderer.js';
import { serializeNativeVisuals } from './native-map-visuals.js';
import { SIDES, edgeTagsForRotation } from './tile-edge-tags.js';
import { EDGE_DIRECTIONS, sceneConnections, inspectPlacedTile, pickPreviewCell } from './tile-edge-preview.js';
import { generateDungeon, getPlayableMap } from './procedural-map.js';
import { fetchJSON, loadArtKit, buildArtScene, drawPiece, revisionURL, environmentMood, visibleSceneCorners } from './generator-art.js';
const $ = id => document.getElementById(id), canvas = $('map'), ctx = canvas.getContext('2d');
const terrainTypes = [{ tag: 'surface.water', letter: 'W', label: 'Water', color: '#82d6ff' }, { tag: 'surface.oil', letter: 'O', label: 'Oil', color: '#d4bbf2' }, { tag: 'surface.burning', letter: 'F', label: 'Fire', color: '#ffb17a' }];
const catalogURL = new URL('assets/book-tiles/catalog.json', location.href);
let manifest, rules, catalog, room, playable, art, scene, rotation = 0, blueprint = false, artRequest = 0, artError = false, zoom = 1, pan = { x: 0, y: 0 }, generating = false, artBusy = false, generationNumber = 0;
let layoutDirty = false, feedbackTimer;
let showConnectionOverlay = false, selectedMapCell = null, camera, infoOpenedFromMap = false;
function status(message, error = false) {
  $('status').textContent = message; $('status').classList.toggle('error', error);
  document.querySelectorAll('.dialog-error').forEach(node => node.remove());
  const dialog = document.querySelector('dialog[open]');
  if (error && dialog) {
    const note = document.createElement('p'); note.className = 'dialog-error';
    note.setAttribute('role', 'alert'); note.textContent = message;
    dialog.prepend(note); dialog.scrollTop = 0;
  }
}
async function safely(action) { try { await action(); } catch (error) { status(error.message, true); } }
function settings() {
  for (const [id, max] of [['width', 20], ['height', 16]]) { const value = Number($(id).value); if (!Number.isInteger(value) || value < 6 || value > max) throw new Error(`${id === 'width' ? 'Width' : 'Height'} must be a whole number from 6 to ${max}.`); }
  return { seed: $('seed').value, width: Number($('width').value), height: Number($('height').value), layout: $('layout').value, biome: $('biome').value, roomCount: Number($('rooms').value), density: Number($('density').value) / 100 };
}
function updateSummary() {
  const entrance = room.entrance || room.start;
  $('ambience-info').textContent = environmentMood(art?.kit.id || $('art-theme').value).label;
  $('map-title').textContent = art?.kit.title || $('art-theme').selectedOptions[0]?.textContent || 'Dungeon';
  $('map-seed').textContent = `Seed: ${room.seed || 'untitled'}`;
  $('map-title').title = $('map-title').textContent;
  $('counts').textContent = `${room.width} × ${room.height} · ${room.rooms.length} rooms · 4 crawlers`;
  $('entrance-info').textContent = `Cell ${entrance.x + 1}, ${entrance.y + 1}`;
  $('exit-info').textContent = `Cell ${room.exit.x + 1}, ${room.exit.y + 1}`;
  $('terrain-summary').replaceChildren(...terrainTypes.map(type => {
    const count = playable.tiles.filter(tile => tile.tags.includes(type.tag)).length;
    const item = document.createElement('span'), key = document.createElement('strong'); key.textContent = type.letter; key.style.color = type.color;
    item.append(key, document.createTextNode(` ${type.label} ${count}`)); return item;
  }));
  $('route-summary').textContent = `${Math.max(0, room.clearRoute.length - 1)} steps between portals`;
  canvas.setAttribute('aria-label', `${room.width} by ${room.height} square dungeon with ${room.rooms.length} rooms. Entrance at column ${entrance.x + 1}, row ${entrance.y + 1}; exit at column ${room.exit.x + 1}, row ${room.exit.y + 1}. A connected route joins them. ${blueprint ? 'Blueprint' : 'Native tile art preview'}, rotated ${rotation * 90} degrees.`);
}
function paletteLegend() {
  $('room-palettes').replaceChildren();
  if (!scene || !art) return;
  selectedMapCell = null;
  for (const style of scene.roomStyles) {
    const row = document.createElement('div'); row.className = 'room-palette';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'), image = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    const crop = style.asset.derived; svg.setAttribute('viewBox', `${crop.offset.x} ${crop.offset.y} ${crop.width} ${crop.height}`); svg.setAttribute('aria-hidden', 'true');
    image.setAttribute('href', revisionURL(style.asset.file, art.manifestURL, [style.asset.source, style.asset.derived])); image.setAttribute('width', '256'); image.setAttribute('height', '256'); svg.append(image);
    const copy = document.createElement('span'), title = document.createElement('strong'), label = document.createElement('span');
    title.textContent = `Room ${style.index + 1}`; label.textContent = style.asset.label; copy.append(title, label); row.append(svg, copy); $('room-palettes').append(row);
  }
  const selected = $('edge-asset').value;
  $('edge-asset').replaceChildren(...art.manifest.assets.map(asset => new Option(asset.label, asset.id)));
  if (art.manifest.assets.some(asset => asset.id === selected)) $('edge-asset').value = selected;
  renderEdgeInspector();
}
function renderEdgeInspector() {
  const placed = selectedMapCell && inspectPlacedTile(scene, selectedMapCell.x, selectedMapCell.y);
  if (placed) {
    $('edge-asset').value = placed.piece.asset.id;
    $('edge-rotation').value = String(((Math.round((placed.piece.angle || 0) / (Math.PI / 2)) % 4) + 4) % 4);
  }
  const asset = art?.manifest.assets.find(item => item.id === $('edge-asset').value);
  if (!asset) return;
  const edges = edgeTagsForRotation(asset, Number($('edge-rotation').value));
  $('edge-cell-summary').textContent = placed ? `Placed tile · column ${selectedMapCell.x + 1}, row ${selectedMapCell.y + 1}` : 'Library component · inspection only';
  $('edge-sides').replaceChildren(...SIDES.map(side => {
    const row = document.createElement('div'), heading = document.createElement('dt'), values = document.createElement('dd');
    row.dataset.side = side; heading.textContent = side[0].toUpperCase() + side.slice(1);
    for (const tag of edges[side]) { const chip = document.createElement('code'); chip.textContent = tag; values.append(chip); }
    if (placed) {
      const join = placed.edges.find(edge => edge.side === side), note = document.createElement('small');
      note.className = join.compatible ? 'edge-match' : 'edge-unmatched';
      note.textContent = join.compatible ? `✓ Matches ${join.kind === 'wall' ? 'wall' : 'neighboring floor'}` : join.reason;
      values.append(note);
    }
    row.append(heading, values); return row;
  }));
  const tags = Object.values(edges).flat();
  $('edge-note').textContent = tags.includes('join.manual') ? 'Manual placement: these edge directions need review before automatic joining.'
    : tags.includes('join.overlay') ? 'Overlay: this component sits on a floor and does not connect floor edges.'
    : 'Neighboring sides connect when their join tags match. Other tags describe the appearance or doorway state.';
  const fit = scene.edgeFit;
  $('edge-check').textContent = fit
    ? `Matching floor edges verified: ${fit.checkedJoins} floor joins and ${fit.checkedBoundaries} wall joins. ${fit.adjustedTiles} floor tiles adjusted, ${fit.rotatedTiles} rotated, ${fit.adjustedWalls || 0} wall variants fitted.`
    : `Matching floor edges verified across ${scene.floor.length} floor tiles.`;
}
function showConnections(enabled) {
  showConnectionOverlay = enabled;
  $('connection-controls').hidden = !enabled;
  canvas.classList.toggle('inspecting', enabled);
  if (enabled && !selectedMapCell) selectedMapCell = { ...(room.entrance || room.start) };
  draw();
}
function inspectMapCell(cell) {
  const placed = scene && inspectPlacedTile(scene, cell.x, cell.y);
  if (!placed) { generationFeedback('Choose a floor tile to inspect its connections.'); return; }
  selectedMapCell = cell;
  $('edge-asset').value = placed.piece.asset.id;
  $('edge-rotation').value = String(((Math.round((placed.piece.angle || 0) / (Math.PI / 2)) % 4) + 4) % 4);
  renderEdgeInspector(); draw();
  $('edge-inspector').open = true; infoOpenedFromMap = true;
  $('info-dialog').showModal(); $('edge-cell-summary').scrollIntoView({ block: 'center' });
}
function randomSeed() {
  const values = new Uint32Array(2); crypto.getRandomValues(values);
  return `dungeon-${values[0].toString(36)}-${values[1].toString(36)}`;
}
function seedMode() {
  $('seed-mode').textContent = $('fixed-seed').checked ? 'Fixed seed: Generate repeats this layout and settings.' : 'Each Generate chooses a new seed. Type a seed to lock it.';
  if (!generating) $('generate').textContent = $('fixed-seed').checked ? 'Regenerate' : 'Generate';
}
function generationFeedback(message, error = false) {
  clearTimeout(feedbackTimer);
  $('generation-feedback').textContent = message; $('generation-feedback').hidden = false;
  $('generation-feedback').classList.toggle('error', error);
  if (!error && !message.endsWith('…')) feedbackTimer = setTimeout(() => { $('generation-feedback').hidden = true; }, 5000);
}
function settingsFeedback() {
  $('settings-status').textContent = layoutDirty ? 'Settings changed. Generate to apply them.' : 'Appearance updates immediately. Generate to change the layout.';
  $('settings-status').classList.toggle('pending', layoutDirty);
}
function markLayoutChanged() {
  layoutDirty = true; settingsFeedback();
  status('Settings changed · Generate to apply. Play opens the map currently shown.');
}
function syncControls() {
  const pending = generating || artBusy;
  const nativeReady = Boolean(room && playable?.visuals && art && scene && !artError && !pending);
  $('settings').disabled = !manifest || pending;
  $('generate').disabled = !manifest || pending; $('reroll').disabled = !manifest || pending;
  $('apply-settings').disabled = !manifest || pending;
  $('open-export').disabled = !room || pending;
  $('open-info').disabled = !room;
  $('show-connections').disabled = !scene || pending;
  $('generate').setAttribute('aria-busy', String(generating));
  for (const id of ['play', 'confirm-play', 'map-json', 'png']) $(id).disabled = !nativeReady;
  for (const id of ['recipe', 'edit']) $(id).disabled = !room || pending;
  if (generating) $('generate').textContent = 'Generating…'; else seedMode();
}
function recordVisualSettings(target = room) {
  if (target) target.visualAuthoring = { schemaVersion: 1, styleId: $('art-style').value, kitId: $('art-theme').value, varyRoomMaterials: $('variety').checked };
}
function exactVisualMap(targetRoom, targetPlayable, targetScene) {
  targetPlayable.visuals = serializeNativeVisuals(targetScene, { styleId: $('art-style').value, kitId: $('art-theme').value, width: targetRoom.width, height: targetRoom.height, tiles: targetPlayable.tiles });
  recordVisualSettings(targetRoom);
}
async function generate({ fresh = !$('fixed-seed').checked, announce = true } = {}) {
  if (generating || artBusy) return false;
  const previous = { room, playable, art, scene, artError };
  const request = ++artRequest;
  let candidate, candidatePlayable;
  generating = true; syncControls();
  generationFeedback(fresh ? 'Creating a new dungeon…' : 'Rebuilding the fixed seed…');
  try {
    // Paint progress before generation and image loading, even for a warm cache.
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const options = settings(); if (fresh) options.seed = randomSeed();
    candidate = generateDungeon(manifest, options, rules); candidatePlayable = getPlayableMap(candidate, manifest);
    $('loading-message').textContent = 'Building the dungeon and loading its exact art…'; $('retry').hidden = true; $('loading').hidden = blueprint;
    $('canvas-wrap').setAttribute('aria-busy', 'true');
    const loaded = await loadArtKit(catalog, catalogURL, $('art-theme').value, $('art-style').value);
    if (request !== artRequest) return false;
    const candidateScene = buildArtScene(candidate, loaded, $('variety').checked);
    exactVisualMap(candidate, candidatePlayable, candidateScene);
    room = candidate; playable = candidatePlayable; art = loaded; scene = candidateScene; artError = false;
    $('seed').value = room.seed; zoom = 1; pan = { x: 0, y: 0 }; generationNumber++; layoutDirty = false; settingsFeedback();
    $('loading').hidden = true; updateSummary(); paletteLegend(); draw();
    if (announce) generationFeedback(`${fresh ? 'New dungeon ready' : 'Fixed seed rebuilt'} · ${room.rooms.length} rooms to explore`);
    else $('generation-feedback').hidden = true;
    status('Ready to play · Defeat all enemies to complete this dungeon.');
    return true;
  } catch (error) {
    // Generation is transactional: failed validation or art keeps the last map intact.
    ({ room, playable, art, scene, artError } = previous);
    if (!room && candidate) { room = candidate; playable = candidatePlayable; artError = true; recordVisualSettings(); updateSummary(); draw(); }
    $('loading').hidden = Boolean(art) || blueprint;
    if (!art) { $('loading-message').textContent = 'The dungeon art could not load. Try again, or use Blueprint.'; $('retry').hidden = false; }
    generationFeedback(`${previous.room ? 'Current dungeon kept. ' : ''}${error.message}`, true); status(error.message, true);
    return false;
  } finally {
    generating = false; $('canvas-wrap').setAttribute('aria-busy', 'false'); syncControls();
  }
}
async function updateArt() {
  if (!room || !catalog || generating) return;
  const request = ++artRequest; artBusy = true; artError = false; syncControls();
  $('loading-message').textContent = 'Loading this dungeon’s exact tile art…'; $('retry').hidden = true; $('loading').hidden = blueprint;
  $('canvas-wrap').setAttribute('aria-busy', 'true');
  try {
    const loaded = await loadArtKit(catalog, catalogURL, $('art-theme').value, $('art-style').value);
    if (request !== artRequest) return;
    const nextScene = buildArtScene(room, loaded, $('variety').checked);
    exactVisualMap(room, playable, nextScene);
    art = loaded; scene = nextScene; artError = false;
    $('loading').hidden = true; updateSummary(); paletteLegend(); draw();
    status(layoutDirty ? 'Appearance updated · Generate to apply your layout changes.' : 'Appearance updated · Play opens this exact map.');
  } catch (error) {
    if (request !== artRequest) return;
    artError = true; $('loading-message').textContent = 'This art could not load. Your previous map is kept; retry before playing.'; $('retry').hidden = false; $('loading').hidden = blueprint;
    status(error.message, true);
  } finally {
    if (request === artRequest) { artBusy = false; $('canvas-wrap').setAttribute('aria-busy', 'false'); syncControls(); }
  }
}
function draw() {
  if (!room) return;
  const bounds = $('canvas-wrap').getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
  if (!bounds.width || !bounds.height) return;
  canvas.width = Math.round(bounds.width * dpr); canvas.height = Math.round(bounds.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const mood = environmentMood(art?.kit.id || $('art-theme').value), glow = ctx.createRadialGradient(bounds.width * .5, bounds.height * .38, 0, bounds.width * .5, bounds.height * .5, Math.max(bounds.width, bounds.height) * .7);
  glow.addColorStop(0, mood.glow); glow.addColorStop(1, mood.background); ctx.fillStyle = glow; ctx.fillRect(0, 0, bounds.width, bounds.height);
  const angle = rotation * Math.PI / 2, cosine = Math.round(Math.cos(angle)), sine = Math.round(Math.sin(angle));
  const rotate = (x, y) => ({ x: x * cosine - y * sine, y: x * sine + y * cosine });
  const worldCorners = !blueprint && scene ? visibleSceneCorners(scene) : [{ x: -64, y: -64 }, { x: room.width * 128 - 64, y: -64 }, { x: -64, y: room.height * 128 - 64 }, { x: room.width * 128 - 64, y: room.height * 128 - 64 }];
  const corners = worldCorners.map(p => rotate(p.x, p.y));
  const minX = Math.min(...corners.map(p => p.x)), maxX = Math.max(...corners.map(p => p.x)), minY = Math.min(...corners.map(p => p.y)), maxY = Math.max(...corners.map(p => p.y));
  const padding = bounds.height < 280 ? 24 : 48;
  const scale = Math.max(.01, Math.min((bounds.width - padding) / (maxX - minX), (bounds.height - padding) / (maxY - minY), 1)) * zoom;
  const offsetX = (bounds.width - (maxX - minX) * scale) / 2 - minX * scale + pan.x, offsetY = (bounds.height - (maxY - minY) * scale) / 2 - minY * scale + pan.y;
  camera = { scale, offsetX, offsetY, angle };
  const project = cell => { const p = rotate(cell.x * 128, cell.y * 128); return { x: offsetX + p.x * scale, y: offsetY + p.y * scale }; };
  ctx.save(); ctx.translate(offsetX, offsetY); ctx.scale(scale, scale); ctx.rotate(angle); ctx.imageSmoothingEnabled = $('art-style').value !== 'pocket-dungeon';
  if (blueprint) {
    const blocked = new Set(room.blockedCells.map(p => `${p.x},${p.y}`));
    for (let y = 0; y < room.height; y++) for (let x = 0; x < room.width; x++) {
      ctx.fillStyle = blocked.has(`${x},${y}`) ? '#203136' : '#749789'; ctx.fillRect(x * 128 - 62, y * 128 - 62, 124, 124);
      ctx.strokeStyle = '#c6d9cf22'; ctx.lineWidth = 1 / scale; ctx.strokeRect(x * 128 - 62, y * 128 - 62, 124, 124);
    }
  } else if (scene && art) {
    drawFloorLayer(ctx, scene.floor, art.images);
  }
  if ($('grid').checked && !blueprint && scene) {
    ctx.strokeStyle = '#70c6d166'; ctx.lineWidth = 1 / scale;
    scene.floor.forEach(piece => ctx.strokeRect(piece.px - 64, piece.py - 64, 128, 128));
  }
  if ($('route').checked && room.clearRoute.length) {
    ctx.beginPath(); room.clearRoute.forEach((cell, index) => ctx[index ? 'lineTo' : 'moveTo'](cell.x * 128, cell.y * 128));
    ctx.strokeStyle = '#f9d18c'; ctx.lineWidth = 2.5 / scale; ctx.lineCap = 'round'; ctx.setLineDash([6 / scale, 5 / scale]); ctx.stroke(); ctx.setLineDash([]);
  }
  if (!blueprint && scene && art) {
    scene.structures.forEach(piece => drawPiece(ctx, piece, art));
    ctx.strokeStyle = '#d2bd8ca6'; ctx.lineWidth = 1.1 / scale;
    scene.decorations.filter(piece => piece.kind === 'obstacle').forEach(piece => ctx.strokeRect(piece.px - 45, piece.py - 45, 90, 90));
    scene.decorations.forEach(piece => drawPiece(ctx, piece, art));
  }
  if (showConnectionOverlay && scene) {
    const { connections } = sceneConnections(scene);
    $('connection-summary').textContent = `${connections.filter(join => join.compatible).length} matching joins · select a tile`;
    ctx.lineWidth = 2 / scale; ctx.lineCap = 'round';
    for (const join of connections) {
      const [dx, dy] = EDGE_DIRECTIONS[join.side], x = join.x * 128 + dx * 64, y = join.y * 128 + dy * 64;
      ctx.strokeStyle = join.compatible ? '#8cf2ba' : '#ff8b7a'; ctx.beginPath();
      ctx.moveTo(x - dy * 15, y + dx * 15); ctx.lineTo(x + dy * 15, y - dx * 15); ctx.stroke();
    }
    if (selectedMapCell) { ctx.strokeStyle = '#ffdb8d'; ctx.strokeRect(selectedMapCell.x * 128 - 60, selectedMapCell.y * 128 - 60, 120, 120); }
  }
  ctx.restore();
  // Screen-space labels remain readable while their cell corners rotate with the map.
  for (const tile of playable.tiles) terrainTypes.filter(type => tile.tags.includes(type.tag)).forEach((type, index) => {
    const corner = rotate(tile.x * 128 - 43, tile.y * 128 - 43), x = offsetX + corner.x * scale + index * 12, y = offsetY + corner.y * scale;
    ctx.fillStyle = '#101b1e'; ctx.fillRect(x - 6, y - 6, 12, 12); ctx.strokeStyle = type.color; ctx.lineWidth = 1; ctx.strokeRect(x - 6, y - 6, 12, 12);
    ctx.fillStyle = type.color; ctx.font = 'bold 8px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(type.letter, x, y + .5);
  });
  const entrance = room.entrance || room.start;
  function actor(cell, color, text) {
    if (!cell) return; const p = project(cell);
    ctx.beginPath(); ctx.arc(p.x, p.y, 6.5, 0, Math.PI * 2); ctx.fillStyle = '#132225'; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = color; ctx.stroke();
    ctx.font = 'bold 9px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = color; ctx.fillText(text, p.x, p.y);
  }
  (playable.playerSpawns || []).forEach((cell, index) => { const position = cell.position || cell; if (position.x !== entrance.x || position.y !== entrance.y) actor(position, '#b5ebd8', String(index + 1)); });
  (playable.enemies || []).forEach(cell => actor(cell.position || cell, '#ffaaa1', '!'));
  function endpoint(cell, text, color) {
    const p = project(cell), width = text === 'ENTER' ? 61 : 52;
    const x = Math.max(10, Math.min(bounds.width - width - 10, p.x + 13)), y = Math.max(11, Math.min(bounds.height - 35, p.y - 34));
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(x + 8, y + 23); ctx.stroke();
    ctx.beginPath(); ctx.arc(p.x, p.y, 8, 0, Math.PI * 2); ctx.stroke(); ctx.fillStyle = '#101b1e'; ctx.fillRect(x, y, width, 25); ctx.strokeRect(x, y, width, 25);
    ctx.fillStyle = color; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, x + width / 2, y + 13);
  }
  endpoint(entrance, 'ENTER', '#b8f1d4'); endpoint(room.exit, 'EXIT', '#ffce79');
  $('view-label').textContent = `${blueprint ? 'BLUEPRINT' : 'SQUARE'} / ${rotation * 90}° · ${Math.round(zoom * 100)}%`;
  canvas.classList.toggle('zoomed', zoom > 1);
  updateSummary();
}
function download(data, name, type = 'application/json') {
  const blob = data instanceof Blob ? data : new Blob([typeof data === 'string' ? data : JSON.stringify(data, null, 2)], { type });
  const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function setView(nextBlueprint) {
  blueprint = nextBlueprint; $('square').setAttribute('aria-pressed', String(!blueprint)); $('blueprint').setAttribute('aria-pressed', String(blueprint));
  $('loading').hidden = blueprint || Boolean(art); if (!blueprint && artError) $('retry').hidden = false; draw();
}
// One set of settings moves into the phone dialog; values and listeners survive
// breakpoint changes, and desktop and mobile cannot disagree about the next map.
const compactViewport = matchMedia('(max-width: 760px), (max-height: 500px)');
function positionSettings() {
  const dialog = $('settings-dialog');
  if (!compactViewport.matches && dialog.open) dialog.close();
  (compactViewport.matches ? $('mobile-controls') : $('desktop-controls')).append($('controls'));
}
for (const name of ['settings', 'export', 'info']) {
  const dialog = $(`${name}-dialog`), opener = $(`open-${name}`);
  opener.onclick = () => {
    dialog.querySelectorAll('.dialog-error').forEach(node => node.remove());
    if (name === 'info') renderEdgeInspector();
    dialog.showModal();
  };
  $(`close-${name}`).onclick = () => dialog.close();
  dialog.addEventListener('close', () => { if (opener.getClientRects().length) opener.focus(); });
}
compactViewport.addEventListener('change', positionSettings); positionSettings(); settingsFeedback();
$('edge-asset').addEventListener('change', () => { selectedMapCell = null; renderEdgeInspector(); draw(); });
$('edge-rotation').addEventListener('change', () => { selectedMapCell = null; renderEdgeInspector(); draw(); });
$('show-connections').onclick = () => { showConnections(true); infoOpenedFromMap = true; $('info-dialog').close(); };
$('hide-connections').onclick = () => { showConnections(false); canvas.focus(); };
$('info-dialog').addEventListener('close', () => { if (infoOpenedFromMap) { infoOpenedFromMap = false; canvas.focus(); } });
$('apply-settings').onclick = () => { $('settings-dialog').close(); safely(() => generate()); };
$('generate').onclick = () => safely(() => generate());
$('reroll').onclick = () => { $('fixed-seed').checked = false; seedMode(); safely(() => generate({ fresh: true })); };
$('seed').addEventListener('input', () => { $('fixed-seed').checked = true; seedMode(); markLayoutChanged(); });
$('fixed-seed').addEventListener('change', seedMode);
for (const id of ['width', 'height', 'layout', 'biome']) $(id).addEventListener('input', markLayoutChanged);
for (const id of ['rooms', 'density']) $(id).oninput = () => { $(`${id}-value`).textContent = $(id).value + (id === 'density' ? '%' : ''); markLayoutChanged(); };
for (const id of ['art-style', 'art-theme']) $(id).onchange = () => safely(updateArt);
$('variety').onchange = () => {
  if (!art || !room) return;
  const previous = room.visualAuthoring.varyRoomMaterials;
  try {
    const candidate = buildArtScene(room, art, $('variety').checked);
    exactVisualMap(room, playable, candidate);
    scene = candidate; paletteLegend(); draw(); syncControls();
  } catch (error) {
    $('variety').checked = previous;
    status(error.message, true); generationFeedback(error.message, true);
  }
};
$('square').onclick = () => setView(false); $('blueprint').onclick = () => setView(true);
$('rotate-left').onclick = () => { rotation = (rotation + 3) % 4; draw(); }; $('rotate-right').onclick = () => { rotation = (rotation + 1) % 4; draw(); };
function fitMap() { zoom = 1; pan = { x: 0, y: 0 }; draw(); }
function zoomMap(factor) { zoom = Math.max(.65, Math.min(3, zoom * factor)); if (zoom <= 1) pan = { x: 0, y: 0 }; draw(); }
$('fit').onclick = fitMap; $('zoom-in').onclick = () => zoomMap(1.25); $('zoom-out').onclick = () => zoomMap(.8); $('route').onchange = draw; $('grid').onchange = draw;
canvas.addEventListener('wheel', event => {
  if (!room || event.ctrlKey) return;
  event.preventDefault(); zoomMap(event.deltaY < 0 ? 1.12 : 1 / 1.12);
}, { passive: false });
let drag, dragged = false;
canvas.addEventListener('pointerdown', event => { dragged = false; if (zoom <= 1) return; drag = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y }; canvas.setPointerCapture(event.pointerId); canvas.classList.add('dragging'); });
canvas.addEventListener('pointermove', event => { if (!drag) return; dragged ||= Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 5; pan = { x: drag.panX + event.clientX - drag.x, y: drag.panY + event.clientY - drag.y }; draw(); });
function endDrag() { drag = null; canvas.classList.remove('dragging'); }
canvas.addEventListener('pointerup', endDrag); canvas.addEventListener('pointercancel', endDrag);
canvas.addEventListener('click', event => {
  if (!showConnectionOverlay || dragged || !camera) return;
  const bounds = canvas.getBoundingClientRect();
  inspectMapCell(pickPreviewCell(event.clientX - bounds.left, event.clientY - bounds.top, camera));
});
canvas.addEventListener('keydown', event => {
  if (showConnectionOverlay && event.key === 'Escape') { event.preventDefault(); showConnections(false); }
  else if (showConnectionOverlay && event.key === 'Enter') { event.preventDefault(); inspectMapCell(selectedMapCell || room.entrance || room.start); }
  else if (showConnectionOverlay && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
    event.preventDefault();
    const cell = selectedMapCell || room.entrance || room.start;
    const dx = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0, dy = event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0;
    const cosine = Math.round(Math.cos(rotation * Math.PI / 2)), sine = Math.round(Math.sin(rotation * Math.PI / 2));
    selectedMapCell = { x: Math.max(0, Math.min(room.width - 1, cell.x + dx * cosine + dy * sine)),
      y: Math.max(0, Math.min(room.height - 1, cell.y - dx * sine + dy * cosine)) };
    draw(); status(`Inspecting column ${selectedMapCell.x + 1}, row ${selectedMapCell.y + 1}. Press Enter for edge details.`);
  }
  else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomMap(1.25); }
  else if (event.key === '-') { event.preventDefault(); zoomMap(.8); }
  else if (event.key === 'Home') { event.preventDefault(); fitMap(); }
  else if (zoom > 1 && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) { event.preventDefault(); pan.x += event.key === 'ArrowLeft' ? 40 : event.key === 'ArrowRight' ? -40 : 0; pan.y += event.key === 'ArrowUp' ? 40 : event.key === 'ArrowDown' ? -40 : 0; draw(); }
});
$('recipe').onclick = () => safely(() => download(room, 'dungeon-recipe.json'));
$('map-json').onclick = () => safely(() => download(playable, 'dungeon-playable-map.json'));
$('png').onclick = () => canvas.toBlob(blob => { if (blob) download(blob, 'dungeon-snapshot.png'); else status('Could not create snapshot.', true); }, 'image/png');
$('edit').onclick = () => safely(() => { localStorage.setItem('dct.workshop-recipe', JSON.stringify(room)); location.href = 'room-kit.html?import=generator'; });
$('play').onclick = () => { if (!$('play').disabled) { $('play-map-summary').textContent = `${room.seed} · ${room.width} × ${room.height} · ${art.kit.title} · ${$('art-style').selectedOptions[0].textContent}`; $('play-dialog').showModal(); } };
$('play-dialog').addEventListener('close', () => {
  if ($('play-dialog').returnValue !== 'play' || $('play').disabled) return;
  safely(() => {
    const token = crypto.randomUUID(), serialized = JSON.stringify(playable);
    // A per-tab immutable packet cannot be replaced by another generator tab.
    sessionStorage.setItem(`dct.workshop-map.${token}`, serialized);
    const exploring = $('explore-first').checked;
    if (exploring) sessionStorage.setItem(`dct.workshop-map.${token}.exploration`, JSON.stringify({entrance:room.entrance || room.start,exit:room.exit}));
    try { localStorage.setItem('dct.workshop-map', serialized); } catch { /* The per-tab packet is sufficient. */ }
    location.href = `index.html?workshop=1&map=${encodeURIComponent(token)}${exploring ? '&explore=1' : ''}`;
  });
});
$('retry').onclick = () => safely(() => room ? updateArt() : load());
new ResizeObserver(draw).observe($('canvas-wrap'));
async function load() {
  try {
    [manifest, rules, catalog] = await Promise.all([fetchJSON('assets/room-kit/manifest.json'), fetchJSON('assets/map-generation-rules.json'), fetchJSON(catalogURL)]);
    $('art-style').replaceChildren(...catalog.styles.map(style => new Option(style.title, style.id)));
    $('art-theme').replaceChildren(...catalog.kits.map(kit => new Option(kit.title, kit.id))); $('art-theme').value = 'starter-dungeon';
    await generate({ fresh: false, announce: false }); document.querySelectorAll('.workspace button,.workspace input').forEach(control => control.disabled = false); syncControls();
  } catch (error) { $('loading-message').textContent = 'The map resources could not load.'; $('retry').hidden = false; status(error.message, true); }
}
load();
