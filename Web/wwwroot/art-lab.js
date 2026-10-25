const CATALOG_URL = new URL('assets/style-packs/catalog.json', document.baseURI);
const categories = ['terrain', 'structure', 'prop', 'actor', 'effect', 'ui', 'portrait', 'equipment', 'loot'];
const categoryNames = { services: 'Home & services', new: 'New additions', biomes: 'Biomes & landmarks', supplies: 'Equipment & supplies', expansion: 'Rooms & creatures', equipment: 'Equipment', loot: 'Loot', terrain: 'Terrain', structure: 'Structures', prop: 'Props', actor: 'Actors', effect: 'Effects', ui: 'UI', portrait: 'Portraits' };
const collectionNames = {arsenal: 'Weapons', armor: 'Armor', gear: 'Gear', settlements: 'Cities & towns', roads: 'Roads', forest: 'Forests', highlands: 'Mountains & volcanic', caverns: 'Caves', attacks: 'Character attacks', spells: 'Spells'};
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
let animationTimer;
let animationObserver;
const directions = {
  'pocket-dungeon': { subtitle: 'Overhead pixel art', accent: '#615064' },
  'ink-and-lanterns': { subtitle: 'Painted gouache & ink', accent: '#547058' },
  'dungeon-after-dark': { subtitle: 'Graphic novel & halftone', accent: '#416975' }
};
const $ = id => document.getElementById(id);
const state = { styles: [], active: null, manifest: null, manifestUrl: null, category: 'all', collection: 'all', limit: 48, search: '', request: 0, failedLayers: new Set(), loadedLayers: new Set(), layers: [] };
const downloadIcon = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/></svg>';
const outwardIcon = '<svg class="small-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M6 18 18 6M6 6h12v12"/></svg>';

function make(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function localUrl(path, base = document.baseURI) {
  if (typeof path !== 'string' || !path.trim()) return null;
  const url = new URL(path, base);
  if (url.origin !== window.location.origin || !['http:', 'https:'].includes(url.protocol)) return null;
  return url.href;
}

// Archive downloads live in the canonical art repository to keep Pages within its size limit.
const ART_ARCHIVE_REF = '1e880cb5adb5ca9cfc59774963b00c4cbd06f1fc';
function canonicalDownloadUrl(path) {
  if (typeof path !== 'string') return null;
  let url;
  try { url = new URL(path, state.manifestUrl); } catch { return null; }
  const marker = '/assets/style-packs/';
  if (url.origin !== window.location.origin) {
    if (url.protocol !== 'https:' || !['github.com','raw.githubusercontent.com'].includes(url.hostname) || !url.pathname.startsWith('/cehinds/AI-Art/') || !url.pathname.includes('/dungeon-crawler-tactics/Web/wwwroot/assets/style-packs/')) return null;
  }
  const offset = url.pathname.indexOf(marker);
  if (offset < 0 || !url.pathname.endsWith('.zip')) return null;
  const relative = url.pathname.slice(offset + marker.length);
  return `https://github.com/cehinds/AI-Art/raw/${ART_ARCHIVE_REF}/dungeon-crawler-tactics/Web/wwwroot/assets/style-packs/${relative}`;
}

function configureArchive(element, path) {
  configureLink(element, canonicalDownloadUrl(path));
  element.removeAttribute('download'); element.target = '_blank'; element.rel = 'noopener';
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`The collection file returned HTTP ${response.status}.`);
  return response.json();
}

function setLoading(message) {
  $('load-status').hidden = false;
  $('load-status').replaceChildren(make('span', 'loading-dot'), document.createTextNode(message));
  $('load-error').hidden = true;
  $('style-panel').hidden = true;
  $('style-panel').setAttribute('aria-busy', 'true');
}

function showError(error) {
  $('load-status').hidden = true;
  $('style-panel').hidden = true;
  $('load-error').hidden = false;
  $('error-detail').textContent = `${error.message || 'The collection could not be read.'} Serve this page over HTTP and check that the art pack files are available, then try again.`;
}

function renderTabs() {
  const restoreFocus = $('style-tabs').contains(document.activeElement);
  const tabs = state.styles.map((style, index) => {
    const button = make('button', 'style-tab');
    button.type = 'button';
    button.id = `tab-${style.id}`;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-controls', 'style-panel');
    button.setAttribute('aria-selected', String(style.id === state.active));
    button.tabIndex = style.id === state.active ? 0 : -1;
    const number = make('span', 'tab-number', String(index + 1).padStart(2, '0'));
    number.setAttribute('aria-hidden', 'true');
    const copy = make('span', 'tab-copy');
    copy.append(make('span', 'tab-title', style.title), make('span', 'tab-description', directions[style.id]?.subtitle || 'Art direction'));
    button.append(number, copy);
    button.addEventListener('click', () => selectStyle(style.id));
    button.addEventListener('keydown', event => {
      if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === 'ArrowRight') nextIndex = (index + 1) % state.styles.length;
      if (event.key === 'ArrowLeft') nextIndex = (index - 1 + state.styles.length) % state.styles.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = state.styles.length - 1;
      selectStyle(state.styles[nextIndex].id);
      $(`tab-${state.styles[nextIndex].id}`).focus();
    });
    return button;
  });
  $('style-tabs').replaceChildren(...tabs);
  if (restoreFocus) $(`tab-${state.active}`)?.focus();
}

function configureLink(element, url) {
  element.hidden = !url;
  if (url) element.href = url;
  else element.removeAttribute('href');
}

