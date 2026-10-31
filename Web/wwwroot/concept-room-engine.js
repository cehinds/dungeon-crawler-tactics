/* Pure deterministic room compiler. No DOM, filesystem, clock, or rendering dependency. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ConceptRoomEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function random(seed) {
    let a = Number(seed) >>> 0;
    return () => {
      a += 0x6d2b79f5;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function assets(c) {
    const all = Array.isArray(c.assets)
      ? Object.fromEntries(c.assets.map((a) => [a.id, a]))
      : c.assets;
    return Object.fromEntries(
      Object.entries(all).map(([id, a]) => [
        id,
        Object.assign({}, a, { size: a.size || [a.width, a.height] }),
      ]),
    );
  }
  function reachable(grid, start) {
    let q = [start],
      seen = new Set([start.join(",")]);
    for (let i = 0; i < q.length; i++) {
      let [x, y] = q[i];
      for (let [dx, dy] of [
        [0, 1],
        [0, -1],
        [1, 0],
        [-1, 0],
      ]) {
        let nx = x + dx,
          ny = y + dy,
          k = [nx, ny].join(",");
        if (
          grid[ny] &&
          grid[ny][nx] &&
          !["water", "wall"].includes(grid[ny][nx]) &&
          !seen.has(k)
        ) {
          seen.add(k);
          q.push([nx, ny]);
        }
      }
    }
    return seen;
  }
  function checkRecipe(r) {
    function requireField(path, test) {
      let value = path.split(".").reduce((o, k) => o && o[k], r);
      if (!test(value)) throw Error("Recipe " + path + " missing/invalid");
    }
    const object = (v) =>
        v !== null && typeof v === "object" && !Array.isArray(v),
      number = (v) => Number.isFinite(v),
      positive = (v) => number(v) && v > 0,
      integer = (v) => Number.isInteger(v),
      string = (v) => typeof v === "string" && v.length > 0;
    if (!object(r)) throw Error("Recipe root missing/invalid");
    for (let path of [
      "canvas",
      "board",
      "uiBounds",
      "roles",
      "constraints",
      "architecture",
      "state",
      "edgeRules",
      "edgeRules.roleSockets",
    ])
      requireField(path, object);
    requireField(
      "constraints.entityArtPadding",
      (v) => Number.isInteger(v) && v >= 0,
    );
    requireField("schemaVersion", (v) => v === 2);
    for (let path of [
      "canvas.width",
      "canvas.height",
      "board.columns",
      "board.rows",
      "board.tileSize",
      "actorScale",
      "constraints.entitySpacing",
      "constraints.exactActors",
      "constraints.minimumProps",
      "architecture.portalMargin",
      "architecture.landmarkInset",
      "architecture.portalClearanceRows",
    ])
      requireField(
        path,
        (v) => positive(v) && (path === "actorScale" || integer(v)),
      );
    requireField("canvas.background", string);
    requireField(
      "board.origin",
      (v) => Array.isArray(v) && v.length === 2 && v.every(number),
    );
    for (let path of [
      "uiBounds.x",
      "uiBounds.y",
      "uiBounds.width",
      "uiBounds.height",
      "architecture.portalClearanceColumns",
    ])
      requireField(path, integer);
    requireField(
      "architecture.channelSides",
      (v) =>
        Array.isArray(v) &&
        v.length > 0 &&
        v.every((x) => ["west", "east"].includes(x)),
    );
    requireField(
      "architecture.landmarkRows",
      (v) => Array.isArray(v) && v.every(integer),
    );
    requireField(
      "architecture.landmarkProbability",
      (v) => number(v) && v >= 0 && v <= 1,
    );
    requireField(
      "edgeRules.allowedPairs",
      (v) =>
        Array.isArray(v) &&
        v.every((p) => Array.isArray(p) && p.length === 2 && p.every(string)),
    );
    for (let role of [
      "floor",
      "waterVariants",
      "bankEastVariants",
      "bankWestVariants",
      "waterEndVariants",
      "waterOutletVariants",
      "wallFace",
      "wallCap",
      "wallCapEndWest",
      "wallCapEndEast",
      "wallCornerNW",
      "wallCornerNE",
      "wallCornerSE",
      "wallCornerSW",
      "pier",
    ])
      requireField(
        "edgeRules.roleSockets." + role,
        (v) =>
          object(v) &&
          ["north", "east", "south", "west"].every((k) => string(v[k])),
      );
    requireField(
      "architecture.placementAttemptLimit",
      (v) => Number.isInteger(v) && v > 0,
    );
    requireField("architecture.entrancePresentation", object);
    requireField(
      "architecture.entrancePresentation.cropTop",
      (v) => Number.isInteger(v) && v >= 0,
    );
    requireField("architecture.footprint", object);
    requireField(
      "architecture.footprint.profileDepths",
      (v) =>
        Array.isArray(v) &&
        v.length > 0 &&
        v.every((x) => integer(x) && x >= 1 && x <= 3),
    );
    for (let path of [
      "architecture.footprint.bandRows",
      "architecture.footprint.wallThickness",
      "architecture.portalApproachRows",
    ])
      requireField(path, (v) => integer(v) && v > 0);
    requireField("architecture.portalPadding", (v) => integer(v) && v >= 0);
    requireField(
      "entities",
      (v) =>
        Array.isArray(v) &&
        v.length > 0 &&
        v.every(
          (e) =>
            object(e) &&
            string(e.id) &&
            string(e.assetId) &&
            ["actor", "prop"].includes(e.kind) &&
            (e.kind !== "actor" || (number(e.hp) && positive(e.maxHp))),
        ),
    );
    for (let path of ["state.selectedId", "state.targetId"])
      requireField(path, string);
    for (let path of [
      "state.hp",
      "state.maxHp",
      "state.mana",
      "state.maxMana",
      "state.move",
      "state.round",
    ])
      requireField(path, number);
  }
  function fixedHudErrors(r, c) {
    const roles = Object.assign({}, c.roles, r.roles);
    if (!roles.hud) return [];
    const fixed = c.fixedHudState,
      errors = [];
    if (!fixed)
      return ["Fixed HUD metadata missing; cannot verify raster state"];
    const expected = {
      hp: Array.isArray(fixed.hp) ? fixed.hp[0] : undefined,
      maxHp: Array.isArray(fixed.hp) ? fixed.hp[1] : undefined,
      mana: Array.isArray(fixed.mana) ? fixed.mana[0] : undefined,
      maxMana: Array.isArray(fixed.mana) ? fixed.mana[1] : undefined,
      move: fixed.move,
      round: fixed.round,
      forecastDamage: fixed.forecastDamage,
      selectedId: fixed.selectedId,
      targetId: fixed.targetId,
    };
    for (let [key, value] of Object.entries(expected))
      if (value === undefined || r.state[key] !== value)
        errors.push(
          "Fixed HUD " +
            key +
            " mismatch: raster requires " +
            JSON.stringify(value) +
            ", recipe declares " +
            JSON.stringify(r.state[key]),
        );
    const selected = r.entities.find((e) => e.id === r.state.selectedId);
    if (
      !selected ||
      selected.hp !== expected.hp ||
      selected.maxHp !== expected.maxHp ||
      selected.assetId !== fixed.selectedAssetId
    )
      errors.push("Fixed HUD selected entity HP mismatch");
    if (
      !r.entities.some(
        (e) =>
          e.id === expected.targetId &&
          e.assetId === fixed.targetAssetId &&
          e.kind === "actor" &&
          e.faction === "enemy",
      )
    )
      errors.push("Fixed HUD target identity mismatch");
    return errors;
  }
  function generate(r, c, seed) {
    checkRecipe(r);
    const hudErrors = fixedHudErrors(r, c);
    if (hudErrors.length) throw Error(hudErrors.join("; "));
    if (!Number.isSafeInteger(Number(seed)))
      throw Error("Seed must be a safe integer");
    const rng = random(seed),
      a = assets(c),
      roles = Object.assign({}, c.roles, r.roles),
      b = r.board,
      t = b.tileSize,
      w = b.columns,
      h = b.rows,
      [ox, oy] = b.origin,
      plan = [],
      placements = [];
    function role(name) {
      let v = roles[name];
      if (Array.isArray(v)) v = v[Math.floor(rng() * v.length)];
      if (!a[v]) throw Error("Missing catalog role " + name + ": " + v);
      return v;
    }
    function stamp(id, x, y, layer, extra = {}) {
      let v = a[id];
      if (!v) throw Error("Unknown asset " + id);
      let size = v.size || [v.width, v.height];
      plan.push(
        Object.assign(
          {
            assetId: id,
            x,
            y,
            width: size[0],
            height: size[1],
            layer,
            footY: y + size[1],
          },
          extra,
        ),
      );
    }
    function tile(name, x, y, layer = 10) {
      let id;
      if (name === "floor") {
        let candidates = [].concat(roles.floor || []).filter((id) => {
          let tags = a[id] && a[id].edgeTags;
          if (!tags) return false;
          return [
            [x - 1, y, "west", "east"],
            [x, y - 1, "north", "south"],
          ].every(([nx, ny, edge, other]) => {
            let n = plan.find(
              (d) =>
                d.layer === 10 &&
                d.cell &&
                d.cell[0] === nx &&
                d.cell[1] === ny &&
                d.tileRole === "floor",
            );
            return !n || a[n.assetId].edgeTags[other] === tags[edge];
          });
        });
        if (!candidates.length)
          throw Error("No compatible directional floor tile");
        id = candidates[Math.floor(rng() * candidates.length)];
      } else id = role(name);
      stamp(id, ox + x * t, oy + y * t, layer, {
        width: t,
        height: t,
        cell: [x, y],
        tileRole: name,
      });
    }
    const arch = r.architecture,
      margin = arch.portalMargin,
      side = arch.channelSides[Math.floor(rng() * arch.channelSides.length)],
      waterX = side === "west" ? 0 : w - 1;
    const fp = arch.footprint,
      profile = Array.from(
        { length: Math.ceil(h / fp.bandRows) },
        () => fp.profileDepths[Math.floor(rng() * fp.profileDepths.length)],
      );
    const grid = Array.from({ length: h }, (_, y) =>
      Array.from({ length: w }, (_, x) =>
        x === waterX
          ? "water"
          : (side === "west" ? w - 1 - x : x) <
              profile[Math.floor(y / fp.bandRows)]
            ? "wall"
            : "floor",
      ),
    );
    const exitX = margin + Math.floor(rng() * (w - 2 * margin)),
      entranceX = margin + Math.floor(rng() * (w - 2 * margin));
    grid[0][exitX] = "exit";
    grid[h - 1][entranceX] = "entrance";
    const portals = {
      entrance: {
        cell: [entranceX, h - 1],
        landing: [entranceX, h - 2],
        tags: ["entrance", "walkable"],
      },
      exit: {
        cell: [exitX, 0],
        landing: [exitX, 1],
        tags: ["exit", "walkable"],
      },
    };
    const reserved = new Set(),
      portalOpenings = [],
      portalDraws = [];
    function reservePixelRect(rect) {
      for (let y = 0; y < h; y++)
        for (let x = 0; x < w; x++)
          if (
            ox + x * t < rect.x + rect.width &&
            ox + (x + 1) * t > rect.x &&
            oy + y * t < rect.y + rect.height &&
            oy + (y + 1) * t > rect.y
          )
            reserved.add([x, y].join(","));
    }
    for (let name of ["entrance", "exit"]) {
      let id = role(name),
        v = a[id],
        anchor = v.anchor || [v.size[0] / 2, v.size[1]],
        cell = portals[name].cell,
        threshold = [ox + (cell[0] + 0.5) * t, oy + (cell[1] + 1) * t],
        rect = {
          x: threshold[0] - anchor[0],
          y: threshold[1] - anchor[1],
          width: v.size[0],
          height: v.size[1],
        };
      const cropTop =
        name === "entrance" ? arch.entrancePresentation.cropTop : 0;
      if (cropTop < 0 || cropTop >= v.size[1])
        throw Error("Invalid entrance presentation crop");
      rect.y += cropTop;
      rect.height -= cropTop;
      let left = Math.floor((rect.x - ox) / t),
        right = Math.ceil((rect.x + rect.width - ox) / t) - 1;
      portalOpenings.push({
        portal: name,
        row: name === "exit" ? -1 : h,
        fromColumn: left,
        toColumn: right,
      });
      const approach = {
        x: rect.x - arch.portalPadding,
        y:
          name === "exit" ? threshold[1] : rect.y - arch.portalApproachRows * t,
        width: rect.width + 2 * arch.portalPadding,
        height: arch.portalApproachRows * t,
      };
      for (let x = left; x <= right; x++)
        for (let step = 0; step <= arch.portalClearanceRows; step++) {
          let y = name === "exit" ? step : h - 1 - step;
          if (x >= 0 && x < w && y >= 0 && y < h)
            reserved.add([x, y].join(","));
        }
      portals[name].bounds = rect;
      portals[name].approach = approach;
      reservePixelRect({
        x: rect.x - arch.portalPadding,
        y: rect.y - arch.portalPadding,
        width: rect.width + arch.portalPadding * 2,
        height: rect.height + arch.portalPadding * 2,
      });
      reservePixelRect(approach);
      portalDraws.push({ id, rect, threshold, name, cropTop });
    }
    // Reserved architecture footprints must remain dry, including the complete approach.
    for (let key of reserved) {
      let [x, y] = key.split(",").map(Number);
      if (grid[y][x] === "wall") grid[y][x] = "floor";
    }
    const landmarks = [];
    // Buttresses attach to stepped masonry instead of floating as isolated obstacles.
    for (let y of arch.landmarkRows) {
      if (y < 1 || y >= h - 1 || rng() >= arch.landmarkProbability) continue;
      let depth = profile[Math.floor(y / fp.bandRows)],
        x = side === "west" ? w - 1 - depth : depth;
      if (!reserved.has([x, y].join(",")) && grid[y][x] === "floor") {
        grid[y][x] = "wall";
        landmarks.push([x, y]);
      }
    }
    const architectureCells = [];
    function opening(x, y) {
      return portalOpenings.some(
        (p) =>
          x >= p.fromColumn &&
          x <= p.toColumn &&
          (p.portal === "exit" ? y < 0 : y >= h),
      );
    }
    for (let y = -fp.wallThickness; y < h + 1; y++)
      for (let x = -fp.wallThickness; x < w + fp.wallThickness; x++) {
        let inside = x >= 0 && x < w && y >= 0 && y < h;
        if (inside && grid[y][x] !== "wall") continue;
        if (!inside && opening(x, y)) continue;
        architectureCells.push([x, y]);
        tile("wallFace", x, y, 20);
        const exposed = (dx, dy) => {
          let xx = x + dx,
            yy = y + dy;
          return (
            xx >= 0 && xx < w && yy >= 0 && yy < h && grid[yy][xx] !== "wall"
          );
        };
        if (exposed(0, 1) || exposed(0, -1) || y === -fp.wallThickness) {
          let name = "wallCap";
          if (exposed(0, 1) && exposed(1, 0)) name = "wallCornerNW";
          else if (exposed(0, 1) && exposed(-1, 0)) name = "wallCornerNE";
          else if (exposed(0, -1) && exposed(1, 0)) name = "wallCornerSW";
          else if (exposed(0, -1) && exposed(-1, 0)) name = "wallCornerSE";
          let id = role(name),
            sz = a[id].size;
          stamp(id, ox + x * t, oy + y * t, 22, {
            width: sz[0],
            height: sz[1],
            cell: [x, y],
            tileRole: name,
          });
        }
      }
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        if (grid[y][x] === "wall") continue;
        if (grid[y][x] === "water") tile("waterVariants", x, y);
        else tile("floor", x, y);
        if (x === waterX)
          tile(
            side === "west" ? "bankEastVariants" : "bankWestVariants",
            x,
            y,
            11,
          );
      }
    tile("waterEndVariants", waterX, 0, 12);
    tile("waterOutletVariants", waterX, h - 1, 12);
    for (let [x, y] of landmarks) {
      let id = role("pier"),
        v = a[id];
      stamp(
        id,
        ox + (x + 0.5) * t - v.anchor[0],
        oy + (y + 1) * t - v.anchor[1],
        30,
        { cell: [x, y], tileRole: "pier", upright: true },
      );
    }
    for (let p of portalDraws)
      stamp(p.id, p.rect.x, p.rect.y, 30, {
        width: p.rect.width,
        height: p.rect.height,
        ...(p.cropTop
          ? { sourceRect: [0, p.cropTop, p.rect.width, p.rect.height] }
          : {}),
        portal: p.name,
        threshold: p.threshold,
        upright: true,
      });
    let cells = [];
    for (let y = 1; y < h - 1; y++)
      for (let x = 1; x < w - 1; x++)
        if (grid[y][x] === "floor" && !reserved.has([x, y].join(",")))
          cells.push([x, y]);
    for (let i = cells.length - 1; i > 0; i--) {
      let j = Math.floor(rng() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    const entities = r.entities;
    if (cells.length < entities.length)
      throw Error("Insufficient cells for exact entity cardinality");
    // Finite deterministic backtracking preserves declared minimum spacing without silently dropping entities.
    let chosen = [],
      chosenRects = [],
      placementAttempts = 0;
    function choose(index, start) {
      if (++placementAttempts > arch.placementAttemptLimit)
        throw Error("Placement search exceeded deterministic attempt limit");
      if (index === entities.length) {
        const blocked = new Set(
            chosen
              .filter((p, i) => entities[i].kind === "prop")
              .map((p) => p.join(",")),
          ),
          g = grid.map((row, y) =>
            row.map((v, x) => (blocked.has([x, y].join(",")) ? "wall" : v)),
          ),
          seen = reachable(g, portals.entrance.cell);
        return (
          seen.has(portals.exit.cell.join(",")) &&
          g.flat().filter((v) => !["wall", "water"].includes(v)).length ===
            seen.size
        );
      }
      for (let i = start; i < cells.length; i++) {
        let p = cells[i];
        let e = entities[index],
          v = a[e.assetId],
          sz = v.size,
          an = v.anchor || [sz[0] / 2, sz[1]],
          rect = {
            x: ox + (p[0] + 0.5) * t - an[0] * r.actorScale,
            y: oy + (p[1] + 1) * t - 4 - an[1] * r.actorScale,
            width: sz[0] * r.actorScale,
            height: sz[1] * r.actorScale,
          };
        if (
          Object.values(portals).some((v) =>
            [v.bounds, v.approach].some(
              (b) =>
                rect.x < b.x + b.width &&
                rect.x + rect.width > b.x &&
                rect.y < b.y + b.height &&
                rect.y + rect.height > b.y,
            ),
          )
        )
          continue;
        const artPadding = r.constraints.entityArtPadding;
        if (
          chosenRects.some(
            (q) =>
              rect.x < q.x + q.width + artPadding &&
              rect.x + rect.width + artPadding > q.x &&
              rect.y < q.y + q.height + artPadding &&
              rect.y + rect.height + artPadding > q.y,
          )
        )
          continue;
        if (
          chosen.every(
            (q) =>
              Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]) >=
              r.constraints.entitySpacing,
          )
        ) {
          if (e.kind === "prop") {
            let blocked = new Set(
                chosen
                  .filter((q, j) => entities[j].kind === "prop")
                  .concat([p])
                  .map((q) => q.join(",")),
              ),
              g = grid.map((row, yy) =>
                row.map((v, xx) =>
                  blocked.has([xx, yy].join(",")) ? "wall" : v,
                ),
              ),
              seen = reachable(g, portals.entrance.cell);
            if (
              seen.size !==
              g.flat().filter((v) => !["water", "wall"].includes(v)).length
            )
              continue;
          }
          chosen.push(p);
          chosenRects.push(rect);
          if (choose(index + 1, 0)) return true;
          chosen.pop();
          chosenRects.pop();
        }
      }
      return false;
    }
    if (!choose(0, 0))
      throw Error("No placement satisfies exact cardinality and spacing");
    entities.forEach((e, i) => {
      let cell = chosen[i],
        v = a[e.assetId];
      if (!v) throw Error("Unknown entity " + e.assetId);
      let scale = r.actorScale,
        sz = v.size,
        an = v.anchor || [sz[0] / 2, sz[1]],
        footY = oy + (cell[1] + 1) * t - 4,
        x = ox + (cell[0] + 0.5) * t - an[0] * scale,
        y = footY - an[1] * scale;
      let p = {
        id: e.id,
        assetId: e.assetId,
        kind: e.kind,
        cell,
        footY,
        hp: e.hp,
        maxHp: e.maxHp,
      };
      placements.push(p);
      stamp(e.assetId, x, y, 30, {
        width: sz[0] * scale,
        height: sz[1] * scale,
        footY,
        entityId: e.id,
        upright: true,
      });
      if (e.id === r.state.selectedId || e.id === r.state.targetId)
        plan.push({
          primitive: "rect",
          x: ox + cell[0] * t + 2,
          y: oy + cell[1] * t + 2,
          width: t - 4,
          height: t - 4,
          stroke: e.id === r.state.selectedId ? "#ffe468" : "#ff4058",
          lineWidth: 3,
          layer: 25,
          footY,
        });
      if (e.kind === "actor") {
        let by = y - 10;
        plan.push({
          primitive: "rect",
          x: x,
          y: by,
          width: 48,
          height: 6,
          fill: "#071018",
          layer: 40,
          footY,
        });
        plan.push({
          primitive: "rect",
          x: x + 1,
          y: by + 1,
          width: (46 * e.hp) / e.maxHp,
          height: 4,
          fill: e.faction === "enemy" ? "#ef4961" : "#38d89a",
          layer: 41,
          footY,
        });
      }
    });
    if (roles.hud) {
      let id = role("hud");
      stamp(id, 0, 0, 100);
    }
    for (let d of plan)
      if (d.layer < 100 && d.y + d.height > r.uiBounds.y) {
        let clipped = Math.max(1, r.uiBounds.y - d.y);
        if (d.assetId)
          d.sourceRect = [
            0,
            0,
            a[d.assetId].size[0],
            (a[d.assetId].size[1] * clipped) / d.height,
          ];
        d.height = clipped;
      }
    plan.sort(
      (a, b) =>
        a.layer - b.layer ||
        (a.layer === 30 ? a.footY - b.footY : 0) ||
        String(a.assetId || "").localeCompare(String(b.assetId || "")),
    );
    let room = {
      architectureCells,
      portalOpenings,
      reservedCells: [...reserved].map((k) => k.split(",").map(Number)),
      blockingCells: placements
        .filter((p) => p.kind === "prop")
        .map((p) => p.cell),
      profile,
      schemaVersion: 2,
      seed: Number(seed),
      canvas: r.canvas,
      tileSize: t,
      boardOffset: b.origin,
      grid,
      portals,
      entrance: portals.entrance,
      exit: portals.exit,
      channel: { side, width: 1, contiguous: true, walkable: false },
      regions: [
        { id: "central-route", kind: "clear-path" },
        { id: "water-channel", kind: "contained-water", side },
      ],
      landmarks,
      placements,
      state: JSON.parse(JSON.stringify(r.state)),
      drawPlan: plan,
      note: "Illustrative composition using derived source art; fixed raster HUD matches declared state.",
    };
    room.validation = validate(r, c, room);
    room.propAwareConnectivity = room.validation.propAwareConnectivity;
    room.connectivity = {
      allWalkableConnected: room.validation.allWalkableConnected,
      entranceToExit: room.validation.entranceToExit,
    };
    if (!room.validation.valid) throw Error(room.validation.errors.join("; "));
    return room;
  }
  function validate(r, c, room) {
    if (
      !room ||
      !Array.isArray(room.grid) ||
      room.grid.length !== r.board.rows ||
      room.grid.some(
        (row) =>
          !Array.isArray(row) ||
          row.length !== r.board.columns ||
          row.some(
            (v) => !["floor", "wall", "water", "entrance", "exit"].includes(v),
          ),
      )
    )
      return {
        valid: false,
        errors: ["Invalid room grid"],
        allWalkableConnected: false,
        entranceToExit: false,
        propAwareConnectivity: false,
      };
    let errors = fixedHudErrors(r, c),
      a = assets(c),
      seen = reachable(room.grid, room.portals.entrance.cell),
      dry = room.grid
        .flat()
        .filter((x) => !["wall", "water"].includes(x)).length,
      allWalkableConnected = seen.size === dry,
      entranceToExit = seen.has(room.portals.exit.cell.join(","));
    if (!allWalkableConnected || !entranceToExit)
      errors.push("Disconnected walkable cells");
    if (room.placements.length !== r.entities.length)
      errors.push("Entity count mismatch");
    if (
      room.placements.filter((p) => p.kind === "actor").length !==
        r.constraints.exactActors ||
      room.placements.filter((p) => p.kind === "prop").length <
        r.constraints.minimumProps
    )
      errors.push("Required actor/prop counts");
    for (let i = 0; i < room.placements.length; i++)
      for (let j = i + 1; j < room.placements.length; j++) {
        let p = room.placements[i].cell,
          q = room.placements[j].cell;
        if (
          Math.abs(p[0] - q[0]) + Math.abs(p[1] - q[1]) <
          r.constraints.entitySpacing
        )
          errors.push("Entity spacing");
      }
    if (JSON.stringify(room.state) !== JSON.stringify(r.state))
      errors.push("State differs from recipe");
    let occupied = new Set();
    for (let p of room.placements) {
      let key = p.cell.join(",");
      if (occupied.has(key)) errors.push("Overlapping entities");
      occupied.add(key);
      if (!seen.has(key)) errors.push("Unreachable entity " + p.id);
    }
    if (r.board.origin[1] + r.board.rows * r.board.tileSize > r.uiBounds.y)
      errors.push("Board overlaps UI");
    for (let d of room.drawPlan) {
      if (d.layer < 100 && d.y + d.height > r.uiBounds.y)
        errors.push("World draw overlaps UI");
      if (d.assetId && !a[d.assetId])
        errors.push("Unknown draw asset " + d.assetId);
      if (![d.x, d.y, d.width, d.height].every(Number.isFinite))
        errors.push("Invalid draw bounds");
    }
    // Effective terrain uses the bank overlay on the nonwalkable water cell.
    const roles = Object.assign({}, c.roles, r.roles),
      rules = r.edgeRules;
    const terrain = new Map();
    for (let d of room.drawPlan.filter(
      (d) => d.cell && [10, 11, 20].includes(d.layer),
    )) {
      if (!a[d.assetId]) continue;
      terrain.set(d.cell.join(","), d);
    }
    for (let d of room.drawPlan.filter((d) => d.tileRole)) {
      if (![].concat(roles[d.tileRole] || []).includes(d.assetId))
        errors.push("Asset does not match declared tile role " + d.tileRole);
      const expected = rules.roleSockets[d.tileRole];
      if (expected) {
        for (let edge of ["north", "east", "south", "west"])
          if (a[d.assetId]?.edgeTags?.[edge] !== expected[edge])
            errors.push(
              "Incorrect directional socket " + d.tileRole + ":" + edge,
            );
      }
      if (
        d.layer === 10 &&
        d.tileRole !==
          (room.grid[d.cell[1]]?.[d.cell[0]] === "water"
            ? "waterVariants"
            : "floor")
      )
        errors.push("Incorrect terrain role");
      if (
        d.layer === 12 &&
        d.tileRole !==
          (d.cell[1] === 0 ? "waterEndVariants" : "waterOutletVariants")
      )
        errors.push("Incorrect channel end/outlet role");
      if (d.layer === 20 && d.tileRole !== "wallFace")
        errors.push("Boundary requires wall face underlay");
      if (
        d.layer === 22 &&
        !room.drawPlan.some(
          (p) =>
            p.layer === 20 &&
            p.cell &&
            p.cell[0] === d.cell[0] &&
            p.cell[1] === d.cell[1],
        )
      )
        errors.push("Missing boundary face underlay");
      if (d.layer === 22 && d.assetId) {
        let sz = a[d.assetId].size;
        if (
          d.width !== sz[0] ||
          (!d.sourceRect && d.height !== sz[1]) ||
          (d.sourceRect && d.height !== d.sourceRect[3])
        )
          errors.push("Distorted native boundary module");
      }
      if (d.layer === 11) {
        let expectedRole =
          room.channel.side === "west"
            ? "bankEastVariants"
            : "bankWestVariants";
        if (
          d.tileRole !== expectedRole ||
          room.grid[d.cell[1]]?.[d.cell[0]] !== "water"
        )
          errors.push("Incorrect bank orientation or footprint");
      }
    }
    for (let d of terrain.values())
      for (let [dx, dy, edge, opposite] of [
        [1, 0, "east", "west"],
        [0, 1, "south", "north"],
      ]) {
        let n = terrain.get([d.cell[0] + dx, d.cell[1] + dy].join(","));
        if (n) {
          let e = a[d.assetId]?.edgeTags?.[edge],
            f = a[n.assetId]?.edgeTags?.[opposite];
          if (
            !e ||
            !f ||
            !(
              e === f ||
              rules.allowedPairs.some(
                (p) => (p[0] === e && p[1] === f) || (p[1] === e && p[0] === f),
              )
            )
          )
            errors.push(
              "Incompatible directional transition " +
                d.tileRole +
                " " +
                edge +
                " " +
                n.tileRole,
            );
        }
      }

    const terrainDraws = room.drawPlan.filter((d) => d.layer === 10 && d.cell),
      terrainKeys = new Set(terrainDraws.map((d) => d.cell.join(","))),
      expectedTerrain = room.grid.flat().filter((v) => v !== "wall").length;
    if (
      terrainDraws.length !== expectedTerrain ||
      terrainKeys.size !== expectedTerrain
    )
      errors.push("Terrain draw cardinality");
    for (let y = 0; y < r.board.rows; y++)
      for (let x = 0; x < r.board.columns; x++) {
        if (room.grid[y][x] !== "wall" && !terrainKeys.has([x, y].join(",")))
          errors.push("Missing terrain cell");
        if (
          room.grid[y][x] === "wall" &&
          !room.drawPlan.some(
            (d) =>
              d.layer === 20 && d.cell && d.cell[0] === x && d.cell[1] === y,
          )
        )
          errors.push("Missing masonry cell");
      }
    const upright = room.drawPlan.filter((d) => d.upright);
    if (
      upright.some(
        (d, i) => d.layer !== 30 || (i && upright[i - 1].footY > d.footY),
      )
    )
      errors.push("Incorrect upright depth order");
    for (let name of ["entrance", "exit"]) {
      let p = room.portals[name],
        draws = room.drawPlan.filter((d) => d.portal === name);
      if (draws.length !== 1) {
        errors.push("Portal draw cardinality");
        continue;
      }
      let d = draws[0],
        v = a[d.assetId],
        anchor = v?.anchor;
      if (
        !anchor ||
        d.width !== v.size[0] ||
        d.height !== v.size[1] - (d.sourceRect?.[1] || 0) ||
        d.x + anchor[0] !== d.threshold[0] ||
        d.y + anchor[1] - (d.sourceRect?.[1] || 0) !== d.threshold[1]
      )
        errors.push("Portal anchor/size mismatch");
      if (
        d.x < 0 ||
        d.y < 0 ||
        d.x + d.width > r.canvas.width ||
        d.y + d.height > r.uiBounds.y
      )
        errors.push("Portal outside world bounds");
      let left = Math.floor((d.x - r.board.origin[0]) / r.board.tileSize),
        right =
          Math.ceil((d.x + d.width - r.board.origin[0]) / r.board.tileSize) - 1;
      if (
        room.drawPlan.some(
          (w) =>
            w.layer === 20 &&
            w.cell &&
            w.cell[0] >= left &&
            w.cell[0] <= right &&
            (name === "exit" ? w.cell[1] < 0 : w.cell[1] >= r.board.rows),
        )
      )
        errors.push("Masonry blocks portal opening");
    }
    const blocked = new Set(
        room.placements
          .filter((p) => p.kind === "prop")
          .map((p) => p.cell.join(",")),
      ),
      walkGrid = room.grid.map((row, y) =>
        row.map((v, x) => (blocked.has([x, y].join(",")) ? "wall" : v)),
      ),
      propSeen = reachable(walkGrid, room.portals.entrance.cell),
      propAwareConnectivity =
        propSeen.size ===
          walkGrid.flat().filter((v) => !["water", "wall"].includes(v))
            .length && propSeen.has(room.portals.exit.cell.join(","));
    if (!propAwareConnectivity)
      errors.push("Props disconnect traversable room");
    const intersects = (d, b) =>
      d.x < b.x + b.width &&
      d.x + d.width > b.x &&
      d.y < b.y + b.height &&
      d.y + d.height > b.y;
    for (let p of room.placements) {
      let d = room.drawPlan.find((d) => d.entityId === p.id);
      if (!d) {
        errors.push("Missing draw entity " + p.id);
        continue;
      }
      for (let portal of Object.values(room.portals))
        if (intersects(d, portal.bounds) || intersects(d, portal.approach))
          errors.push("Entity overlaps portal footprint " + p.id);
    }
    const entityDraws = room.drawPlan.filter((d) => d.entityId);
    for (let i = 0; i < entityDraws.length; i++) {
      const d = entityDraws[i],
        padding = r.constraints.entityArtPadding;
      for (let q of entityDraws.slice(i + 1)) {
        if (
          d.x < q.x + q.width + padding &&
          d.x + d.width + padding > q.x &&
          d.y < q.y + q.height + padding &&
          d.y + d.height + padding > q.y
        )
          errors.push(
            "Entity artwork overlaps " + d.entityId + " / " + q.entityId,
          );
      }
    }
    for (let e of r.entities) {
      let p = room.placements.find((p) => p.id === e.id);
      if (!p || p.assetId !== e.assetId || p.hp !== e.hp || p.maxHp !== e.maxHp)
        errors.push("Entity contract mismatch " + e.id);
    }
    let selected = room.placements.find((p) => p.id === room.state.selectedId);
    if (
      selected &&
      (selected.hp !== room.state.hp || selected.maxHp !== room.state.maxHp)
    )
      errors.push("HUD HP mismatch");
    for (let key of ["selectedId", "targetId"])
      if (!room.placements.some((p) => p.id === room.state[key]))
        errors.push("Unknown state " + key);
    return {
      valid: errors.length === 0,
      errors,
      propAwareConnectivity,
      allWalkableConnected,
      entranceToExit,
      reachableCells: seen.size,
      exactEntityCount: room.placements.length,
    };
  }
  return { generate, validate };
});
