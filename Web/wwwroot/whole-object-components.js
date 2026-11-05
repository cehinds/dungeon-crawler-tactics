import { validateNativeComponents } from './native-map-visuals.js';
// Whole PNG components are presentation data. Shared C# tiles own all collision.
const TILE = 128;
const manifestLoads = new Map();
const imageLoads = new Map();

export function componentFootprint(component) {
  const cells = [];
  for (let y = component.y; y < component.y + component.height; y++) {
    for (let x = component.x; x < component.x + component.width; x++) cells.push({ x, y });
  }
  return cells;
}

export function componentDepth(component, rotation = 0) {
  const q = ((rotation % 4) + 4) % 4;
  // The front edge changes with the camera; authored PNGs keep their whole footprint.
  return [component.y + component.height - .5, component.x + component.width - .5,
    -component.y + .5, -component.x + .5][q] * 4;
}

export function componentKnown(component, revealed) {
  return !revealed || componentFootprint(component).some(cell => revealed.has(`${cell.x},${cell.y}`));
}

export function componentDisplayGeometry(component, asset) {
  const [left, top, right, bottom] = asset.visibleBounds;
  const width = right - left, height = bottom - top;
  const sideways = component.rotation % 2 === 1;
  const scale = Math.min(component.width * TILE / (sideways ? height : width), component.height * TILE / (sideways ? width : height));
  return { source: [left, top, width, height], scale,
    x: (component.x + (component.width - 1) / 2) * TILE,
    y: (component.y + (component.height - 1) / 2) * TILE,
    width: width * scale, height: height * scale, angle: component.rotation * Math.PI / 2 };
}

export function validateWholeComponents(visuals, width, height, tiles, library) {
  const components = validateNativeComponents(visuals, width, height, tiles);
  if (library) {
    const ids = new Set(library.objects.map(asset => asset.id));
    if (components.some(component => !ids.has(component.assetId))) throw new Error('Unknown whole-object component asset.');
  }
  return components;
}

async function loadImage(url) {
  if (!imageLoads.has(url)) {
    const pending = new Promise((resolve, reject) => {
      const image = new Image(); image.crossOrigin = 'anonymous';
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('A whole-object PNG could not load. Retry map art.'));
      image.src = url;
    }).catch(error => { imageLoads.delete(url); throw error; });
    imageLoads.set(url, pending);
  }
  return imageLoads.get(url);
}

export async function loadWholeComponents(visuals, width, height, tiles, assetBase) {
  const components = validateWholeComponents(visuals, width, height, tiles);
  if (!components.length) return { components: [], assets: new Map(), images: new Map() };
  const manifestURL = new URL('manifest.json', assetBase).href;
  if (!manifestLoads.has(manifestURL)) {
    manifestLoads.set(manifestURL, fetch(manifestURL).then(response => {
      if (!response.ok) throw new Error('The whole-object library could not load. Retry map art.');
      return response.json();
    }).catch(error => { manifestLoads.delete(manifestURL); throw error; }));
  }
  const manifest = await manifestLoads.get(manifestURL);
  validateWholeComponents(visuals, width, height, tiles, manifest);
  const assets = new Map(manifest.objects.map(asset => [asset.id, asset]));
  const entries = await Promise.all([...new Set(components.map(component => component.assetId))].map(async id => {
    const asset = assets.get(id), path = asset.asset?.path ?? asset.asset;
    return [id, await loadImage(new URL(path, assetBase).href)];
  }));
  return { components, assets, images: new Map(entries) };
}

export function drawWholeComponent(context, component, art, revealed = null) {
  const asset = art.assets.get(component.assetId), image = art.images.get(component.assetId);
  if (!asset || !image || !componentKnown(component, revealed)) return;
  const geometry = componentDisplayGeometry(component, asset);
  context.save();
  if (revealed) {
    // Clip at fog cells: a partly known shelf cannot reveal an unseen room.
    context.beginPath();
    for (const cell of componentFootprint(component)) {
      if (revealed.has(`${cell.x},${cell.y}`)) context.rect((cell.x - .5) * TILE, (cell.y - .5) * TILE, TILE, TILE);
    }
    context.clip();
  }
  context.translate(geometry.x, geometry.y); context.rotate(geometry.angle);
  context.drawImage(image, ...geometry.source, -geometry.width / 2, -geometry.height / 2, geometry.width, geometry.height);
  context.restore();
}
