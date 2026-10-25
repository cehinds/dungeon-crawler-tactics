import { generateDungeon, getPlayableMap } from './procedural-map.js';
import { fetchJSON, loadArtKit, buildArtScene, drawPiece, revisionURL, environmentMood, visibleSceneCorners } from './generator-art.js';
const $ = id => document.getElementById(id), canvas = $('map'), ctx = canvas.getContext('2d');
const terrainTypes = [{ tag: 'surface.water', letter: 'W', label: 'Water', color: '#82d6ff' }, { tag: 'surface.oil', letter: 'O', label: 'Oil', color: '#d4bbf2' }, { tag: 'surface.burning', letter: 'F', label: 'Fire', color: '#ffb17a' }];
const catalogURL = new URL('assets/book-tiles/catalog.json', location.href);
let manifest, rules, catalog, room, playable, art, scene, rotation = 0, blueprint = false, artRequest = 0, artError = false, zoom = 1, pan = { x: 0, y: 0 };
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
async function safely(action) { try { await action(); } catch (error) { status(error.message, true); } }
function settings() {
  for (const [id, max] of [['width', 20], ['height', 16]]) { const value = Number($(id).value); if (!Number.isInteger(value) || value < 6 || value > max) throw new Error(`${id === 'width' ? 'Width' : 'Height'} must be a whole number from 6 to ${max}.`); }
  return { seed: $('seed').value, width: Number($('width').value), height: Number($('height').value), layout: $('layout').value, biome: $('biome').value, roomCount: Number($('rooms').value), density: Number($('density').value) / 100 };
}
function updateSummary() {
  const entrance = room.entrance || room.start;
  $('ambience-info').textContent = environmentMood($('art-theme').value).label;
  $('map-title').textContent = `${art?.kit.title || $('art-theme').selectedOptions[0]?.textContent || 'Dungeon'} / ${room.seed || 'untitled'}`;
  $('counts').textContent = `${room.rooms.length} rooms · ${room.corridors.length} connections · ${room.clearRoute.length} route cells`;
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
  for (const style of scene.roomStyles) {
    const row = document.createElement('div'); row.className = 'room-palette';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'), image = document.createElementNS('http://www.w3.org/2000/svg', 'image');
    const crop = style.asset.derived; svg.setAttribute('viewBox', `${crop.offset.x} ${crop.offset.y} ${crop.width} ${crop.height}`); svg.setAttribute('aria-hidden', 'true');
    image.setAttribute('href', revisionURL(style.asset.file, art.manifestURL, [style.asset.source, style.asset.derived])); image.setAttribute('width', '256'); image.setAttribute('height', '256'); svg.append(image);
    const copy = document.createElement('span'), title = document.createElement('strong'), label = document.createElement('span');
    title.textContent = `Room ${style.index + 1}`; label.textContent = style.asset.label; copy.append(title, label); row.append(svg, copy); $('room-palettes').append(row);
  }
}
async function generate() {
  const next = generateDungeon(manifest, settings(), rules), nextPlayable = getPlayableMap(next, manifest);
  room = next; playable = nextPlayable; zoom = 1; pan = { x: 0, y: 0 };
  updateSummary(); await updateArt();
}
function recordVisualSettings() {
  if (room) room.visualAuthoring = { schemaVersion: 1, styleId: $('art-style').value, kitId: $('art-theme').value, varyRoomMaterials: $('variety').checked };
}
async function updateArt() {
  if (!room || !catalog) return;
  recordVisualSettings();
  const request = ++artRequest; art = null; scene = null; artError = false;
  $('loading-message').textContent = 'Loading this environment’s square tiles…'; $('retry').hidden = true; $('loading').hidden = blueprint;
  $('canvas-wrap').setAttribute('aria-busy', 'true'); paletteLegend(); draw();
  try {
    const loaded = await loadArtKit(catalog, catalogURL, $('art-theme').value, $('art-style').value);
    if (request !== artRequest) return;
    art = loaded; scene = buildArtScene(room, art, $('variety').checked);
    $('loading').hidden = true; $('canvas-wrap').setAttribute('aria-busy', 'false');
    updateSummary(); paletteLegend(); draw();
    status(`${room.width} × ${room.height} cells · ${art.kit.title} · ${$('art-style').selectedOptions[0].textContent}. Entrance and exit are connected; preview art stays separate from playable exports.`);
  } catch (error) {
    if (request !== artRequest) return;
    artError = true; $('loading-message').textContent = 'The art could not load. Try again, or use Blueprint.'; $('retry').hidden = false; $('loading').hidden = blueprint; $('canvas-wrap').setAttribute('aria-busy', 'false'); status(error.message, true);
  }
}
function draw() {
  if (!room) return;
  const bounds = $('canvas-wrap').getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
  if (!bounds.width || !bounds.height) return;
  canvas.width = Math.round(bounds.width * dpr); canvas.height = Math.round(bounds.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const mood = environmentMood($('art-theme').value), glow = ctx.createRadialGradient(bounds.width * .5, bounds.height * .38, 0, bounds.width * .5, bounds.height * .5, Math.max(bounds.width, bounds.height) * .7);
  glow.addColorStop(0, mood.glow); glow.addColorStop(1, mood.background); ctx.fillStyle = glow; ctx.fillRect(0, 0, bounds.width, bounds.height);
  const angle = rotation * Math.PI / 2, cosine = Math.round(Math.cos(angle)), sine = Math.round(Math.sin(angle));
  const rotate = (x, y) => ({ x: x * cosine - y * sine, y: x * sine + y * cosine });
  const worldCorners = !blueprint && scene ? visibleSceneCorners(scene) : [{ x: -64, y: -64 }, { x: room.width * 128 - 64, y: -64 }, { x: -64, y: room.height * 128 - 64 }, { x: room.width * 128 - 64, y: room.height * 128 - 64 }];
  const corners = worldCorners.map(p => rotate(p.x, p.y));
  const minX = Math.min(...corners.map(p => p.x)), maxX = Math.max(...corners.map(p => p.x)), minY = Math.min(...corners.map(p => p.y)), maxY = Math.max(...corners.map(p => p.y));
  const scale = Math.max(.01, Math.min((bounds.width - 65) / (maxX - minX), (bounds.height - 70) / (maxY - minY), 1)) * zoom;
  const offsetX = (bounds.width - (maxX - minX) * scale) / 2 - minX * scale + pan.x, offsetY = (bounds.height - (maxY - minY) * scale) / 2 - minY * scale + pan.y;
  const project = cell => { const p = rotate(cell.x * 128, cell.y * 128); return { x: offsetX + p.x * scale, y: offsetY + p.y * scale }; };
  ctx.save(); ctx.translate(offsetX, offsetY); ctx.scale(scale, scale); ctx.rotate(angle); ctx.imageSmoothingEnabled = $('art-style').value !== 'pocket-dungeon';
  if (blueprint) {
    const blocked = new Set(room.blockedCells.map(p => `${p.x},${p.y}`));
    for (let y = 0; y < room.height; y++) for (let x = 0; x < room.width; x++) {
      ctx.fillStyle = blocked.has(`${x},${y}`) ? '#203136' : '#749789'; ctx.fillRect(x * 128 - 62, y * 128 - 62, 124, 124);
      ctx.strokeStyle = '#c6d9cf22'; ctx.lineWidth = 1 / scale; ctx.strokeRect(x * 128 - 62, y * 128 - 62, 124, 124);
    }
  } else if (scene && art) {
    scene.floor.forEach(piece => drawPiece(ctx, piece, art));
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
$('generate').onclick = () => safely(generate);
$('reroll').onclick = () => { const values = new Uint32Array(1); crypto.getRandomValues(values); $('seed').value = `dungeon-${values[0].toString(36)}`; safely(generate); };
for (const id of ['rooms', 'density']) $(id).oninput = () => { $(`${id}-value`).textContent = $(id).value + (id === 'density' ? '%' : ''); };
for (const id of ['art-style', 'art-theme']) $(id).onchange = () => safely(updateArt);
$('variety').onchange = () => { if (art && room) { recordVisualSettings(); scene = buildArtScene(room, art, $('variety').checked); paletteLegend(); draw(); } };
$('square').onclick = () => setView(false); $('blueprint').onclick = () => setView(true);
$('rotate-left').onclick = () => { rotation = (rotation + 3) % 4; draw(); }; $('rotate-right').onclick = () => { rotation = (rotation + 1) % 4; draw(); };
function fitMap() { zoom = 1; pan = { x: 0, y: 0 }; draw(); }
function zoomMap(factor) { zoom = Math.max(.65, Math.min(3, zoom * factor)); if (zoom <= 1) pan = { x: 0, y: 0 }; draw(); }
$('fit').onclick = fitMap; $('zoom-in').onclick = () => zoomMap(1.25); $('zoom-out').onclick = () => zoomMap(.8); $('route').onchange = draw; $('grid').onchange = draw;
let drag;
canvas.addEventListener('pointerdown', event => { if (zoom <= 1) return; drag = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y }; canvas.setPointerCapture(event.pointerId); canvas.classList.add('dragging'); });
canvas.addEventListener('pointermove', event => { if (!drag) return; pan = { x: drag.panX + event.clientX - drag.x, y: drag.panY + event.clientY - drag.y }; draw(); });
function endDrag() { drag = null; canvas.classList.remove('dragging'); }
canvas.addEventListener('pointerup', endDrag); canvas.addEventListener('pointercancel', endDrag);
canvas.addEventListener('keydown', event => {
  if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomMap(1.25); }
  else if (event.key === '-') { event.preventDefault(); zoomMap(.8); }
  else if (event.key === 'Home') { event.preventDefault(); fitMap(); }
  else if (zoom > 1 && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) { event.preventDefault(); pan.x += event.key === 'ArrowLeft' ? 40 : event.key === 'ArrowRight' ? -40 : 0; pan.y += event.key === 'ArrowUp' ? 40 : event.key === 'ArrowDown' ? -40 : 0; draw(); }
});
$('recipe').onclick = () => safely(() => download(room, 'dungeon-recipe.json'));
$('map-json').onclick = () => safely(() => download(playable, 'dungeon-playable-map.json'));
$('png').onclick = () => canvas.toBlob(blob => { if (blob) download(blob, 'dungeon-snapshot.png'); else status('Could not create snapshot.', true); }, 'image/png');
$('edit').onclick = () => safely(() => { localStorage.setItem('dct.workshop-recipe', JSON.stringify(room)); location.href = 'room-kit.html?import=generator'; });
$('play').onclick = () => $('play-dialog').showModal();
$('play-dialog').addEventListener('close', () => { if ($('play-dialog').returnValue === 'play') safely(() => { localStorage.setItem('dct.workshop-map', JSON.stringify(playable)); location.href = 'index.html?workshop=1'; }); });
$('retry').onclick = () => safely(() => room ? updateArt() : load());
new ResizeObserver(draw).observe($('canvas-wrap'));
async function load() {
  try {
    [manifest, rules, catalog] = await Promise.all([fetchJSON('assets/room-kit/manifest.json'), fetchJSON('assets/map-generation-rules.json'), fetchJSON(catalogURL)]);
    $('art-style').replaceChildren(...catalog.styles.map(style => new Option(style.title, style.id)));
    $('art-theme').replaceChildren(...catalog.kits.map(kit => new Option(kit.title, kit.id))); $('art-theme').value = 'starter-dungeon';
    await generate(); $('settings').disabled = false; document.querySelectorAll('.workspace button,.workspace input').forEach(control => control.disabled = false);
  } catch (error) { $('loading-message').textContent = 'The map resources could not load.'; $('retry').hidden = false; status(error.message, true); }
}
load();
