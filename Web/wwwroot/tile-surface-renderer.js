// Assemble touching floors at their native integer resolution before zooming.
// Scaling separate transparent sprites can expose the backdrop along shared edges.
const floorLayers = new WeakMap();

export function floorLayer(placements, images) {
  const cached = floorLayers.get(placements);
  if (cached?.images === images) return cached;
  if (!placements.length) return null;
  const cells = placements.map(piece => {
    const anchor = piece.asset.anchor || { x: 128, y: 192 };
    const box = piece.asset.derived;
    const x = box.offset.x - anchor.x, y = box.offset.y - anchor.y;
    const cosine = Math.round(Math.cos(piece.angle || 0)), sine = Math.round(Math.sin(piece.angle || 0));
    const corners = [[x, y], [x + box.width, y], [x, y + box.height], [x + box.width, y + box.height]]
      .map(([a, b]) => ({ x: piece.px + a * cosine - b * sine, y: piece.py + a * sine + b * cosine }));
    return { piece, anchor, box, left: Math.min(...corners.map(p => p.x)), top: Math.min(...corners.map(p => p.y)),
      right: Math.max(...corners.map(p => p.x)), bottom: Math.max(...corners.map(p => p.y)) };
  });
  const left = Math.floor(Math.min(...cells.map(cell => cell.left)));
  const top = Math.floor(Math.min(...cells.map(cell => cell.top)));
  const right = Math.ceil(Math.max(...cells.map(cell => cell.right)));
  const bottom = Math.ceil(Math.max(...cells.map(cell => cell.bottom)));
  const canvas = document.createElement('canvas');
  canvas.width = right - left; canvas.height = bottom - top;
  const context = canvas.getContext('2d');
  context.imageSmoothingEnabled = false;
  for (const { piece, anchor, box } of cells) {
    const image = images.get(piece.asset.id);
    if (!image) continue;
    context.save(); context.translate(piece.px - left, piece.py - top); context.rotate(piece.angle || 0);
    context.drawImage(image, box.offset.x, box.offset.y, box.width, box.height, box.offset.x - anchor.x, box.offset.y - anchor.y, box.width, box.height);
    context.restore();
  }
  const layer = { canvas, left, top, images };
  floorLayers.set(placements, layer);
  return layer;
}

export function drawFloorLayer(context, placements, images) {
  const layer = floorLayer(placements, images);
  if (layer) context.drawImage(layer.canvas, layer.left, layer.top);
}
