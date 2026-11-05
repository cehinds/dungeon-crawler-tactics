import { getBookOneFloorPlayable } from "./book-one-playable-floor.js";
import { WHOLE_OBJECT_ASSET_BASE } from "./whole-object-map.js";
import {
  generateBookOneFloor,
  validateBookOneFloor,
  createBookOneExploration,
  restoreBookOneExploration,
} from "./book-one-floor.js";
const standalone =
  document.querySelector('meta[name="book-one-floor-mode"]')?.content ===
  "standalone";
const $ = (id) => document.getElementById(id),
  canvas = $("map"),
  worldCanvas = document.createElement("canvas"),
  ctx = worldCanvas.getContext("2d"),
  screenCtx = canvas.getContext("2d");
let library,
  rules,
  canonicalManifest,
  catalog,
  archetypes,
  floor,
  state,
  selected,
  map,
  packet,
  images = new Map(),
  loadSerial = 0;
const tilesize = 48,
  palettes = {
    guild: { floor: [42, 49, 61], edge: "#202a38", ambient: "#ddae5a13" },
    "safe-rest": { floor: [50, 47, 44], edge: "#29272a", ambient: "#e6b46b20" },
    machinery: { floor: [30, 45, 55], edge: "#172833", ambient: "#65adba17" },
  };
