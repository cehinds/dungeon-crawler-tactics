import { Renderer } from "./rpg-renderer.js";
const $ = (s) => document.querySelector(s),
  esc = (s) =>
    String(s ?? "").replace(
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
let view,
  content,
  busy = false,
  modal = "",
  skill = "",
  manaSpend = 0,
  skillsActorId = "",
  toastTimer;
const SAVE = "dcc.rebuild.v1";
const renderer = new Renderer($("#world"), tileClick);
const invoke = (name, ...args) =>
  DotNet.invokeMethodAsync("DungeonCrawlerTactics.Web", name, ...args);
const parse = (x) => (typeof x === "string" ? JSON.parse(x) : x);
function notify(text) {
  $("#toast").textContent = text || "";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").textContent = ""), 5000);
}
async function command(type, args = {}) {
  if (busy || !view) return;
  if (type === "interact" && !args.targetId) {
    const o = nearby();
    if (o) args = { ...args, targetId: o.id };
  }
  busy = true;
  try {
    const next = parse(
      await invoke("Dispatch", JSON.stringify({ type, ...args })),
    );
    apply(next);
    if (type === "endUnit" && view.mode === "battle") {
      const nextActor = view.battle.units.find((u) => u.hp > 0 && !u.ended);
      if (nextActor && nextActor.id !== view.selectedId) {
        skill = "";
        manaSpend = 0;
        apply(
          parse(
            await invoke(
              "Dispatch",
              JSON.stringify({ type: "select", actorId: nextActor.id }),
            ),
          ),
        );
      }
    }
  } catch (e) {
    notify(e.message);
  } finally {
    busy = false;
  }
}
function nearby() {
  return view?.world.objects
    .filter(
      (o) =>
        Math.abs(o.x - view.x) + Math.abs(o.y - view.y) <= 1 &&
        !(
          ["encounter", "boss", "chest"].includes(o.kind) &&
          view.cleared.includes(o.id)
        ),
    )
    .sort(
      (a, b) =>
        (a.kind === "door" ? 1 : 0) - (b.kind === "door" ? 1 : 0) ||
        Math.abs(a.x - view.x) +
          Math.abs(a.y - view.y) -
          Math.abs(b.x - view.x) -
          Math.abs(b.y - view.y),
    )[0];
}
function apply(next) {
  const old = view;
  view = next;
  renderer.set(view);
  const room = view.world.rooms?.find(
    (r) =>
      view.x >= r.x &&
      view.y >= r.y &&
      view.x < r.x + r.width &&
      view.y < r.y + r.height,
  );
  $("#area").textContent =
    "Floor 1 · " +
    (view.mode === "battle"
      ? view.battle.encounterName ||
        view.world.objects.find((o) => o.id === view.battle.encounterId)
          ?.name ||
        "Battle"
      : room?.name || "Dungeon passages");
  $("#quest").textContent =
    view.quest ||
    [
      "Survive the False Tutorial Guild",
      "Find Mordecai’s real guildhall",
      "Investigate the Goblin Workshop",
      "Defeat the Ball of Swine",
      "Reach the descending stair",
      "Floor cleared",
    ][view.questStage] ||
    "Reach the next floor";
  $("#battle-banner").textContent =
    view.mode === "battle"
      ? `TURN ${view.turn} · ${view.battle.phase === "enemy" ? "ENEMY PHASE" : "YOUR PARTY"}`
      : "";
  $("#controls").style.display = view.mode === "explore" ? "flex" : "none";
  $("#interact").innerHTML =
    (nearby() ? "Interact: " + esc(nearby().name) : "Interact") +
    " <kbd>E</kbd>";
  renderDeck();
  const gains = old ? view.party.flatMap((p) => {
    const before = old.party.find((x) => x.id === p.id);
    if (!before) return [];
    const changes = p.level > before.level ? [`${p.name} reached level ${p.level}`] : [];
    for (const progress of p.skillProgress || []) {
      const prior = before.skillProgress?.find((x) => x.skillId === progress.skillId);
      if (prior && progress.trainedRank > prior.trainedRank)
        changes.push(`${content.skills.find((x) => x.id === progress.skillId)?.name || progress.skillId} rank ${progress.trainedRank}`);
    }
    return changes;
  }) : [];
  if (gains.length) notify([next.message, ...gains].filter(Boolean).join(" · "));
  else if (next.message && next.message !== old?.message) notify(next.message);
  if (modal) renderModal();
  if (next.mode === "defeat" || next.mode === "complete") {
    modal = next.mode;
    renderModal();
  }
  if (next.mode === "battle" && old?.mode !== "battle")
    notify("Battle! Select a crawler, then a tile or action.");
  window.rpgView = view;
}
function portrait(u) {
  return `<img class="portrait" src="assets/directional/${u.id === "donut" ? "donut" : "carl"}-portrait.png" alt="${esc(u.name)}">`;
}
function progressBar(value, label, kind = "xp") {
  return `<progress class="progress-meter ${kind}" max="100" value="${Number(value) || 0}" aria-label="${esc(label)}"></progress>`;
}
function characterProgress(u, compact = false) {
  const text = u.level >= u.maxLevel ? "Maximum level" : `${u.xpToNext} XP to next level`;
  return `<div class="character-progress" data-xp="${esc(u.id)}"><small>${compact ? "" : `XP ${u.xp} · `}${esc(text)}</small>${progressBar(u.xpProgressPercent, text)}${!compact && u.nextLevelEffect ? `<p class="next-effect">Next: ${esc(u.nextLevelEffect)}</p>` : ""}</div>`;
}
function skillState(u, id) {
  return u.skillProgress?.find((p) => p.skillId === id);
}
function actionTooltip(p) {
  return p ? `${p.cost} ${p.resource || "Mana"} · ${p.effect || ""}${p.disabledReason ? ` · ${p.disabledReason}` : ""}` : "";
}
function manaChooser() {
  const actor = view.battle?.units.find((x) => x.id === view.selectedId);
  const p = skillState(actor || {}, skill || actor?.skills[0]);
  if (!p?.manaOptions?.length) return "";
  if (!p.manaOptions.includes(manaSpend)) manaSpend = p.manaOptions[0];
  return `<label class="mana-choice">Mana spend <select data-mana-spend aria-label="Magic Missile Mana spend" title="${esc(p.effect || "")} Select Mana to preview the resulting damage.">${p.manaOptions.map((n) => `<option value="${n}" ${n === manaSpend ? "selected" : ""}>${n} Mana</option>`).join("")}</select></label><p class="map-key">${esc(p.effect || "")} Choose Mana before forecasting.</p>`;
}
function statuses(u) {
  return (u.statuses || []).length ? `<div class="status-list" aria-label="Active effects">${u.statuses.map((s) => `<span class="status-chip" title="${esc(s.tags?.join(", ") || s.id)}">◈ ${esc(s.name || s.id)} <small>${s.duration < 0 ? "ongoing" : `${s.duration} turns`}</small></span>`).join("")}</div>` : "";
}
function effectSummary(events = []) {
  const names = new Map([...(view.battle?.units || view.party), ...(view.battle?.enemies || []), ...(view.battle?.effectObjects || [])].map((u) => [u.id, u.name || u.label || u.id.replaceAll("-", " ")]));
  const labels = { damage:"Damage", heal:"Healing", resource:"Resource", statusApplied:"Effect applied", statusRemoved:"Effect removed", move:"Move", displace:"Push", blocked:"Blocked", objectDamaged:"Object damage", objectDestroyed:"Object destroyed", explosion:"Explosion", reaction:"Reaction" };
  return events.filter((e) => !(["damage", "heal", "resource", "objectDamaged"].includes(e.kind) && e.amount === 0)).map((e) => `<li data-effect-kind="${esc(e.kind)}">${esc(e.detail || [labels[e.kind] || e.kind, names.get(e.targetId) || e.targetId, e.amount || "", e.tag?.replaceAll("-", " ")].filter(Boolean).join(" · "))}</li>`).join("");
}
function mini(u) {
  return `<div class="party-mini" data-character="${esc(u.id)}">${portrait(u)}<div class="unit-info"><strong>${esc(u.name)}</strong> <small>Lv ${u.level}</small><div><small>HP ${u.hp}/${u.maxHp} · Mana ${u.mp}/${u.maxMp}</small></div><div class="meter"><i style="width:${(u.hp / u.maxHp) * 100}%"></i></div><div class="meter mp"><i style="width:${(u.mp / u.maxMp) * 100}%"></i></div>${characterProgress(u, true)}${statuses(u)}</div></div>`;
}
function renderDeck() {
  if (view.mode !== "battle") {
    $("#deck").innerHTML =
      view.party.map(mini).join("") +
      '<span class="hint">WASD / Arrows · Move &nbsp; E · Interact</span>';
    return;
  }
  const u =
    view.battle.units.find((u) => u.id === view.selectedId) ||
    view.battle.units[0];
  $("#deck").innerHTML =
    mini(u) +
    `<div><span class="turn-label">${u.moved ? "MOVE USED" : "MOVE 3"} · ${u.acted ? "ACTION USED" : "ACTION READY"} · ATK ${u.power} · DEF ${u.armor}</span><div class="actions">${u.skills.map((id) => { const p = skillState(u, id); return `<button data-skill="${id}" title="${esc(actionTooltip(p))}" class="${skill === id ? "active" : ""}" ${u.acted || u.ended || p?.canUse === false ? "disabled" : ""}>${esc(content.skills.find((s) => s.id === id)?.name || id)}${p ? `<small class="action-cost">${p.cost} ${esc(p.resource || "Mana")}${p.disabledReason ? ` · ${esc(p.disabledReason)}` : ""}</small>` : ""}</button>`; }).join("")}<button data-command="endUnit" ${u.ended ? "disabled" : ""}>End ${esc(u.name)} turn</button><button data-command="endTurn">End party turn</button><button data-open="Items">Items</button></div></div>`;
  $("#deck")
    .querySelectorAll("[data-skill]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          skill = b.dataset.skill;
          manaSpend = 0;
          renderDeck();
          modal = "Targets";
          renderModal();
        }),
    );
  $("#deck")
    .querySelectorAll("[data-command]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          b.dataset.command === "endTurn"
            ? open("End turn")
            : command(b.dataset.command, { actorId: u.id })),
    );
  $("#deck").querySelector("[data-open]").onclick = () => open("Items");
}
function tileClick(x, y) {
  if (
    modal ||
    busy ||
    view.mode !== "battle" ||
    x < 0 ||
    y < 0 ||
    x >= view.battle.width ||
    y >= view.battle.height
  )
    return;
  const ally = view.battle.units.find(
    (u) => u.x === x && u.y === y && u.hp > 0,
  );
  if (ally) {
    skill = "";
    manaSpend = 0;
    command("select", { actorId: ally.id });
    return;
  }
  const enemy = view.battle.enemies.find(
    (u) => u.x === x && u.y === y && u.hp > 0,
  );
  if (enemy) {
    forecast(enemy.id);
    return;
  }
  command("moveUnit", { x, y });
}
async function forecast(targetId, x = 0, y = 0) {
  await command("forecast", {
    targetId,
    x, y,
    manaSpend,
    skillId:
      skill ||
      view.battle.units.find((u) => u.id === view.selectedId)?.skills[0] ||
      "punch",
  });
  modal = "Forecast";
  renderModal();
}
function open(name) {
  if (name === "Skills") skillsActorId = view.selectedId || view.party[0]?.id;
  modal = name;
  renderModal();
}
function close() {
  modal = "";
  $("#modal-root").innerHTML = "";
  $("#world").focus();
}
function selected() {
  return (
    view.party.find(
      (u) => u.id === ($("#crawler-select")?.value || view.selectedId),
    ) || view.party[0]
  );
}
function renderModal() {
  let body = "";
  const u = selected();
  if (modal === "Menu")
    body = `<div class="menu-grid">${["Map", "Party", "Equipment", "Skills", "Items", "Journal", "Save"].map((n) => `<button data-open="${n}">${n}</button>`).join("")}</div><p class="map-key">Carl and Princess Donut · ${view.gold} gold · Floor one</p>`;
  else if (modal === "Party")
    body = view.party
      .map(
        (p) =>
          `<div class="row">${portrait(p)}<div><strong>${esc(p.name)} · Level ${p.level}</strong><p>HP ${p.hp}/${p.maxHp} · Mana ${p.mp}/${p.maxMp}</p>${characterProgress(p)}<p>Power ${p.power} · Armor ${p.armor}</p>${statuses(p)}<p>${esc(p.equipment ? (content.items.find((item) => item.id === p.equipment)?.name || p.equipment) : "No equipment equipped")}</p></div></div>`,
      )
      .join("");
  else if (modal === "Equipment")
    body =
      `<select id="crawler-select">${view.party.map((p) => `<option value="${p.id}" ${p.id === u.id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}</select>` +
      view.inventory
        .map((i) => {
          const item = content.items.find((x) => x.id === i.itemId);
          return item && item.kind !== "consumable"
            ? `<div class="row"><div>${esc(item.name)} <span class="tag">${esc(item.kind)} · ×${i.count}</span><p>${esc(item.description)} · Power ${item.power || 0} · Armor ${item.armor || 0}</p></div><button data-equip="${item.id}">Equip</button></div>`
            : "";
        })
        .join("");
  else if (modal === "Skills")
    body = `<div class="actions character-tabs" role="group" aria-label="Character skills">${view.party.map((p) => `<button data-skills-actor="${esc(p.id)}" aria-pressed="${p.id === (skillsActorId || u.id)}" class="${p.id === (skillsActorId || u.id) ? "active" : ""}">${esc(p.name)}</button>`).join("")}</div><p class="map-key">Successful skill uses earn practice toward trained ranks. Character XP raises your level.</p>` + view.party.filter((p) => p.id === (skillsActorId || u.id))
      .map(
        (partyMember) =>
          `<h2>${esc(partyMember.name)}</h2>` +
          partyMember.skills
            .map((id) => {
              const s = content.skills.find((s) => s.id === id) || {};
              const p = skillState(partyMember, id);
              return `<div class="row skill-row" data-skill-progress="${esc(id)}"><div><strong>${esc(s.name || id)}</strong> <span class="tag">Trained ${p?.trainedRank ?? partyMember.ranks?.[id] ?? 1} · Effective ${p?.effectiveRank ?? partyMember.ranks?.[id] ?? 1}</span><p>${esc(s.description)}</p>${p ? `<p class="map-key">Available cap ${p.permissionMaxRank ?? p.maxRank} · Rank capacity ${p.rankCapacity ?? 20} · Gear ${p.gearBonusRank >= 0 ? "+" : ""}${p.gearBonusRank || 0} · Temporary ${p.temporaryBonusRank >= 0 ? "+" : ""}${p.temporaryBonusRank || 0}</p><p class="skill-effect">${esc(p.effect)} · ${p.cost} ${esc(p.resource || "Mana")}</p><p>${p.trainedRank >= p.maxRank ? "Maximum rank" : `Practice ${p.practice} · ${p.practiceToNext} to next rank`}</p>${progressBar(p.practiceProgressPercent, "Skill practice", "practice")}<p class="next-effect">Next: ${esc(p.nextEffect)}</p>${p.disabledReason ? `<p class="cost-warning">${esc(p.disabledReason)}</p>` : ""}` : ""}</div></div>`;
            })
            .join(""),
      )
      .join("");
  else if (modal === "Items")
    body =
      view.inventory
        .map((i) => {
          const it = content.items.find((s) => s.id === i.itemId);
          return it?.kind === "consumable"
            ? `<div class="row"><div>${esc(it.name)} ×${i.count}<p>${esc(it.description)}</p></div>${view.party.map((p) => `<button data-item="${it.id}" data-actor="${p.id}" ${i.count < 1 ? "disabled" : ""}>${esc(p.name)}</button>`).join("")}</div>`
            : "";
        })
        .join("") || "<p>No consumables.</p>";
  else if (modal === "Journal")
    body = (view.availability || []).filter((s) => s.kind === "storyEvent" || s.kind === "facility").map((s) => `<div class="row"><div><strong>${esc(s.name)}</strong><p>${esc(s.reason || (s.available ? "Available" : "Locked"))}</p></div></div>`).join("") + (view.journal || [])
      .map(
        (s) =>
          `<div class="row"><div>${esc(typeof s === "string" ? s : s.text || s.description)}</div></div>`,
      )
      .join("");
  else if (modal === "Save")
    body = `<p>Rest and save beside a safe room. Your save stays in this browser.</p><div class="actions"><button id="rest-button">Rest</button><button id="save-button">Save game</button><button id="load-button" ${localStorage.getItem(SAVE) ? "" : "disabled"}>Load game</button></div><p class="map-key" id="save-result"></p>`;
  else if (modal === "Map")
    body =
      '<canvas id="map-preview" class="map-preview"></canvas><p class="map-key">● Carl · Gold: destinations · Green: cleared · Travel through the dungeon with WASD or arrows.</p>';
  else if (modal === "End turn")
    body =
      '<p>End the party turn? Crawlers with actions remaining will wait, then the enemies will move and attack.</p><button id="end-turn-confirm">End turn</button>';
  else if (modal === "Targets") {
    const actor = view.battle.units.find((u) => u.id === view.selectedId);
    const kind = skillState(actor || {}, skill || actor?.skills[0])?.targetKind || "enemy";
    const targets = kind === "self" ? [actor] : kind === "ally" ? view.battle.units : kind === "object" ? (view.battle.effectObjects || []).filter((o) => !o.destroyed) : kind === "enemyOrObject" ? [...view.battle.enemies, ...(view.battle.effectObjects || []).filter((o) => !o.destroyed)] : kind === "cell" ? [] : view.battle.enemies;
    body = `<p>Select ${kind === "cell" ? "a tile" : kind === "object" ? "an object" : "a target"} to preview the result. The forecast checks range and available resources.</p>` + manaChooser() +
      (kind === "cell" ? `<div class="cell-target-grid" style="--columns:${view.battle.width}">${Array.from({length:view.battle.width * view.battle.height}, (_,i) => {const x=i % view.battle.width,y=Math.floor(i / view.battle.width); return `<button data-target-cell="${x},${y}" aria-label="Forecast tile ${x+1}, ${y+1}" title="Tile ${x+1}, ${y+1}">${x+1},${y+1}</button>`;}).join("")}</div>` : targets.filter((e) => e && e.hp > 0).map((e) => `<div class="row"><div>${esc(e.name || e.label || e.id)}<p>HP ${e.hp}${e.maxHp ? `/${e.maxHp}` : ""}${e.armor !== undefined ? ` · Armor ${e.armor}` : ""}</p>${statuses(e)}</div><button data-target="${esc(e.id)}">Forecast</button></div>`).join("") || "<p>No targets available.</p>");
  }
  else if (modal === "Forecast") {
    const f = view.forecast;
    body = f
      ? `<div class="forecast"><div>Damage<strong>${f.damage}</strong></div><div>${esc(f.resource || "Mana")} cost<strong>${f.cost}</strong></div></div><p data-forecast-ranks>Trained rank ${f.trainedRank} · Effective rank ${f.effectiveRank} · Range ${f.range}</p><p class="${f.valid ? "" : "cost-warning"}" data-forecast-reason>${esc(f.reason || (!f.valid ? view.message : f.reaction) || "")}</p>${f.events?.length ? `<ul class="effect-list" aria-label="Forecast effects">${effectSummary(f.events)}</ul>` : ""}<div class="actions"><button id="confirm-action" ${f.valid ? "" : "disabled"}>Confirm action</button><button data-open="Targets">Choose target</button></div>`
      : "<p>Select a skill and target.</p>";
  } else if (modal === "defeat")
    body =
      '<p>The dungeon wins this round. Return to your last safe-room checkpoint, or the entrance if you have not rested.</p><button id="retry-button">Return to checkpoint</button>';
  else if (modal === "complete")
    body =
      '<p>Carl and Donut have reached the staircase. Floor one is cleared.</p><button data-open="Journal">Read your journal</button>';
  $("#modal-root").innerHTML =
    `<div class="modal-backdrop"><section class="window modal" role="dialog" aria-modal="true" aria-label="${esc(modal)}"><div class="modal-head"><h1>${esc(modal === "defeat" ? "Party defeated" : modal === "complete" ? "Floor cleared" : modal)}</h1><button id="close-modal" aria-label="Close menu">✕</button></div><div class="modal-content">${body}</div></section></div>`;
  $("#close-modal").onclick = close;
  $("#modal-root")
    .querySelectorAll("[data-open]")
    .forEach((b) => (b.onclick = () => open(b.dataset.open)));
  $("#modal-root")
    .querySelectorAll("[data-target]")
    .forEach((b) => (b.onclick = () => forecast(b.dataset.target)));
  $("#modal-root").querySelectorAll("[data-target-cell]").forEach((b) => { b.onclick = () => { const [x,y] = b.dataset.targetCell.split(",").map(Number); forecast("", x, y); }; });
  $("#modal-root")
    .querySelectorAll("[data-equip]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          command("equip", {
            actorId: selected().id,
            itemId: b.dataset.equip,
          })),
    );
  $("#modal-root")
    .querySelectorAll("[data-item]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          command("useItem", {
            actorId: b.dataset.actor,
            itemId: b.dataset.item,
          })),
    );
  if ($("[data-mana-spend]")) $("[data-mana-spend]").onchange = (e) => { manaSpend = Number(e.target.value); };
  $("#modal-root").querySelectorAll("[data-skills-actor]").forEach((b) => { b.onclick = () => { skillsActorId = b.dataset.skillsActor; renderModal(); }; });
  if ($("#crawler-select")) $("#crawler-select").onchange = renderModal;
  if ($("#end-turn-confirm"))
    $("#end-turn-confirm").onclick = async () => {
      close();
      await command("endTurn");
    };
  if ($("#confirm-action"))
    $("#confirm-action").onclick = async () => {
      close();
      await command("confirm", { manaSpend: view.forecast?.manaSpend || manaSpend });
    };
  if ($("#retry-button"))
    $("#retry-button").onclick = async () => {
      close();
      await command("retry");
    };
  if ($("#rest-button")) $("#rest-button").onclick = () => command("rest");
  if ($("#save-button"))
    $("#save-button").onclick = async () => {
      try {
        const saved = await invoke("GetSave");
        localStorage.setItem(SAVE, saved);
        $("#save-result").textContent = "Game saved.";
        $("#load-button").disabled = false;
      } catch (e) {
        $("#save-result").textContent = e.message;
      }
    };
  if ($("#load-button"))
    $("#load-button").onclick = async () => {
      try {
        const loaded = parse(await invoke("LoadSave", localStorage.getItem(SAVE)));
        apply(loaded);
        close();
        notify(loaded.message);
      } catch (e) {
        notify(e.message);
      }
    };
  if (modal === "Map") drawMap();
}
function drawMap() {
  const cv = $("#map-preview"),
    m = view.world,
    c = cv.getContext("2d");
  cv.width = m.width * 12;
  cv.height = m.height * 12;
  for (let y = 0; y < m.height; y++)
    for (let x = 0; x < m.width; x++) {
      c.fillStyle = m.tiles[y * m.width + x] === "#" ? "#111b2e" : "#60718b";
      c.fillRect(x * 12, y * 12, 11, 11);
    }
  for (const o of m.objects) {
    c.fillStyle = view.cleared.includes(o.id) ? "#81b89b" : "#dfbd7c";
    c.fillRect(o.x * 12 + 2, o.y * 12 + 2, 8, 8);
  }
  c.fillStyle = "#fff";
  c.fillRect(view.x * 12 + 2, view.y * 12 + 2, 8, 8);
}
$("#menu-button").onclick = () => (modal ? close() : open("Menu"));
$("#interact").onclick = () => command("interact");
const held = new Map(),
  directions = {
    ArrowUp: "up",
    w: "up",
    ArrowDown: "down",
    s: "down",
    ArrowLeft: "left",
    a: "left",
    ArrowRight: "right",
    d: "right",
  };
let lastMove = 0;
window.addEventListener("keydown", (e) => {
  const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  if (directions[k]) {
    e.preventDefault();
    held.set(k, directions[k]);
  }
  if (!e.repeat && (k === "e" || k === "Enter") && !modal) command("interact");
  if (!e.repeat && k === "Escape") modal ? close() : open("Menu");
});
window.addEventListener("keyup", (e) =>
  held.delete(e.key.length === 1 ? e.key.toLowerCase() : e.key),
);
window.addEventListener("blur", () => held.clear());
document.querySelectorAll("[data-dir]").forEach((b) => {
  b.onpointerdown = (e) => {
    e.preventDefault();
    b.setPointerCapture(e.pointerId);
    held.set("touch", b.dataset.dir);
  };
  b.onpointerup = b.onpointercancel = () => held.delete("touch");
});
function movement(t) {
  if (
    view?.mode === "explore" &&
    !modal &&
    !busy &&
    held.size &&
    t - lastMove > 175
  ) {
    const d = [...held.values()].at(-1);
    renderer.facing = { up: "ne", down: "sw", left: "nw", right: "se" }[d];
    lastMove = t;
    command("move", { direction: d });
  }
  requestAnimationFrame(movement);
}
requestAnimationFrame(movement);
try {
  content = await fetch("data/floor-one-rpg.json").then((r) => {
    if (!r.ok) throw Error("Floor content unavailable");
    return r.json();
  });
  await Blazor.start();
  const requestedSeed = new URLSearchParams(location.search).get("seed");
  const seedNumber = requestedSeed === null ? 1337 : Number(requestedSeed);
  const seed = Number.isInteger(seedNumber) && seedNumber >= -2147483648 && seedNumber <= 2147483647 ? seedNumber : 1337;
  const initial = parse(
    await invoke("Initialize", JSON.stringify(content), seed),
  );
  apply(initial);
  $("#loading").remove();
  $("#world").focus();
  renderer.ready.catch((e) =>
    notify("Some artwork could not load. " + e.message),
  );
} catch (e) {
  $("#loading").innerHTML =
    "Unable to enter the dungeon.<small>" + esc(e.message) + "</small>";
  console.error(e);
}