async function selectStyle(id) {
  const style = state.styles.find(item => item.id === id);
  if (!style) return;
  const request = ++state.request;
  state.active = id;
  state.category = 'all';
  state.collection = 'all';
  state.limit = 48;
  clearInterval(animationTimer);
  state.search = '';
  $('component-search').value = '';
  renderTabs();
  setLoading(`Loading ${style.title}…`);
  document.documentElement.style.setProperty('--accent', directions[id]?.accent || '#3b535c');
  try {
    const manifestUrl = localUrl(style.manifest);
    if (!manifestUrl) throw new Error('This collection has no valid manifest path.');
    const manifest = await fetchJson(manifestUrl);
    if (request !== state.request) return;
    if (!Array.isArray(manifest.assets) || !Array.isArray(manifest.preview?.layers)) throw new Error('The manifest is missing its components or room layers.');
    state.manifest = manifest;
    state.manifestUrl = manifestUrl;
    renderCollection(style, manifest);
    $('style-panel').setAttribute('aria-labelledby', `tab-${id}`);
    $('style-panel').setAttribute('aria-busy', 'false');
    $('style-panel').hidden = false;
    $('load-status').hidden = true;
    history.replaceState(null, '', `#${encodeURIComponent(id)}`);
  } catch (error) {
    if (request === state.request) showError(error);
  }
}

function renderCollection(style, manifest) {
  $('style-panel').classList.toggle('pixel-art', style.id === 'pocket-dungeon');
  $('style-title').textContent = manifest.title || style.title;
  $('style-description').textContent = manifest.description || style.description || '';
  configureArchive($('pack-download'), manifest.download);
  configureLink($('manifest-link'), state.manifestUrl);
  configureLink($('contact-sheet'), localUrl(manifest.contactSheet, state.manifestUrl));
  configureLink($('preview-download'), localUrl(manifest.preview.file, state.manifestUrl));
  renderLayers(manifest.preview);
  renderConcepts(style);
  renderCollections();
  renderAnimations();
  renderFilters();
  renderComponents();
  loadReusable(style.id);
}

function renderLayers(preview) {
  state.failedLayers = new Set();
  state.loadedLayers = new Set();
  state.layers = preview.layers.map((layer, index) => ({ ...layer, key: `${index}-${layer.id}`, order: Number.isFinite(layer.z) ? layer.z : index, checked: layer.visible !== false })).sort((a, b) => a.order - b.order);
  const room = $('room-preview');
  const width = Number(preview.width), height = Number(preview.height);
  room.style.aspectRatio = width > 0 && height > 0 ? `${width}/${height}` : '4/3';
  room.setAttribute('aria-label', `${state.manifest.title || 'Art pack'} room composition. Use the layer checkboxes to change the visible scene.`);
  room.replaceChildren();
  $('layer-list').replaceChildren();
  state.layers.forEach((layer, index) => {
    const url = localUrl(layer.file, state.manifestUrl);
    const image = make('img');
    image.alt = '';
    image.style.zIndex = index;
    image.hidden = !layer.checked;
    const currentRequest = state.request;
    image.addEventListener('load', () => {
      if (state.request !== currentRequest) return;
      state.loadedLayers.add(layer.key);
      updateLayerStatus();
    });
    image.addEventListener('error', () => {
      if (state.request !== currentRequest) return;
      state.failedLayers.add(layer.key);
      image.hidden = true;
      updateLayerStatus();
    });
    if (url) image.src = url;
    else state.failedLayers.add(layer.key);
    layer.image = image;
    room.append(image);
    const row = make('li', 'layer-row');
    const label = make('label');
    const input = make('input');
    input.type = 'checkbox';
    input.checked = layer.checked;
    input.addEventListener('change', () => {
      layer.checked = input.checked;
      image.hidden = !layer.checked || state.failedLayers.has(layer.key);
      updateLayerStatus();
    });
    layer.input = input;
    label.append(input, make('span', 'layer-number', String(index + 1).padStart(2, '0')), make('span', 'layer-label', layer.label || layer.id));
    const link = make('a', 'layer-download', 'PNG');
    const icon = make('span');
    icon.innerHTML = downloadIcon;
    link.append(icon);
    link.download = '';
    link.setAttribute('aria-label', `Download ${layer.label || layer.id} layer PNG`);
    configureLink(link, url);
    row.append(label, link);
    $('layer-list').append(row);
  });
  updateLayerStatus();
}

function updateLayerStatus() {
  const checked = state.layers.filter(layer => layer.checked).length;
  const loadedVisible = state.layers.filter(layer => layer.checked && state.loadedLayers.has(layer.key)).length;
  const pending = state.layers.length - state.loadedLayers.size - state.failedLayers.size;
  $('visible-layers').textContent = pending > 0 ? `Loading ${pending} layer${pending === 1 ? '' : 's'}…` : `${loadedVisible} / ${state.layers.length} layers visible`;
  $('preview-status').hidden = !state.failedLayers.size && !!state.layers.length;
  if (!state.layers.length) $('preview-status').textContent = 'This pack has no separate room layers.';
  else if (state.failedLayers.size) $('preview-status').textContent = `${state.failedLayers.size} room layer${state.failedLayers.size === 1 ? ' could' : 's could'} not be loaded. The visible scene may be incomplete.`;
  $('preview-caption').textContent = checked === 0 ? 'All layers hidden · use Show all to restore the room' : 'Room composition · transparent PNG layers';
}

function setAllLayers(checked) {
  state.layers.forEach(layer => {
    layer.checked = checked;
    layer.input.checked = checked;
    layer.image.hidden = !checked || state.failedLayers.has(layer.key);
  });
  updateLayerStatus();
}

