// Presentation only: enemy sheets contain poses of one view, not four directions.
export function rememberSpriteFacing(facing, id, dx, dy) {
  if (Number.isFinite(dx) && Number.isFinite(dy) && (dx || dy))
    facing.set(id, {x: Math.sign(dx), y: Math.sign(dy)});
}

export function seedEnemyFacing(facing, unit, opponents) {
  if (unit.team !== 'enemy' || facing.has(unit.id)) return;
  let nearest = null, distance = Infinity;
  for (const other of opponents) {
    if (other.team !== 'player' || other.hp <= 0) continue;
    const d = (other.x - unit.x) ** 2 + (other.y - unit.y) ** 2;
    if (d < distance) { nearest = other; distance = d; }
  }
  if (nearest) rememberSpriteFacing(facing, unit.id, nearest.x - unit.x, nearest.y - unit.y);
}

export function enemySpriteScaleX(key, frame, direction, rotation, native = true) {
  const {x, y} = direction ?? {x: 0, y: 1};
  const q = ((rotation % 4) + 4) % 4;
  const rx = q === 1 ? -y : q === 2 ? -x : q === 3 ? y : x;
  const ry = q === 1 ? x : q === 2 ? -y : q === 3 ? -x : y;
  // Vertical travel uses down=right/up=left because these sheets lack front/back art.
  const horizontal = native ? rx : rx - ry;
  const desired = Math.sign(horizontal || (native ? ry : rx + ry)) || 1;
  // Verified against the painted source sheets. Hoarder's walk2 switches sides.
  const authored = key === 'boss-hoarder' ? (frame < 2 ? -1 : 1)
    : ['sludge', 'cinder', 'frost', 'spore', 'sentry', 'mauler', 'scatterer'].includes(key) ? -1 : 1;
  return desired * authored;
}

export function drawFacingSprite(context, scaleX, x, y, draw) {
  context.save();
  context.translate(x, y);
  context.scale(scaleX, 1);
  try { draw(); } finally { context.restore(); }
}
