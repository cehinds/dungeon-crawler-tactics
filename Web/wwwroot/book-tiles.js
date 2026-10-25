import { drawFloorLayer } from './tile-surface-renderer.js';
import { composeKit, worldContacts } from './book-tile-layout.js';
const $ = id => document.getElementById(id);
const catalogURL = new URL('assets/book-tiles/catalog.json', document.baseURI);
const state = { catalog: null, style: '', book: 'all', search: '', location: '', kit: '', manifest: null, manifestURL: null, images: new Map(), seed: 1, request: 0 };
const manifestCache = new Map();
const imageCache = new Map();
const imageCacheLimit = 96;
const asArray = value => Array.isArray(value) ? value : value == null ? [] : [value];
const words = value => String(value ?? '').replaceAll('_', ' ').replaceAll('-', ' ');
const resolve = (path, base = catalogURL) => new URL(path, base).href;
// Stable content revisions prevent previously viewed tiles surviving a redraw in cache.
function revisedURL(path, base, metadata) {
  let hash = 2166136261;
  for (const character of JSON.stringify(metadata)) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  const url = new URL(path, base); url.searchParams.set('v', (hash >>> 0).toString(16)); return url.href;
}
function componentURL(asset, manifestURL) { return revisedURL(asset.file, manifestURL, [asset.source, asset.derived]); }