function matchesCategory(asset, category) {
  if (category === 'all') return true;
  if (category === 'new') return Object.hasOwn(collectionNames, asset.collection || asset.source?.sheet);
  return ['services', 'biomes', 'supplies', 'expansion'].includes(category)
    ? asset.source?.sheet === category
    : asset.category === category;
}

function renderConcepts(style) {
  const concepts = [
    { file: style.concept, title: 'Original style study' },
    { file: style.newConcept, title: 'Exploration concept' },
    { file: style.combatConcept, title: 'Combat concept' }
  ];
  const links = concepts.map(concept => {
    const url = localUrl(concept.file);
    if (!url) return null;
    const link = make('a', 'concept-link');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener';
    const media = make('div', 'concept-media');
    const image = make('img');
    image.alt = `${style.title} — ${concept.title.toLowerCase()}`;
    image.loading = 'lazy';
    image.addEventListener('error', () => {
      media.replaceChildren(make('p', 'image-failure', 'Concept preview is not available yet. Reload once the image has been added.'));
    }, { once: true });
    image.src = url;
    media.append(image);
    const caption = make('span', 'concept-caption');
    const openLabel = make('span', 'concept-open', 'Open image');
    const icon = make('span');
    icon.innerHTML = outwardIcon;
    openLabel.append(icon);
    caption.append(make('span', '', concept.title), openLabel);
    link.append(media, caption);
    return link;
  }).filter(Boolean);
  $('concepts').replaceChildren(...links);
  $('concept-art').hidden = links.length === 0;
}

function renderFilters() {
  const assets = state.manifest.assets;
  const available = ['all', 'new', 'services', 'biomes', 'supplies', 'expansion', ...categories];
  const buttons = available.map(category => {
    const count = category === 'all' ? assets.length : assets.filter(asset => matchesCategory(asset, category)).length;
    const button = make('button', 'category-filter', category === 'all' ? 'All pieces' : categoryNames[category]);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(state.category === category));
    button.append(make('span', '', String(count)));
    button.disabled = count === 0;
    button.addEventListener('click', () => {
      state.category = category;
      state.limit = 48;
      renderFilters();
      renderComponents();
      const index = available.indexOf(category);
      $('category-filters').children[index]?.focus();
    });
    return button;
  });
  $('category-filters').replaceChildren(...buttons);
}

function renderComponents() {
  const assets = state.manifest.assets.filter(asset => {
    const matchingCategory = matchesCategory(asset, state.category);
    const text = `${asset.label || ''} ${asset.id || ''} ${asset.category || ''} ${asset.layer || ''} ${(reuse.metadata.get(asset.id)?.tags || []).join(' ')} ${collectionNames[asset.collection || asset.source?.sheet] || ''}`.toLowerCase();
    return matchingCategory && (state.collection === 'all' || (asset.collection || asset.source?.sheet) === state.collection) && text.includes(state.search.toLowerCase().trim());
  });
  const cards = assets.slice(0, state.limit).map(asset => {
    const card = make('article', 'component-card');
    const label = asset.label || asset.id || 'Untitled component';
    const url = localUrl(asset.file, state.manifestUrl);
    const imageLink = make('a', 'component-image checkerboard');
    imageLink.setAttribute('aria-label', `Download ${label} PNG`);
    imageLink.download = '';
    configureLink(imageLink, url);
    const image = make('img');
    image.alt = label;
    image.loading = 'lazy';
    image.decoding = 'async';
    if (Number(asset.width) > 0) image.width = asset.width;
    if (Number(asset.height) > 0) image.height = asset.height;
    image.addEventListener('error', () => imageLink.replaceChildren(make('span', 'image-failure', 'PNG preview unavailable')), { once: true });
    if (url) image.src = url;
    else imageLink.append(make('span', 'image-failure', 'No PNG path in manifest'));
    if (url) imageLink.append(image);
    const title = make('div', 'component-title');
    const download = make('a', 'component-download');
    download.innerHTML = downloadIcon;
    download.download = '';
    download.setAttribute('aria-label', `Download ${label} PNG`);
    configureLink(download, url);
    title.append(make('h3', '', label), download);
    const dimensions = Number(asset.width) > 0 && Number(asset.height) > 0 ? `${asset.width} × ${asset.height}` : 'PNG';
    const category = categoryNames[asset.category] || asset.category || 'Component';
    card.append(imageLink, title, make('p', 'component-meta', `${category} · ${dimensions}`));
    if (asset.anchor && Number.isFinite(asset.anchor.x) && Number.isFinite(asset.anchor.y)) {
      card.append(make('p', 'component-meta', `Anchor ${asset.anchor.x}, ${asset.anchor.y}`));
    }
    const metadata = reuse.metadata.get(asset.id);
    if (metadata) {
      const link = make('a', 'text-link', 'Item JSON & tags');
      link.download = ''; configureLink(link, reuseUrl(metadata.metadata_path)); card.append(link);
      card.append(make('p', 'component-meta', (metadata.tags || []).join(' · ')));
    }
    card.append(make('p', 'component-id', asset.id));
    return card;
  });
  $('component-grid').replaceChildren(...cards);
  $('load-more').hidden = assets.length <= state.limit;
  $('load-more').textContent = `Show ${Math.min(48, Math.max(0, assets.length - state.limit))} more pieces`;
  $('result-count').textContent = `Showing ${Math.min(state.limit, assets.length)} of ${assets.length} matching pieces · ${state.manifest.assets.length} total${state.category === 'all' ? '' : ` · ${categoryNames[state.category]}`}`;
  $('empty-state').hidden = assets.length > 0;
}