const status = (message, error = false) => {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
};
async function json(url) {
  const inline = {
    "data/procedural-object-room-rules.json": "book-one-rules",
    "assets/room-kit/manifest.json": "book-one-canonical",
    "data/book-one-floor-one.json": "book-one-catalog",
    "data/book-one-location-archetypes.json": "book-one-archetypes",
  }[url];
  if (inline && $(inline)) return JSON.parse($(inline).textContent);
  const response = await fetch(url);
  if (!response.ok)
    throw new Error(`Could not load ${url} (${response.status})`);
  return response.json();
}
function assetURL(path) {
  return new URL(path, WHOLE_OBJECT_ASSET_BASE).href;
}
async function imageFor(path) {
  const url = assetURL(path);
  if (images.has(url)) return images.get(url);
  const image = new Image();
  image.crossOrigin = "anonymous";
  const promise = new Promise((resolve, reject) => {
    image.onload = () => resolve(image);
    image.onerror = () =>
      reject(
        new Error("A whole-object image could not load. Reload to retry."),
      );
  });
  images.set(url, promise);
  image.src = url;
  try {
    const result = await promise;
    images.set(url, result);
    return result;
  } catch (e) {
    images.delete(url);
    throw e;
  }
}
function tileHash(x, y) {
  let h = 2166136261;
  for (const ch of `${map.seed}:${x}:${y}`) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function drawTile(cell) {
  const x = cell.x * tilesize,
    y = cell.y * tilesize,
    h = tileHash(cell.x, cell.y);
  if (cell.kind === "void") return;
  if (cell.kind === "wall") {
    ctx.fillStyle = "#172b43";
    ctx.fillRect(x, y, tilesize, tilesize);
    ctx.fillStyle = "#27405a";
    ctx.fillRect(x + 2, y + 2, tilesize - 4, tilesize - 7);
    ctx.fillStyle = "#344c63";
    ctx.fillRect(x + 3, y + 3, tilesize - 6, 2);
    ctx.fillStyle = "#122237";
    ctx.fillRect(x + 2, y + 23, tilesize - 4, 2);
    ctx.fillRect(x + 23, y + 3, 2, 20);
    ctx.fillRect(x + 12, y + 25, 2, 17);
    return;
  }
  const shade = h % 5,
    base = (palettes[map.theme] || palettes.guild).floor;
  ctx.fillStyle = `rgb(${base[0] + shade * 2},${base[1] + shade * 2},${base[2] + shade * 2})`;
  ctx.fillRect(x, y, tilesize, tilesize);
  ctx.strokeStyle = (palettes[map.theme] || palettes.guild).edge;
  ctx.lineWidth = 1;
  ctx.strokeRect(x + 0.5, y + 0.5, tilesize - 1, tilesize - 1);
  ctx.fillStyle = "#6d7b8b38";
  ctx.fillRect(x + 2, y + 2, tilesize - 4, 1);
  ctx.strokeStyle = "#13223588";
  ctx.lineWidth = 1;
  if (h % 4 === 0) {
    ctx.beginPath();
    ctx.moveTo(x + tilesize / 2, y + 1);
    ctx.lineTo(x + tilesize / 2, y + tilesize - 1);
    ctx.stroke();
  } else if (h % 4 === 1) {
    ctx.beginPath();
    ctx.moveTo(x + 1, y + tilesize / 2);
    ctx.lineTo(x + tilesize - 1, y + tilesize / 2);
    ctx.stroke();
  }
  if (h % 3 === 0) {
    ctx.strokeStyle = "#0d1c2b80";
    ctx.beginPath();
    const crackX = x + 9 + (h % 25);
    ctx.moveTo(crackX, y + 5);
    ctx.lineTo(crackX - 3, y + 12);
    ctx.lineTo(crackX + 2, y + 18);
    ctx.lineTo(crackX, y + 23);
    ctx.stroke();
    ctx.strokeStyle = "#82909a25";
    ctx.beginPath();
    ctx.moveTo(crackX + 1, y + 5);
    ctx.lineTo(crackX - 2, y + 12);
    ctx.stroke();
  }
  for (let n = 0; n < 3; n++) {
    const dx = ((h >>> (n * 5)) % 40) + 4,
      dy = ((h >>> (n * 7)) % 40) + 4;
    ctx.fillStyle = n === 0 ? "#78808a22" : "#0a172327";
    ctx.fillRect(x + dx, y + dy, 2, 1);
  }
}
function drawAtmosphere() {
  for (const room of map.rooms) {
    const x = (room.x + room.width / 2) * tilesize,
      y = (room.y + room.height / 2) * tilesize;
    const radius = Math.max(room.width, room.height) * tilesize * 0.65;
    const light = ctx.createRadialGradient(x, y, 0, x, y, radius);
    light.addColorStop(0, (palettes[map.theme] || palettes.guild).ambient);
    light.addColorStop(1, "#00000000");
    ctx.save();
    ctx.beginPath();
    ctx.rect(
      room.x * tilesize,
      room.y * tilesize,
      room.width * tilesize,
      room.height * tilesize,
    );
    ctx.clip();
    ctx.fillStyle = light;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    ctx.restore();
  }
}
function drawThresholds() {
  const cells = new Map(map.cells.map((c) => [`${c.x},${c.y}`, c]));
  const wall = (x, y) => cells.get(`${x},${y}`)?.kind === "wall";
  const steps = { north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0] };
  ctx.save();
  for (const door of map.doors || []) {
    const vertical = door.side === "east" || door.side === "west";
    const [dx, dy] = steps[door.side] || [0, 0];
    const neck = [
      { x: door.x, y: door.y },
      { x: door.x + dx, y: door.y + dy },
    ].some((p) =>
      vertical
        ? wall(p.x, p.y - 1) && wall(p.x, p.y + 1)
        : wall(p.x - 1, p.y) && wall(p.x + 1, p.y),
    );
    if (!neck) continue;
    const x = (door.x + (door.side === "east" ? 1 : 0)) * tilesize,
      y = (door.y + (door.side === "south" ? 1 : 0)) * tilesize;
    ctx.translate(x, y);
    if (vertical) ctx.rotate(Math.PI / 2);
    ctx.fillStyle = "#8e7441";
    ctx.fillRect(5, -2, tilesize - 10, 4);
    ctx.fillStyle = "#c5a461";
    ctx.fillRect(7, -1, tilesize - 14, 1);
    ctx.fillStyle = "#354658";
    ctx.fillRect(0, -6, 5, 12);
    ctx.fillRect(tilesize - 5, -6, 5, 12);
    ctx.fillStyle = "#658092";
    ctx.fillRect(1, -6, 3, 2);
    ctx.fillRect(tilesize - 4, -6, 3, 2);
    if (vertical) ctx.rotate(-Math.PI / 2);
    ctx.translate(-x, -y);
  }
  ctx.restore();
}
function drawRoomLabels() {
  if (!$("room-labels").checked) return;
  ctx.save();
  ctx.font = "12px system-ui";
  ctx.textBaseline = "top";
  for (const room of map.rooms) {
    const template = rules.templates.find((t) => t.id === room.templateId);
    const text =
      room.label || template?.label || room.templateId.replace(/-/g, " ");
    const x = (room.x + 0.15) * tilesize,
      y = (room.y + 0.15) * tilesize;
    const width = ctx.measureText(text).width + 14;
    ctx.fillStyle = "#07101ce8";
    ctx.fillRect(x, y, width, 23);
    ctx.strokeStyle = "#9e814c88";
    ctx.strokeRect(x + 0.5, y + 0.5, width - 1, 22);
    ctx.fillStyle = "#dec18a";
    ctx.fillText(text, x + 7, y + 4);
  }
  ctx.restore();
}
function drawObject(object) {
  const record = library.objects.find((item) => item.id === object.assetId);
  if (!record) return;
  const path = object.assetPath || record.asset?.path || record.asset;
  const image = images.get(assetURL(path));
  if (!image || image instanceof Promise) return;
  const vb = record.visibleBounds;
  const bounds =
    object.sourceVisibleBounds ||
    (vb
      ? [vb[0], vb[1], vb[2] - vb[0], vb[3] - vb[1]]
      : [0, 0, image.width, image.height]);
  const [sx, sy, sw, sh] = bounds;
  const angle = (((object.rotationDegrees || 0) % 360) * Math.PI) / 180;
  const sideways =
    Math.abs(Math.round((object.rotationDegrees || 0) / 90)) % 2 === 1;
  const areaW = object.width * tilesize,
    areaH = object.height * tilesize;
  const scale = Math.min(
    areaW / (sideways ? sh : sw),
    areaH / (sideways ? sw : sh),
  );
  ctx.save();
  ctx.translate(
    (object.x + object.width / 2) * tilesize,
    (object.y + object.height / 2) * tilesize,
  );
  ctx.rotate(angle);
  ctx.drawImage(
    image,
    sx,
    sy,
    sw,
    sh,
    (-sw * scale) / 2,
    (-sh * scale) / 2,
    sw * scale,
    sh * scale,
  );
  ctx.restore();
}
function marker(point, color, letter) {
  if (!point) return;
  const x = (point.x + 0.5) * tilesize,
    y = (point.y + 0.5) * tilesize;
  ctx.save();
  ctx.fillStyle = color + "25";
  ctx.fillRect(
    point.x * tilesize + 3,
    point.y * tilesize + 3,
    tilesize - 6,
    tilesize - 6,
  );
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.strokeRect(
    point.x * tilesize + 5,
    point.y * tilesize + 5,
    tilesize - 10,
    tilesize - 10,
  );
  ctx.fillStyle = color;
  ctx.font = "bold 12px Georgia";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(letter, x, y - 9);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  if (letter === "IN") {
    for (let step = 0; step < 3; step++) {
      const half = 7 + step * 2;
      ctx.beginPath();
      ctx.moveTo(x - half, y + step * 4);
      ctx.lineTo(x + half, y + step * 4);
      ctx.stroke();
    }
  } else {
    ctx.strokeRect(x - 10, y + 1, 20, 10);
    ctx.beginPath();
    ctx.moveTo(x, y + 2);
    ctx.lineTo(x, y + 9);
    ctx.moveTo(x - 3, y + 5);
    ctx.lineTo(x, y + 2);
    ctx.lineTo(x + 3, y + 5);
    ctx.stroke();
  }
  ctx.restore();
}
function draw() {
  if (!map) return;
  const occupied = map.cells.filter((c) => c.kind !== "void");
  const minX = Math.max(0, Math.min(...occupied.map((c) => c.x)) - 1),
    minY = Math.max(0, Math.min(...occupied.map((c) => c.y)) - 1),
    maxX = Math.min(map.width - 1, Math.max(...occupied.map((c) => c.x)) + 1),
    maxY = Math.min(map.height - 1, Math.max(...occupied.map((c) => c.y)) + 1);
  map.viewBounds = {
    x: minX,
    y: minY,
    width: maxX - minX + 1,
    height: maxY - minY + 1,
  };
  worldCanvas.width = map.viewBounds.width * tilesize;
  worldCanvas.height = map.viewBounds.height * tilesize;
  worldCanvas.style.setProperty(
    "--map-ratio",
    String(map.viewBounds.width / map.viewBounds.height),
  );
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = "#050c15";
  ctx.fillRect(0, 0, worldCanvas.width, worldCanvas.height);
  ctx.translate(-minX * tilesize, -minY * tilesize);
  for (const cell of map.cells) drawTile(cell);
  drawAtmosphere();
  drawThresholds();
  if ($("route").checked && map.clearRoute?.length) {
    ctx.beginPath();
    for (const [i, p] of map.clearRoute.entries()) {
      const x = (p.x + 0.5) * tilesize,
        y = (p.y + 0.5) * tilesize;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.strokeStyle = "#d0b77888";
    ctx.lineWidth = 5;
    ctx.setLineDash([8, 6]);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  if ($("objects").checked) {
    for (const object of map.objects) {
      if (!/torch|lamp/.test(object.assetId)) continue;
      const x = (object.x + object.width / 2) * tilesize,
        y = (object.y + object.height / 2) * tilesize,
        radius = tilesize * 2.3;
      const light = ctx.createRadialGradient(x, y, 0, x, y, radius);
      light.addColorStop(0, "#f7ad3e30");
      light.addColorStop(1, "#f7ad3e00");
      ctx.fillStyle = light;
      ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    }
  }
  if ($("objects").checked)
    for (const object of [...map.objects].sort(
      (a, b) => (a.z || 0) - (b.z || 0) || a.id.localeCompare(b.id),
    ))
      drawObject(object);
  if ($("collision").checked) {
    for (const cell of map.cells) {
      if (!cell.blocked || cell.kind !== "floor") continue;
      ctx.fillStyle = "#e8747050";
      ctx.fillRect(
        cell.x * tilesize + 2,
        cell.y * tilesize + 2,
        tilesize - 4,
        tilesize - 4,
      );
      ctx.strokeStyle = "#ed8f8b";
      ctx.lineWidth = 1;
      ctx.strokeRect(
        cell.x * tilesize + 2.5,
        cell.y * tilesize + 2.5,
        tilesize - 5,
        tilesize - 5,
      );
    }
  }
  if ($("grid").checked) {
    ctx.strokeStyle = "#c1cbd230";
    ctx.lineWidth = 1;
    for (let x = 0; x <= map.width; x++) {
      ctx.beginPath();
      ctx.moveTo(x * tilesize + 0.5, 0);
      ctx.lineTo(x * tilesize + 0.5, worldCanvas.height);
      ctx.stroke();
    }
    for (let y = 0; y <= map.height; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * tilesize + 0.5);
      ctx.lineTo(worldCanvas.width, y * tilesize + 0.5);
      ctx.stroke();
    }
  }
  drawAtlasMarkers();
  drawRoomLabels();
  drawCamera(performance.now());
}
function atlasLocations() {
  return [...floor.regions, ...(packet.generatedLocations || [])];
}
function region() {
  return atlasLocations().find((r) => r.id === selected);
}
function isGeneratedLocation(location) {
  return (packet.generatedLocations || []).some(
    (item) => item.id === location.id,
  );
}
function locationNumber(id) {
  const generatedIndex = (packet.generatedLocations || []).findIndex(
    (item) => item.id === id,
  );
  if (generatedIndex >= 0) return `S${generatedIndex + 1}`;
  const namedIndex = packet.regionBounds
    .filter((b) => !isGeneratedLocation(b))
    .findIndex((b) => b.id === id);
  return namedIndex >= 0 ? String(namedIndex + 1).padStart(2, "0") : "N";
}
function dot(point, color, text) {
  const x = (point.x + 0.5) * tilesize,
    y = (point.y + 0.5) * tilesize;
  ctx.save();
  ctx.fillStyle = "#07111eee";
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(x, y, 15, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "bold 17px system-ui";
  ctx.fillText(text, x, y);
  ctx.restore();
}
function save() {
  try {
    localStorage.setItem(
      "dct.book-one.atlas",
      JSON.stringify({ seed: floor.seed, state, selected, walk }),
    );
  } catch {
    status(
      "Browser storage is unavailable; export the floor to keep its layout.",
      true,
    );
  }
  const url = new URL(location.href);
  url.searchParams.set("seed", floor.seed);
  url.searchParams.set("region", selected);
  history.replaceState(null, "", url);
}
function renderGraph() {
  const svg = $("graph");
  svg.replaceChildren();
  const ns = "http://www.w3.org/2000/svg",
    points = new Map(
      atlasLocations().map((r, i) => [
        r.id,
        { x: 40 + (i % 3) * 95, y: 30 + Math.floor(i / 3) * 80 },
      ]),
    );
  const height = Math.max(180, Math.ceil(atlasLocations().length / 3) * 80);
  svg.setAttribute("viewBox", `0 0 280 ${height}`);
  for (const l of packet.links) {
    const a = points.get(l.from),
      b = points.get(l.to),
      line = document.createElementNS(ns, "line");
    for (const [k, v] of Object.entries({
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
      stroke: "#536072",
      "stroke-width": 2,
    }))
      line.setAttribute(k, v);
    svg.append(line);
  }
  atlasLocations().forEach((r, i) => {
    const p = points.get(r.id),
      g = document.createElementNS(ns, "g"),
      c = document.createElementNS(ns, "circle"),
      t = document.createElementNS(ns, "text");
    for (const [k, v] of Object.entries({
      cx: p.x,
      cy: p.y,
      r: 15,
      fill: r.id === selected ? "#d6b577" : "#182a3b",
      stroke: walk?.visitedRegionIds.includes(r.id) ? "#d6b577" : "#556579",
      "stroke-width": 2,
    }))
      c.setAttribute(k, v);
    for (const [k, v] of Object.entries({
      x: p.x,
      y: p.y + 4,
      "text-anchor": "middle",
      fill: r.id === selected ? "#101b29" : "#b6c0cd",
      "font-size": 11,
    }))
      t.setAttribute(k, v);
    t.textContent = locationNumber(r.id);
    g.append(c, t);
    g.style.cursor = "pointer";
    g.onclick = () => select(r.id);
    svg.append(g);
  });
}
function render() {
  const r = region();
  $("region-name").textContent = r.label;
  $("region-kind").textContent = isGeneratedLocation(r)
    ? "Generated side location · optional adaptation"
    : r.safeZone
      ? "Book location · safe district"
      : r.optional
        ? "Book location · optional district"
        : "Book location · main route district";
  $("description").textContent = r.description;
  $("reference-detail").textContent =
    `${isGeneratedLocation(r) ? "Invented side location for this seed. " : "Named Book 1 location; compact tactical adaptation. "}${r.description}`;
  $("dimensions").textContent =
    `40 × 32 · ${packet.regionBounds.length - (packet.generatedLocations?.length || 0)} book districts · ${packet.generatedLocations?.length || 0} generated side locations`;
  $("objective").textContent = r.objective.label;
  $("progress").textContent =
    `${packet.generatedLocations?.length || 0} optional side locations for seed ${floor.seed}`;
  $("return").hidden = true;
  $("interact").hidden = true;
  $("regions").replaceChildren();
  atlasLocations().forEach((item, i) => {
    const b = document.createElement("button"),
      name = document.createElement("span"),
      tag = document.createElement("small");
    const number = locationNumber(item.id);
    name.textContent =
      number !== "N"
        ? `${number}  ${item.label}`
        : `Guild note · ${item.label}`;
    tag.textContent = isGeneratedLocation(item)
      ? "GENERATED"
      : item.safeZone
        ? "SAFE"
        : item.optional
          ? "OPTIONAL"
          : item.encounterIds?.length
            ? "ENCOUNTER"
            : "";
    b.append(name, tag);
    b.className = item.id === selected ? "selected" : "";
    b.onclick = () => select(item.id);
    $("regions").append(b);
  });
  $("passages").replaceChildren();
  for (const link of packet.links.filter(
    (l) => l.from === selected || l.to === selected,
  )) {
    const id = link.from === selected ? link.to : link.from,
      b = document.createElement("span");
    b.textContent = atlasLocations().find((r) => r.id === id)?.label || id;
    $("passages").append(b);
  }
  renderGraph();
  draw();
  updateNearby();
  canvas.setAttribute(
    "aria-label",
    `Walking exploration preview. Party column ${walk.position.x + 1}, row ${walk.position.y + 1}. Use WASD or arrows to move, E or Space to inspect nearby.`,
  );
}
function drawAtlasMarkers() {
  if (!packet) return;
  ctx.save();
  for (const b of packet.regionBounds) {
    if ($("route").checked || !$("map-drawer").hidden) {
      ctx.strokeStyle =
        b.id === selected ? "#f3ce89" : b.safeZone ? "#7ce0ba90" : "#6e7c8a70";
      ctx.lineWidth = b.id === selected ? 4 : 1;
      ctx.strokeRect(
        b.x * tilesize + 2,
        b.y * tilesize + 2,
        b.width * tilesize - 4,
        b.height * tilesize - 4,
      );
      if (b.id === selected) {
        ctx.fillStyle = "#dfbb7118";
        ctx.fillRect(
          b.x * tilesize,
          b.y * tilesize,
          b.width * tilesize,
          b.height * tilesize,
        );
      }
      ctx.font = "bold 17px system-ui";
      ctx.fillStyle = b.id === selected ? "#f3ce89" : "#b1bdca";
      ctx.textAlign = "center";
      ctx.fillText(
        locationNumber(b.id),
        (b.center.x + 0.5) * tilesize,
        (b.y + 0.7) * tilesize,
      );
    }
    dot(
      b.objective,
      "#c9a4ed",
      walk?.discoveredIds.includes(b.objective.id) ? "✓" : "?",
    );
  }
  for (const enemy of packet.floorPlan.map.enemies) dot(enemy, "#f29a8d", "!");
  marker(packet.floorPlan.entrance, "#7ce0ba", "IN");
  marker(packet.floorPlan.exit, "#f3ca72", "OUT");
  ctx.restore();
}
function select(id) {
  stopMovement();
  selected = id;
  save();
  render();
  status(
    packet.regionBounds.some((b) => b.id === id)
      ? "Selected district highlighted on the complete playable floor."
      : "Reported route leads are held at the guild; no separate room is asserted.",
  );
}
async function generate() {
  stopMovement();
  const serial = ++loadSerial;
  $("loading").hidden = false;
  for (const id of ["generate", "new-seed", "export", "play"])
    $(id).disabled = true;
  try {
    const seed = $("seed").value.trim() || "book-one-floor-one",
      candidate = generateBookOneFloor(
        library,
        { seed },
        rules,
        canonicalManifest,
        catalog,
      );
    if (!validateBookOneFloor(candidate, library).valid)
      throw new Error("Floor validation failed.");
    const playable = getBookOneFloorPlayable(candidate, library, archetypes);
    await Promise.all(
      [
        ...new Set(
          playable.presentationObjects.map(
            (o) =>
              o.assetPath ||
              library.objects.find((a) => a.id === o.assetId)?.asset?.path,
          ),
        ),
      ]
        .filter(Boolean)
        .map(imageFor),
    );
    if (serial !== loadSerial) return;
    floor = candidate;
    packet = playable;
    map = {
      seed: floor.seed,
      theme: "guild",
      width: packet.floorPlan.map.width,
      height: packet.floorPlan.map.height,
      cells: packet.floorPlan.map.tiles.map((c) => ({
        ...c,
        kind:
          !c.blocked ||
          packet.presentationObjects.some(
            (o) =>
              c.x >= o.x &&
              c.x < o.x + o.width &&
              c.y >= o.y &&
              c.y < o.y + o.height,
          )
            ? "floor"
            : packet.floorPlan.map.tiles.some(
                  (n) =>
                    !n.blocked &&
                    Math.abs(c.x - n.x) + Math.abs(c.y - n.y) === 1,
                )
              ? "wall"
              : "void",
      })),
      rooms: packet.regionBounds,
      objects: packet.presentationObjects || [],
      doors: [],
      clearRoute: packet.links.flatMap((l) => l.path),
    };
    state = createBookOneExploration(floor);
    walk = {
      position: { ...packet.floorPlan.entrance },
      discoveredIds: [],
      visitedRegionIds: [floor.entryRegionId],
    };
    movement = null;
    try {
      const saved = JSON.parse(localStorage.getItem("dct.book-one.atlas"));
      if (saved?.seed === seed) {
        state = restoreBookOneExploration(floor, saved.state);
        if (validWalkSave(saved.walk)) walk = saved.walk;
      }
    } catch {}
    let requested = new URLSearchParams(location.search).get("region");
    if (!requested)
      try {
        const saved = JSON.parse(localStorage.getItem("dct.book-one.atlas"));
        if (saved?.seed === seed) requested = saved.selected;
      } catch {}
    selected = atlasLocations().some((r) => r.id === requested)
      ? requested
      : state.regionId;
    selected = districtAt(walk.position)?.id || floor.entryRegionId;
    $("seed").value = seed;
    $("adaptation").textContent = packet.adaptationNote;
    save();
    render();
    status(
      standalone
        ? `Preview · ${packet.generatedLocations.length} generated side locations · WASD/arrows/touch to walk, E to inspect. Combat runs in the game.`
        : `Preview · ${packet.generatedLocations.length} generated side locations · WASD/arrows to walk, E to inspect. Enter playable floor for combat.`,
    );
  } catch (error) {
    status(error.message, true);
  } finally {
    if (serial === loadSerial) {
      $("loading").hidden = true;
      for (const id of ["generate", "new-seed"]) $(id).disabled = false;
      for (const id of ["export", "play"])
        $(id).disabled = !floor || (standalone && id === "play");
      if (standalone) {
        $("play").textContent = "Game unavailable offline";
        $("play").title =
          "Standalone atlas exports floor JSON; starting a game requires the hosted game.";
      }
    }
  }
}
$("zoom").onclick = () => {
  wideView = !wideView;
  $("zoom").setAttribute("aria-pressed", String(wideView));
  $("zoom").textContent = wideView ? "Closer view" : "Wider view";
  drawCamera(performance.now());
};
$("map-toggle").onclick = () => {
  stopMovement();
  const open = $("map-drawer").hidden;
  $("map-drawer").hidden = !open;
  $("map-toggle").setAttribute("aria-expanded", String(open));
  document.querySelector(".workspace").classList.toggle("reference-open", open);
  if (!open) {
    const actualDistrict = districtAt(walk.position);
    if (actualDistrict) selected = actualDistrict.id;
  }
  render();
};
$("map-close").onclick = () => $("map-toggle").click();
$("controls").onsubmit = (e) => {
  e.preventDefault();
  generate();
};
$("new-seed").onclick = () => {
  const n = new Uint32Array(1);
  crypto.getRandomValues(n);
  $("seed").value = "book-one-" + n[0].toString(36);
  generate();
};
for (const id of ["objects", "route", "grid", "collision", "room-labels"])
  $(id).onchange = draw;
canvas.onclick = () => canvas.focus();
$("export").onclick = () => {
  const blob = new Blob(
      [JSON.stringify({ ...packet, atlas: floor }, null, 2)],
      { type: "application/json" },
    ),
    url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = `book-one-floor-one-${floor.seed.replace(/[^a-z0-9_-]/gi, "_")}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status("Exported complete floor JSON with geometry and object metadata.");
};
$("play").onclick = () => {
  stopMovement();
  if (!standalone) $("play-dialog").showModal();
};
$("play-dialog").addEventListener("close", () => {
  if ($("play-dialog").returnValue !== "play") return;
  try {
    const token = crypto.randomUUID();
    sessionStorage.setItem(`dct.book1-floor.${token}`, JSON.stringify(packet));
    location.href = `index.html?book1=1&map=${encodeURIComponent(token)}`;
  } catch (error) {
    status(error.message, true);
  }
});
window.bookOneFloorAtlas = {
  getFloor: () => floor,
  getState: () => structuredClone(state),
  getSelected: () => selected,
  getPacket: () => packet,
  getViewport: () => structuredClone(map?.viewBounds),
  getWalk: () => structuredClone(walk),
  generate,
  select,
};
// The preview owns navigation only. Combat and character progression stay in C#.
let walk,
  movement = null,
  wideView = false,
  partySprite = null,
  partyArt = null;
let facing = { x: 0, y: 1 },
  lastTime = 0;
const heldDirections = new Map();
const directionKeys = {
  ArrowUp: [0, -1],
  w: [0, -1],
  W: [0, -1],
  ArrowDown: [0, 1],
  s: [0, 1],
  S: [0, 1],
  ArrowLeft: [-1, 0],
  a: [-1, 0],
  A: [-1, 0],
  ArrowRight: [1, 0],
  d: [1, 0],
  D: [1, 0],
};
function openTile(point) {
  return packet?.floorPlan.map.tiles.some(
    (cell) => cell.x === point?.x && cell.y === point?.y && !cell.blocked,
  );
}
function validWalkSave(saved) {
  return (
    saved &&
    openTile(saved.position) &&
    Array.isArray(saved.discoveredIds) &&
    saved.discoveredIds.every((id) =>
      packet.floorPlan.discoveries.some((d) => d.id === id),
    ) &&
    Array.isArray(saved.visitedRegionIds) &&
    saved.visitedRegionIds.every((id) =>
      atlasLocations().some((r) => r.id === id),
    )
  );
}
function districtAt(point) {
  return packet?.regionBounds.find(
    (b) =>
      point.x >= b.x &&
      point.x < b.x + b.width &&
      point.y >= b.y &&
      point.y < b.y + b.height,
  );
}
function near(point, range = 1) {
  return (
    Math.abs(point.x - walk.position.x) + Math.abs(point.y - walk.position.y) <=
    range
  );
}
function nearbyInteraction() {
  if (!walk || !packet) return null;
  const discovery = packet.floorPlan.discoveries.find(
    (d) => !walk.discoveredIds.includes(d.id) && near(d),
  );
  if (discovery)
    return {
      kind: "discovery",
      point: discovery,
      label: `Inspect · ${discovery.label}`,
    };
  const encounter = packet.floorPlan.groups.find((g) => near(g, 3));
  if (encounter)
    return {
      kind: "encounter",
      point: encounter,
      label: standalone
        ? "Encounter · game required"
        : "Enter playable floor · encounter",
    };
  if (near(packet.floorPlan.exit))
    return {
      kind: "exit",
      label: standalone
        ? "Exit · game required"
        : "Enter playable floor · exit",
    };
  return null;
}
function updateNearby() {
  const action = nearbyInteraction();
  $("nearby-action").disabled =
    !action || (standalone && action.kind !== "discovery");
  $("nearby-action").textContent = action
    ? `${action.label} [E]`
    : "Explore the passage";
}
function interactNearby() {
  const action = nearbyInteraction();
  if (!action) return;
  if (action.kind === "discovery") {
    walk.discoveredIds.push(action.point.id);
    save();
    draw();
    updateNearby();
    status(
      `Preview discovery: ${action.point.label}. Game objectives and rewards are tracked separately.`,
    );
  } else if (standalone) {
    status(
      "This encounter belongs to the playable game. The standalone preview has no combat or game rewards.",
    );
  } else {
    stopMovement();
    $("play-dialog").showModal();
  }
}
function startStep(dx, dy, time) {
  facing = { x: dx, y: dy };
  const next = { x: walk.position.x + dx, y: walk.position.y + dy };
  if (!openTile(next)) return false;
  movement = {
    from: { ...walk.position },
    to: next,
    started: time,
    duration: 170,
  };
  walk.position = next;
  const district = districtAt(next);
  if (district && !walk.visitedRegionIds.includes(district.id))
    walk.visitedRegionIds.push(district.id);
  if (district && selected !== district.id) {
    selected = district.id;
    render();
  }
  updateNearby();
  save();
  return true;
}
function visualPosition(time) {
  if (!movement) return walk?.position;
  const t = Math.min(
    1,
    Math.max(0, (time - movement.started) / movement.duration),
  );
  return {
    x: movement.from.x + (movement.to.x - movement.from.x) * t,
    y: movement.from.y + (movement.to.y - movement.from.y) * t,
  };
}
function frameLoop(time) {
  if (walk && packet && !$("play-dialog").open && $("map-drawer").hidden) {
    if (movement && time - movement.started >= movement.duration)
      movement = null;
    if (!movement && heldDirections.size) {
      const [dx, dy] = [...heldDirections.values()].at(-1);
      startStep(dx, dy, time);
    }
    if (movement || time - lastTime > 90) {
      drawCamera(time);
      lastTime = time;
    }
  }
  requestAnimationFrame(frameLoop);
}
function drawCamera(time) {
  if (!map || !walk || !worldCanvas.width) return;
  const box = canvas.parentElement.getBoundingClientRect(),
    width = Math.max(1, Math.round(box.width)),
    height = Math.max(1, Math.round(box.height));
  const dpr = Math.min(devicePixelRatio || 1, 2);
  if (
    canvas.width !== Math.round(width * dpr) ||
    canvas.height !== Math.round(height * dpr)
  ) {
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
  screenCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  screenCtx.imageSmoothingEnabled = false;
  screenCtx.fillStyle = "#050c15";
  screenCtx.fillRect(0, 0, width, height);
  const position = visualPosition(time),
    scale = wideView ? 0.82 : width < 600 ? 1.45 : 1.8;
  const centerX = (position.x + 0.5 - map.viewBounds.x) * tilesize,
    centerY = (position.y + 0.5 - map.viewBounds.y) * tilesize;
  const sourceX = centerX - width / (2 * scale),
    sourceY = centerY - height / (2 * scale);
  screenCtx.drawImage(
    worldCanvas,
    sourceX,
    sourceY,
    width / scale,
    height / scale,
    0,
    0,
    width,
    height,
  );
  const x = width / 2,
    y = height / 2;
  screenCtx.fillStyle = "#0008";
  screenCtx.beginPath();
  screenCtx.ellipse(
    x,
    y + 12 * scale,
    15 * scale,
    6 * scale,
    0,
    0,
    Math.PI * 2,
  );
  screenCtx.fill();
  screenCtx.strokeStyle = "#9ce7c4";
  screenCtx.lineWidth = 2;
  screenCtx.beginPath();
  screenCtx.ellipse(
    x,
    y + 12 * scale,
    18 * scale,
    8 * scale,
    0,
    0,
    Math.PI * 2,
  );
  screenCtx.stroke();
  if (partySprite && partyArt) {
    const direction = facing.y < 0 ? "ne" : facing.x > 0 ? "se" : "sw";
    const pose = movement ? `walk${1 + (Math.floor(time / 110) % 2)}` : "idle";
    const frame = partyArt.frames[direction]?.[pose] || partyArt.frames.se.idle;
    const targetHeight = 64 * scale,
      ratio = targetHeight / frame.height;
    screenCtx.drawImage(
      partySprite,
      frame.x,
      frame.y,
      frame.width,
      frame.height,
      x - frame.width * ratio * (frame.anchorX ?? 0.5),
      y + 14 * scale - frame.height * ratio * (frame.anchorY ?? 0.9),
      frame.width * ratio,
      frame.height * ratio,
    );
  } else {
    screenCtx.fillStyle = "#a6f0ce";
    screenCtx.beginPath();
    screenCtx.arc(x, y, 12 * scale, 0, Math.PI * 2);
    screenCtx.fill();
  }
}
async function loadPartySprite() {
  try {
    const base = standalone
      ? new URL("../directional/", WHOLE_OBJECT_ASSET_BASE).href
      : "assets/directional/";
    const manifest = await json(base + "manifest.json");
    partyArt = manifest.characters.carl;
    partySprite = await new Promise((resolve, reject) => {
      const image = new Image();
      image.crossOrigin = "anonymous";
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = base + partyArt.file;
    });
  } catch {
    partySprite = null;
  }
}
function typingTarget(target) {
  return (
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
    target.isContentEditable
  );
}
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("map-drawer").hidden) {
    $("map-toggle").click();
    return;
  }
  if (
    event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    typingTarget(event.target) ||
    $("play-dialog").open ||
    !$("map-drawer").hidden
  )
    return;
  const direction = directionKeys[event.key];
  if (direction) {
    event.preventDefault();
    heldDirections.set(event.code, direction);
  }
  if ((event.code === "Space" || event.code === "KeyE") && !event.repeat) {
    event.preventDefault();
    interactNearby();
  }
});
document.addEventListener("focusin", (event) => {
  if (typingTarget(event.target)) stopMovement();
});
document.addEventListener("keyup", (event) =>
  heldDirections.delete(event.code),
);
function stopMovement() {
  heldDirections.clear();
  movement = null;
  if (walk) drawCamera(performance.now());
}
window.addEventListener("blur", stopMovement);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopMovement();
});
for (const button of document.querySelectorAll("[data-move]")) {
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    heldDirections.set("touch", button.dataset.move.split(",").map(Number));
  });
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"])
    button.addEventListener(type, () => heldDirections.delete("touch"));
}
$("nearby-action").onclick = interactNearby;
window.addEventListener("resize", () => drawCamera(performance.now()));

async function init() {
  try {
    [library, rules, canonicalManifest, catalog, archetypes] =
      await Promise.all([
        json(assetURL("manifest.json")),
        json("data/procedural-object-room-rules.json"),
        json("assets/room-kit/manifest.json"),
        json("data/book-one-floor-one.json"),
        json("data/book-one-location-archetypes.json"),
      ]);
    const query = new URLSearchParams(location.search);
    let seed = query.get("seed");
    if (!seed)
      try {
        seed = JSON.parse(localStorage.getItem("dct.book-one.atlas"))?.seed;
      } catch {}
    if (seed) $("seed").value = seed.slice(0, 80);
    await loadPartySprite();
    await generate();
    requestAnimationFrame(frameLoop);
  } catch (error) {
    $("loading").hidden = true;
    status(error.message, true);
  }
}
init();
