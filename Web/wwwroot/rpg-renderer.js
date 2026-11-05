export const WHOLE_OBJECT_ASSET_BASE =
  "https://raw.githubusercontent.com/cehinds/AI-Art/a0483c7db869f28e35bf2878d22e9bc68ead77a7/dungeon-crawler-tactics/Web/wwwroot/assets/top-down-object-kit/";
const remote = new URL("../", WHOLE_OBJECT_ASSET_BASE).href;
function load(path) {
  return new Promise((resolve) => {
    const im = new Image();
    im.onload = () => resolve(im);
    im.onerror = () => {
      if (!im.dataset.retry) {
        im.dataset.retry = "1";
        im.src = remote + path.replace(/^assets\//, "");
      } else resolve(null);
    };
    im.src = path;
  });
}
export class Renderer {
  constructor(canvas, onTile) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.view = null;
    this.positions = new Map();
    this.facing = "se";
    this.fx = [];
    this.camera = { x: 0, y: 0 };
    this.tiles = [];
    this.objects = new Map();
    this.characters = {};
    canvas.addEventListener("pointerdown", (e) => {
      if (!this.view || this.view.mode !== "battle") return;
      const r = canvas.getBoundingClientRect();
      onTile(
        Math.floor((e.clientX - r.left - this.offsetX) / this.tile),
        Math.floor((e.clientY - r.top - this.offsetY) / this.tile),
      );
    });
    this.ready = this.assets();
    requestAnimationFrame((t) => this.frame(t));
  }
  explorers(v) {
    return v.party.map((p, i) => ({
      ...p,
      x: i ? (this.follower?.x ?? v.x) : v.x,
      y: i ? (this.follower?.y ?? v.y) : v.y,
    }));
  }
  reachable(map, u) {
    if (u.moved || u.ended || u.hp <= 0) return [];
    const seen = new Set([`${u.x},${u.y}`]),
      out = [],
      q = [[u.x, u.y, 0]];
    while (q.length) {
      const [x, y, n] = q.shift();
      if (n === 3) continue;
      for (const [dx, dy] of [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ]) {
        const a = x + dx,
          b = y + dy,
          k = `${a},${b}`;
        if (
          a < 0 ||
          b < 0 ||
          a >= map.width ||
          b >= map.height ||
          seen.has(k) ||
          map.obstacles.some((o) => o.x === a && o.y === b) ||
          [...map.units, ...map.enemies].some(
            (o) => o.hp > 0 && o.id !== u.id && o.x === a && o.y === b,
          )
        )
          continue;
        seen.add(k);
        out.push({ x: a, y: b });
        q.push([a, b, n + 1]);
      }
    }
    return out;
  }
  async assets() {
    const manifest = await fetch("assets/directional/manifest.json")
      .then((r) => r.json())
      .catch(() =>
        fetch(remote + "directional/manifest.json").then((r) => r.json()),
      );
    await Promise.all(
      ["carl", "donut"].map(async (id) => {
        const d = manifest.characters[id];
        this.characters[id] = {
          ...d,
          image: await load("assets/directional/" + d.file),
        };
      }),
    );
    const m = await fetch("assets/top-down-object-kit/manifest.json")
      .then((r) => r.json())
      .catch(() =>
        fetch(WHOLE_OBJECT_ASSET_BASE + "manifest.json").then((r) => r.json()),
      );
    await Promise.all(
      m.objects.map(async (a) => {
        this.objects.set(a.id, {
          ...a,
          image: await load("assets/top-down-object-kit/" + a.asset.path),
        });
      }),
    );
    this.tiles = await Promise.all(
      ["grey", "worn-grey", "cracked-grey"].map((t) =>
        load(
          `assets/book-tiles/pocket-dungeon/starter-dungeon/components/starter-dungeon-${t}-flagstone-floor.png`,
        ),
      ),
    );
    const art = await fetch("assets/revamp/character-art.json")
      .then((r) => r.json())
      .catch(() => null);
    if (art)
      this.enemyAtlas = {
        ...art.enemies,
        image: await load("assets/revamp/enemies.png"),
      };
    this.enemy = await load("assets/enemy.png");
    this.boss = await load("assets/boss.png");
  }
  set(view) {
    const old = this.view;
    this.view = view;
    if (!old) {
      this.camera = { x: view.x, y: view.y };
      const m = view.world;
      const p = [
        [view.x - 1, view.y],
        [view.x, view.y - 1],
        [view.x + 1, view.y],
        [view.x, view.y + 1],
      ].find(([x, y]) => m.tiles[y * m.width + x] === ".");
      this.follower = p ? { x: p[0], y: p[1] } : { x: view.x, y: view.y };
    } else if (
      old.mode === "explore" &&
      view.mode === "explore" &&
      (old.x !== view.x || old.y !== view.y)
    ) {
      this.follower = { x: old.x, y: old.y };
    }
    const units =
      view.mode === "battle"
        ? [...view.battle.units, ...view.battle.enemies]
        : this.explorers(view);
    for (const u of units) {
      if (old?.mode !== view.mode) this.positions.set(u.id, { x: u.x, y: u.y });
      const prev = (
        old?.battle
          ? [...old.battle.units, ...old.battle.enemies]
          : old?.party || []
      ).find((x) => x.id === u.id);
      if (prev && u.hp < prev.hp)
        this.fx.push({
          x: u.x,
          y: u.y,
          text: "−" + (prev.hp - u.hp),
          start: performance.now(),
        });
    }
  }
  sprite(id, x, y, t, moving, enemy = false, templateId = "") {
    const c = this.ctx;
    const d = this.characters[id];
    c.fillStyle = "#0006";
    c.beginPath();
    c.ellipse(
      x,
      y + this.tile * 0.27,
      this.tile * 0.25,
      this.tile * 0.1,
      0,
      0,
      Math.PI * 2,
    );
    c.fill();
    if (d?.image) {
      const f =
        d.frames[this.facing]?.[
          moving ? "walk" + (1 + (Math.floor(t / 140) % 2)) : "idle"
        ] || d.frames.se.idle;
      const h = this.tile * (id === "donut" ? 0.82 : 1.22),
        w = (h * f.width) / f.height;
      c.drawImage(
        d.image,
        f.x,
        f.y,
        f.width,
        f.height,
        x - w / 2,
        y + this.tile * 0.37 - h,
        w,
        h,
      );
    } else if (enemy && this.drawEnemy(templateId, x, y, moving)) {
      // Authored enemy identity selects preserved art; combat rules stay in C#.
    } else if (enemy && this.enemy) {
      const im = this.enemy;
      const h = this.tile * 1.08;
      c.drawImage(im, x - h * 0.5, y - h * 0.7, h, h);
    } else {
      c.fillStyle = enemy ? "#c77d71" : "#d6d0ac";
      c.fillRect(
        x - this.tile * 0.18,
        y - this.tile * 0.2,
        this.tile * 0.36,
        this.tile * 0.5,
      );
    }
  }
  drawEnemy(templateId, x, y, moving) {
    const whole = {
      "enemy.murder-dozer": "cd-dozer",
      "enemy.ball-of-swine": "cd-swine-boss",
    }[templateId];
    if (whole && this.objects.get(whole)?.image) {
      const size = 1.35;
      this.object(
        whole,
        x - (this.tile * size) / 2,
        y - this.tile * 0.65,
        size,
        1.05,
      );
      return true;
    }
    const key = {
      "enemy.goblin": "guard",
      "enemy.goblin-bomber": "guard",
      "enemy.scatterer": "rat",
      "enemy.hoarder-elite": "rat",
      "enemy.juicer": "boss",
    }[templateId];
    const art = this.enemyAtlas;
    const f = art?.frames[key]?.[moving ? "walk" : "idle"];
    if (!f || !art.image) return false;
    const h = this.tile * (key === "rat" ? 0.8 : 1.12),
      w = (h * f.width) / f.height;
    this.ctx.drawImage(
      art.image,
      f.x,
      f.y,
      f.width,
      f.height,
      x - w * f.anchorX,
      y + this.tile * 0.35 - h,
      w,
      h,
    );
    return true;
  }
  object(id, x, y, w = 1, h = 1, rotation = 0) {
    const a = this.objects.get(id);
    if (!a?.image) return;
    const b = a.visibleBounds;
    const sw = b[2] - b[0],
      sh = b[3] - b[1];
    const quarterTurn = rotation % 180 !== 0;
    const rw = quarterTurn ? sh : sw, rh = quarterTurn ? sw : sh;
    const s = Math.min((this.tile * w) / rw, (this.tile * h) / rh);
    this.ctx.save();
    this.ctx.translate(x + this.tile * w / 2, y + this.tile * h / 2);
    this.ctx.rotate(rotation * Math.PI / 180);
    this.ctx.drawImage(
      a.image,
      b[0],
      b[1],
      sw,
      sh,
      -sw * s / 2,
      -sh * s / 2,
      sw * s,
      sh * s,
    );
    this.ctx.restore();
  }
  frame(t) {
    const c = this.ctx,
      canvas = this.canvas,
      r = canvas.getBoundingClientRect();
    if (
      canvas.width !== Math.floor(r.width) ||
      canvas.height !== Math.floor(r.height)
    ) {
      canvas.width = r.width;
      canvas.height = r.height;
    }
    c.imageSmoothingEnabled = false;
    c.fillStyle = "#080e19";
    c.fillRect(0, 0, canvas.width, canvas.height);
    const v = this.view;
    if (v) {
      const battle = v.mode === "battle";
      const map = battle ? v.battle : v.world;
      const player = this.explorers(v)[0];
      const target = battle ? { x: 4.5, y: 3.5 } : player;
      const cp = this.positions.get(player.id) || player;
      if (!battle) {
        this.camera.x += (cp.x - this.camera.x) * 0.14;
        this.camera.y += (cp.y - this.camera.y) * 0.14;
      } else {
        this.camera = { ...target };
      }
      this.tile = battle
        ? Math.floor(Math.min(r.width / 10, r.height / 8))
        : Math.floor(Math.max(r.width / 15, r.height / 11));
      this.offsetX = Math.floor(
        r.width / 2 - (this.camera.x + 0.5) * this.tile,
      );
      this.offsetY = Math.floor(
        r.height / 2 - (this.camera.y + 0.5) * this.tile,
      );
      const tile = this.tile,
        ox = this.offsetX,
        oy = this.offsetY;
      // Props own their collision tiles: blocked furniture still sits on floor.
      if (!battle && this.propMap !== map) {
        this.propMap = map;
        this.propFloor = new Set();
        for (const p of map.props || []) {
          if (p.blocksMovement === false) continue;
          for (let dy = 0; dy < p.height; dy++)
            for (let dx = 0; dx < p.width; dx++)
              this.propFloor.add((p.y + dy) * map.width + p.x + dx);
        }
      }
      const propQueue = battle ? [] : (map.props || [])
        .filter(p => p.layer !== "underlay")
        .slice().sort((a, b) => a.y + a.height - b.y - b.height);
      const drawProp = p => this.object(p.assetId, ox + p.x * tile,
        oy + p.y * tile, p.width || 1, p.height || 1, p.rotation || 0);
      for (let y = 0; y < map.height; y++)
        for (let x = 0; x < map.width; x++) {
          const sx = ox + x * tile,
            sy = oy + y * tile;
          if (sx < -tile || sy < -tile || sx > r.width || sy > r.height)
            continue;
          const wall = !battle && map.tiles[y * map.width + x] === "#" && !this.propFloor.has(y * map.width + x);
          const water = !battle && map.tiles[y * map.width + x] === "~";
          if (wall) {
            c.fillStyle = "#172339";
            c.fillRect(sx, sy, tile, tile);
            c.fillStyle = "#263b54";
            c.fillRect(sx + 1, sy + 1, tile - 2, tile * 0.31);
            c.fillStyle = "#0b1525";
            c.fillRect(sx, sy + tile * 0.8, tile, tile * 0.2);
            c.strokeStyle = "#0c1727";
            c.strokeRect(sx, sy, tile, tile);
          } else {
            const im =
              this.tiles[
                (x * 7 + y * 3) % 11 === 0 ? 2 : (x + y) % 5 === 0 ? 1 : 0
              ];
            if (im) c.drawImage(im, 64, 128, 128, 128, sx, sy, tile, tile);
            else {
              c.fillStyle = (x + y) % 2 ? "#394656" : "#3d4958";
              c.fillRect(sx, sy, tile, tile);
              c.strokeStyle = "#283647";
              c.strokeRect(sx + 1, sy + 1, tile - 2, tile - 2);
            }
            if (water) {
              c.fillStyle = "#174b68bb";
              c.fillRect(sx, sy, tile, tile);
              c.strokeStyle = "#4a8194";
              c.beginPath();
              c.moveTo(sx + tile * 0.15, sy + tile * 0.5);
              c.lineTo(sx + tile * 0.8, sy + tile * 0.5);
              c.stroke();
            }
            if (battle) {
              c.strokeStyle = "#a5b4c01c";
              c.strokeRect(sx, sy, tile, tile);
            }
          }
        }
      if (battle) {
        for (const o of map.obstacles || [])
          this.object(
            "ab-clean-crate-wood-cross",
            ox + o.x * tile,
            oy + o.y * tile,
          );
        const u = map.units.find((u) => u.id === v.selectedId);
        if (u) {
          c.fillStyle = "#70b5d818";
          for (const p of this.reachable(map, u))
            c.fillRect(ox + p.x * tile, oy + p.y * tile, tile, tile);
          c.strokeStyle = "#eed28e";
          c.lineWidth = 2;
          c.strokeRect(
            ox + u.x * tile + 2,
            oy + u.y * tile + 2,
            tile - 4,
            tile - 4,
          );
        }
      } else {
        for (const p of map.props || [])
          if (p.layer === "underlay") drawProp(p);
        for (const o of map.objects || []) {
          if (
            v.cleared.includes(o.id) &&
            ["encounter", "boss", "chest"].includes(o.kind)
          )
            continue;
          const ids = {
            guide: "ab-clean-table-wood-empty",
            safe: "ab-clean-cot-metal-green",
            chest: "ab-clean-crate-wood-cross",
            exit: "cd-stair-module",
            boss: "cd-swine-boss",
            encounter: "cd-lever-plinth",
            door: "cd-door-threshold",
            discovery: "cd-drain-grate",
          };
          this.object(
            o.assetId ||
              {
                "false-guild": "cd-dozer",
                "goblin-workshop": "cd-trap-machine",
                juicer: "cd-weight-bench",
                hoarder: "cd-hay-trough",
                entrance: "cd-stair-module",
              }[o.id] ||
              ids[o.kind],
            ox + o.x * tile,
            oy + o.y * tile,
          );
          if (
            !v.cleared.includes(o.id) &&
            !["door", "discovery"].includes(o.kind)
          ) {
            c.font = `${Math.max(10, tile * 0.2)}px Georgia`;
            c.textAlign = "center";
            c.fillStyle = "#f4deb0";
            c.shadowColor = "#000";
            c.shadowBlur = 4;
            c.fillText(
              o.kind === "encounter" ? "!" : o.name,
              ox + (o.x + 0.5) * tile,
              oy + o.y * tile - 5,
            );
            c.shadowBlur = 0;
          }
        }
      }
      const units = battle ? [...map.units, ...map.enemies] : this.explorers(v);
      for (const u of [...units].sort((a, b) => a.y - b.y)) {
        if (u.hp <= 0) continue;
        let p = this.positions.get(u.id);
        if (!p) {
          p = { x: u.x, y: u.y };
          this.positions.set(u.id, p);
        }
        const moving = Math.abs(p.x - u.x) + Math.abs(p.y - u.y) > 0.02;
        p.x += (u.x - p.x) * 0.22;
        p.y += (u.y - p.y) * 0.22;
        const x = ox + (p.x + 0.5) * tile,
          y = oy + (p.y + 0.5) * tile;
        while (propQueue.length && propQueue[0].y + propQueue[0].height <= p.y + 1)
          drawProp(propQueue.shift());
        if (
          this.fx.some((f) => f.x === u.x && f.y === u.y && t - f.start < 350)
        )
          c.filter = "brightness(2) sepia(1)";
        this.sprite(
          u.id,
          x,
          y,
          t,
          moving,
          battle && map.enemies.includes(u),
          u.templateId,
        );
        c.filter = "none";
        if (battle) {
          c.fillStyle = "#0a0e18";
          c.fillRect(x - tile * 0.29, y + tile * 0.41, tile * 0.58, 4);
          c.fillStyle = map.enemies.includes(u) ? "#cc786d" : "#8fc29e";
          c.fillRect(
            x - tile * 0.29,
            y + tile * 0.41,
            (tile * 0.58 * u.hp) / u.maxHp,
            4,
          );
        }
      }
      for (const p of propQueue) drawProp(p);
      this.fx = this.fx.filter((f) => t - f.start < 1100);
      for (const f of this.fx) {
        const age = t - f.start;
        c.globalAlpha = 1 - age / 1100;
        c.fillStyle = "#ffe0a0";
        c.font = "bold 24px Georgia";
        c.textAlign = "center";
        c.fillText(
          f.text,
          ox + (f.x + 0.5) * tile,
          oy + f.y * tile - age * 0.045,
        );
        c.globalAlpha = 1;
      }
    }
    requestAnimationFrame((t) => this.frame(t));
  }
}