function renderCollections() {
  const collections = state.manifest.collections || [];
  const select = $('collection-filter');
  select.replaceChildren(new Option('All collections', 'all'));
  const cards = collections.map(collection => {
    const label = collectionNames[collection.id] || collection.label || collection.id;
    select.add(new Option(`${label} (${collection.count || 24})`, collection.id));
    const card = make('article', 'collection-card');
    card.append(make('h3', '', label), make('p', 'component-meta', `${collection.count || 24} transparent PNGs`));
    const link = make('a', 'text-link', 'Download collection ZIP · GitHub');
    link.download = '';
    configureArchive(link, collection.download);
    card.append(link);
    return card;
  });
  select.value = state.collection;
  $('collection-downloads').replaceChildren(...cards);
  $('collections').hidden = !cards.length;
}

function renderAnimations() {
  clearInterval(animationTimer);
  animationObserver?.disconnect();
  const players = [];
  const cards = (state.manifest.animations || []).map(clip => {
    const frames = (clip.frames || []).map(path => localUrl(typeof path === 'string' ? path : path.file, state.manifestUrl)).filter(Boolean);
    const card = make('article', 'animation-card');
    const media = make('div', 'animation-media checkerboard');
    const image = make('img');
    image.alt = `${clip.label || clip.id} animation frame`;
    image.width = clip.frameWidth || 256;
    image.height = clip.frameHeight || 256;
    if (frames.length) image.src = frames[0];
    media.append(image);
    const controls = make('div', 'animation-controls');
    const button = make('button', 'animation-toggle');
    button.type = 'button';
    const slider = make('input');
    slider.type = 'range'; slider.min = '0'; slider.max = String(Math.max(0, frames.length - 1)); slider.value = '0'; slider.step = '1';
    slider.setAttribute('aria-label', `${clip.label || clip.id} frame`);
    const counter = make('span', 'frame-count', `1 / ${frames.length}`);
    const player = {card, image, frames, slider, counter, button, frame: 0, playing: !motionPreference.matches, last: 0, fps: Number(clip.fps) || 8};
    const updateButton = () => { button.textContent = player.playing ? 'Pause' : 'Play'; button.setAttribute('aria-label', `${player.playing ? 'Pause' : 'Play'} ${clip.label || clip.id}`); };
    player.updateButton = updateButton;
    player.show = frame => { player.frame = frame; image.src = frames[frame]; slider.value = String(frame); counter.textContent = `${frame + 1} / ${frames.length}`; };
    button.disabled = !frames.length; slider.disabled = !frames.length;
    updateButton();
    button.addEventListener('click', () => { player.playing = !player.playing; updateButton(); });
    slider.addEventListener('input', () => { player.playing = false; updateButton(); player.show(Number(slider.value)); });
    image.addEventListener('error', () => { player.playing = false; updateButton(); media.replaceChildren(make('p', 'image-failure', 'Animation preview unavailable')); }, {once:true});
    controls.append(button, slider, counter);
    card.append(media, make('h3', '', clip.label || clip.id), controls);
    const downloads = make('div', 'animation-downloads');
    for (const [label, path] of [['Sprite sheet PNG', clip.spriteSheet], ['Frame metadata JSON', clip.metadata]]) {
      const link = make('a', 'text-link', label); link.download = ''; configureLink(link, localUrl(path, state.manifestUrl)); downloads.append(link);
    }
    card.append(downloads); players.push(player); return card;
  });
  $('animation-grid').replaceChildren(...cards);
  $('animations').hidden = !cards.length;
  state.players = players;
  // Warm each six-frame sequence shortly before it enters the viewport.
  animationObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const player = players.find(item => item.card === entry.target);
      if (player) player.preloadedFrames = player.frames.map(url => { const image = new Image(); image.src = url; return image; });
      animationObserver.unobserve(entry.target);
    }
  }, {rootMargin: '300px'});
  players.forEach(player => animationObserver.observe(player.card));
  animationTimer = setInterval(() => {
    if (document.hidden) return;
    const now = performance.now();
    for (const player of players) {
      if (!player.playing || player.frames.length < 2 || now - player.last < 1000 / player.fps) continue;
      const bounds = player.card.getBoundingClientRect();
      if (bounds.bottom < 0 || bounds.top > innerHeight) continue;
      player.last = now; player.show((player.frame + 1) % player.frames.length);
    }
  }, 40);
}

$('collection-filter').addEventListener('change', event => { state.collection = event.target.value; state.limit = 48; renderComponents(); });
$('load-more').addEventListener('click', () => { state.limit += 48; renderComponents(); });
motionPreference.addEventListener('change', event => {
  if (event.matches) for (const player of state.players || []) { player.playing = false; player.updateButton(); }
});

async function loadCatalog() {
  setLoading('Loading the art collections…');
  try {
    const catalog = await fetchJson(CATALOG_URL);
    if (!Array.isArray(catalog.styles) || !catalog.styles.length) throw new Error('The art catalog does not contain any collections.');
    state.styles = catalog.styles.filter(style => style.id && style.title && style.manifest);
    if (!state.styles.length) throw new Error('The art catalog does not contain valid collection records.');
    const requestedId = decodeURIComponent(window.location.hash.slice(1));
    const initial = state.styles.find(style => style.id === requestedId) || state.styles[0];
    await selectStyle(initial.id);
  } catch (error) {
    showError(error);
  }
}

