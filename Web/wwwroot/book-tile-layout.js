// Grid positions refer to the walking surface, never to a sprite's alpha bounds.
export function projectCell(grid, x, y) {
  return grid.projection === 'isometric'
    ? { x: (x - y) * grid.tileWidth / 2, y: (x + y) * grid.tileHeight / 2 }
    : { x: x * grid.tileWidth, y: y * grid.tileHeight };
}

export function boundaryCenter(grid, axis, index) {
  const p = projectCell(grid, axis === 'x' ? index : 0, axis === 'y' ? index : 0);
  if (grid.projection === 'isometric') {
    return { x: p.x + (axis === 'x' ? 1 : -1) * grid.tileWidth / 4, y: p.y - grid.tileHeight / 4 };
  }
  return axis === 'x' ? { x: p.x, y: p.y - grid.tileHeight / 2 } : { x: p.x - grid.tileWidth / 2, y: p.y };
}

export function worldContacts(placement) {
  const anchor = placement.asset.anchor || { x: 128, y: 192 };
  return (placement.asset.placement?.points || []).map(([x, y]) => [placement.px + x - anchor.x, placement.py + y - anchor.y]);
}

export function composeKit(manifest, seedValue, size = 5) {
  const grid = manifest.grid; const assets = manifest.assets;
  let seed = seedValue >>> 0;
  const random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
  const ground = assets.filter(a => a.role === 'ground').slice(0, 4);
  const registeredGround = ground.filter(a => a.placement?.kind === 'floor');
  // Partial rails remain downloadable but require manual placement.
  const floors = registeredGround.length ? registeredGround : ground;
  const walls = assets.filter(a => a.role === 'wall');
  const doors = assets.filter(a => a.role === 'door');
  const props = assets.filter(a => a.role === 'prop');
  const placements = [];
  const add = (asset, position, layer) => { if (asset) placements.push({ asset, px: position.x, py: position.y, layer }); };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) add(floors[Math.floor(random() * floors.length)], projectCell(grid, x, y), 0);
  const hasSideWall = walls.some(a => a.placement?.kind === 'wall' && a.placement.axis === 'y');
  const axes = grid.projection === 'isometric' || hasSideWall ? ['x', 'y'] : ['x'];
  for (const axis of axes) {
    const wall = walls.find(a => a.placement?.kind === 'wall' && a.placement.axis === axis);
    if (wall) {
      const door = doors.find(a => a.placement?.kind === 'wall' && a.placement.axis === axis);
      for (let i = 0; i < size; i++) add(i === 2 && door ? door : wall, boundaryCenter(grid, axis, i), 1);
    } else {
      // Older, unregistered kits retain their illustrative placement until reviewed.
      for (let i = 0; i < size; i++) {
        const p = projectCell(grid, axis === 'x' ? i : 0, axis === 'y' ? i : 0);
        if (grid.projection === 'isometric') p.x += (axis === 'x' ? 1 : -1) * grid.tileWidth / 4;
        else p.y -= grid.tileHeight / 2;
        add(walls[axis === 'x' ? 0 : 1], p, 1);
      }
    }
  }
  for (const [x, y] of [[1, 2], [3, 2], [2, 4], [4, 4]]) add(props[Math.floor(random() * props.length)], projectCell(grid, x, y), 1);
  return placements.sort((a, b) => a.layer - b.layer || a.py - b.py || a.px - b.px);
}