function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content != null) node.textContent = content;
  return node;
}
function option(value, label) { const node = element('option', '', label); node.value = value; return node; }
function link(text, href, download = false) {
  const node = element('a', '', text); node.href = href;
  if (download) node.download = ''; else { node.target = '_blank'; node.rel = 'noopener'; }
  return node;
}
async function fetchJSON(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`The library returned HTTP ${response.status}. Please try again.`);
  return response.json();
}
function showError(error) {
  $('load-status').hidden = true;
  $('load-error').hidden = false;
  $('error-detail').textContent = error.message || 'Please check your connection and try again.';
  $('collection').setAttribute('aria-busy', 'false');
}
function matchesBook(item) { return state.book === 'all' || asArray(item.books).some(book => String(book) === state.book); }
function filteredLocations() {
  return state.catalog.locations.filter(location => matchesBook(location) && [location.name, ...asArray(location.aliases)].join(' ').toLocaleLowerCase().includes(state.search));
}
function selectedLocation() { return state.catalog.locations.find(location => location.id === state.location); }
function selectedKit() { return state.catalog.kits.find(kit => kit.id === state.kit); }
function selectedStyle() { return state.catalog.styles.find(style => style.id === state.style); }
function setFact(label, value) {
  $('location-facts').append(element('dt', '', label), element('dd', '', value));
}
function appearanceLabel(appearance) {
  const value = words(typeof appearance === 'object' ? appearance.status || appearance.type : appearance);
  if (!value) return 'Not established';
  return value.charAt(0).toUpperCase() + value.slice(1);
}
function renderLocation() {
  const location = selectedLocation();
  if (!location) return;
  $('location-title').textContent = location.name;
  $('location-summary').textContent = location.summary || location.canonSummary || 'See the source links for the evidence available for this location.';
  $('location-facts').replaceChildren();
  setFact('Book', asArray(location.books).map(book => `Book ${book}`).join(', '));
  setFact('Floor', asArray(location.floors ?? location.floor).length ? asArray(location.floors ?? location.floor).join(', ') : 'Surface / not specified');
  setFact('Appearance', appearanceLabel(location.appearance ?? location.visitStatus));
  setFact('Confidence', typeof location.confidence === 'object' ? location.confidence.level || JSON.stringify(location.confidence) : location.confidence || 'Not established');
  const sources = asArray(location.sourceUrls).map(source => typeof source === 'string' ? { url: source } : source).filter(source => /^https?:\/\//.test(source.url));
  $('source-count').textContent = `(${sources.length})`;
  $('source-list').replaceChildren(...sources.map((source, index) => {
    const row = element('li');
    let domain = ''; try { domain = new URL(source.url).hostname.replace(/^www\./, ''); } catch { /* Invalid URLs are excluded above. */ }
    row.append(link(source.title || `Source ${index + 1} · ${domain}`, source.url)); return row;
  }));
  const evidence = location.evidenceNote || location.notes || '';
  $('location-evidence').textContent = typeof evidence === 'string' ? evidence : JSON.stringify(evidence);
}
function updateLocations() {
  const locations = filteredLocations();
  if (!locations.some(location => location.id === state.location)) state.location = locations[0]?.id || '';
  $('location-select').replaceChildren(...locations.map(location => option(location.id, location.name)));
  $('location-select').value = state.location;
  $('location-select').disabled = !locations.length;
  $('location-count').textContent = `${locations.length} matching ${locations.length === 1 ? 'location' : 'locations'} · source-based survey, with spoilers through book 8`;
  $('empty-state').hidden = Boolean(locations.length);
  $('location-workspace').hidden = !locations.length;
  if (!locations.length) { state.request++; return; }
  renderLocation();
  updateKits();
}
function updateKits() {
  const location = selectedLocation();
  const kits = state.catalog.kits.filter(kit => asArray(location?.kitIds).includes(kit.id));
  if (!kits.some(kit => kit.id === state.kit)) state.kit = kits[0]?.id || '';
  $('kit-select').replaceChildren(...kits.map(kit => option(kit.id, kit.title)));
  $('kit-select').value = state.kit;
  $('kit-select').disabled = kits.length < 2;
  if (!kits.length) {
    state.request++; state.manifest = null;
    $('kit-title').textContent = 'No authored kit mapped yet';
    $('kit-description').textContent = 'This location is retained as research evidence.';
    $('tile-grid').replaceChildren(); $('asset-status').textContent = '';
    $('map-status').hidden = false; $('map-status').textContent = 'No tile kit is available for this location.';
    $('regenerate').disabled = true;
    document.querySelector('.kit-tools').hidden = true;
    return;
  }
  document.querySelector('.kit-tools').hidden = false;
  loadKit();
}
function renderTabs() {
  $('style-tabs').replaceChildren(...state.catalog.styles.map((style, index) => {
    const tab = element('button', 'style-tab'); tab.type = 'button'; tab.role = 'tab'; tab.id = `tab-${style.id}`;
    tab.setAttribute('aria-controls', 'collection'); tab.setAttribute('aria-selected', String(style.id === state.style)); tab.tabIndex = style.id === state.style ? 0 : -1;
    tab.append(element('span', 'tab-number', String(index + 1).padStart(2, '0')));
    const copy = element('span', 'tab-copy'); copy.append(element('span', 'tab-title', style.title), element('span', 'tab-description', `${style.projection === 'orthogonal' ? 'Square grid' : 'Isometric'} · ${style.tileWidth} × ${style.tileHeight}`)); tab.append(copy);
    tab.addEventListener('click', () => changeStyle(style.id));
    tab.addEventListener('keydown', event => {
      const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End']; if (!keys.includes(event.key)) return;
      event.preventDefault(); const count = state.catalog.styles.length;
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? count - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + count) % count;
      changeStyle(state.catalog.styles[next].id); $(`tab-${state.style}`).focus();
    }); return tab;
  }));
  $('collection').setAttribute('aria-labelledby', `tab-${state.style}`);
}
function changeStyle(id) {
  if (id === state.style) return;
  state.style = id; renderTabs(); updateStyleHeading(); if (state.location) loadKit();
}
function updateStyleHeading() {
  const style = selectedStyle(); $('style-title').textContent = style.title;
  $('collection').classList.toggle('pixel-art', state.style === 'pocket-dungeon');
  const total = state.catalog.kits.length * state.catalog.styles.length * 24;
  $('library-count').textContent = `${state.catalog.locations.length} researched locations · ${state.catalog.kits.length} environment kits · ${total.toLocaleString()} PNG tiles across three styles`;
}
function imageFor(url) {
  const cached = imageCache.get(url);
  if (cached) {
    imageCache.delete(url);
    imageCache.set(url, cached);
    return cached;
  }
  const pending = new Promise((resolveImage, reject) => {
    const image = new Image();
    image.onload = () => resolveImage(image);
    image.onerror = () => {
      if (imageCache.get(url) === pending) imageCache.delete(url);
      reject(new Error('A tile image could not be loaded. Try again to reload the kit.'));
    };
    image.src = url;
  });
  imageCache.set(url, pending);
  // Active compositions retain their own image references when older cache entries leave.
  while (imageCache.size > imageCacheLimit) imageCache.delete(imageCache.keys().next().value);
  return pending;
}
function edgeDetails(asset) {
  const details = element('details', 'tile-edges');
  details.append(element('summary', '', 'Edge tags'));
  details.append(element('p', 'edge-note', 'Local orientation · north up · 0° rotation'));
  const sides = [['north', 'N · North'], ['east', 'E · East'], ['south', 'S · South'], ['west', 'W · West']];
  const list = element('dl', 'edge-sides');
  const allTags = [];
  for (const [side, label] of sides) {
    const tags = asArray(asset.edges?.[side]);
    allTags.push(...tags);
    const values = element('dd', 'edge-chips');
    for (const tag of tags) values.append(element('code', 'edge-chip', tag));
    if (!tags.length) values.append(element('span', 'edge-note', 'Not authored'));
    list.append(element('dt', '', label), values);
  }
  details.append(list);
  if (allTags.includes('join.manual')) details.append(element('p', 'edge-note edge-review', 'Manual connection · requires review.'));
  if (allTags.includes('join.overlay')) details.append(element('p', 'edge-note', 'Visual overlay · no automatic joining.'));
  return details;
}
function renderTiles(manifest, manifestURL) {
  $('tile-grid').replaceChildren(...manifest.assets.map(asset => {
    const card = element('article', 'tile-card');
    const url = componentURL(asset, manifestURL);
    const preview = link('', url, true); preview.className = 'tile-image checkerboard'; preview.setAttribute('aria-label', `Download ${asset.label} PNG`);
    // Zoom to the declared visible export rectangle; downloads retain the full canvas.
    const namespace = 'http://www.w3.org/2000/svg';
    const thumbnail = document.createElementNS(namespace, 'svg');
    const derived = asset.derived;
    const crop = derived?.width > 0 && derived?.height > 0 && derived.offset ? `${derived.offset.x} ${derived.offset.y} ${derived.width} ${derived.height}` : '0 0 256 256';
    thumbnail.setAttribute('viewBox', crop); thumbnail.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    thumbnail.setAttribute('role', 'img'); thumbnail.setAttribute('aria-label', asset.label);
    const image = document.createElementNS(namespace, 'image');
    image.setAttribute('href', url); image.setAttribute('width', String(asset.width || 256)); image.setAttribute('height', String(asset.height || 256));
    image.addEventListener('error', () => preview.replaceChildren(element('span', 'image-failure', 'Image unavailable. Use Try again above to reload.')));
    thumbnail.append(image); preview.append(thumbnail);
    card.append(preview, element('h3', '', asset.label), element('p', 'tile-meta', `${words(asset.layer)} layer · ${words(asset.role)}`), element('p', 'tile-tags', asArray(asset.tags).map(words).join(' · ')));
    if (asset.role === 'ground' && asset.cell < 4 && !asset.placement) card.append(element('p', 'tile-meta', 'Irregular support: manual alignment required.'));
    card.append(edgeDetails(asset));
    const download = link('Download PNG ↓', url, true); download.className = 'tile-download'; card.append(download); return card;
  }));
}
async function loadKit() {
  const kit = selectedKit(); if (!kit) return;
  const variant = kit.variants?.[state.style];
  const request = ++state.request;
  state.manifest = null;
  $('load-error').hidden = true; $('collection').setAttribute('aria-busy', 'true');
  $('regenerate').disabled = true; $('sample-map').classList.add('is-loading');
  $('map-status').hidden = false; $('map-status').textContent = 'Loading this kit’s tiles…';
  $('asset-status').classList.remove('is-error'); $('asset-status').textContent = 'Loading individual tiles…';
  $('kit-title').textContent = kit.title;
  $('kit-description').textContent = 'A reusable visual interpretation of this environment. Named locations may share this kit.';
  $('tile-grid').replaceChildren();
  document.querySelector('.kit-downloads').hidden = true;
  try {
    if (!variant?.manifest) throw new Error('This art direction has not been built for the selected kit yet.');
    const manifestURL = resolve(variant.manifest);
    let manifest = manifestCache.get(manifestURL);
    if (!manifest) { manifest = await fetchJSON(manifestURL); if (!Array.isArray(manifest.assets) || !manifest.assets.length) throw new Error('This kit manifest contains no tile assets.'); manifestCache.set(manifestURL, manifest); }
    if (request !== state.request) return;
    state.manifestURL = manifestURL;
    $('zip-download').href = revisedURL(variant.download, catalogURL, manifest); $('manifest-download').href = revisedURL(manifestURL, catalogURL, manifest);
    $('contact-sheet').href = revisedURL(variant.contactSheet, catalogURL, manifest);
    $('zip-download').setAttribute('aria-label', `Download ${kit.title}, ${selectedStyle().title}, ZIP`);
    const grid = manifest.grid || selectedStyle();
    $('tile-spec').textContent = `${manifest.assets.length} separate transparent PNGs · 256 × 256 canvas · anchor (128, 192) · ${grid.tileWidth} × ${grid.tileHeight} ${grid.projection === 'orthogonal' ? 'square' : 'isometric'} grid`;
    renderTiles(manifest, manifestURL);
    document.querySelector('.kit-downloads').hidden = false;
    const loaded = await Promise.all(manifest.assets.map(async asset => [asset.id, await imageFor(componentURL(asset, manifestURL))]));
    if (request !== state.request) return;
    state.manifest = manifest; state.images = new Map(loaded);
    $('asset-status').textContent = `${manifest.assets.length} pieces · floors, walls, doorways, stairs and environment props`;
    $('map-status').hidden = true; $('sample-map').classList.remove('is-loading'); $('regenerate').disabled = false;
    $('collection').setAttribute('aria-busy', 'false'); drawMap();
  } catch (error) {
    if (request !== state.request) return;
    $('map-status').textContent = 'This composition could not load. Use Try again above.';
    $('asset-status').textContent = 'Tile loading failed.'; $('asset-status').classList.add('is-error'); showError(error);
  }
}
function drawMap() {
  const manifest = state.manifest; if (!manifest) return;
  const grid = manifest.grid || selectedStyle(); const canvas = $('sample-map'); const context = canvas.getContext('2d');
  if (state.composedManifest !== manifest || state.composedSeed !== state.seed) {
    state.placements = composeKit(manifest, state.seed);
    state.floorPlacements = state.placements.filter(piece => piece.asset.role === 'ground');
    state.composedManifest = manifest; state.composedSeed = state.seed;
  }
  const placements = state.placements;
  const bounds = placements.reduce((box, placement) => {
    const anchor = placement.asset.anchor || grid.anchor || { x: 128, y: 192 };
    const x = placement.px - anchor.x, y = placement.py - anchor.y;
    return { left: Math.min(box.left, x), top: Math.min(box.top, y), right: Math.max(box.right, x + 256), bottom: Math.max(box.bottom, y + 256) };
  }, { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity });
  context.clearRect(0, 0, canvas.width, canvas.height);
  const scale = Math.min((canvas.width - 70) / (bounds.right - bounds.left), (canvas.height - 50) / (bounds.bottom - bounds.top));
  const offsetX = (canvas.width - (bounds.right - bounds.left) * scale) / 2 - bounds.left * scale;
  const offsetY = (canvas.height - (bounds.bottom - bounds.top) * scale) / 2 - bounds.top * scale;
  context.imageSmoothingEnabled = state.style !== 'pocket-dungeon';
  if (grid.projection === 'orthogonal') {
    context.save(); context.translate(offsetX, offsetY); context.scale(scale, scale);
    drawFloorLayer(context, state.floorPlacements, state.images); context.restore();
  }
  for (const placement of placements) {
    if (grid.projection === 'orthogonal' && placement.asset.role === 'ground') continue;
    const anchor = placement.asset.anchor || grid.anchor || { x: 128, y: 192 };
    const image = state.images.get(placement.asset.id);
    if (image) context.drawImage(image, offsetX + (placement.px - anchor.x) * scale, offsetY + (placement.py - anchor.y) * scale, 256 * scale, 256 * scale);
  }
  if ($('show-grid').checked) {
    context.save(); context.lineWidth = 1.5; context.strokeStyle = '#11d7ff';
    for (const placement of placements) {
      const points = worldContacts(placement); if (!points.length) continue;
      context.beginPath();
      points.forEach(([x, y], index) => context[index ? 'lineTo' : 'moveTo'](offsetX + x * scale, offsetY + y * scale));
      if (placement.asset.placement.kind === 'floor') context.closePath();
      context.stroke();
    }
    context.restore();
  }
  $('map-seed').textContent = `Seed ${state.seed}`;
  canvas.setAttribute('aria-label', `Illustrative five by five ${selectedKit().title} composition in ${selectedStyle().title}, seed ${state.seed}. Floor tiles, back-wall pieces, a doorway and four props. Not a canonical map.`);
}
function gapText(gap) {
  if (typeof gap === 'string') return gap;
  return gap.summary || gap.reason || gap.status || gap.issue || gap.description || JSON.stringify(gap);
}
async function initialize() {
  $('load-status').hidden = false; $('load-error').hidden = true;
  try {
    const catalog = await fetchJSON(catalogURL);
    if (!catalog.styles?.length || !catalog.kits?.length || !Array.isArray(catalog.locations)) throw new Error('The book-tile library is not ready yet.');
    state.catalog = catalog; state.style = catalog.styles[0].id;
    $('book-filter').replaceChildren(option('all', 'All eight books'), ...catalog.books.map(book => option(String(book.id), `${book.id}. ${book.title}`)));
    $('coverage-gaps').replaceChildren(...asArray(catalog.coverageGaps).map(gap => element('li', '', gapText(gap))));
    renderTabs(); updateStyleHeading();
    $('load-status').hidden = true; $('collection').hidden = false;
    updateLocations();
  } catch (error) { showError(error); }
}
$('book-filter').addEventListener('change', event => { state.book = event.target.value; updateLocations(); });
$('location-search').addEventListener('input', event => { state.search = event.target.value.trim().toLocaleLowerCase(); updateLocations(); });
$('location-select').addEventListener('change', event => { state.location = event.target.value; renderLocation(); updateKits(); });
$('kit-select').addEventListener('change', event => { state.kit = event.target.value; loadKit(); });
$('show-grid').addEventListener('change', drawMap);
$('regenerate').addEventListener('click', () => { state.seed++; drawMap(); });
$('retry').addEventListener('click', () => state.catalog && state.kit ? loadKit() : initialize());
initialize();