$('retry').addEventListener('click', () => state.styles.length && state.active ? selectStyle(state.active) : loadCatalog());
$('component-search').addEventListener('input', event => {
  state.search = event.target.value;
  state.limit = 48;
  if (state.manifest) renderComponents();
});
$('show-layers').addEventListener('click', () => setAllLayers(true));
$('hide-layers').addEventListener('click', () => setAllLayers(false));
document.querySelector('.collection-jumps').addEventListener('click', event => {
  const link = event.target.closest('a[href^="#"]');
  const target = link && document.getElementById(link.hash.slice(1));
  if (!target) return;
  event.preventDefault();
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
});
loadCatalog();

const reuse = { index: null, metadata: new Map(), base: null, mapRequest: 0, map: null, checks: [], images: new Map(), placements: [] };
function reuseUrl(path) { return localUrl(path, reuse.base); }
async function reuseImage(path) {
  const url = reuseUrl(path);
  if (!url) throw new Error('Missing local image path.');
  if (!reuse.images.has(url)) reuse.images.set(url, new Promise((resolve, reject) => {
    const image = new Image(); image.onload = () => resolve(image); image.onerror = () => reject(new Error(`Could not load ${path}`)); image.src = url;
  }));
  return reuse.images.get(url);
}
async function loadReusable(id) {
  $('reusable').hidden = id !== 'pocket-dungeon';
  const loadRequest = reuse.loadRequest = (reuse.loadRequest || 0) + 1;
  reuse.index = null; reuse.metadata = new Map();
  reuse.placements = []; reuse.remixRequest = (reuse.remixRequest || 0) + 1;
  $('remix-canvas').getContext('2d').clearRect(0,0,960,640);
  reuse.mapRequest++; reuse.drawRequest = (reuse.drawRequest || 0) + 1;
  if (id !== 'pocket-dungeon') return;
  $('reusable-status').textContent = 'Loading reusable asset metadata…'; $('reusable-tools').hidden = true;
  reuse.base = new URL('.', state.manifestUrl);
  const indexUrl = reuseUrl('reusable/index.json');
  try {
    const index = await fetchJson(indexUrl);
    if (state.active !== id || loadRequest !== reuse.loadRequest) return;
    reuse.index = index; reuse.metadata = new Map(index.assets.map(asset => [asset.id, asset]));
    configureLink($('reusable-index'), indexUrl);
    $('reusable-downloads').replaceChildren(...(index.downloads || []).map(item => {
      const card=make('div','reuse-download');const link=make('a','text-link',`${item.label || 'Download asset archive'} · GitHub`);
      configureArchive(link,item.path);card.append(link);
      if(item.bytes)card.append(make('span','',`${(item.bytes/1048576).toFixed(1)} MiB`));
      if(item.description)card.append(make('p','',item.description));return card;
    }));
    $('reconstruction-source').replaceChildren(...index.maps.map(map => { const option = make('option', '', map.label || map.id); option.value = map.id; return option; }));
    $('reusable-tools').hidden = false;
    $('reusable-status').textContent = `${index.assets.length} recorded assets · ${index.maps.length} reconstruction maps. Fidelity is determined by the exported pixel validation report.`;
    renderReuseAssets(); renderComponents(); loadProcedural(); await loadReconstruction();
  } catch (error) { if (state.active === id && loadRequest === reuse.loadRequest) $('reusable-status').textContent = `Reusable package unavailable: ${error.message}`; }
}
async function loadReconstruction() {
  const entry = reuse.index?.maps.find(map => map.id === $('reconstruction-source').value);
  if (!entry) return;
  const request = ++reuse.mapRequest;
  $('reconstruction-caption').textContent = 'Loading source map…';
  try {
    const map = await fetchJson(reuseUrl(entry.file));
    if (request !== reuse.mapRequest) return;
    reuse.map = map;
    configureLink($('reconstruction-json'), reuseUrl(entry.file));
    const canvas = $('reconstruction-canvas'); canvas.width = map.canvas.width; canvas.height = map.canvas.height;
    reuse.checks = map.layers.map(() => true);
    $('reconstruction-layers').replaceChildren(...map.layers.map((layer, index) => {
      const label = make('label', 'reuse-layer'); const checkbox = make('input'); checkbox.type = 'checkbox'; checkbox.checked = true;
      checkbox.addEventListener('change', () => { reuse.checks[index] = checkbox.checked; drawReconstruction(); });
      label.append(checkbox, make('span', '', `${layer.role}: ${layer.asset_id}`)); return label;
    }));
    await drawReconstruction();
  } catch (error) { $('reconstruction-caption').textContent = `Map unavailable: ${error.message}`; }
}
async function drawReconstruction() {
  const map = reuse.map; if (!map) return;
  const request = reuse.drawRequest = (reuse.drawRequest || 0) + 1;
  try {
    const layers = map.layers.map((layer, index) => ({ ...layer, index })).filter(layer => reuse.checks[layer.index]).sort((a,b) => a.z-b.z || a.index-b.index);
    const images = await Promise.all(layers.map(layer => reuseImage(layer.path)));
    if (request !== reuse.drawRequest || map !== reuse.map) return;
    const canvas = $('reconstruction-canvas'); const context = canvas.getContext('2d'); context.clearRect(0,0,canvas.width,canvas.height);
    for (let i=0;i<layers.length;i++) {
      const layer=layers[i], image=images[i];
      if (layer.blend === 'replace' || layer.blend === 'masked-replace') {
        const patch=document.createElement('canvas'); patch.width=image.width; patch.height=image.height;
        const pc=patch.getContext('2d'); pc.drawImage(image,0,0); const src=pc.getImageData(0,0,patch.width,patch.height);
        const dest=context.getImageData(layer.x,layer.y,patch.width,patch.height);
        for(let p=0;p<src.data.length;p+=4) if(layer.blend==='replace'||src.data[p+3]>0) dest.data.set(src.data.subarray(p,p+4),p);
        context.putImageData(dest,layer.x,layer.y);
      } else { context.save(); context.translate(layer.x,layer.y); context.rotate((layer.rotation_deg||0)*Math.PI/180); context.scale(layer.scale||1,layer.scale||1); context.drawImage(image,0,0); context.restore(); }
    }
    const semantic=layers.filter(l=>l.role==='semantic').length, residual=layers.length-semantic;
    $('reconstruction-caption').textContent = `${map.canvas.width} × ${map.canvas.height} · ${semantic} semantic layers · ${residual} residual layers visible. Browser canvas can normalize transparent RGB; exported maps and source PNGs are the authoritative reconstruction.`;
  } catch(error) { $('reconstruction-caption').textContent=`Reconstruction failed: ${error.message}`; }
}
function usableAssets() { return (reuse.index?.assets || []).filter(asset => ['tile','terrain_tile','sprite','icon','effect','ui','ui_region','portrait'].includes(asset.kind) && asset.image?.path && (!asset.view || asset.view === 'source' || (asset.view === 'front' && reuse.metadata.get(asset.object_id)?.kind === 'reconstruction_patch')) && !asset.metadata?.view); }
function renderReuseAssets() {
  const query=$('reusable-search').value.trim().toLowerCase(); const previous=$('reusable-asset').value;
  const assets=usableAssets().filter(asset=>`${asset.id} ${asset.name} ${(asset.tags||[]).join(' ')}`.toLowerCase().includes(query));
  $('reusable-asset').replaceChildren(...assets.map(asset=>{const option=make('option','',asset.name||asset.id);option.value=asset.id;return option;}));
  if(assets.some(asset=>asset.id===previous)) $('reusable-asset').value=previous;
  renderReuseAsset();
}
function renderReuseAsset() {
  const asset=reuse.metadata.get($('reusable-asset').value); const image=$('reusable-image');
  if(!asset) { image.removeAttribute('src');image.alt='No matching semantic asset';$('reusable-views').replaceChildren();$('reusable-tags').textContent='No matching assets.';configureLink($('reusable-metadata'),null);return; }
  image.src=reuseUrl(asset.image.path); image.alt=asset.name||asset.id;
  const set = (reuse.index.view_sets || []).find(item => item.object_id === (asset.object_id || asset.id));
  const views = set ? {applicable:true,complete:set.complete,...Object.fromEntries(Object.entries(set.views || {}).map(([direction,id])=>[direction,{status:'generated-inferred',asset_id:typeof id==='string'?id:id.asset_id}]))} : asset.views;
  $('reusable-tags').textContent=(asset.tags||[]).join(' · '); configureLink($('reusable-metadata'),reuseUrl(asset.metadata_path));
  if (views?.applicable === false) { $('reusable-views').replaceChildren(make('p', '', `Six principal views: not applicable. ${views.reason || views.notes || 'This image represents a flat graphic or effect.'}`)); return; }
  $('reusable-views').replaceChildren(...['front','top','right','left','bottom','rear'].map(direction=>{
    const item=views?.[direction];const card=make('div','reuse-view');card.append(make('strong','',direction),make('span','',item?.status||'unavailable'));
    const target=item?.asset_id&&reuse.metadata.get(item.asset_id); if(target) {const preview=make('img');preview.src=reuseUrl(target.image.path);preview.alt=`${asset.name||asset.id}: ${direction} view`;preview.loading='lazy';card.append(preview,make('span','','Generated view: inferred surfaces, not recovered source pixels.'));const link=make('a','','Download PNG');link.download='';configureLink(link,reuseUrl(target.image.path));card.append(link);const metadata=make('a','','Download view JSON');metadata.download='';configureLink(metadata,reuseUrl(target.metadata_path));card.append(metadata);}return card;
  }));
}
async function drawRemix() {
  const canvas=$('remix-canvas'), context=canvas.getContext('2d'); const placements=[...reuse.placements];
  const request = reuse.remixRequest = (reuse.remixRequest || 0) + 1;
  let images;
  try { images=await Promise.all(placements.map(item=>reuseImage(reuse.metadata.get(item.asset_id).image.path))); } catch(error) { $('remix-status').textContent=`Could not draw placement: ${error.message}`; return; }
  if (request !== reuse.remixRequest) return;
  context.clearRect(0,0,canvas.width,canvas.height);
  placements.forEach((item,index)=>{const image=images[index];context.save();context.translate(item.x,item.y);context.rotate(item.rotation_deg*Math.PI/180);context.drawImage(image,-image.width/2,-image.height/2);context.restore();});
  $('remix-status').textContent=`${placements.length} semantic pieces placed · 960 × 640 canvas`;
}
function placeRemix(x,y) {const asset=reuse.metadata.get($('reusable-asset').value);if(!asset)return;reuse.placements.push({asset_id:asset.id,path:asset.image.path,x:Math.round(x),y:Math.round(y),rotation_deg:Number($('remix-rotation').value),scale:1,anchor:'center'});drawRemix();}
$('reconstruction-source').addEventListener('change',loadReconstruction);
for(const [id,semanticOnly] of [['reconstruction-all',false],['reconstruction-semantic',true]]) $(id).addEventListener('click',()=>{reuse.checks=reuse.map.layers.map(layer=>!semanticOnly||layer.role==='semantic');$('reconstruction-layers').querySelectorAll('input').forEach((input,index)=>input.checked=reuse.checks[index]);drawReconstruction();});
$('reusable-search').addEventListener('input',renderReuseAssets);$('reusable-asset').addEventListener('change',renderReuseAsset);
$('remix-canvas').addEventListener('click',event=>{const bounds=event.currentTarget.getBoundingClientRect();placeRemix((event.clientX-bounds.left)*960/bounds.width,(event.clientY-bounds.top)*640/bounds.height);});
$('remix-canvas').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();placeRemix(480,320);}});
$('remix-undo').addEventListener('click',()=>{reuse.placements.pop();drawRemix();});$('remix-clear').addEventListener('click',()=>{reuse.placements=[];drawRemix();});
$('remix-export').addEventListener('click',()=>{const data={schema_version:1,kind:'semantic-remix',canvas:{width:960,height:640},assets_base:'assets/style-packs/pocket-dungeon/',placements:reuse.placements};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=make('a');link.href=url;link.download='pocket-dungeon-remix.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

let floorRecipe = null, floorOutput = null, floorRequest = 0;
async function loadProcedural() {
  const request=++floorRequest; floorRecipe=null;floorOutput=null;$('procedural-export').disabled=true;
  try {const recipe=await fetchJson(reuseUrl(reuse.index?.procedural?.recipe || 'reusable/procedural/sample.json'));if(request!==floorRequest||state.active!=='pocket-dungeon')return;floorRecipe=recipe;await generateFloor();}
  catch(error){$('procedural-status').textContent=`Floor recipe unavailable: ${error.message}`;}
}
async function generateFloor() {
  if(!floorRecipe)return;
  const request=++floorRequest;
  const seed=Number($('procedural-seed').value)>>>0; let random=seed;
  const next=()=>{random=(Math.imul(1664525,random)+1013904223)>>>0;return random/4294967296;};
  const tiles=[...new Map(floorRecipe.cells.filter(cell=>cell.walkable&&cell.path).map(cell=>[cell.asset_id,{asset_id:cell.asset_id,path:cell.path}])).values()];
  if(!tiles.length){$('procedural-status').textContent='No native floor tiles in recipe.';return;}
  const width=floorRecipe.grid.width,height=floorRecipe.grid.height,size=floorRecipe.grid.cell_size_px;
  const walkable=new Set(), rooms=[];
  const carve=(x,y)=>walkable.add(`${x},${y}`);
  const carveLine=(a,b)=>{let [x,y]=a;carve(x,y);while(x!==b[0]){x+=Math.sign(b[0]-x);carve(x,y);}while(y!==b[1]){y+=Math.sign(b[1]-y);carve(x,y);}};
  for(let roomIndex=0;roomIndex<7;roomIndex++){
    const w=3+Math.floor(next()*4),h=3+Math.floor(next()*3),x=1+Math.floor(next()*(width-w-1)),y=1+Math.floor(next()*(height-h-1));
    const center=[x+Math.floor(w/2),y+Math.floor(h/2)];
    for(let row=y;row<y+h;row++)for(let column=x;column<x+w;column++)carve(column,row);
    if(rooms.length) {const previous=rooms[rooms.length-1].center;const corner=next()<0.5?[center[0],previous[1]]:[previous[0],center[1]];carveLine(previous,corner);carveLine(corner,center);}
    rooms.push({x,y,width:w,height:h,center});
  }
  const cells=[];
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const open=walkable.has(`${x},${y}`),connections=[];
    for(const [direction,dx,dy] of [['north',0,-1],['east',1,0],['south',0,1],['west',-1,0]])if(walkable.has(`${x+dx},${y+dy}`))connections.push(direction);
    cells.push(open?{x,y,walkable:true,connections,...tiles[Math.floor(next()*tiles.length)],rotation_deg:Math.floor(next()*4)*90,position_px:[x*size,y*size],anchor_px:[0,0]}:{x,y,walkable:false,connections:[]});
  }
  const visited=new Set(),queue=[rooms[0].center];
  for(let i=0;i<queue.length;i++){const [x,y]=queue[i],key=`${x},${y}`;if(visited.has(key)||!walkable.has(key))continue;visited.add(key);for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]])if(walkable.has(`${x+dx},${y+dy}`)&&!visited.has(`${x+dx},${y+dy}`))queue.push([x+dx,y+dy]);}
  const connected=visited.size===walkable.size;
  if(!connected){$('procedural-status').textContent='Generated layout failed connectivity validation.';return;}

  try {
    const images=await Promise.all(tiles.map(tile=>reuseImage(tile.path)));if(request!==floorRequest||state.active!=='pocket-dungeon')return;
    const imageById=new Map(tiles.map((tile,index)=>[tile.asset_id,images[index]]));
    const canvas=$('procedural-canvas');canvas.width=floorRecipe.grid.width*size;canvas.height=floorRecipe.grid.height*size;
    const ctx=canvas.getContext('2d');ctx.fillStyle='#181721';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
    cells.filter(cell=>cell.walkable).forEach(cell=>{ctx.save();ctx.translate(cell.x*size+size/2,cell.y*size+size/2);ctx.rotate(cell.rotation_deg*Math.PI/180);ctx.drawImage(imageById.get(cell.asset_id),-size/2,-size/2,size,size);ctx.restore();});
    floorOutput={schema_version:1,seed,grid:floorRecipe.grid,rooms,entry:rooms[0].center,exit:rooms[rooms.length-1].center,validation:{all_walkable_cells_connected:connected,reachable_walkable_cells:visited.size},cells};
    $('procedural-export').disabled=false;$('procedural-status').textContent=`Seed ${seed} · ${tiles.length} native tiles · ${cells.filter(cell=>cell.walkable).length} walkable cells. 7 seeded rooms with connecting corridors; all walkable cells verified connected. Preview art only; gameplay collision is not integrated.`;
  }catch(error){$('procedural-status').textContent=`Floor rendering failed: ${error.message}`;}
}
$('procedural-generate').addEventListener('click',generateFloor);
$('procedural-export').addEventListener('click',()=>{if(!floorOutput)return;const url=URL.createObjectURL(new Blob([JSON.stringify(floorOutput,null,2)],{type:'application/json'}));const link=make('a');link.href=url;link.download='pocket-dungeon-floor.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

function importNumber(value, minimum, maximum, name) {
  if(typeof value!=='number'||!Number.isFinite(value)||value<minimum||value>maximum)throw Error(`Invalid ${name}.`);return value;
}
async function readImport(input) {
  const file=input.files?.[0];if(!file)return null;if(file.size>2000000)throw Error('JSON must be under 2 MB.');return JSON.parse(await file.text());
}
$('remix-import').addEventListener('change',async event=>{
  try{
    const document=await readImport(event.target);if(!document)return;
    if(document.kind!=='semantic-remix'||document.schema_version!==1||document.canvas?.width!==960||document.canvas?.height!==640||!Array.isArray(document.placements)||document.placements.length>1000)throw Error('Expected a 960 × 640 semantic-remix export.');
    const eligible=new Set(usableAssets().map(asset=>asset.id));
    const placements=document.placements.map(item=>{
      if(!eligible.has(item.asset_id))throw Error(`Unknown or ineligible asset: ${item.asset_id}`);
      if(![0,90,180,270].includes(item.rotation_deg)||item.scale!==1||item.anchor!=='center')throw Error('Unsupported placement transform.');
      return{asset_id:item.asset_id,path:reuse.metadata.get(item.asset_id).image.path,x:importNumber(item.x,0,960,'x'),y:importNumber(item.y,0,640,'y'),rotation_deg:item.rotation_deg,scale:1,anchor:'center'};
    });
    await Promise.all(placements.map(item=>reuseImage(item.path)));reuse.placements=placements;await drawRemix();
  }catch(error){$('remix-status').textContent=`Import rejected; previous room retained. ${error.message}`;}finally{event.target.value='';}
});
$('procedural-import').addEventListener('change',async event=>{
  try{
    const document=await readImport(event.target);if(!document)return;
    const grid=document.grid;if(!grid||!Number.isInteger(grid.width)||!Number.isInteger(grid.height)||grid.width<4||grid.width>64||grid.height<4||grid.height>64||grid.cell_size_px!==32||!Array.isArray(document.cells)||document.cells.length!==grid.width*grid.height)throw Error('Expected a complete grid, 4–64 cells per side, using 32 px tiles.');
    const native=new Map(floorRecipe.cells.filter(cell=>cell.walkable&&cell.path).map(cell=>[cell.asset_id,cell.path]));const keys=new Set();const open=new Set();
    const cells=document.cells.map(cell=>{
      if(!Number.isInteger(cell.x)||!Number.isInteger(cell.y)||cell.x<0||cell.y<0||cell.x>=grid.width||cell.y>=grid.height||typeof cell.walkable!=='boolean')throw Error('Invalid grid cell.');
      const key=`${cell.x},${cell.y}`;if(keys.has(key))throw Error('Duplicate grid cell.');keys.add(key);
      if(!cell.walkable)return{x:cell.x,y:cell.y,walkable:false,connections:[]};
      if(!native.has(cell.asset_id)||![0,90,180,270].includes(cell.rotation_deg))throw Error('Unknown floor tile or rotation.');open.add(key);
      return{...cell,path:native.get(cell.asset_id),position_px:[cell.x*32,cell.y*32],anchor_px:[0,0]};
    });
    if(!open.size)throw Error('Floor has no walkable cells.');
    const queue=[[...open][0]],visited=new Set();for(let i=0;i<queue.length;i++){const key=queue[i];if(visited.has(key))continue;visited.add(key);const[x,y]=key.split(',').map(Number);for(const[dx,dy]of[[1,0],[-1,0],[0,1],[0,-1]]){const next=`${x+dx},${y+dy}`;if(open.has(next)&&!visited.has(next))queue.push(next);}}
    if(visited.size!==open.size)throw Error('Floor cells are disconnected.');
    const imageEntries=await Promise.all([...native].map(async([id,path])=>[id,await reuseImage(path)]));const images=new Map(imageEntries);
    const canvas=$('procedural-canvas'),ctx=canvas.getContext('2d');canvas.width=grid.width*32;canvas.height=grid.height*32;ctx.fillStyle='#181721';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
    cells.filter(cell=>cell.walkable).forEach(cell=>{ctx.save();ctx.translate(cell.x*32+16,cell.y*32+16);ctx.rotate(cell.rotation_deg*Math.PI/180);ctx.drawImage(images.get(cell.asset_id),-16,-16,32,32);ctx.restore();});
    floorRequest++;floorOutput={...document,cells,validation:{all_walkable_cells_connected:true,reachable_walkable_cells:visited.size}};$('procedural-export').disabled=false;$('procedural-status').textContent=`Imported floor · ${visited.size} connected walkable cells. Image references resolved from the local native tile set.`;
  }catch(error){$('procedural-status').textContent=`Import rejected; previous floor retained. ${error.message}`;}finally{event.target.value='';}
});
