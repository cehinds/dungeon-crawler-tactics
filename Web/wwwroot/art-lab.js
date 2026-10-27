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
const ART_ARCHIVE_REF = '4bfbe30977d95f9070fa01e0793db1a4543df9ae';
function canonicalDownloadUrl(path) {
  if (typeof path !== 'string') return null;
  let url;
  try { url = new URL(path, state.manifestUrl); } catch { return null; }
  const marker = '/assets/';
  if (url.origin !== window.location.origin) {
    if (url.protocol !== 'https:' || !['github.com','raw.githubusercontent.com'].includes(url.hostname) || !url.pathname.startsWith('/cehinds/AI-Art/') || !url.pathname.includes('/dungeon-crawler-tactics/Web/wwwroot/assets/')) return null;
  }
  const offset = url.pathname.indexOf(marker);
  const archiveFile = /\.zip(?:\.parts\.json|\.part-\d+)?$/.test(url.pathname) || url.pathname.endsWith('/assemble_archive_parts.py');
  if (offset < 0 || !archiveFile) return null;
  const relative = url.pathname.slice(offset + marker.length);
  return `https://github.com/cehinds/AI-Art/raw/${ART_ARCHIVE_REF}/dungeon-crawler-tactics/Web/wwwroot/assets/${relative}`;
}

function configureArchive(element, path) {
  configureLink(element, canonicalDownloadUrl(path));
  element.removeAttribute('download'); element.target = '_blank'; element.rel = 'noopener';
}

