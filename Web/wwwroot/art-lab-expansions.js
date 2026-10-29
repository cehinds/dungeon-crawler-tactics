// Standalone expansion browser; the frozen reusable library registry stays authoritative.
const host = document.getElementById('expansion-content');
const base = new URL('assets/expansions/drainage-channels-v1/', document.baseURI);
function node(tag, text) { const el = document.createElement(tag); if (text) el.textContent = text; return el; }
function expansionUrl(path) { if (typeof path !== 'string' || !path.trim()) throw new Error('Missing expansion path'); const url = new URL(path, base); if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol) || !url.pathname.startsWith(base.pathname)) throw new Error('Invalid expansion path'); return url.href; }
function archiveLink(path) {
  const el = node('a', 'Expansion ZIP');
  if (typeof path === 'string' && /^https:\/\/raw\.githubusercontent\.com\/cehinds\/AI-Art\/[0-9a-f]{40}\/dungeon-crawler-tactics\/Web\/wwwroot\/assets\/expansions\/drainage-channels-v1\/drainage-channels-v1\.zip$/.test(path)) el.href = path;
  else el.href = expansionUrl(path);
  el.download = ''; return el;
}
function link(text, path) { const el = node('a', text); el.href = expansionUrl(path); el.download = ''; return el; }
try {
  const response = await fetch(new URL('catalog.json', base));
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const catalog = await response.json();
  if (!Array.isArray(catalog.assets) || catalog.assets.length !== 21) throw new Error('Expansion catalog incomplete');
  const reviewed = catalog.status === 'qualified-reviewed';
  if (reviewed) {
    document.getElementById('expansions-title').textContent = 'Reviewed dungeon tiles';
    document.querySelector('#art-expansions > p').textContent = 'Three matching channel tiles, each with six principal views plus an isometric view. Includes JSON tags, attachment hints, and an example layout.';
  }
  host.replaceChildren(); host.removeAttribute('role');
  if (reviewed) host.append(node('p', 'Review notes: visible grid seams, modest outlet offsets, and illustrative proportions.'));
  host.append(node('p', `Drainage channels · 3 new objects · 21 PNG views · ${reviewed ? 'Reviewed with notes' : catalog.status.replaceAll('-', ' ')}`));
  const controls = node('div'); controls.className = 'reuse-controls';
  if (catalog.download) controls.append(archiveLink(catalog.download));
  controls.append(link('Expansion catalog JSON', 'catalog.json'), link('Review records JSON', 'review.json'), link('Example map JSON', 'maps/example.json'));
  host.append(controls);
  const grid = node('div'); grid.className = 'drainage-expansion-grid';
  for (const shape of ['straight', 'corner', 'tee']) {
    const card = node('article'); card.append(node('h3', `Stone drainage ${shape}`));
    const label = node('label', 'View '); const select = node('select');
    const assets = catalog.assets.filter(a => a.object_id === `drainage-${shape}`);
    assets.forEach((asset, index) => { const option = node('option', asset.view); option.value = String(index); select.append(option); });
    label.append(select); card.append(label);
    const img = node('img'); img.className = 'checkerboard'; img.loading = 'lazy';
    const downloads = node('div'); downloads.className = 'reuse-controls';
    function show() { const asset = assets[Number(select.value)]; img.src = expansionUrl(asset.image.path); img.alt = asset.name; downloads.replaceChildren(link('PNG', asset.image.path), link('JSON', asset.metadata_path)); }
    select.addEventListener('change', show); show(); card.append(img, downloads, node('p', reviewed ? '1 × 1 cell · top-view quarter turns · floor support suggested · reviewed with notes' : '1 × 1 cell · top-view quarter turns · floor support suggested · visual fit pending')); grid.append(card);
  }
  host.append(grid);
  const figure = node('figure'); const map = node('img'); map.src = expansionUrl('maps/example.png'); map.alt = 'Drainage channel connection study using top views'; map.style.maxWidth = '100%'; map.style.height = 'auto'; map.width = 640; map.height = 640;
  figure.append(map, node('figcaption', reviewed ? 'Deterministic top-view connection study. Logical connections and rendered overlap reviewed with visible grid seams and modest port offsets.' : 'Deterministic top-view connection study. Logical edges are validated; rendered channel seams and visual alignment remain under review.')); host.append(figure);
} catch (error) { host.textContent = `Drainage expansion unavailable: ${error.message}. The frozen libraries remain available above.`; }
