import {
  buildSceneGraph,
  validatePlacement,
  suggestPlacements,
} from "./map-scene-graph.js";
const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
let world,
  catalog,
  graph,
  selected,
  roomId = "",
  baseline = "",
  candidate = null,
  ready = false;
let nodeIndex = new Map();
const byId = (id) => nodeIndex.get(id),
  typeFor = (n) =>
    [
      ...(catalog.objectTypes || []),
      ...(catalog.terrainTypes || []),
      ...(catalog.worldObjectTypes || []),
    ].find((t) => t.id === n.typeId || t.assetIds?.includes(n.assetId));
const expandedGroups = new Set();
const isAdvisory = (edge) =>
  Boolean(edge.advisory || edge.inferred || edge.relation === "near");
const isObject = (node) => node.runtimeId && node.typeId !== "room";
function roomFor(n) {
  while (n && n.typeId !== "room") n = byId(n.parentId);
  return n;
}
function select(id) {
  selected = byId(id);
  candidate = null;
  if (!selected) return;
  if (selected.typeId === "room") roomId = selected.id;
  else if (selected.id !== "world") roomId = roomFor(selected)?.id || "";
  if (selected.typeId === "group") expandedGroups.add(selected.id);
  if (selected.collision?.source === "runtime-tile") {
    $("#show-surfaces").checked = true;
    expandedGroups.add(selected.parentId);
  }
  $("#room").value = roomId;
  render();
}
// Expand only selected-room groups: terrain remains accessible without a 5,000-row outline.
function renderTree() {
  const query = $("#search").value.toLowerCase();
  const matches = (node) =>
    !query ||
    JSON.stringify([node.label, node.runtimeId, node.assetId, node.tags])
      .toLowerCase()
      .includes(query);
  const button = (node, css, prefix = "") =>
    `<button class="${css}" role="treeitem" aria-selected="${selected?.id === node.id}" data-id="${esc(node.id)}">${prefix}${esc(node.label)}${node.runtimeId ? `<br><small>${esc(node.runtimeId)}</small>` : ""}</button>`;
  let html = button(byId("world"), "world", "◈ ");
  for (const room of graph.nodes.filter((node) => node.typeId === "room")) {
    const descendants = graph.nodes.filter(
      (node) => roomFor(node)?.id === room.id,
    );
    if (query && !matches(room) && !descendants.some(matches)) continue;
    html += button(room, "room", roomId === room.id ? "▾ " : "▸ ");
    if (roomId !== room.id && !query) continue;
    for (const group of graph.nodes.filter(
      (node) => node.parentId === room.id,
    )) {
      const children = graph.nodes.filter((node) => node.parentId === group.id);
      const terrain = children.some(
        (node) => node.collision?.source === "runtime-tile",
      );
      const shown = children.filter(
        (node) => matches(node) && (!terrain || $("#show-surfaces").checked),
      );
      if (terrain && !$("#show-surfaces").checked) continue;
      if (query && !shown.length) continue;
      const expanded = !terrain || expandedGroups.has(group.id) || query;
      html += `<button class="group" data-group="${esc(group.id)}" aria-expanded="${Boolean(expanded)}">${expanded ? "▾" : "▸"} ${esc(group.label)} <small>${children.length}</small></button>`;
      if (expanded)
        for (const node of shown)
          html += button(node, "object", isObject(node) ? "▧ " : "· ");
    }
  }
  if (!roomId) {
    for (const group of graph.nodes.filter(
      (node) => node.parentId === "world" && node.typeId === "group",
    )) {
      const children = graph.nodes.filter((node) => node.parentId === group.id);
      const terrain = children.some(
        (node) => node.collision?.source === "runtime-tile",
      );
      if (terrain && !$("#show-surfaces").checked) continue;
      const expanded = expandedGroups.has(group.id);
      html += `<button class="group" data-group="${esc(group.id)}" aria-expanded="${expanded}">${expanded ? "▾" : "▸"} Dungeon passages / ${esc(group.label)} <small>${children.length}</small></button>`;
      if (expanded)
        for (const node of children.filter(matches))
          html += button(node, "object", "· ");
    }
  }
  $("#tree").innerHTML = html;
}
function renderMap() {
  const room = byId(roomId),
    bounds = room
      ? {
          x: room.x - 1,
          y: room.y - 1,
          width: room.width + 2,
          height: room.height + 2,
        }
      : { x: 0, y: 0, width: world.width, height: world.height };
  $("#room-title").textContent = room?.label || "World overview";
  $("#room-note").textContent = room
    ? `${room.runtime.kind} · ${room.width} × ${room.height} tiles · ${room.runtime.theme}`
    : `${world.width} × ${world.height} tiles · select a room to see attachment ports`;
  const svg = $("#map");
  svg.setAttribute(
    "viewBox",
    `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`,
  );
  let html = "";
  for (
    let y = Math.max(0, bounds.y);
    y < Math.min(world.height, bounds.y + bounds.height);
    y++
  )
    for (
      let x = Math.max(0, bounds.x);
      x < Math.min(world.width, bounds.x + bounds.width);
      x++
    ) {
      const tile = world.tiles[y * world.width + x];
      html += `<rect class="map-cell" data-id="world/cell:${x},${y}" x="${x}" y="${y}" width="1" height="1" fill="${tile === "#" ? "#a9b4bf" : tile === "~" ? "#9ebfce" : "#f7f8f9"}" stroke="#e6e9ed" stroke-width=".025"/>`;
    }
  const visible = graph.nodes.filter(
    (n) => isObject(n) && (!room || roomFor(n)?.id === roomId),
  );
  for (const n of visible) {
    const active = n.id === selected?.id;
    html += `<rect class="map-node" data-id="${esc(n.id)}" x="${n.x + 0.05}" y="${n.y + 0.05}" width="${Math.max(0.65, (n.width || 1) - 0.1)}" height="${Math.max(0.65, (n.height || 1) - 0.1)}" rx=".08" fill="${n.id.startsWith("object:") ? "#e8bc70" : n.layer === "wallfixture" ? "#687c92" : "#8facc0"}" stroke="${active ? "#1d4e85" : "#617c91"}" stroke-width="${active ? ".17" : ".05"}"><title>${esc(n.label)} · ${esc(n.runtimeId)}</title></rect>`;
    if (room && active)
      for (const port of n.ports || []) {
        const px =
            n.x +
            (port.side === "west"
              ? 0
              : port.side === "east"
                ? n.width || 1
                : (n.width || 1) / 2),
          py =
            n.y +
            (port.side === "north"
              ? 0
              : port.side === "south"
                ? n.height || 1
                : (n.height || 1) / 2);
        html += `<circle cx="${px}" cy="${py}" r=".15" fill="#fff" stroke="#315d8c" stroke-width=".07"><title>${esc(port.id)} · ${esc(port.side)}</title></circle>`;
      }
  }
  if (selected && room)
    for (const edge of graph.edges.filter(
      (e) =>
        e.relation !== "contains" &&
        (e.source === selected.id || e.target === selected.id),
    )) {
      const a = byId(edge.source),
        b = byId(edge.target);
      if (a?.x == null || b?.x == null) continue;
      html += `<line x1="${a.x + (a.width || 1) / 2}" y1="${a.y + (a.height || 1) / 2}" x2="${b.x + (b.width || 1) / 2}" y2="${b.y + (b.height || 1) / 2}" stroke="${isAdvisory(edge) ? "#bd8a36" : "#497a75"}" stroke-width=".065" ${isAdvisory(edge) ? 'stroke-dasharray=".15 .1"' : ""}><title>${isAdvisory(edge) ? "Suggested proximity: " : "Actual relation: "}${esc(edge.relation)}</title></line>`;
    }
  if (candidate)
    html += `<rect x="${candidate.x}" y="${candidate.y}" width="${candidate.width || 1}" height="${candidate.height || 1}" fill="#f4975633" stroke="#bd5632" stroke-width=".12" stroke-dasharray=".2 .12"/>`;
  svg.innerHTML = html;
  $("#summary").textContent =
    `${visible.length} objects in view · ${graph.nodes.length} graph nodes · ${graph.diagnostics.length} graph diagnostics · shapes show runtime footprints`;
}
function renderProperties() {
  const n = selected;
  if (!n) return;
  const type = typeFor(n),
    edges = graph.edges.filter((e) => e.source === n.id || e.target === n.id),
    actualEdges = edges.filter((edge) => !isAdvisory(edge)),
    advisoryEdges = edges.filter(isAdvisory),
    issues = graph.diagnostics.filter((d) => d.nodeId === n.id),
    value = (v) =>
      esc(
        Array.isArray(v)
          ? v.length
            ? v.join(", ")
            : "No restriction"
          : (v ?? "Not specified"),
      ),
    field = (label, v) => `<dt>${label}</dt><dd>${value(v)}</dd>`;
  $("#properties").innerHTML =
    `<h3>${esc(n.label)}</h3><span class="muted">${esc(n.id)}</span><div>${n.tags.map((t) => `<span class="badge">${esc(t)}</span>`).join("")}</div><dl>${field("Catalog", type ? "Matched authored type: " + type.id : n.typeId === "room" || n.typeId === "world" ? "Runtime container" : "No authored type matched")}${field("Footprint", n.x == null ? "World root" : `${n.width || 1} × ${n.height || 1} at ${n.x}, ${n.y}`)}${field("Rotation", `${n.rotation || 0}°`)}${field("Layer", n.layer)}${field("Runtime collision", n.collision ? `${n.collision.blocked === null ? "Not specified" : n.collision.blocked ? "Blocks movement" : "Does not block movement"} (${n.collision.source})` : "Container")}${field("Allowed parent tags", type?.placement?.requiredParentTags || "Not specified")}${field("Type supports", type?.placement?.allowedSurfaceTags || "Not specified")}${n.layer === "wallfixture" ? field("Layer requirement", "Solid masonry (wallfixture)") : ""}${field("Allowed rotations", type?.placement?.allowedRotations || "Not specified")}</dl><h2>Actual graph relations</h2><ul>${
      actualEdges
        .slice(0, 12)
        .map(
          (e) =>
            `<li>${esc(byId(e.source)?.label || e.source)} — ${esc(e.relation)} → ${esc(byId(e.target)?.label || e.target)}</li>`,
        )
        .join("") || "<li>None</li>"
    }</ul>${actualEdges.length > 12 ? `<p class="muted">${actualEdges.length - 12} further actual relations</p>` : ""}<h2>Suggested proximity · advisory</h2><ul>${advisoryEdges.map((edge) => `<li>${esc(byId(edge.source)?.label || edge.source)} — ${esc(edge.relation)} → ${esc(byId(edge.target)?.label || edge.target)} (suggested)</li>`).join("") || "<li>No advisory matches</li>"}</ul><h2>Expected relations · catalog intent</h2><pre>${esc(JSON.stringify(n.expectedRelations || [], null, 2))}</pre><h2>Attachment ports · declared</h2><pre>${esc(JSON.stringify(n.ports || [], null, 2))}</pre><h2>Validation issues</h2><p class="muted">${issues.map((i) => esc(i.message || i.code)).join("<br>") || "No graph issues reported for this node."}</p>`;
  $("#placement").hidden = !n.id.startsWith("prop:");
  $("#test-x").value = n.x ?? 0;
  $("#test-y").value = n.y ?? 0;
  $("#test-rotation").value = n.rotation || 0;
  $("#test-result").textContent = "";
  $("#suggestions").innerHTML = "";
}
function render() {
  renderTree();
  renderMap();
  renderProperties();
}
// Initialize uses the existing Core generator; this page never sends gameplay commands.
async function loadWorld() {
  ready = false;
  $("#status").textContent = "Generating an actual C# world…";
  try {
    if (!catalog)
      catalog = await fetch("data/map-object-rules.json").then((r) => {
        if (!r.ok) throw Error("Object catalog unavailable");
        return r.json();
      });
    const content = await fetch("data/floor-one-rpg.json").then((r) =>
      r.json(),
    );
    if (!window.__inspectorBlazor) {
      window.__inspectorBlazor = Blazor.start();
    }
    await window.__inspectorBlazor;
    const result = await DotNet.invokeMethodAsync(
      "DungeonCrawlerTactics.Web",
      "Initialize",
      JSON.stringify(content),
      Number($("#seed").value),
    );
    world = structuredClone(
      (typeof result === "string" ? JSON.parse(result) : result).world,
    );
    baseline = JSON.stringify(world);
    graph = buildSceneGraph(world, { catalog, seed: Number($("#seed").value) });
    nodeIndex = new Map(graph.nodes.map((node) => [node.id, node]));
    window.objectInspector = {
      get world() {
        return structuredClone(world);
      },
      get graph() {
        return graph;
      },
      validatePlacement,
    };
    $("#room").innerHTML =
      '<option value="">Entire world</option>' +
      graph.nodes
        .filter((n) => n.typeId === "room")
        .map((n) => `<option value="${esc(n.id)}">${esc(n.label)}</option>`)
        .join("");
    roomId = "";
    selected = byId("world");
    ready = true;
    render();
    const unknown = graph.diagnostics.filter(
      (d) => d.code === "unknown-asset",
    ).length;
    $("#status").textContent =
      `C# runtime · seed ${$("#seed").value} · generation v${world.generationVersion} · ${world.props.length} props · ${unknown} uncatalogued props · catalog v${catalog.schemaVersion || catalog.version || 1} · preview only`;
  } catch (e) {
    $("#status").textContent =
      `Unable to load inspector: ${e.message}. Serve the published Web host so the existing WASM engine is available.`;
    console.error(e);
  }
}
$("#seed").addEventListener("change", loadWorld);
$("#search").addEventListener("input", () => ready && renderTree());
$("#room").addEventListener("change", () => {
  roomId = $("#room").value;
  select(roomId || "world");
});
$("#tree").addEventListener("click", (e) => {
  const group = e.target.closest("[data-group]");
  if (group) {
    const id = group.dataset.group;
    if (expandedGroups.has(id)) expandedGroups.delete(id);
    else expandedGroups.add(id);
    renderTree();
    return;
  }
  const b = e.target.closest("[data-id]");
  if (b) select(b.dataset.id);
});
$("#map").addEventListener("click", (e) => {
  const b = e.target.closest("[data-id]");
  if (b) select(b.dataset.id);
});
// Candidates are detached objects. No position is written into the runtime snapshot.
function validateCandidate(e) {
  e.preventDefault();
  if (!selected?.runtime) return;
  candidate = {
    ...selected.runtime,
    typeId: selected.typeId,
    x: Number($("#test-x").value),
    y: Number($("#test-y").value),
    rotation: Number($("#test-rotation").value),
  };
  const result = validatePlacement(candidate, {
    catalog,
    parent: byId(selected.parentId),
    map: world,
    props: world.props,
  });
  if (JSON.stringify(world) !== baseline)
    throw Error("World snapshot changed during preview");
  $("#test-result").className = result.valid ? "good" : "bad";
  $("#test-result").innerHTML = result.valid
    ? "Candidate accepted by catalog checks. Runtime snapshot unchanged."
    : `Candidate rejected<ul>${result.reasons
        .slice(0, 12)
        .map((r) => `<li>${esc(r.message)}</li>`)
        .join("")}</ul><span class="muted">Runtime snapshot unchanged.</span>`;
  renderMap();
}
$("#test-form").addEventListener("submit", validateCandidate);
function showSuggestions() {
  const n = selected,
    room = roomFor(n);
  if (!n?.runtime) return;
  const suggestions = suggestPlacements(
    { ...n.runtime, typeId: n.typeId },
    {
      catalog,
      parent: byId(n.parentId),
      map: world,
      props: world.props,
      nodes: graph.nodes,
      bounds: room
        ? { x: room.x, y: room.y, width: room.width, height: room.height }
        : undefined,
      reservedCells: (world.objects || []).map((o) => ({ x: o.x, y: o.y })),
    },
    { limit: 3 },
  );
  $("#suggestions").innerHTML = suggestions.length
    ? suggestions
        .map(
          (s, i) =>
            `<button type="button" data-suggestion="${i}">${s.candidate.x}, ${s.candidate.y} · ${s.candidate.rotation}°<br><small>Valid support and footprint · relation score ${s.score.toFixed(2)}</small></button>`,
        )
        .join("")
    : '<p class="bad">No candidates meet catalog support, collision and reserved interaction checks in this room.</p>';
  $("#suggestions").onclick = (e) => {
    const b = e.target.closest("[data-suggestion]");
    if (!b) return;
    candidate = suggestions[Number(b.dataset.suggestion)].candidate;
    $("#test-x").value = candidate.x;
    $("#test-y").value = candidate.y;
    $("#test-rotation").value = candidate.rotation;
    $("#test-form").requestSubmit();
  };
}
$("#suggest").addEventListener("click", showSuggestions);
loadWorld();

$("#show-surfaces").addEventListener("change", renderTree);
$("#export").addEventListener("click", () => {
  if (!graph) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(graph, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `map-scene-graph-${$("#seed").value}.json`;
  link.click();
  URL.revokeObjectURL(url);
});