function renderReuseDownload(item) {
  const card = make('div', 'reuse-download');
  const link = (label, path) => {
    const element = make('a', 'text-link', label);
    configureLink(element, canonicalDownloadUrl(reuseUrl(path)));
    element.target = '_blank'; element.rel = 'noopener';
    return element;
  };
  const label = item.label || 'Asset archive';
  if (item.format === 'multipart-zip') {
    const parts = [...(item.parts || [])].sort((a, b) => a.number - b.number);
    card.append(make('strong', '', label));
    card.append(make('span', '', `Multipart ZIP · ${parts.length} parts${item.archive_bytes ? ` · ${(item.archive_bytes / 1048576).toFixed(1)} MiB assembled` : ''}`));
    card.append(link('Download JSON manifest', item.path));
    const list = make('ol', 'archive-parts');
    for (const part of parts) {
      const row = make('li');
      row.append(link(`Part ${part.number} of ${parts.length} · ${(part.bytes / 1048576).toFixed(1)} MiB`, part.path));
      list.append(row);
    }
    card.append(list);
    if (item.assembly_tool?.path) card.append(link('Download assembly helper (Python)', item.assembly_tool.path));
    card.append(make('p', '', 'Save the manifest, every numbered part and the helper in one folder. Assemble and verify the ZIP before extracting it.'));
    const filename = (item.file || item.path || '').split('/').pop();
    if (/^[a-zA-Z0-9_.-]+\.zip\.parts\.json$/.test(filename)) {
      card.append(make('code', 'archive-command', `python assemble_archive_parts.py ${filename} --output ${filename.replace(/\.parts\.json$/, '')}`));
    }
  } else {
    card.append(link(`${label} · Download ZIP`, item.path));
    if (item.bytes) card.append(make('span', '', `${(item.bytes / 1048576).toFixed(1)} MiB`));
  }
  if (item.description) card.append(make('p', '', item.description));
  return card;
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
    const text = `${asset.label || ''} ${asset.id || ''} ${asset.category || ''} ${asset.layer || ''} ${(componentMetadata(asset.id)?.tags || []).join(' ')} ${collectionNames[asset.collection || asset.source?.sheet] || ''}`.toLowerCase();
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
    const metadata = componentMetadata(asset.id);
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
const ASSETS_ROOT = new URL('assets/', document.baseURI);
function assetUrl(path, base = reuse.base) {
  if (typeof path !== 'string' || !path.trim()) return null;
  let url; try { url = new URL(path, base); } catch { return null; }
  if (url.origin === location.origin && ['http:','https:'].includes(url.protocol)) return url.href;
  if (url.protocol === 'https:' && url.hostname === 'raw.githubusercontent.com' && /^\/cehinds\/AI-Art\/[a-f0-9]{40}\/dungeon-crawler-tactics\//.test(url.pathname)) return url.href;
  return null;
}
function reuseUrl(path) { return assetUrl(path); }
function renderReviewMetadata(reference, linkId, statusId, targeted = false) {
  const url=typeof reference?.path==='string'?reuseUrl(reference.path):null;
  const link=$(linkId),status=$(statusId);
  configureLink(link,url);link.hidden=!url;
  link.title=typeof reference?.sha256==='string'?`SHA-256: ${reference.sha256}`:'';
  const stats=reference?.statistics;
  const validCount=value=>Number.isSafeInteger(value)&&value>=0;
  const valid=url&&validCount(stats?.expected_sets)&&validCount(stats?.approved_sets)&&stats.approved_sets<=stats.expected_sets;
  status.hidden=!valid;
  status.textContent=valid?(targeted
    ?`Targeted legacy review: ${stats.approved_sets} of ${stats.expected_sets} selected sets approved. Other previously delivered sets are outside this targeted review.`
    :`Independent visual review: ${stats.approved_sets} of ${stats.expected_sets} sets approved. Pending and failed sets remain recorded in the review JSON.`):'';
}
let reusableRegistry;
const libraryCache = new Map();
async function loadReusableRegistry() {
  if (!reusableRegistry) reusableRegistry = fetch(new URL('reusable-library.json', ASSETS_ROOT)).then(async response => {
    if (response.status === 404) return [{id:'pocket-dungeon',label:'Pocket Dungeon',index:'style-packs/pocket-dungeon/reusable/index.json',base:'style-packs/pocket-dungeon/',style:'pocket-dungeon',kind:'style-pack'}];
    if (!response.ok) throw Error(`Library registry returned HTTP ${response.status}.`);
    const data=await response.json();
    if((data.version??data.schema_version)!==1 || !Array.isArray(data.libraries) || !data.libraries.length || new Set(data.libraries.map(item=>item.id)).size!==data.libraries.length || data.libraries.some(item=>!item.id||!item.label||typeof item.base!=='string'||!assetUrl(item.index,ASSETS_ROOT)||!assetUrl(item.base,ASSETS_ROOT))) throw Error('The reusable library registry is malformed.');
    return data.libraries.map(library=>({...library,art_commit:library.art_commit||data.art_commit}));
  });
  return reusableRegistry;
}
async function libraryData(id) {
  const libraries=await loadReusableRegistry(),library=libraries.find(item=>item.id===id);
  if(!library)throw Error(`Unknown library: ${id}`);
  if(!libraryCache.has(id))libraryCache.set(id,(async()=>{
    const base=assetUrl(library.base.endsWith('/')?library.base:`${library.base}/`,ASSETS_ROOT),indexUrl=assetUrl(library.index,ASSETS_ROOT);
    const index=await fetchJson(indexUrl);
    if(!Array.isArray(index.assets)||!Array.isArray(index.maps)||new Set(index.assets.map(asset=>asset.id)).size!==index.assets.length)throw Error(`Malformed asset index: ${id}`);
    await loadGenerationBlocks(index,base);
    return{library,index,base,indexUrl,metadata:new Map(index.assets.map(asset=>[asset.id,asset])),art_commit:library.art_commit||new URL(indexUrl).pathname.match(/\/AI-Art\/([a-f0-9]{40})\//)?.[1]||ART_ARCHIVE_REF};
  })());
  return libraryCache.get(id);
}
const PRINCIPAL_VIEWS = ['front','top','right','left','bottom','rear'];
// The release validator authenticates receipts and approvals; the browser additionally
// pins the report and checks its catalog bindings before enabling partial views.
async function loadGenerationBlocks(index,base) {
  index.recordedBlocks=new Map();
  if(!index.generation_blocks)return;
  const reference=index.generation_blocks,url=assetUrl(reference.path,base);
  if(!url||!/^[a-f0-9]{64}$/.test(reference.sha256||''))throw Error('Invalid recorded-block reference.');
  const response=await fetch(url);if(!response.ok)throw Error('Recorded-block report unavailable.');
  const bytes=await response.arrayBuffer();
  const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  if(digest!==reference.sha256)throw Error('Recorded-block report hash mismatch.');
  const report=JSON.parse(new TextDecoder().decode(bytes));
  bindGenerationBlocks(index,report);
}
function bindGenerationBlocks(index,report) {
  const records=new Map(),assets=new Map(index.assets.map(asset=>[asset.id,asset]));
  if(report.schema_version!==1||report.policy!=='recorded-image-tool-block-release-v1'||report.path_base!=='library-root'||!Array.isArray(report.records))throw Error('Malformed recorded-block report.');
  let count=0;
  for(const row of report.records){
    const group=index.view_sets?.find(set=>set.object_id===row.object_id),affected=row.affected_views;
    if(records.has(row.object_id)||row.status!=='external-generation-blocked'||row.complete!==false||group?.complete!==false||!Array.isArray(affected)||!affected.length||new Set(affected).size!==affected.length||affected.some(view=>!PRINCIPAL_VIEWS.includes(view)))throw Error('Invalid incomplete recorded-block set.');
    const primary=assets.get(row.primary_source?.asset_id);
    if(!primary||primary.image?.path!==row.primary_source.path||!/^[a-f0-9]{64}$/.test(row.primary_source.sha256||'')||['sha256','rgba_sha256'].some(key=>primary.image?.[key]&&primary.image[key]!==row.primary_source[key]))throw Error('Recorded-block source differs from catalog.');
    const review=row.unaffected_review,approved=PRINCIPAL_VIEWS.filter(view=>!affected.includes(view));
    if(review?.status!=='independent-partial-review'||!Array.isArray(review.approved_views)||review.approved_views.length!==approved.length||approved.some(view=>!review.approved_views.includes(view)))throw Error('Missing partial-view approval.');
    for(const view of PRINCIPAL_VIEWS){
      const reference=group.views?.[view],id=typeof reference==='string'?reference:reference?.asset_id,leaf=assets.get(id),binding=row.views?.[view];
      if(!leaf||leaf.object_id!==row.object_id||leaf.view!==view||binding?.asset_id!==id||binding.path!==leaf.image?.path||!/^[a-f0-9]{64}$/.test(binding.sha256||'')||(leaf.image.sha256&&leaf.image.sha256!==binding.sha256)||(binding.rgba_sha256&&leaf.image.rgba_sha256&&leaf.image.rgba_sha256!==binding.rgba_sha256)||(!affected.includes(view)&&['asset_id','path','sha256','rgba_sha256'].some(key=>review.views?.[view]?.[key]!==binding[key])))throw Error('Recorded-block view differs from catalog.');
    }
    records.set(row.object_id,row);count+=affected.length;
  }
  for(const stats of [report.statistics,index.generation_blocks?.statistics])if(stats?.recorded_blocked_sets!==records.size||stats?.recorded_blocked_views!==count)throw Error('Incorrect recorded-block counts.');
  index.recordedBlocks=records;
}
function recordedBlock(asset,index) {return index?.recordedBlocks?.get(asset?.object_id||asset?.id);}
function blockedDirection(asset,index) {return !!recordedBlock(asset,index)?.affected_views.includes(asset?.view);}
function selectableAsset(asset,metadata,index) {
  if(blockedDirection(asset,index))return false;
  if(!asset||asset.reusable===false||['composition_layer','reconstruction_patch','residual'].includes(asset.kind)||!asset.image?.path)return false;
  if(!asset.view||asset.view==='source')return true;
  const parent=metadata.get(asset.object_id);
  return asset.view==='front'&&parent?.kind==='reconstruction_patch'&&canonicalViewReferences(parent,index).front.asset_id===asset.id;
}

function canonicalViewReferences(parent,index) {
  const set=index?.view_sets?.find(item=>item.object_id===(parent.object_id||parent.id));
  const references={};
  for(const direction of PRINCIPAL_VIEWS){
    const fromSet=set?.views?.[direction] || (set?.directions&&set?.assets?set.assets[set.directions.indexOf(direction)]:null);
    const fromParent=parent.views?.[direction];
    const block=recordedBlock(parent,index);
    references[direction]={blocked:!!block?.affected_views.includes(direction),blockReason:block?.affected_views.includes(direction)&&typeof block.reason==='string'?block.reason:null,asset_id:typeof fromSet==='string'?fromSet:fromSet?.asset_id||fromParent?.asset_id,status:block?.affected_views.includes(direction)?'unapproved reference · generation unavailable':fromParent?.status||'generated-inferred',reviewed:block?block.unaffected_review.approved_views.includes(direction):(set?.complete??parent.views?.complete??false)};
  }
  return references;
}
function eligibleAsset(asset,metadata,index) {
  if(blockedDirection(asset,index))return false;
  if(selectableAsset(asset,metadata,index))return true;
  if(!asset||asset.reusable===false||!PRINCIPAL_VIEWS.includes(asset.view)||!asset.image?.path)return false;
  const parent=metadata.get(asset.object_id);
  if(!parent||parent.id===asset.id)return false;
  return canonicalViewReferences(parent,index)[asset.view]?.asset_id===asset.id;
}


async function reuseImage(path) { return reuseImageAt(path,reuse.base); }
async function reuseImageAt(path,base) {
  const url = assetUrl(path,base);
  if (!url) throw new Error('Missing local image path.');
  if (!reuse.images.has(url)) reuse.images.set(url, new Promise((resolve, reject) => {
    const image = new Image(); if(new URL(url).origin!==location.origin) image.crossOrigin='anonymous'; image.onload = () => resolve(image); image.onerror = () => reject(new Error(`Could not load ${path}`)); image.src = url;
  }));
  return reuse.images.get(url);
}
async function loadReusable(id, libraryId = null) {
  $('reusable').hidden = false;
  const loadRequest = reuse.loadRequest = (reuse.loadRequest || 0) + 1;
  reuse.index = null; reuse.metadata = new Map(); reuse.images.clear(); reuse.map = null;
  reuse.remixRequest = (reuse.remixRequest || 0) + 1;
  reuse.mapRequest++; reuse.drawRequest = (reuse.drawRequest || 0) + 1;
  floorRequest++; floorRecipe=null;floorOutput=null;
  let libraries;try{libraries=await loadReusableRegistry();}catch(error){$('reusable-tools').hidden=true;$('reusable-status').textContent=`Library registry unavailable: ${error.message}`;return;}
  if(loadRequest !== reuse.loadRequest) return;
  const library = libraries.find(item=>item.id===libraryId) || libraries.find(item=>item.style===id && item.kind==='style-pack') || libraries.find(item=>item.style===id) || libraries[0];
  $('reusable-library').replaceChildren(...libraries.map(item=>{const option=make('option','',item.label);option.value=item.id;return option;}));
  if(!library){$('reusable-status').textContent='No reusable libraries are registered.';return;}
  reuse.library=library;$('reusable-library').value=library.id;
  $('reusable-status').textContent = 'Loading reusable asset metadata…'; $('reusable-tools').hidden = true;
  reuse.base = assetUrl(library.base.endsWith('/') ? library.base : `${library.base}/`, ASSETS_ROOT);
  const indexUrl = assetUrl(library.index, ASSETS_ROOT);
  reuse.indexUrl = indexUrl;
  try {
    const resolved = await libraryData(library.id);
    const index = resolved.index;
    if (state.active !== id || loadRequest !== reuse.loadRequest) return;
    reuse.index = index; reuse.metadata = resolved.metadata;
    configureLink($('reusable-index'), indexUrl);
    const blockRef=index.generation_blocks;configureLink($('reusable-blocks'),blockRef?reuseUrl(blockRef.path):null);$('reusable-blocks').hidden=!blockRef;
    $('reusable-blocks-status').hidden=!blockRef;$('reusable-blocks-status').textContent=blockRef?`${blockRef.statistics.recorded_blocked_sets} incomplete sets · ${blockRef.statistics.recorded_blocked_views} unavailable directions. Existing PNGs for these directions are unapproved references and cannot be placed. Other directions retain their recorded partial approval.`:'';
    renderReviewMetadata(index.view_review,'reusable-review','reusable-review-status');
    renderReviewMetadata(index.legacy_view_review,'reusable-legacy-review','reusable-legacy-review-status',true);
    $('reusable-downloads').replaceChildren(...(index.downloads || []).map(renderReuseDownload));
    $('reconstruction-source').replaceChildren(...index.maps.map(map => { const option = make('option', '', map.label || map.id); option.value = map.id; return option; }));
    $('reusable-tools').hidden = false;
    const physical = index.assets.filter(asset=>asset.views?.applicable===true && (!asset.view || asset.view==='source'));
    const identities = new Set(physical.map(asset=>asset.object_id||asset.id));
    const objectCount=index.statistics?.canonical_physical_object_count ?? identities.size;
    const missing=index.statistics?.canonical_physical_objects_missing_six_views ?? [...identities].filter(id=>!reuse.metadata.get(id)?.views?.complete&&!index.view_sets?.some(set=>set.object_id===id&&set.complete)).length;
    $('reusable-coverage').textContent=`${library.label} · ${index.maps.length} source reconstruction maps · ${objectCount} physical objects · ${physical.length} native source references · ${missing} objects missing complete six-view sets. Missing views remain explicitly recorded.`;
    $('reusable-status').textContent = `${index.assets.length} recorded assets · ${index.maps.length} reconstruction maps. Fidelity is determined by the exported pixel validation report.`;
    $('reusable-source-coverage').replaceChildren(...index.maps.map(map=>{const item=make('li');const link=make('a','',map.label||map.id);configureLink(link,reuseUrl(map.file));item.append(link,document.createTextNode(` · ${map.kind||'source'} · ${typeof map.source==='string'?map.source:map.source?.path||map.id}`));return item;}));
    $('reusable-search').value='';
    const attachmentTags=[...new Set(usableAssets().flatMap(asset=>[...(asset.tags||[]).filter(tag=>tag.startsWith('attachment:')),...(asset.attachment?.requires?.any||[]),...(asset.attachment?.requires?.all||[]),...(asset.attachment?.provides||[])]))].sort();
    $('attachment-filter').replaceChildren(new Option('All attachments','all'),...attachmentTags.map(tag=>new Option(tag,tag)));
    renderReuseAssets();drawRemix(); renderComponents(); loadProcedural(); if(index.maps.length)await loadReconstruction();else $('reconstruction-caption').textContent='No reconstruction maps in this library.';
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
function usableAssets() { return (reuse.index?.assets || []).filter(asset => selectableAsset(asset,reuse.metadata,reuse.index)); }
function renderReuseAssets() {
  const query=$('reusable-search').value.trim().toLowerCase(); const previous=$('reusable-asset').value;
  const support=$('attachment-filter').value;
  const assets=usableAssets().filter(asset=>`${asset.id} ${asset.name} ${(asset.tags||[]).join(' ')}`.toLowerCase().includes(query) && (support==='all'||[...(asset.tags||[]),...(asset.attachment?.requires?.any||[]),...(asset.attachment?.requires?.all||[]),...(asset.attachment?.provides||[])].includes(support)));
  $('reusable-asset').replaceChildren(...assets.map(asset=>{const option=make('option','',asset.name||asset.id);option.value=asset.id;return option;}));
  if(assets.some(asset=>asset.id===previous)) $('reusable-asset').value=previous;
  renderReuseAsset();
}
function renderReuseAsset() {
  const asset=reuse.metadata.get($('reusable-asset').value); const image=$('reusable-image');
  if(!asset) { renderPlacementViews(null);$('attachment-detail').textContent='No matching asset.';$('attachment-suggestions').replaceChildren();image.removeAttribute('src');image.alt='No matching semantic asset';$('reusable-views').replaceChildren();$('reusable-tags').textContent='No matching assets.';configureLink($('reusable-metadata'),null);return; }
  image.src=reuseUrl(asset.image.path); image.alt=asset.name||asset.id;
  renderAttachment(asset);
  renderPlacementViews(asset);
  const set = (reuse.index.view_sets || []).find(item => item.object_id === (asset.object_id || asset.id));
  const parent=reuse.metadata.get(asset.object_id)||asset;
  const views = set ? {applicable:true,complete:set.complete,...canonicalViewReferences(parent,reuse.index)} : asset.views;
  $('reusable-tags').textContent=(asset.tags||[]).join(' · '); configureLink($('reusable-metadata'),reuseUrl(asset.metadata_path));
  if (views?.applicable === false) { $('reusable-views').replaceChildren(make('p', '', `Six principal views: not applicable. ${views.reason || views.notes || 'This image represents a flat graphic or effect.'}`)); return; }
  $('reusable-views').replaceChildren(...['front','top','right','left','bottom','rear'].map(direction=>{
    const item=views?.[direction];const card=make('div','reuse-view');card.append(make('strong','',direction),make('span','',item?.status||'unavailable'));
    const target=item?.asset_id&&reuse.metadata.get(item.asset_id); if(target) {const preview=make('img');preview.src=reuseUrl(target.image.path);preview.alt=`${asset.name||asset.id}: ${direction} view`;preview.loading='lazy';card.append(preview,make('span','',item?.blocked?`Unapproved reference only: generation unavailable. Placement disabled. ${item.blockReason||''}`:item?.reviewed?'Approved reusable direction; hidden surfaces inferred.':'Generated view: inferred surfaces, review pending.'));const link=make('a','','Download PNG');link.download='';configureLink(link,reuseUrl(target.image.path));card.append(link);const metadata=make('a','','Download view JSON');metadata.download='';configureLink(metadata,reuseUrl(target.metadata_path));card.append(metadata);}return card;
  }));
}
async function drawRemix() {
  const canvas=$('remix-canvas'), context=canvas.getContext('2d'); const placements=[...reuse.placements];
  const request = reuse.remixRequest = (reuse.remixRequest || 0) + 1;
  let images;
  try { images=await Promise.all(placements.map(async item=>{const data=await libraryData(item.library_id);const asset=data.metadata.get(item.asset_id);if(!eligibleAsset(asset,data.metadata,data.index))throw Error(`Ineligible asset: ${item.asset_id}`);return reuseImageAt(asset.image.path,data.base);})); } catch(error) { $('remix-status').textContent=`Could not draw placement: ${error.message}`; return; }
  if (request !== reuse.remixRequest) return;
  context.clearRect(0,0,canvas.width,canvas.height);context.imageSmoothingEnabled=false;
  placements.forEach((item,index)=>{const image=images[index];context.save();context.translate(item.x,item.y);context.rotate(item.rotation_deg*Math.PI/180);context.drawImage(image,-Math.floor(image.width/2),-Math.floor(image.height/2));context.restore();});
  $('remix-status').textContent=`${placements.length} semantic pieces placed · ${new Set(placements.map(item=>item.library_id)).size} libraries · 960 × 640 canvas`;
}
function renderPlacementViews(selected) {
  reuse.placementOptions=new Map();
  const selector=$('remix-view');selector.replaceChildren();
  if(!selected){renderPlacementPreview();return;}
  const add=(direction,id,label,status,reviewed)=>{const asset=reuse.metadata.get(id);const option=make('option','',label);option.value=direction;option.disabled=!eligibleAsset(asset,reuse.metadata,reuse.index);selector.append(option);if(!option.disabled)reuse.placementOptions.set(direction,{asset,status,reviewed});};
  add('source',selected.id,selected.view&&selected.view!=='source'?'Selected clean front proxy':'Source image',selected.view&&selected.view!=='source'?'generated-inferred':'source pixels',!selected.view||selected.view==='source');
  const parent=reuse.metadata.get(selected.object_id)||selected;
  const references=canonicalViewReferences(parent,reuse.index);
  for(const direction of PRINCIPAL_VIEWS){const reference=references[direction];const exists=reference.asset_id&&reuse.metadata.has(reference.asset_id);add(direction,reference.asset_id,`${direction[0].toUpperCase()+direction.slice(1)} · ${exists?(reference.blocked?'unapproved reference, generation unavailable':reference.reviewed?'approved direction':'available, review pending'):'unavailable'}`,reference.status,reference.reviewed);}
  selector.value='source';renderPlacementPreview();
}
function renderPlacementPreview() {
  const option=reuse.placementOptions?.get($('remix-view').value),preview=$('remix-placement-preview');
  if(!option){preview.removeAttribute('src');preview.alt='No eligible placement view';$('remix-view-status').textContent='Select an object with an available image.';return;}
  preview.src=reuseUrl(option.asset.image.path);preview.alt=`Selected placement: ${option.asset.name||option.asset.id}`;
  $('remix-view-status').textContent=`Places ${option.asset.id} · ${option.status}${option.status==='source pixels'?'':option.reviewed?' · recorded direction approval; surfaces inferred':' · review pending; inferred preview'}. Rotation changes this flat image.`;
}
function placeRemix(x,y) {
  const asset=reuse.placementOptions?.get($('remix-view').value)?.asset;
  if(!eligibleAsset(asset,reuse.metadata,reuse.index))return;
  reuse.placements.push({library_id:reuse.library.id,asset_id:asset.id,path:asset.image.path,x:Math.round(x),y:Math.round(y),rotation_deg:Number($('remix-rotation').value),scale:1,anchor:'center'});drawRemix();
}
$('remix-view').addEventListener('change',renderPlacementPreview);

$('reconstruction-source').addEventListener('change',loadReconstruction);
for(const [id,semanticOnly] of [['reconstruction-all',false],['reconstruction-semantic',true]]) $(id).addEventListener('click',()=>{reuse.checks=reuse.map.layers.map(layer=>!semanticOnly||layer.role==='semantic');$('reconstruction-layers').querySelectorAll('input').forEach((input,index)=>input.checked=reuse.checks[index]);drawReconstruction();});
$('reusable-search').addEventListener('input',renderReuseAssets);$('reusable-asset').addEventListener('change',renderReuseAsset);
$('remix-canvas').addEventListener('click',event=>{const bounds=event.currentTarget.getBoundingClientRect();placeRemix((event.clientX-bounds.left)*960/bounds.width,(event.clientY-bounds.top)*640/bounds.height);});
$('remix-canvas').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();placeRemix(480,320);}});
$('remix-undo').addEventListener('click',()=>{reuse.placements.pop();drawRemix();});$('remix-clear').addEventListener('click',()=>{reuse.placements=[];drawRemix();});
$('remix-export').addEventListener('click',async()=>{
  try {
    const ids=[...new Set(reuse.placements.map(item=>item.library_id))];
    const dependencies=await Promise.all(ids.map(async id=>{const data=await libraryData(id);return{library_id:id,art_commit:data.art_commit};}));
    const data={schema_version:2,kind:'semantic-remix',canvas:{width:960,height:640},dependencies,placements:reuse.placements};
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=make('a');link.href=url;link.download='mixed-library-remix.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(error){$('remix-status').textContent=`Export failed: ${error.message}`;}
});

let floorRecipe = null, floorOutput = null, floorRequest = 0;
async function loadProcedural() {
  const request=++floorRequest; floorRecipe=null;floorOutput=null;$('procedural-export').disabled=true;
  const recipePath=reuse.index?.procedural?.recipe; $('procedural-section').hidden=!recipePath; if(!recipePath)return;
  try {const recipe=await fetchJson(reuseUrl(recipePath));if(request!==floorRequest)return;floorRecipe=recipe;await generateFloor();}
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
    const images=await Promise.all(tiles.map(tile=>reuseImage(tile.path)));if(request!==floorRequest)return;
    const imageById=new Map(tiles.map((tile,index)=>[tile.asset_id,images[index]]));
    const canvas=$('procedural-canvas');canvas.width=floorRecipe.grid.width*size;canvas.height=floorRecipe.grid.height*size;
    const ctx=canvas.getContext('2d');ctx.fillStyle='#181721';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
    cells.filter(cell=>cell.walkable).forEach(cell=>{ctx.save();ctx.translate(cell.x*size+size/2,cell.y*size+size/2);ctx.rotate(cell.rotation_deg*Math.PI/180);ctx.drawImage(imageById.get(cell.asset_id),-size/2,-size/2,size,size);ctx.restore();});
    floorOutput={schema_version:1,library_id:reuse.library.id,style:reuse.library.style,index:reuse.indexUrl,seed,grid:floorRecipe.grid,rooms,entry:rooms[0].center,exit:rooms[rooms.length-1].center,validation:{all_walkable_cells_connected:connected,reachable_walkable_cells:visited.size},cells};
    $('procedural-export').disabled=false;$('procedural-status').textContent=`Seed ${seed} · ${tiles.length} native tiles · ${cells.filter(cell=>cell.walkable).length} walkable cells. 7 seeded rooms with connecting corridors; all walkable cells verified connected. Preview art only; gameplay collision is not integrated.`;
  }catch(error){$('procedural-status').textContent=`Floor rendering failed: ${error.message}`;}
}
$('procedural-generate').addEventListener('click',generateFloor);
$('procedural-export').addEventListener('click',()=>{if(!floorOutput)return;const url=URL.createObjectURL(new Blob([JSON.stringify(floorOutput,null,2)],{type:'application/json'}));const link=make('a');link.href=url;link.download=`${reuse.library.id}-floor.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

function importNumber(value, minimum, maximum, name) {
  if(typeof value!=='number'||!Number.isFinite(value)||value<minimum||value>maximum)throw Error(`Invalid ${name}.`);return value;
}
async function readImport(input) {
  const file=input.files?.[0];if(!file)return null;if(file.size>2000000)throw Error('JSON must be under 2 MB.');return JSON.parse(await file.text());
}
$('remix-import').addEventListener('change',async event=>{
  const importRequest=reuse.remixRequest;
  try{
    const document=await readImport(event.target);if(!document)return;
    if(document.kind!=='semantic-remix'||![1,2].includes(document.schema_version)||document.canvas?.width!==960||document.canvas?.height!==640||!Array.isArray(document.placements)||document.placements.length>1000)throw Error('Expected a 960 × 640 semantic-remix export.');
    const dependencies=new Map();let legacyId=null;
    if(document.schema_version===2){
      if(!Array.isArray(document.dependencies)||document.dependencies.length>100)throw Error('Missing library dependencies.');
      for(const dep of document.dependencies){const data=await libraryData(dep.library_id);if(dep.art_commit!==data.art_commit)throw Error(`Art revision mismatch for ${dep.library_id}.`);dependencies.set(dep.library_id,data);}
    }else{const original=document.library_id||'pocket-dungeon',libraries=await loadReusableRegistry();const id=libraries.some(item=>item.id===original)?original:libraries.find(item=>item.style===original&&item.kind==='style-pack')?.id;legacyId=id;if(id!==reuse.library.id)throw Error('Select the legacy export’s original library before importing.');dependencies.set(id,await libraryData(id));}
    const placements=[];
    for(const item of document.placements){
      const library_id=item.library_id||legacyId||document.library_id||'pocket-dungeon',data=dependencies.get(library_id),asset=data?.metadata.get(item.asset_id);
      if(!data||!eligibleAsset(asset,data.metadata,data.index))throw Error(`Unknown or ineligible asset: ${library_id}/${item.asset_id}`);
      if(document.schema_version===2 && (!Number.isInteger(item.x)||!Number.isInteger(item.y)))throw Error('Placement coordinates must be native-pixel integers.');
      if(item.path && item.path!==asset.image.path)throw Error('Asset path differs from trusted library metadata.');
      if(![0,90,180,270].includes(item.rotation_deg)||item.scale!==1||item.anchor!=='center')throw Error('Unsupported placement transform.');
      placements.push({library_id,asset_id:item.asset_id,path:asset.image.path,x:importNumber(item.x,0,960,'x'),y:importNumber(item.y,0,640,'y'),rotation_deg:item.rotation_deg,scale:1,anchor:'center'});
    }
    await Promise.all(placements.map(async item=>{const data=dependencies.get(item.library_id);return reuseImageAt(item.path,data.base);}));
    if(importRequest!==reuse.remixRequest)throw Error('Workspace changed during import; retry.');
    reuse.placements=placements;await drawRemix();
  }catch(error){$('remix-status').textContent=`Import rejected; previous room retained. ${error.message}`;}finally{event.target.value='';}
});
$('procedural-import').addEventListener('change',async event=>{
  try{
    const document=await readImport(event.target);if(!document)return;
    if(document.library_id && document.library_id!==reuse.library.id && !(document.library_id===reuse.library.style&&reuse.library.kind==='style-pack'))throw Error('Select the export’s original library before importing.');
    if(!floorRecipe)throw Error('This library has no native floor recipe.');
    const grid=document.grid;if(!grid||!Number.isInteger(grid.width)||!Number.isInteger(grid.height)||grid.width<4||grid.width>64||grid.height<4||grid.height>64||grid.cell_size_px!==floorRecipe.grid.cell_size_px||grid.width*grid.cell_size_px>8192||grid.height*grid.cell_size_px>8192||!Array.isArray(document.cells)||document.cells.length!==grid.width*grid.height)throw Error('Expected a complete grid, 4–64 cells per side, using the library’s recorded tile size.');
    const native=new Map(floorRecipe.cells.filter(cell=>cell.walkable&&cell.path).map(cell=>[cell.asset_id,cell.path]));const keys=new Set();const open=new Set();
    const cells=document.cells.map(cell=>{
      if(!Number.isInteger(cell.x)||!Number.isInteger(cell.y)||cell.x<0||cell.y<0||cell.x>=grid.width||cell.y>=grid.height||typeof cell.walkable!=='boolean')throw Error('Invalid grid cell.');
      const key=`${cell.x},${cell.y}`;if(keys.has(key))throw Error('Duplicate grid cell.');keys.add(key);
      if(!cell.walkable)return{x:cell.x,y:cell.y,walkable:false,connections:[]};
      if(!native.has(cell.asset_id)||![0,90,180,270].includes(cell.rotation_deg))throw Error('Unknown floor tile or rotation.');open.add(key);
      return{...cell,path:native.get(cell.asset_id),position_px:[cell.x*grid.cell_size_px,cell.y*grid.cell_size_px],anchor_px:[0,0]};
    });
    if(!open.size)throw Error('Floor has no walkable cells.');
    const queue=[[...open][0]],visited=new Set();for(let i=0;i<queue.length;i++){const key=queue[i];if(visited.has(key))continue;visited.add(key);const[x,y]=key.split(',').map(Number);for(const[dx,dy]of[[1,0],[-1,0],[0,1],[0,-1]]){const next=`${x+dx},${y+dy}`;if(open.has(next)&&!visited.has(next))queue.push(next);}}
    if(visited.size!==open.size)throw Error('Floor cells are disconnected.');
    const imageEntries=await Promise.all([...native].map(async([id,path])=>[id,await reuseImage(path)]));const images=new Map(imageEntries);
    const canvas=$('procedural-canvas'),ctx=canvas.getContext('2d');canvas.width=grid.width*grid.cell_size_px;canvas.height=grid.height*grid.cell_size_px;ctx.fillStyle='#181721';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
    cells.filter(cell=>cell.walkable).forEach(cell=>{ctx.save();ctx.translate((cell.x+0.5)*grid.cell_size_px,(cell.y+0.5)*grid.cell_size_px);ctx.rotate(cell.rotation_deg*Math.PI/180);ctx.drawImage(images.get(cell.asset_id),-grid.cell_size_px/2,-grid.cell_size_px/2,grid.cell_size_px,grid.cell_size_px);ctx.restore();});
    floorRequest++;floorOutput={...document,cells,validation:{all_walkable_cells_connected:true,reachable_walkable_cells:visited.size}};$('procedural-export').disabled=false;$('procedural-status').textContent=`Imported floor · ${visited.size} connected walkable cells. Image references resolved from the local native tile set.`;
  }catch(error){$('procedural-status').textContent=`Import rejected; previous floor retained. ${error.message}`;}finally{event.target.value='';}
});

$('reusable-library').addEventListener('change',event=>loadReusable(state.active,event.target.value));

function componentMetadata(id) { return reuse.library?.style === state.active && reuse.library?.kind === 'style-pack' ? reuse.metadata.get(id) : null; }

const attachmentCache=new Map();
async function renderAttachment(asset) {
  const libraryId=reuse.library.id,rulePath=reuse.index.attachment_rules;
  const rulesUrl=typeof rulePath==='string'?reuseUrl(rulePath):assetUrl('attachment-rules.json',ASSETS_ROOT);
  configureLink($('attachment-rules-link'),rulesUrl);
  const block=recordedBlock(asset,reuse.index);
  const info=block&&asset.attachment?{...asset.attachment,provides:[]}:asset.attachment;
  $('attachment-detail').textContent=info?`${info.space} · ${info.role} · requires any: ${(info.requires?.any||[]).join(', ')||'none'} · requires all: ${(info.requires?.all||[]).join(', ')||'none'} · excludes: ${(info.requires?.none||[]).join(', ')||'none'} · provides: ${(info.provides||[]).join(', ')||'none'}. ${info.reason||''}`:'No attachment record has been supplied for this asset.';
  $('attachment-suggestions').replaceChildren();
  if(block)$('attachment-detail').textContent+=' Incomplete recorded-block set: not eligible as a trusted surface provider.';
  if(!info?.compatibility_group||!rulesUrl)return;
  try {
    if(!attachmentCache.has(rulesUrl))attachmentCache.set(rulesUrl,fetchJson(rulesUrl));
    const rules=await attachmentCache.get(rulesUrl);
    if(libraryId!==reuse.library.id||asset.id!==$('reusable-asset').value)return;
    const group=rules.groups?.find(group=>group.id===info.compatibility_group);
    if(!group){$('attachment-suggestions').append(make('li','','No compatibility group record is available.'));return;}
    $('attachment-suggestions').append(make('li','',group.reason||'Compatible tile suggestions from the authored attachment group.'));
    const selfId=`${libraryId}::${asset.canonical_asset_id||asset.object_id||asset.id}`;
    const compatible=id=>!info.exclude_self||id!==selfId;
    const preferred=[...new Set(group.preferred_tile_ids||[])].filter(compatible);
    const suggestions=[...new Set([...preferred,...(group.tile_ids||[])])].filter(compatible);
    if(preferred.length)$('attachment-suggestions').append(make('li','',`${preferred.length} tiles share this visual style; other styles may be semantically compatible.`));
    for(const id of suggestions.slice(0,30))$('attachment-suggestions').append(make('li','',id));
    if(suggestions.length>30)$('attachment-suggestions').append(make('li','',`${suggestions.length} suggestions total; download the rules JSON for the complete list.`));
  }catch(error){if(libraryId===reuse.library.id)$('attachment-suggestions').append(make('li','',`Suggestions unavailable: ${error.message}`));}
}
$('attachment-filter').addEventListener('change',renderReuseAssets);
