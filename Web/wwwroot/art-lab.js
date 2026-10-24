const CATALOG_URL = new URL('assets/style-packs/catalog.json', document.baseURI);
const categories = ['terrain', 'structure', 'prop', 'actor', 'effect', 'ui', 'portrait', 'equipment', 'loot'];
const categoryNames = { supplies: 'New additions', expansion: 'Rooms & creatures', equipment: 'Equipment', loot: 'Loot', terrain: 'Terrain', structure: 'Structures', prop: 'Props', actor: 'Actors', effect: 'Effects', ui: 'UI', portrait: 'Portraits' };
const directions = {
  'pocket-dungeon': { subtitle: 'Overhead pixel art', accent: '#615064' },
  'ink-and-lanterns': { subtitle: 'Painted gouache & ink', accent: '#547058' },
  'dungeon-after-dark': { subtitle: 'Graphic novel & halftone', accent: '#416975' }
};
const $ = id => document.getElementById(id);
const state = { styles: [], active: null, manifest: null, manifestUrl: null, category: 'all', search: '', request: 0, failedLayers: new Set(), loadedLayers: new Set(), layers: [] };
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
  configureLink($('pack-download'), localUrl(manifest.download, state.manifestUrl));
  configureLink($('manifest-link'), state.manifestUrl);
  configureLink($('contact-sheet'), localUrl(manifest.contactSheet, state.manifestUrl));
  configureLink($('preview-download'), localUrl(manifest.preview.file, state.manifestUrl));
  renderLayers(manifest.preview);
  renderConcepts(style);
  renderFilters();
  renderComponents();
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
  return category === 'supplies' || category === 'expansion'
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
  const available = ['all', 'supplies', 'expansion', ...categories];
  const buttons = available.map(category => {
    const count = category === 'all' ? assets.length : assets.filter(asset => matchesCategory(asset, category)).length;
    const button = make('button', 'category-filter', category === 'all' ? 'All pieces' : categoryNames[category]);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(state.category === category));
    button.append(make('span', '', String(count)));
    button.disabled = count === 0;
    button.addEventListener('click', () => {
      state.category = category;
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
    const text = `${asset.label || ''} ${asset.id || ''} ${asset.category || ''} ${asset.layer || ''}`.toLowerCase();
    return matchingCategory && text.includes(state.search.toLowerCase().trim());
  });
  const cards = assets.map(asset => {
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
    card.append(make('p', 'component-id', asset.id));
    return card;
  });
  $('component-grid').replaceChildren(...cards);
  $('result-count').textContent = `${assets.length} of ${state.manifest.assets.length} pieces${state.category === 'all' ? '' : ` · ${categoryNames[state.category]}`}`;
  $('empty-state').hidden = assets.length > 0;
}

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
