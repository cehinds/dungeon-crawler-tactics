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
    const kit = "assets/map-grid-pass/components/generated/";
    this.materials = {};
    await Promise.all([
      "floor-dry", "floor-wet", "floor-moss", "floor-reflection",
      "wall-straight", "wall-low-cap", "water-surface", "bank-straight", "moss-hanging",
    ].map(async id => { this.materials[id] = await load(kit + id + ".png"); }));
    await Promise.all(Object.entries({
      "industrial-grate": "grate", "industrial-machine": "machine-controls",
      "industrial-pipe": "pipe-straight", "industrial-pipe-elbow": "pipe-elbow",
      "industrial-pipe-tee": "pipe-tee",
      "industrial-torch": "torch", "industrial-crate": "crate",
      "industrial-outlet": "water-outlet",
    }).map(async ([id, file]) => {
      const image = await load(kit + file + ".png");
      // Bounds describe the complete opaque object, not its square export gutter.
      // In particular a tall pipe must fill a 1×2 footprint instead of shrinking
      // to one cell because of transparent space on either side.
      const bounds = {
        "pipe-straight": [44,5,83,124], "pipe-elbow": [11,6,116,123],
        "pipe-tee": [4,21,124,105],
        "machine-controls": [7,4,121,124], "torch": [34,5,94,123],
        "grate": [5,6,123,121], "water-outlet": [21,4,113,122],
        "crate": [13,5,114,123],
      };
      if (image) this.objects.set(id, { image, visibleBounds: bounds[file] || [0,0,image.width,image.height] });
    }));
    // Architectural overlays are complete alpha pieces; the ground remains below them.
    await Promise.all(["water-ironbridge-iron-deck", "water-dryarch-left-jamb",
      "water-dryarch-right-jamb", "water-dryarch-lintel"].map(async id => {
      const image = await load("assets/map-grid-pass/expansion/native/water/" + id + ".png");
      if (image) this.materials[id] = image;
    }));
    await Promise.all(["industrial-pipeH","industrial-pipeV-upper-collar"].map(async id => {
      const image=await load("assets/map-grid-pass/expansion/native/industrial/"+id+".png");
      if (image) this.materials[id]=image;
    }));
    await Promise.all(["floors-fine","floors-worn","floors-hairline-crack",
      "floors-damp","floors-moss-edge","floors-branching-crack","floors-shallow-puddle"].map(async id => {
      const image=await load("assets/map-grid-pass/expansion/native/floors/"+id+".png");
      if (image) this.materials[id]=image;
    }));
    const exit = await load("assets/completed-layers/native/complete-gold-exit.png");
    if (exit) this.objects.set("industrial-exit", {
      image: exit, visibleBounds: [0, 0, exit.width, exit.height],
    });
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
  assembleArchitecture(map) {
    if (this.assemblyMap === map) return this.assembly;
    this.assemblyMap = map;
    const at = (x,y) => x < 0 || y < 0 || x >= map.width || y >= map.height
      ? "#" : this.propFloor.has(y*map.width+x) ? "." : map.tiles?.[y*map.width+x] || ".";
    const parts = [];
    // Coping follows the actual blocked/open contour. Adjacent edge samples
    // share stone corner keys so stepped boundaries read as one built wall.
    for (let y=-1;y<=map.height;y++) for (let x=-1;x<=map.width;x++) {
      if (at(x,y) !== "#") continue;
      for (const [dx,dy] of [[0,1],[0,-1],[1,0],[-1,0]]) {
        if (at(x+dx,y+dy) === "#") continue;
        parts.push({kind: dy === 1 ? "front" : "cap", x,y,dx,dy, depth:y+1.12});
      }
    }
    // Join exposed perpendicular rails on the same blocked cell. These keys
    // stay on masonry and never extend a platform over a walkable cell.
    for (let y=-1;y<=map.height;y++) for (let x=-1;x<=map.width;x++) {
      if (at(x,y) !== "#") continue;
      for (const dx of [-1,1]) for (const dy of [-1,1]) {
        if (at(x+dx,y) !== "#" && at(x,y+dy) !== "#")
          parts.push({kind:"corner",x,y,dx,dy,depth:y+1.12});
      }
    }
    // Frames occur only where a chamber boundary meets an open corridor.
    // A nearby # on both sides is mandatory: no arch is invented in open rooms.
    const doors = new Set();
    for (const room of map.rooms || []) {
      const ports = [];
      for (let x=room.x;x<room.x+room.width;x++)
        ports.push([x,room.y-1,0],[x,room.y+room.height,0]);
      for (let y=room.y;y<room.y+room.height;y++)
        ports.push([room.x-1,y,1],[room.x+room.width,y,1]);
      for (const [x,y,axis] of ports) {
        const ax=axis ? 0:1, ay=axis ? 1:0;
        if (at(x,y) !== "." || at(x-ax,y-ay) !== "#" || at(x+ax,y+ay) !== "#"
          || at(x-ay,y-ax) !== "." || at(x+ay,y+ax) !== ".") continue;
        if ((at(x,y-1)==="~" && at(x,y+1)==="~") || (at(x-1,y)==="~" && at(x+1,y)==="~")) continue;
        // The authored gold stair already supplies its own complete doorway.
        if ((map.props || []).some(p => p.assetId === "industrial-exit"
          && x >= p.x-1 && x < p.x+p.width+1 && y >= p.y-1 && y < p.y+p.height+1)) continue;
        const key=`${x},${y}`;
        if (!doors.has(key)) {parts.push({kind:"door",x,y,axis});doors.add(key);}
      }
    }
    // Six anchored green breaks per industrial chamber, never loose floor scatter.
    // A selected cluster is clipped to a true blocked boundary tile.
    const industrialRooms = map.rooms?.filter(r => (map.props || []).some(p =>
      p.assetId === "industrial-machine" && p.x >= r.x && p.x < r.x+r.width
      && p.y >= r.y && p.y < r.y+r.height)) || [];
    if (!map.rooms && (map.props || []).some(p => p.assetId === "industrial-machine"))
      industrialRooms.push({x:0,y:0,width:map.width,height:map.height});
    const mossCells = new Set();
    for (const r of industrialRooms) {
      const anchors = [[r.x-1,r.y+1],[r.x-1,r.y+r.height-2],
        [r.x+r.width,r.y+1],[r.x+r.width,r.y+r.height-2],
        [r.x+1,r.y+r.height],[r.x+r.width-2,r.y+r.height]];
      for (const [ax,ay] of anchors) {
        const candidates=[];
        for (let dy=-2;dy<=2;dy++) for(let dx=-2;dx<=2;dx++) {
          const x=ax+dx,y=ay+dy,key=`${x},${y}`;
          if(at(x,y)!=="#" || mossCells.has(key)) continue;
          if(![[0,1],[1,0],[0,-1],[-1,0]].some(([a,b])=>[".","~"].includes(at(x+a,y+b)))) continue;
          candidates.push({kind:"moss",x,y,distance:Math.abs(dx)+Math.abs(dy)});
        }
        candidates.sort((a,b)=>a.distance-b.distance || a.y-b.y || a.x-b.x);
        if(candidates.length) {const p=candidates[0];parts.push(p);mossCells.add(`${p.x},${p.y}`);}
      }
    }
    this.assembly = parts.filter(p=>p.kind!=="front").concat(parts.filter(p=>p.kind==="front").sort((a,b)=>a.depth-b.depth));
    return this.assembly;
  }
  drawArchitecture(p, ox, oy, tile) {
    const c=this.ctx, sx=ox+p.x*tile, sy=oy+p.y*tile;
    const im=this.materials?.["wall-straight"];
    if (!im) return;
    if (p.kind === "moss") {
      const moss=this.materials?.["moss-hanging"];
      if(moss) {
        c.save();c.beginPath();c.rect(sx,sy,tile,tile);c.clip();
        c.drawImage(moss,11,5,106,119,sx+tile*.04,sy+tile*.10,tile*.92,tile*.96);
        c.restore();
      }
      return;
    }
    if (p.kind === "door") {
      // Jambs are anchored inside the enclosing wall; the center stays clear.
      c.save(); c.translate(sx+tile/2,sy+tile/2);
      if (p.axis) c.rotate(Math.PI/2);
      const left=this.materials["water-dryarch-left-jamb"], right=this.materials["water-dryarch-right-jamb"];
      const lintel=this.materials["water-dryarch-lintel"];
      if (left) c.drawImage(left,-tile*.77,-tile*.58,tile*.27,tile*1.16);
      if (right) c.drawImage(right,tile*.50,-tile*.58,tile*.27,tile*1.16);
      // Lintel hugs the north wall line instead of obscuring a unit's feet.
      if (lintel) c.drawImage(lintel,-tile*.77,-tile*.61,tile*1.54,tile*.24);
      c.restore(); return;
    }
    if (p.kind === "corner") {
      const edge = tile*.26;
      const cx = sx+(p.dx===1 ? tile-edge : 0);
      const cy = sy+(p.dy===1 ? tile*.72 : 0);
      c.drawImage(im,10,9,28,18,cx,cy,edge+.5,edge+.5);
      return;
    }
    if (p.kind === "front") {
      // The coping and upright face meet at the southern masonry edge.
      // Keep the whole cap on the blocked cell; only its shallow shadow falls
      // onto the adjoining floor, preserving the visible movement boundary.
      c.drawImage(im,10,47,108,66,sx,sy+tile*.79,tile+.5,tile*.31);
      c.fillStyle="#03101c55";
      c.fillRect(sx,sy+tile*.94,tile+.5,tile*.16);
      c.drawImage(im,10,9,108,18,sx,sy+tile*.72,tile+.5,tile*.26);
      const shade=c.createLinearGradient(0,sy+tile*1.08,0,sy+tile*1.19);
      shade.addColorStop(0,"#02081080");shade.addColorStop(1,"#02081000");
      c.fillStyle=shade;c.fillRect(sx,sy+tile*1.08,tile+.5,tile*.11);
    } else if (p.dy === -1) {
      c.drawImage(im,10,9,108,18,sx,sy,tile+.5,tile*.26);
      c.fillStyle="#020b174d";c.fillRect(sx,sy+tile*.26,tile+.5,tile*.045);
    } else {
      c.save();c.translate(sx+(p.dx===1?tile*.87:tile*.13),sy+tile/2);c.rotate(Math.PI/2);
      c.drawImage(im,10,9,108,18,-tile/2,-tile*.13,tile+.5,tile*.26);c.restore();
      c.fillStyle="#020b173b";
      c.fillRect(sx+(p.dx===1?tile*.70:tile*.26),sy,tile*.04,tile);
    }
  }
  surfaceLights(map) {
    this.lightPlans ||= new WeakMap();
    if (this.lightPlans.has(map)) return this.lightPlans.get(map);
    const lights=[];
    for (const p of map.props || []) {
      const w=p.width || 1,h=p.height || 1;
      let light;
      if (p.assetId === "industrial-exit")
        light={x:p.x+w/2,y:p.y+h+.55,rx:1.65,ry:2.65,color:"255,181,57",alpha:.29};
      else if (p.assetId === "industrial-torch")
        light={x:p.x+w/2,y:p.y+h*.75,rx:1.7,ry:2,color:"255,157,42",alpha:.22};
      else if (p.assetId === "industrial-machine")
        light={x:p.x+w/2,y:p.y+h*.75,rx:1.6,ry:1.5,color:"255,172,56",alpha:.17};
      else if (p.assetId === "industrial-outlet")
        light={x:p.x+w/2,y:p.y+h,rx:1.35,ry:1.8,color:"32,174,206",alpha:.17};
      if (!light) continue;
      light.cells=[];
      for (let y=Math.max(0,Math.floor(light.y-light.ry));y<Math.min(map.height,Math.ceil(light.y+light.ry));y++)
        for (let x=Math.max(0,Math.floor(light.x-light.rx));x<Math.min(map.width,Math.ceil(light.x+light.rx));x++) {
          const wall=map.tiles?.[y*map.width+x]==="#";
          // Warm sources may illuminate the immediately mounted masonry;
          // distant blocked cells never receive a glow through their walls.
          if (!wall || (x>=p.x-.5 && x<p.x+w+.5 && y>=p.y && y<p.y+h))
            light.cells.push([x,y]);
        }
      lights.push(light);
    }
    this.lightPlans.set(map,lights);
    return lights;
  }
  drawSurfaceLighting(map, ox, oy, tile) {
    const c=this.ctx;
    for (const light of this.surfaceLights(map)) {
      const lx=ox+light.x*tile,ly=oy+light.y*tile;
      if (lx+light.rx*tile<0 || ly+light.ry*tile<0
        || lx-light.rx*tile>this.canvas.width || ly-light.ry*tile>this.canvas.height) continue;
      c.save();c.beginPath();
      for (const [x,y] of light.cells)c.rect(ox+x*tile,oy+y*tile,tile+.5,tile+.5);
      c.clip();c.globalCompositeOperation="screen";
      c.translate(lx,ly);c.scale(light.rx*tile,light.ry*tile);
      const glow=c.createRadialGradient(0,0,0,0,0,1);
      glow.addColorStop(0,`rgba(${light.color},${light.alpha})`);
      glow.addColorStop(.45,`rgba(${light.color},${light.alpha*.55})`);
      glow.addColorStop(1,`rgba(${light.color},0)`);
      c.fillStyle=glow;c.fillRect(-1,-1,2,2);c.restore();
    }
  }
  drawFloorSlab(sx, sy, tile, x, y, map, at, wetEdge, torch) {
    const c=this.ctx,fine=this.materials?.["floors-fine"];
    if (!fine) return false;
    const wallEdge=[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>at(x+dx,y+dy)==="#");
    // Broad worn slabs carry readable fractures; stronger moisture belongs
    // to channel margins and drain approaches rather than uniform floor noise.
    const hash=Math.abs(x*31+y*17);
    const worn=this.materials["floors-worn"];
    if (worn) c.drawImage(worn,5,5,153,110,sx,sy,tile+.5,tile+.5);
    else c.drawImage(fine,12,12,fine.width-24,fine.height-24,sx,sy,tile+.5,tile+.5);
    const base=this.materials["floor-dry"];
    if (base) {
      c.save();c.globalAlpha=.48;
      c.drawImage(base,(x&1)*64+3,(y&1)*64+3,58,58,sx,sy,tile+.5,tile+.5);
      c.restore();
    }
    const drain=(map.props || []).some(p=>p.assetId==="industrial-grate"
      && Math.abs(x-p.x)+Math.abs(y-p.y)<=1);
    const puddle=(wetEdge && hash%3!==0) || (drain && hash%2===0);
    const detail=puddle ? this.materials["floors-shallow-puddle"]
      : wetEdge || drain ? this.materials["floors-damp"]
      : hash%4===0 ? this.materials["floors-branching-crack"]
      : hash%3===0 || wallEdge ? this.materials["floors-hairline-crack"] : null;
    if (detail) {
      c.save();c.globalAlpha=puddle ? .83 : wetEdge || drain ? .62 : .48;
      c.drawImage(detail,12,12,detail.width-24,detail.height-24,sx,sy,tile+.5,tile+.5);
      c.restore();
    }
    if (wetEdge && wallEdge && (x+y)%5===0) {
      const moss=this.materials["floors-moss-edge"];
      if (moss) {c.save();c.globalAlpha=.24;c.drawImage(moss,sx,sy,tile,tile);c.restore();}
    }
    if (torch) {
      const reflection=this.materials["floor-reflection"];
      if (reflection) {c.save();c.globalAlpha=.62;
        c.drawImage(reflection,(x&1)*64,(y&1)*64,64,64,sx,sy,tile,tile);c.restore();}
    }
    // Every movement cell retains a straight recessed joint, without repeating
    // bright gold outlines around each slab or adding another grid scale.
    c.fillStyle="#06121d99";
    c.fillRect(sx+tile-.8,sy,1,tile);c.fillRect(sx,sy+tile-.8,tile,1);
    c.fillStyle="#90a3ac24";c.fillRect(sx,sy,tile,Math.max(.5,tile*.009));
    return true;
  }
  pipeConnections(map) {
    const pipes=(map.props || []).filter(p=>p.assetId==="industrial-pipe" && p.layer==="wallfixture");
    const rows=new Map();
    for (const pipe of pipes) {
      const row=rows.get(pipe.y) || [];row.push(pipe);rows.set(pipe.y,row);
    }
    const runs=[];
    for (const row of rows.values()) {
      row.sort((a,b)=>a.x-b.x);
      for (let i=1;i<row.length;i++) {
        const a=row[i-1],b=row[i];
        // A header only crosses verified blocked masonry, never a gate or floor.
        if (b.x-a.x>6) continue;
        let blocked=true;
        for (let x=a.x;x<=b.x;x++)
          if (map.tiles?.[a.y*map.width+x]!=="#") blocked=false;
        if (blocked) runs.push({a,b,depth:a.y+Math.max(a.height,b.height)+.17});
      }
    }
    return runs;
  }
  drawPipeConnection(run, ox, oy, tile) {
    const c=this.ctx,{a,b}=run,header=this.materials?.["industrial-pipeH"];
    if (!header) return;
    const left=ox+(a.x+.5)*tile,right=ox+(b.x+.5)*tile;
    const top=oy+(a.y+.03)*tile;
    // Sample the native shaft without open end flanges: tees close every joint.
    c.drawImage(header,55,0,125,header.height,left,top,right-left,tile*.43);
    for (const pipe of [a,b]) {
      this.object("industrial-pipe-tee",ox+(pipe.x+.07)*tile,
        oy+(pipe.y-.015)*tile,.86,.60,180);
    }
  }
  drawChannelWater(sx, sy, tile, x, y, map, at, time) {
    const c=this.ctx;
    // The original caustic texture remains visible below a deep, still body.
    // Bright cyan belongs to the physical outlet sprites, not every water cell.
    c.fillStyle="#06374770";
    c.fillRect(sx,sy,tile+.5,tile+.5);
    const outlet=(map.props || []).some(p => p.assetId === "industrial-outlet"
      && Math.abs(x+.5-(p.x+(p.width || 1)/2)) < .9
      && y >= p.y+(p.height || 1)*.65 && y < p.y+(p.height || 1)+.7);
    if (outlet) {
      const light=c.createRadialGradient(sx+tile*.5,sy+tile*.2,0,
        sx+tile*.5,sy+tile*.2,tile*.85);
      light.addColorStop(0,"#38d7e93d");light.addColorStop(1,"#12778600");
      c.fillStyle=light;c.fillRect(sx,sy,tile,tile);
    }
    const bank=this.materials?.["bank-straight"];
    for (const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
      const neighbor=at(x+dx,y+dy);
      if (neighbor !== "." && neighbor !== "#") continue;
      c.save();c.translate(sx+tile/2,sy+tile/2);
      c.rotate(dx===1 ? Math.PI/2 : dx===-1 ? -Math.PI/2 : dy===1 ? Math.PI : 0);
      // Recessed water receives a narrow contact shadow below its stone rim.
      const shadow=c.createLinearGradient(0,-tile*.5,0,-tile*.20);
      shadow.addColorStop(0,"#010c1699");shadow.addColorStop(1,"#010c1600");
      c.fillStyle=shadow;c.fillRect(-tile*.5,-tile*.5,tile+.5,tile*.30);
      if (neighbor === "." && bank)
        c.drawImage(bank,10,27,108,22,-tile/2-.25,-tile/2,tile+.5,tile*.13);
      c.restore();
    }
    const moss=this.materials?.["moss-hanging"];
    if (moss && at(x,y-1)==="#")
      c.drawImage(moss,sx,sy-tile*.12,tile*.46,tile*.54);
    c.fillStyle=`rgba(25,112,132,${.018+Math.sin(time/1500+y*.6)*.01})`;
    c.fillRect(sx,sy,tile,tile);
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
      const target = battle ? { x: (map.width - 1) / 2, y: (map.height - 1) / 2 } : player;
      const cp = this.positions.get(player.id) || player;
      if (!battle) {
        this.camera.x += (cp.x - this.camera.x) * 0.14;
        this.camera.y += (cp.y - this.camera.y) * 0.14;
      } else {
        this.camera = { ...target };
      }
      this.tile = battle
        ? Math.floor(Math.min(r.width / (map.width + 2), r.height / (map.height + 2)))
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
      if (this.propMap !== map) {
        this.propMap = map;
        this.propFloor = new Set();
        for (const p of map.props || []) {
          if (p.blocksMovement === false || p.layer === "wallfixture") continue;
          for (let dy = 0; dy < p.height; dy++)
            for (let dx = 0; dx < p.width; dx++)
              this.propFloor.add((p.y + dy) * map.width + p.x + dx);
        }
      }
      const propQueue = (map.props || [])
        .filter(p => p.layer !== "underlay")
        .slice().sort((a, b) => a.y + a.height - b.y - b.height);
      const drawProp = p => {
        this.object(p.assetId,ox+p.x*tile,oy+p.y*tile,p.width || 1,p.height || 1,p.rotation || 0);
        if (p.assetId === "industrial-pipe" && p.layer === "wallfixture") {
          const collar=this.materials?.["industrial-pipeV-upper-collar"];
          if (collar) c.drawImage(collar,ox+(p.x+.22)*tile,
            oy+(p.y+(p.height || 2)-.27)*tile,tile*.56,tile*.29);
        }
      };
      for (let y = battle ? -1 : 0; y < map.height + (battle ? 1 : 0); y++)
        for (let x = battle ? -1 : 0; x < map.width + (battle ? 1 : 0); x++) {
          const sx = ox + x * tile,
            sy = oy + y * tile;
          if (sx < -tile || sy < -tile || sx > r.width || sy > r.height)
            continue;
          const at = (a, b) => a >= 0 && b >= 0 && a < map.width && b < map.height
            ? map.tiles?.[b * map.width + a] : "#";
          const outside = x < 0 || y < 0 || x >= map.width || y >= map.height;
          const wall = at(x, y) === "#" && (outside || !this.propFloor.has(y * map.width + x));
          const water = at(x, y) === "~";
          if (wall) {
            // Continuous masonry field: faces and cap rails are assembled below,
            // rather than stamping a self-contained wall square on every cell.
            c.fillStyle = "#101c2b";
            c.fillRect(sx, sy, tile + .5, tile + .5);
            const exposed = [[0,1],[1,0],[0,-1],[-1,0]].some(([dx,dy]) =>
              [".","~"].includes(at(x+dx,y+dy)) ||
              (x+dx>=0 && y+dy>=0 && x+dx<map.width && y+dy<map.height
                && this.propFloor.has((y+dy)*map.width+x+dx)));
            const im = this.materials?.["wall-straight"];
            if (im) {
              c.save(); c.globalAlpha = exposed ? 1 : .34; c.beginPath(); c.rect(sx,sy,tile+.5,tile+.5); c.clip();
              // Preserve the brick aspect while repeating the face texture;
              // stretching one short face to a square makes upright stripes.
              for (let row=0;row<2;row++)
                c.drawImage(im,10,47,108,66,sx,sy+row*tile*.61,tile+.5,tile*.61+.5);
              c.restore();
            }
          } else {
            const wetEdge = [[1, 0], [-1, 0], [0, 1], [0, -1]]
              .some(([dx, dy]) => at(x + dx, y + dy) === "~");
            const torch = (map.props || []).find(p => p.assetId === "industrial-torch"
              && Math.abs(p.x - x) < 0.6 && y >= p.y + 1 && y < p.y + 3);
            const bridge = !water && at(x,y) === "." && ((at(x,y-1) === "~" && at(x,y+1) === "~") || (at(x-1,y) === "~" && at(x+1,y) === "~"));
            const material = water || bridge ? "water-surface" : torch ? "floor-reflection"
              : wetEdge ? "floor-wet" : "floor-dry";
            const im = this.materials?.[material];
            if (im) {
              if (water || bridge) c.drawImage(im, sx, sy, tile + 0.5, tile + 0.5);
              else {
                if (!this.drawFloorSlab(sx,sy,tile,x,y,map,at,wetEdge,torch))
                  c.drawImage(im,(x&1)*64,(y&1)*64,64,64,sx,sy,tile+.5,tile+.5);
              }
            } else {
              c.fillStyle = water ? "#146782" : "#39485b";
              c.fillRect(sx, sy, tile, tile);
            }
            if (bridge) {
              const deck = this.materials?.["water-ironbridge-iron-deck"];
              if (deck) {
                c.save(); c.translate(sx+tile/2,sy+tile/2);
                if (at(x-1,y) === "~") c.rotate(Math.PI/2);
                // The deck overlaps the bank at each end, but stays on real floor.
                // A multi-cell crossing is one connected deck: retain only
                // the outside abutment rails, not a brass frame on every cell.
                const vertical = at(x-1,y) === "~";
                const isCrossing = (a,b) => at(a,b) === "." && (vertical
                  ? at(a-1,b) === "~" && at(a+1,b) === "~"
                  : at(a,b-1) === "~" && at(a,b+1) === "~");
                const before = vertical ? isCrossing(x,y-1) : isCrossing(x-1,y);
                const after = vertical ? isCrossing(x,y+1) : isCrossing(x+1,y);
                const left = before ? 11 : 0, right = after ? deck.width-11 : deck.width;
                c.drawImage(deck,left,0,right-left,deck.height,
                  -tile*.5,-tile*.43,tile+.5,tile*.86);
                c.restore();
              }
            }
            if (!water && !bridge) {
              c.fillStyle = "rgba(9,24,45,.17)";
              c.fillRect(sx, sy, tile + 0.5, tile + 0.5);
            }
            if (water)
              this.drawChannelWater(sx,sy,tile,x,y,map,at,t);
            if (battle) {
              c.strokeStyle = "#a5b4c01c";
              c.strokeRect(sx, sy, tile, tile);
            }
          }
        }
      const architecture = this.assembleArchitecture(map);
      const architectureQueue = [];
      for (const part of architecture) {
        if (part.kind === "front" || (part.kind === "corner" && part.dy === 1)) architectureQueue.push(part);
        else this.drawArchitecture(part, ox, oy, tile);
      }
      for (const p of map.props || [])
        if (p.layer === "underlay") drawProp(p);
      this.drawSurfaceLighting(map,ox,oy,tile);
      if (battle) {
        for (const o of map.obstacles || [])
          if (!this.propFloor.has(o.y * map.width + o.x) && map.tiles?.[o.y * map.width + o.x] !== "~" && map.tiles?.[o.y * map.width + o.x] !== "#") this.object(
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
          const hasExitArchitecture = o.kind === "exit" && (map.props || []).some(p =>
            p.assetId === "industrial-exit" && o.x >= p.x && o.x < p.x + p.width
            && o.y >= p.y && o.y < p.y + p.height);
          if (!hasExitArchitecture && o.kind !== "door") this.object(
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
      // Props and architectural fronts share one depth ordering around actors.
      const sceneryQueue = [
        ...propQueue.map(p => ({depth:p.y+p.height+(p.layer === "wallfixture" ? .15 : 0), prop:p})),
        ...architectureQueue.map(part => ({depth:part.depth, part})),
        ...this.pipeConnections(map).map(run=>({depth:run.depth,run})),
      ].sort((a,b)=>a.depth-b.depth);
      const drawScenery = entry => entry.prop ? drawProp(entry.prop)
        : entry.run ? this.drawPipeConnection(entry.run,ox,oy,tile)
        : this.drawArchitecture(entry.part,ox,oy,tile);
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
        while (sceneryQueue.length && sceneryQueue[0].depth <= p.y + 1)
          drawScenery(sceneryQueue.shift());
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
      for (const entry of sceneryQueue) drawScenery(entry);
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
