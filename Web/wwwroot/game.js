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
  aiming = false,
  skillsActorId = "",
  toastTimer,
  inventoryActorId = "",
  enemyTimer,
  enemyEpoch = 0;
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
  if (busy || !view || (view.mode === "battle" && view.battle?.phase === "enemy" && type !== "advanceEnemyTurn")) return;
  if (["retry"].includes(type)) cancelEnemy();
  if (["endUnit", "endTurn"].includes(type)) args = { ...args, animateEnemyTurn: true };
  if (type === "interact" && !args.targetId) {
    const choices = nearbyChoices();
    if (choices.length > 1) { open("Interact"); return; }
    const o = choices[0];
    if (!o || o.available === false) { if (o?.reason) notify(o.reason); return; }
    args = { ...args, targetId: o.id };
  }
  busy = true;
  try {
    const next = parse(
      await invoke("Dispatch", JSON.stringify({ type, ...args })),
    );
    apply(next);
    if (type === "interact" && args.targetId === view.safeRoom?.safeRoomId && view.mode === "explore" && view.safeRoom?.preparationAllowed) open("Safe room");
    if (type === "endUnit" && view.mode === "battle" && view.battle.phase !== "enemy") {
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
    scheduleEnemy();
  }
}
function cancelEnemy() { clearTimeout(enemyTimer); enemyTimer = undefined; enemyEpoch++; }
const enemyPresentationDelay = { move: 180, attack: 450, tick: 250, wait: 250 };
function scheduleEnemy() {
  if (view?.battle?.phase !== "enemy" || view.mode !== "battle") { cancelEnemy(); return; }
  if (enemyTimer) return;
  const epoch = enemyEpoch;
  const delay = enemyPresentationDelay[view.battle.enemyIntent?.stage] ?? 300;
  enemyTimer = setTimeout(async () => { enemyTimer = undefined; if (epoch !== enemyEpoch) return; await command("advanceEnemyTurn"); }, delay);
}
function nearbyChoices() { return view?.nearbyInteractions || []; }
function nearby() {
  return nearbyChoices()[0];
}
function apply(next) {
  const old = view;
  view = next;
  if (old?.selectedId !== view.selectedId || view.mode !== "battle" || view.battle?.phase === "enemy") { skill = ""; manaSpend = 0; aiming = false; }
  if (old?.battle?.phase === "enemy" && (view.mode !== "battle" || view.battle?.phase !== "enemy")) cancelEnemy();
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
    (typeof view.objective === "string" ? view.objective : view.objective?.name) || view.quest ||
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
  $("#stage").dataset.phase = view.battle?.phase || "explore";
  $("#menu-button").disabled = view.mode === "battle" && view.battle?.phase === "enemy";
  $("#controls").style.display = view.mode === "explore" ? "flex" : "none";
  $("#interact").innerHTML =
    (nearby() ? "Interact: " + esc(nearby().name) : "Interact") +
    " <kbd>E</kbd>";
  $("#interact").disabled = !nearbyChoices().length;
  $("#interact").title = nearby()?.reason || "Interact with nearby people and objects";
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
  if (view.reward) modal = "Victory";
  if (modal) renderModal();
  if (next.mode === "defeat" || next.mode === "complete") {
    modal = next.mode;
    renderModal();
  }
  if (next.mode === "battle" && old?.mode !== "battle")
    notify("Battle! Select a crawler, then a tile or action.");
  window.rpgView = view;
  scheduleEnemy();
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
function forecastDamage(events = []) {
  const targets = [...(view.battle?.units || []), ...(view.battle?.enemies || []), ...(view.battle?.effectObjects || [])];
  const rows = events.filter(e => ["damage", "objectDamaged"].includes(e.kind));
  if (!rows.length) return "";
  return `<ul class="forecast-damage" aria-label="Damage by target">${rows.map(e => {
    const target = targets.find(t => t.id === e.targetId);
    const ally = view.battle.units.some(t => t.id === e.targetId);
    return `<li class="${ally ? "ally-damage" : ""}" data-damage-target="${esc(e.targetId)}"><span>${esc(target?.name || target?.label || e.targetId)} <small>${ally ? "ALLY" : e.kind === "objectDamaged" ? "OBJECT" : "ENEMY"}</small></span><strong>${e.amount} damage</strong></li>`;
  }).join("")}</ul>`;
}
function mini(u) {
  return `<div class="party-mini" data-character="${esc(u.id)}">${portrait(u)}<div class="unit-info"><strong>${esc(u.name)}</strong> <small>Lv ${u.level}</small><div><small>HP ${u.hp}/${u.maxHp} · Mana ${u.mp}/${u.maxMp}</small></div><div class="meter"><i style="width:${(u.hp / u.maxHp) * 100}%"></i></div><div class="meter mp"><i style="width:${(u.mp / u.maxMp) * 100}%"></i></div>${characterProgress(u, true)}${statuses(u)}</div></div>`;
}
function enemyDescription() {
  const i = view.battle?.enemyIntent;
  if (!i) return "Enemies are preparing. Your party acts next.";
  const actor = view.battle.enemies.find((u) => u.id === i.actorId)?.name || "Enemies";
  const target = view.battle.units.find((u) => u.id === i.targetId)?.name;
  return `${actor} · ${i.stage === "move" ? "Moving" : i.stage === "attack" ? "Attacking" : i.stage === "tick" ? "Resolving effects" : "Waiting"}${target ? ` → ${target}` : ""}`;
}
function renderDeck() {
  if (view.mode === "battle" && view.battle.phase === "enemy") {
    $("#deck").innerHTML = `<div class="enemy-readout"><strong>Enemy turn</strong><p>${esc(enemyDescription())}</p></div>`; return;
  }
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
    `<div><span class="turn-label">${u.moved ? "MOVE USED" : "MOVE 3"} · ${u.acted ? "ACTION USED" : "ACTION READY"} · ATK ${u.power} · DEF ${u.armor}</span><div class="actions"><button data-move-mode ${!aiming && (u.moved || u.ended) ? "disabled" : ""}>${aiming ? "Cancel aim / Move" : "Move"}</button>${u.skills.map((id) => { const p = skillState(u, id); return `<button data-skill="${id}" title="${esc(actionTooltip(p))}" class="${skill === id ? "active" : ""}" ${u.acted || u.ended || p?.canUse === false ? "disabled" : ""}>${esc(content.skills.find((s) => s.id === id)?.name || id)}${p ? `<small class="action-cost">${p.cost} ${esc(p.resource || "Mana")}${p.disabledReason ? ` · ${esc(p.disabledReason)}` : ""}</small>` : ""}</button>`; }).join("")}<button data-command="endUnit" ${u.ended ? "disabled" : ""}>End ${esc(u.name)} turn</button><button data-command="endTurn">End party turn</button><button data-open="Items">Items</button></div></div>`;
  $("#deck").querySelector("[data-move-mode]").onclick = () => { if (modal) close(); aiming = false; skill = ""; manaSpend = 0; renderDeck(); notify("Move: select an empty tile within movement range."); };
  if (aiming) $("#deck").insertAdjacentHTML("beforeend", `<p class="aim-instruction" role="status" data-aim-instruction>Aim: select any tile on the map, including an ally’s tile. Cancel aim / Move returns to movement.</p>`);
  $("#deck")
    .querySelectorAll("[data-skill]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          aiming = false;
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
    (view.mode === "battle" && view.battle?.phase === "enemy") ||
    view.mode !== "battle" ||
    x < 0 ||
    y < 0 ||
    x >= view.battle.width ||
    y >= view.battle.height
  )
    return;
  if (aiming) { forecast("", x, y); return; }
  const ally = view.battle.units.find(
    (u) => u.x === x && u.y === y && u.hp > 0,
  );
  if (ally) {
    skill = "";
    manaSpend = 0;
    command("select", { actorId: ally.id });
    return;
  }
  const activeSkill = content.skills.find(s => s.id === skill);
  const object = view.battle.effectObjects?.find(o => !o.destroyed && x >= o.x && y >= o.y && x < o.x + (o.width || 1) && y < o.y + (o.height || 1));
  if (object && ["object", "enemyOrObject"].includes(activeSkill?.targetKind)) {
    forecast(object.id); return;
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
  aiming = false;
  renderDeck();
  modal = "Forecast";
  renderModal();
}
function open(name) {
  if (!view || (view.mode === "battle" && view.battle?.phase === "enemy")) return;
  held.clear();
  if (["Equipment", "Items"].includes(name) && !inventoryActorId) inventoryActorId = view.selectedId || view.party[0]?.id;
  if (name === "Skills") skillsActorId = view.selectedId || view.party[0]?.id;
  modal = name;
  renderModal();
}
function close() {
  aiming = false;
  if (["Targets", "Forecast"].includes(modal)) { skill = ""; manaSpend = 0; }
  if (modal === "Victory" && view?.reward) { command("acknowledgeReward"); }
  held.clear();
  modal = "";
  renderer.forecastVisible = false;
  document.body.classList.remove("forecast-open");
  $("#modal-root").innerHTML = "";
  $("#world").focus();
  renderDeck();
}
function selected() {
  return (
    view.party.find(
      (u) => u.id === (inventoryActorId || view.selectedId),
    ) || view.party[0]
  );
}
function actorChooser(u) {
  return `<label class="crawler-choice">Crawler <select id="crawler-select" aria-label="Select crawler">${view.party.map((p) => `<option value="${esc(p.id)}" ${p.id === u.id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}</select></label>`;
}
function equipmentBody(u) {
  const previews = (view.equipmentPreviews || []).filter((p) => p.actorId === u.id);
  return actorChooser(u) + `<p class="map-key">Equipped: ${esc(content.items.find((i) => i.id === u.equipment)?.name || "None")} · Power ${u.power} · Armor ${u.armor}</p>` + previews.map((p) => {
    const item = content.items.find((i) => i.id === p.itemId);
    const delta = (n) => n > 0 ? `+${n}` : `${n}`;
    return `<div class="row"><div><strong>${esc(item?.name || "Remove equipment")}</strong> <span class="tag">${p.itemId ? `×${p.count}` : "Unequip"}</span><p>${esc(item?.description || "Return equipment to your inventory.")}</p><p class="stat-preview">Power ${delta(p.powerDelta)} · Armor ${delta(p.armorDelta)}${Object.entries(p.rankDeltas || {}).map(([id,n]) => ` · ${esc(content.skills.find((x) => x.id === id)?.name || id)} ${delta(n)}`).join("")}</p>${p.reason ? `<p class="${p.available ? "map-key" : "cost-warning"}">${esc(p.reason)}</p>` : ""}</div><button data-equip="${esc(p.itemId)}" ${p.available ? "" : "disabled"}>${p.itemId ? "Equip" : "Unequip"}</button></div>`;
  }).join("");
}
function itemsBody(u) {
  const rows = (view.consumablePreviews || []).filter((p) => p.actorId === u.id && p.count > 0);
  return actorChooser(u) + `<p class="map-key">HP ${u.hp}/${u.maxHp} · Mana ${u.mp}/${u.maxMp}</p>` + (rows.map((p) => {
    const item = content.items.find((i) => i.id === p.itemId);
    return `<div class="row"><div><strong>${esc(item?.name || p.itemId)} ×${p.count}</strong><p>${esc(item?.description || "")}</p><p>Restore ${p.heal} HP · ${p.mp} Mana</p>${p.reason ? `<p class="${p.available ? "map-key" : "cost-warning"}">${esc(p.reason)}</p>` : ""}</div><button data-item="${esc(p.itemId)}" data-actor="${esc(u.id)}" ${p.available ? "" : "disabled"}>Use</button></div>`;
  }).join("") || "<p>No consumables.</p>");
}
function safeBody() {
  const safe = view.safeRoom || {};
  return `<p class="map-key">A moment to prepare. ${view.gold} gold</p><div class="menu-grid"><button id="rest-button" ${safe.restAllowed ? "" : "disabled"}>Rest party</button><button id="save-button" ${safe.saveAllowed ? "" : "disabled"}>Save game</button><button data-open="Equipment">Equipment</button><button data-open="Items">Items</button><button data-open="Shop" ${safe.resupplyAllowed ? "" : "disabled"}>Buy supplies</button><button id="leave-safe">Leave on foot</button></div><p id="save-result" role="status"></p><p class="map-key">${esc(safe.reason || "Rest restores the party. Save keeps a checkpoint in this browser.")}</p>`;
}
function shopBody() {
  return `<p class="map-key">${view.gold} gold · Safe room supplies</p>` + (view.resupplyOffers || []).map((p) => `<div class="row"><div><strong>${esc(p.name)} ×${p.quantity}</strong><p>${p.goldCost} gold · Owned ${p.count}</p>${p.reason ? `<p class="${p.available ? "map-key" : "cost-warning"}">${esc(p.reason)}</p>` : ""}</div><button data-buy="${esc(p.offerId)}" ${p.available ? "" : "disabled"}>Buy</button></div>`).join("") + '<button data-open="Safe room">Back to safe room</button>';
}
function rewardBody() {
  const r = view.reward;
  if (!r) return "<p>Rewards received.</p>";
  return `<p class="reward-title">${esc(r.name)}</p><p class="reward-gold">+${r.gold} gold</p>${(r.party || []).map((p) => `<div class="row"><div><strong>${esc(view.party.find((u) => u.id === p.actorId)?.name || p.actorId)}</strong><p>+${p.xp} XP${p.levelAfter > p.levelBefore ? ` · Level ${p.levelBefore} → ${p.levelAfter}` : ""}</p></div></div>`).join("")}${(r.items || []).map((i) => `<p>+${i.count} ${esc(content.items.find((x) => x.id === i.itemId)?.name || i.itemId)}</p>`).join("")}<p class="map-key">${view.nearestSafe ? (view.nearestSafe.distance === 0 ? `You are beside ${esc(view.nearestSafe.name)}. Rest and save here.` : `Safe room: ${esc(view.nearestSafe.name)} · ${view.nearestSafe.distance} steps away · start ${esc(view.nearestSafe.direction)}. Walk there to rest and save.`) : "Continue exploring the dungeon."}</p><button id="reward-continue">Continue</button>`;
}

function renderModal() {
  let body = "";
  const u = selected();
  if (modal === "Interact")
    body = nearbyChoices().map((o) => `<div class="row"><div><strong>${esc(o.name)}</strong><p>${esc(o.reason || "Nearby")}</p></div><button data-interact="${esc(o.id)}" ${o.available === false ? "disabled" : ""}>Interact</button></div>`).join("");
  else if (modal === "Victory") body = rewardBody();
  else if (modal === "Safe room") body = safeBody();
  else if (modal === "Shop") body = shopBody();
  else if (modal === "Menu")
    body = `<div class="menu-grid">${["Map", "Party", "Equipment", "Skills", "Items", "Journal", "Save"].map((n) => `<button data-open="${n}">${n}</button>`).join("")}</div><p class="map-key">Carl and Princess Donut · ${view.gold} gold · Floor one</p>`;
  else if (modal === "Party")
    body = view.party
      .map(
        (p) =>
          `<div class="row">${portrait(p)}<div><strong>${esc(p.name)} · Level ${p.level}</strong><p>HP ${p.hp}/${p.maxHp} · Mana ${p.mp}/${p.maxMp}</p>${characterProgress(p)}<p>Power ${p.power} · Armor ${p.armor}</p>${statuses(p)}<p>${esc(p.equipment ? (content.items.find((item) => item.id === p.equipment)?.name || p.equipment) : "No equipment equipped")}</p></div></div>`,
      )
      .join("");
  else if (modal === "Equipment") body = equipmentBody(u);
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
  else if (modal === "Items") body = itemsBody(u);
  else if (modal === "Journal")
    body = (view.availability || []).filter((s) => s.kind === "storyEvent" || s.kind === "facility").map((s) => `<div class="row"><div><strong>${esc(s.name)}</strong><p>${esc(s.reason || (s.available ? "Available" : "Locked"))}</p></div></div>`).join("") + (view.journal || [])
      .map(
        (s) =>
          `<div class="row"><div>${esc(typeof s === "string" ? s : s.text || s.description)}</div></div>`,
      )
      .join("");
  else if (modal === "Save")
    body = `<p>Rest and save beside a safe room. Your save stays in this browser.</p><div class="actions"><button id="rest-button" ${view.safeRoom?.restAllowed ? "" : "disabled"}>Rest</button><button id="save-button" ${view.safeRoom?.saveAllowed ? "" : "disabled"}>Save game</button><button id="load-button" ${localStorage.getItem(SAVE) ? "" : "disabled"}>Load game</button></div><p class="map-key" id="save-result"></p>`;
  else if (modal === "Map")
    body =
      '<canvas id="map-preview" class="map-preview"></canvas><p class="map-key">● Carl · Gold: destinations · Green: cleared · Travel through the dungeon with WASD or arrows.</p>';
  else if (modal === "End turn")
    body =
      '<p>End the party turn? Crawlers with actions remaining will wait, then the enemies will move and attack.</p><button id="end-turn-confirm">End turn</button>';
  else if (modal === "Targets") {
    const actor = view.battle.units.find((u) => u.id === view.selectedId);
    const kind = skillState(actor || {}, skill || actor?.skills[0])?.targetKind || "enemy";
    const groundAllowed = content.skills.find(s => s.id === (skill || actor?.skills[0]))?.allowGroundTarget;
    const targets = kind === "self" ? [actor] : kind === "ally" ? view.battle.units : kind === "object" ? (view.battle.effectObjects || []).filter((o) => !o.destroyed) : kind === "enemyOrObject" ? [...view.battle.enemies, ...(view.battle.effectObjects || []).filter((o) => !o.destroyed)] : kind === "cell" ? [] : view.battle.enemies;
    body = `<p>Select ${kind === "cell" ? "a tile" : kind === "object" ? "an object" : "a target"} to preview the result. The forecast checks range and available resources.</p>` + manaChooser() +
      (kind === "cell" ? `<div class="cell-target-grid" style="--columns:${view.battle.width}">${Array.from({length:view.battle.width * view.battle.height}, (_,i) => {const x=i % view.battle.width,y=Math.floor(i / view.battle.width); return `<button data-target-cell="${x},${y}" aria-label="Forecast tile ${x+1}, ${y+1}" title="Tile ${x+1}, ${y+1}">${x+1},${y+1}</button>`;}).join("")}</div>` : targets.filter((e) => e && e.hp > 0).map((e) => `<div class="row"><div>${esc(e.name || e.label || e.id)}<p>HP ${e.hp}${e.maxHp ? `/${e.maxHp}` : ""}${e.armor !== undefined ? ` · Armor ${e.armor}` : ""}</p>${statuses(e)}</div><button data-target="${esc(e.id)}">Forecast</button></div>`).join("") || "<p>No targets available.</p>");
    if (groundAllowed && kind !== "cell") body += `<button data-aim-map>Aim on map</button><details class="ground-targets"><summary>Choose tile by coordinates</summary><p class="map-key">Choose the blast center. The forecast checks range and shows every affected target.</p><div class="cell-target-grid" style="--columns:${view.battle.width}">${Array.from({length:view.battle.width * view.battle.height}, (_,i) => { const x=i % view.battle.width,y=Math.floor(i / view.battle.width); return `<button data-target-cell="${x},${y}" aria-label="Forecast tile ${x+1}, ${y+1}">${x+1},${y+1}</button>`; }).join("")}</div></details>`;
  }
  else if (modal === "Forecast") {
    const f = view.forecast;
    body = f
      ? `<div class="forecast-brief"><strong>${esc(content.skills.find(s => s.id === f.skillId)?.name || f.skillId)}</strong><span>${f.cost} ${esc(f.resource || "Mana")}${f.affectedCells?.length > 1 ? "" : ` · ${f.damage} damage`}</span></div>${f.friendlyFire ? `<p class="friendly-fire-warning" role="alert" data-friendly-fire>⚠ FRIENDLY FIRE: party members will be hit.</p>` : ""}${!f.valid ? `<p class="cost-warning" data-forecast-reason>${esc(f.reason || view.message)}</p>` : ""}<div class="forecast-scroll">${forecastDamage(f.events)}<details class="forecast-details"><summary>Skill and effect details</summary><p>${esc(content.skills.find(s => s.id === f.skillId)?.description || "")}</p><p data-forecast-ranks>Trained rank ${f.trainedRank} · Effective rank ${f.effectiveRank} · Range ${f.range}</p><p data-forecast-detail-reason>${esc(f.reason || f.reaction || "")}</p><ul class="effect-list" aria-label="Forecast effects">${effectSummary(f.events)}</ul></details></div><div class="actions forecast-actions"><button id="confirm-action" ${f.valid ? "" : "disabled"}>${f.friendlyFire ? "Confirm friendly fire" : "Confirm action"}</button><button data-open="Targets">Choose target</button><button id="close-modal" data-cancel-forecast>Cancel</button></div>`
      : "<p>Select a skill and target.</p>";
  } else if (modal === "defeat")
    body =
      '<p>The dungeon wins this round. Return to your last safe-room checkpoint, or the entrance if you have not rested.</p><button id="retry-button">Return to checkpoint</button>';
  else if (modal === "complete")
    body =
      '<p>Carl and Donut have reached the staircase. Floor one is cleared.</p><button data-open="Journal">Read your journal</button>';
  renderer.forecastVisible = modal === "Forecast";
  document.body.classList.toggle("forecast-open", modal === "Forecast");
  $("#modal-root").innerHTML =
    `<div class="modal-backdrop ${modal === "Forecast" ? "forecast-backdrop" : ""}"><section class="window modal" role="dialog" aria-modal="true" aria-label="${esc(modal)}">${modal === "Forecast" ? "" : `<div class="modal-head"><h1>${esc(modal === "defeat" ? "Party defeated" : modal === "complete" ? "Floor cleared" : modal === "Victory" ? (view.reward?.sourceKind === "cache" ? "Cache found" : "Victory") : modal)}</h1><button id="close-modal" aria-label="Close menu">✕</button></div>`}<div class="modal-content">${body}</div></section></div>`;
  $("#close-modal").onclick = close;
  if ($("[data-cancel-forecast]")) $("[data-cancel-forecast]").onclick = close;
  if ($("[data-aim-map]")) $("[data-aim-map]").onclick = () => {
    const chosenSkill = skill, chosenMana = manaSpend;
    close(); skill = chosenSkill; manaSpend = chosenMana; aiming = true; renderDeck();
    notify("Aim: select a map tile. Use Cancel aim / Move to return to movement.");
  };
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
  if ($("#crawler-select")) $("#crawler-select").onchange = (e) => { inventoryActorId = e.target.value; renderModal(); };
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
        if ($("#load-button")) $("#load-button").disabled = false;
      } catch (e) {
        $("#save-result").textContent = e.message;
      }
    };
  if ($("#load-button"))
    $("#load-button").onclick = async () => {
      try {
        cancelEnemy(); held.clear();
        const loaded = parse(await invoke("LoadSave", localStorage.getItem(SAVE)));
        apply(loaded);
        close();
        notify(loaded.message);
      } catch (e) {
        notify(e.message);
      }
    };
  $("#modal-root").querySelectorAll("[data-interact]").forEach((b) => b.onclick = async () => { close(); await command("interact", {targetId:b.dataset.interact}); });
  $("#modal-root").querySelectorAll("[data-buy]").forEach((b) => b.onclick = () => command("buy", {targetId:b.dataset.buy}));
  if ($("#leave-safe")) $("#leave-safe").onclick = close;
  if ($("#reward-continue")) $("#reward-continue").onclick = close;
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
  if (k === "Escape") {
    if (!e.repeat) { e.preventDefault(); aiming ? (aiming = false, skill = "", manaSpend = 0, renderDeck(), notify("Aim canceled. Select an empty tile to move.")) : modal ? close() : open("Menu"); }
    return;
  }
  if (e.target.closest?.("select, input, textarea, button, [contenteditable]")) return;
  if (modal || (view?.mode === "battle" && view.battle?.phase === "enemy")) return;
  if (directions[k]) {
    e.preventDefault();
    held.set(k, directions[k]);
  }
  if (!e.repeat && (k === "e" || k === "Enter") && !modal) command("interact");
});
window.addEventListener("keyup", (e) =>
  held.delete(e.key.length === 1 ? e.key.toLowerCase() : e.key),
);
window.addEventListener("blur", () => held.clear());
document.addEventListener("visibilitychange", () => held.clear());
document.querySelectorAll("[data-dir]").forEach((b) => {
  b.onpointerdown = (e) => {
    e.preventDefault();
    if (modal || view?.mode !== "explore") return;
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
