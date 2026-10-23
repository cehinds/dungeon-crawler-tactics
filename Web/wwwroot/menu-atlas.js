const atlas = document.querySelector('#atlas');
const menuFilter = document.querySelector('#menu-filter');
const kindFilter = document.querySelector('#kind-filter');
const search = document.querySelector('#search');
const count = document.querySelector('#result-count');
const sheetDialog = document.querySelector('#sheet-dialog');
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const bar = (value, max, mana = false) => `<div class="meter ${mana ? 'mana' : ''}" role="meter" aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="${max}" aria-label="${mana ? 'Mana' : 'Health'}"><span style="width:${100 * value / max}%"></span></div>`;
const badge = (text, color = '') => `<span class="tag ${color}">${esc(text)}</span>`;
const button = (text, disabled = false, ready = false) => `<button type="button" class="gold-button ${ready ? 'ready' : ''}" data-cycle ${disabled ? 'disabled' : ''}>${esc(text)}</button>`;
const portrait = (source = 'brawler', name = 'Carl') => `<img class="portrait" src="assets/${source}.png" alt="${name} pixel portrait" loading="lazy">`;
const row = (left, right) => `<div class="row">${left}${right}</div>`;
const grid = state => `<div class="cell-grid" aria-label="${state} tile preview">${Array.from({length:15}, (_, i) => `<span class="cell ${state === 'movement' && [1,2,3,6,7,8,11,12].includes(i) ? 'reach' : state === 'danger' && i >= 5 && i < 10 ? 'threat' : state === 'target' && i === 7 ? 'target' : ''}"></span>`).join('')}</div>`;
function demo(id, state) {
    switch (id) {
        case 'mission-tile': return `<div class="mission-title"><span class="title-line">NEIGHBORHOOD BOSS</span><br><strong>The Hoarder</strong><br><small>Garbage stockpile · Emergence pressure</small></div>${row(badge(state === 'completed' ? 'CLEARED' : state === 'selected' ? 'SELECTED' : 'AVAILABLE'), '<small>Illustrative · 3 turns</small>')}${button(state === 'completed' ? 'Replay briefing' : 'Inspect mission', false, state === 'selected')}`;
        case 'mission-briefing': return `<span class="title-line">OBJECTIVE</span><strong>${state === 'completed' ? 'Room cleared' : 'Break the hoard'}</strong><small>Defeat the boss and surviving Scatterers.</small><hr>${badge(state === 'danger' ? 'EMERGENCE IN 1 TURN' : state === 'completed' ? 'EXIT OPEN' : 'FIRE CAN INTERRUPT', state === 'danger' ? 'orange' : 'cyan')}`;
        case 'quest-row': return `<span class="title-line">FLOOR OBJECTIVE</span><div class="checkline"><span class="${state === 'complete' ? 'green' : 'gold'}" aria-hidden="true">${state === 'complete' ? '☑' : '□'}</span><strong>Brace the Speedbump</strong></div>${bar(state === 'active' ? 0 : state === 'progress' ? 2 : 3, 3, true)}<small>${state === 'active' ? '0' : state === 'progress' ? '2' : '3'} / 3 parts secured · Illustrative</small>`;
        case 'party-turn': return `<span class="title-line">PARTY ACTIVATION</span><div class="turns"><span class="turn-token ${state === 'finished' ? 'finished' : 'current'}">CARL</span><span class="turn-token ${state === 'current' ? 'current' : ''}">DONUT</span><span class="turn-token">KATIA</span><span class="turn-token">MONGO</span></div><small>${state === 'finished' ? 'Carl finished · Donut is next.' : 'Move and act in either order.'}</small><small>Mixed timeline roster adaptation</small>`;
        case 'entry-confirm': return `<strong>${state === 'entered' ? 'Encounter ready' : 'Enter the boss room?'}</strong><small>Your campaign remains separate from this scenario.</small>${button(state === 'entered' ? 'Reset preview' : state === 'confirm' ? 'Confirm entry' : 'Review briefing', false, state === 'confirm')}<small>Return to campaign is always available.</small>`;
        case 'skill-node': return `<div class="row"><div class="skill-node ${state}" title="${esc(state)} node">${state === 'locked' ? '⌑' : state === 'maxed' ? '✦' : '✧'}</div><div class="stack"><strong>Impact training</strong>${badge(state.toUpperCase(), state === 'available' ? 'cyan' : '')}<small>${state === 'maxed' ? 'Rank 3 / 3' : state === 'learned' ? 'Rank 1 / 3' : 'Cost: 1 point'}</small></div></div><small>${state === 'locked' ? 'Requires Improvised Tools.' : state === 'available' ? 'Prerequisite met. Inspect before learning.' : 'Illustrative skill package.'}</small>`;
        case 'prerequisite-connector': return `<div class="node-route"><div class="skill-node learned">Ⅰ</div><div class="connector ${state !== 'locked' ? 'on' : ''}" aria-label="${state === 'locked' ? 'Locked' : 'Active'} connection"></div><div class="skill-node ${state}">Ⅱ</div></div><small>${state === 'locked' ? 'Learn the preceding node to continue.' : state === 'available' ? 'Path available · Next node costs 1 point.' : 'Both nodes learned · Path complete.'}</small>`;
        case 'points-badge': return `<div class="points"><b>${state === 'available' ? '3' : '0'}</b> UNSPENT POINTS</div><small>${state === 'empty' ? 'Earn a level to receive more points.' : state === 'spent' ? 'Point spent. Your new effect is active.' : 'Select a node to review its cost.'}</small><small>Demo budget only</small>`;
        case 'node-details': return `<span class="title-line">IMPACT TRAINING · RANK 1</span><strong>Know the tradeoff</strong><div class="stat-table"><span>Illustrative benefit</span><b class="cyan">+1 impact</b><span>Cost</span><b>1 point</b><span>Requirement</span><b>${state === 'locked' ? 'Not met' : 'Met'}</b></div>${button(state === 'locked' ? 'Prerequisite required' : state === 'learned' ? 'Learned' : 'Review node', state !== 'available')}`;
        case 'unlock-confirm': return `<strong>${state === 'unlocked' ? 'Node learned' : 'Learn Impact training?'}</strong><small>${state === 'unlocked' ? 'Your local preview is updated.' : 'Unspent points: 3 → 2. Rank: 0 → 1.'}</small>${button(state === 'unlocked' ? 'Reset preview' : state === 'confirm' ? 'Spend 1 point' : 'Review unlock', false, state === 'confirm')}<small>Requires the preceding node.</small>`;
        case 'equipment-slot': return `${row(`<div class="slot ${state === 'empty' ? 'empty' : state === 'incompatible' ? 'invalid' : ''}" aria-label="Weapon slot">${state === 'empty' ? '+' : '⚒'}</div>`, `<div class="stack"><span class="title-line">WEAPON</span><strong>${state === 'empty' ? 'Empty slot' : 'Workshop gloves'}</strong><small>${state === 'incompatible' ? 'Cannot equip in this slot.' : state === 'empty' ? 'Choose an owned item.' : 'Illustrative equipped item.'}</small></div>`)}${badge(state === 'incompatible' ? 'WRONG SLOT' : state.toUpperCase())}`;
        case 'item-stats': return `<span class="title-line">WORKSHOP GLOVES · WEAPON</span><strong>Make it count</strong><div class="stat-table"><span>HP cap</span><b class="green">+3</b><span>Mana cap</span><b>+0</b><span>Movement</span><b>+0</b></div>${button(state === 'equipped' ? 'Equipped' : state === 'selected' ? 'Preview equip' : 'Inspect item', state === 'equipped', state === 'selected')}`;
        case 'resource-bars': { const hp = state === 'healthy' ? 42 : state === 'wounded' ? 17 : 0; const mp = state === 'healthy' ? 12 : state === 'wounded' ? 5 : 0; return `<span class="title-line">CARL · ILLUSTRATIVE VALUES</span>${row('<strong>HP</strong>', `<b>${hp} / 42</b>`)}${bar(hp, 42)}${row('<strong>MANA</strong>', `<b>${mp} / 12</b>`)}${bar(mp, 12, true)}`; }
        case 'stat-comparison': return `<span class="title-line">EQUIPMENT PREVIEW</span><div class="stat-table"><span>HP cap</span><b class="${state === 'neutral' ? '' : 'green'}">42 → ${state === 'neutral' ? 42 : 45}</b><span>Mana cap</span><b>12 → 12</b><span>Movement</span><b class="${state === 'tradeoff' ? 'orange' : ''}">4 → ${state === 'tradeoff' ? 3 : 4}</b></div><small>${state === 'tradeoff' ? 'Gain toughness; give up one movement.' : 'Changing a resource cap does not restore HP.'}</small>`;
        case 'party-selection': return `${row(portrait(), `<div class="stack"><strong>Carl</strong><small>Compensated Anarchist</small>${badge(state === 'selected' ? 'IN PARTY' : state === 'full' ? 'PARTY FULL' : 'AVAILABLE')}</div>`)}${button(state === 'selected' ? 'Remove from party' : state === 'full' ? 'Remove another crawler first' : 'Add to party', state === 'full', state === 'selected')}`;
        case 'action-card': return `<span class="title-line">${state === 'selected' ? 'SELECTED ACTION' : 'CRAWLER ACTION'}</span><strong>Improvised bomb</strong><small>Blast the selected target. Review the shared-core forecast.</small><div class="tags">${badge('2 MANA')}${badge('4 RANGE')}</div>${button(state === 'disabled' ? 'Not enough Mana' : state === 'selected' ? 'Choose a target' : 'Select action', state === 'disabled', state === 'selected')}`;
        case 'target-forecast': return `<span class="title-line">${state === 'canceled' ? 'FORECAST CANCELED' : 'TARGET: MAINTENANCE RAT'}</span><div class="arrow-preview"><span>18 HP</span><span class="muted">→</span><span class="${state === 'canceled' ? 'muted' : 'orange'}">${state === 'canceled' ? '18' : '9'} HP</span></div><small>Mana: 12 → ${state === 'canceled' ? '12' : '10'} · ${state === 'canceled' ? 'Nothing spent.' : 'No hidden random roll.'}</small>${button(state === 'confirm' ? 'Confirm action' : state === 'canceled' ? 'Start another preview' : 'Review forecast', false, state === 'confirm')}`;
        case 'range-legend': return `${grid(state)}<div class="tags">${badge('REACH', 'cyan')}${badge('THREAT', 'orange')}${badge('TARGET')}</div><small>${state === 'movement' ? 'Cyan: reachable movement cells.' : state === 'danger' ? 'Amber: the declared attack footprint.' : 'Gold: the selected target tile.'}</small>`;
        case 'enemy-intent': return `<span class="title-line">NEXT ENEMY ACTION</span><strong>${state === 'interrupted' ? 'Throw interrupted' : state === 'impact' ? 'Plate resolved' : 'Flaming plate'}</strong><div class="intent-lane ${state === 'interrupted' ? 'safe' : ''}" aria-label="${state === 'interrupted' ? 'Interrupted' : 'Threatened'} lane">${'<i></i>'.repeat(5)}</div><small>${state === 'interrupted' ? 'Control or displacement canceled the windup.' : state === 'impact' ? 'A toppled bench intercepted the plate.' : 'Locked lane · Side-step or topple cover.'}</small>`;
        case 'end-turn': return `<strong>${state === 'ended' ? 'Donut is ready' : 'Finish Carl’s turn?'}</strong><small>${state === 'unused' ? 'You still have movement and an action.' : state === 'ended' ? 'The next unfinished ally is selected.' : 'Movement spent · Action spent'}</small>${button(state === 'ended' ? 'Reset preview' : 'End turn → Donut', false, state !== 'unused')}`;
        case 'recipe-ingredients': return `<span class="title-line">ILLUSTRATIVE RECIPE · BLAST CHARGE</span><div class="ingredient ${state === 'missing' ? 'missing' : ''}"><span>Powder</span><b>${state === 'consumed' ? '0' : state === 'missing' ? '1' : '3'} / 2</b></div><div class="ingredient"><span>Metal casing</span><b>${state === 'consumed' ? '0' : '1'} / 1</b></div><hr><small>${state === 'missing' ? 'Need 1 more powder before crafting.' : state === 'consumed' ? 'Ingredients consumed by the local preview.' : 'All ingredients available.'}</small>`;
        case 'craft-confirm': return `<strong>${state === 'crafted' ? 'Charge assembled' : 'Craft one blast charge?'}</strong><small>Cost: 2 powder + 1 casing.<br>Result: 1 blast charge.</small>${button(state === 'crafted' ? 'Reset preview' : state === 'confirm' ? 'Consume materials & craft' : 'Review recipe', false, state === 'confirm')}<small>Illustrative workshop flow</small>`;
        case 'loot-box': return `<div class="loot-chest" aria-hidden="true">${state === 'claimed' ? '◇' : '▣'}</div><strong>${state === 'claimed' ? 'Reward claimed' : state === 'opening' ? 'Sponsor delivery' : 'Bronze reward box'}</strong><small>${state === 'claimed' ? 'Health tonic × 1 · Demo inventory' : state === 'opening' ? 'The contents are ready to inspect.' : 'Owned reward · Open inside a safe room.'}</small>${button(state === 'claimed' ? 'Reset preview' : 'Open reward', false, state === 'opening')}`;
        case 'rest-service': return `<strong>${state === 'rested' ? 'Party recovered' : 'Rest in the safe room'}</strong><small>${state === 'unavailable' ? 'Return to the safe room before resting.' : state === 'rested' ? 'HP and Mana are full.' : 'Restore the party’s HP and Mana.'}</small>${bar(state === 'needed' ? 17 : 42, 42)}${button(state === 'rested' ? 'Fully rested' : state === 'unavailable' ? 'Unavailable in battle' : 'Rest party', state !== 'needed', state === 'needed')}`;
        case 'service-row': return `<div class="row"><div class="stack"><span class="title-line">SAFE ROOM</span><strong>Workshop</strong><small>Inspect recipes and materials.</small></div><strong class="${state === 'locked' ? 'muted' : 'cyan'}">${state === 'locked' ? '⌑' : '→'}</strong></div>${button(state === 'locked' ? 'Find a workshop first' : state === 'selected' ? 'Workshop selected' : 'Browse services', state === 'locked', state === 'selected')}`;
        case 'enemy-card': { const hp = state === 'healthy' ? 52 : state === 'wounded' ? 19 : 0; return `${row(portrait('enemy', 'Enemy silhouette'), `<div class="stack"><strong>The Juicer</strong><small>Troglodyte boss</small>${badge(state.toUpperCase(), state === 'wounded' ? 'orange' : '')}</div>`)}${bar(hp, 52)}<small>${hp} / 52 HP · Illustrative boss values</small>`; }
        case 'enemy-tags': return `<strong>Conditions</strong><div class="tags">${state === 'normal' ? badge('NO CONDITIONS') : state === 'wet' ? badge('WET · 2 ROUNDS', 'cyan') : badge('BURNING · 1 ROUND', 'orange')}</div><small>${state === 'normal' ? 'No active condition to account for.' : state === 'wet' ? 'Wet can interact with cold or lightning.' : 'Burning applies damage over time.'}</small>${button('Inspect condition')}`;
        case 'intent-details': return `<span class="title-line">DECLARED ATTACK</span><strong>Rolling impact</strong><small>${state === 'planned' ? 'Traverses the three marked cells. Move clear before the enemy phase.' : state === 'blocked' ? 'A completed Speedbump stops the roll and damages the boss.' : 'Collision resolved. Read the next route before moving.'}</small><div class="tags">${badge(state === 'blocked' ? 'BARRIER INTERCEPT' : state === 'resolved' ? 'RESOLVED' : '3 TILE PATH', state === 'blocked' ? 'cyan' : 'orange')}</div>`;
        case 'status-legend': return `<div class="row"><strong>${state.toUpperCase()}</strong>${badge(state === 'guarded' ? 'SINGLE HIT' : '2 ROUNDS')}</div><small>${state === 'wet' ? 'Water contact can set up a reaction. Inspect the action forecast for the result.' : state === 'frozen' ? 'Cold control can interrupt a boss windup. A shatter reaction consumes Frozen.' : 'Protection reduces a qualifying hit. Inspect the forecast for its exact effect.'}</small><small>Condition rules remain owned by C#.</small>`;
        case 'inspection-panel': return `<span class="title-line">SCATTERER</span><strong>${state === 'overview' ? 'Small body. Big nuisance.' : state === 'weakness' ? 'Control the emergence' : 'Make room to move'}</strong><small>${state === 'overview' ? 'A minion emerging near the Hoarder’s stockpile. Keep an eye on the living cap.' : state === 'weakness' ? 'Read the boss warning. Burning or control can stop the next emergence.' : 'Clear a garbage lane with an action, then use your remaining movement.'}</small>${button('Cycle inspection')}`;
        default: return '<small>Preview unavailable.</small>';
    }
}
function card(component) {
    const article = document.createElement('article');
    article.className = 'component';
    article.id = `component-${component.id}`;
    article.dataset.menu = component.menu;
    article.dataset.kind = component.kind;
    article.dataset.search = `${component.name} ${component.description} ${component.states.join(' ')}`.toLowerCase();
    article.innerHTML = `<div class="component-head"><h3><a href="#${article.id}">${esc(component.name)}</a></h3><p class="component-description">${esc(component.description)}</p></div><div class="demo" aria-label="${esc(component.name)} interactive preview"></div><div class="state-controls"><label for="state-${component.id}">State</label><select id="state-${component.id}" aria-label="${esc(component.name)} state">${component.states.map(state => `<option value="${state}">${esc(state.charAt(0).toUpperCase() + state.slice(1))}</option>`).join('')}</select><button type="button" class="reset-demo" aria-label="Reset ${esc(component.name)} preview" title="Reset preview">↺</button></div><details><summary>Data, source & integration</summary><p>Illustrative values. Preview actions stay local.</p><p>Preview: <code>${esc(component.previewSource)}</code></p><p>Integration reference: <code>${esc(component.integrationSource)}</code></p><p>Fields: <code>${component.dataFields.map(esc).join(' · ')}</code></p><a href="#${article.id}">Link to this component</a></details>`;
    const select = article.querySelector('select');
    const update = () => {
        article.querySelector('.demo').innerHTML = demo(component.id, select.value);
        article.querySelectorAll('[data-cycle]').forEach(button => button.addEventListener('click', () => {
            select.selectedIndex = (select.selectedIndex + 1) % component.states.length;
            update();
        }));
    };
    select.addEventListener('change', update);
    article.querySelector('.reset-demo').addEventListener('click', () => { select.selectedIndex = 0; update(); });
    update();
    return article;
}
function filter() {
    const query = search.value.trim().toLowerCase();
    let shown = 0;
    document.querySelectorAll('.component').forEach(component => {
        const visible = (menuFilter.value === 'all' || component.dataset.menu === menuFilter.value) && (kindFilter.value === 'all' || component.dataset.kind === kindFilter.value) && (!query || component.dataset.search.includes(query));
        component.hidden = !visible;
        if (visible) shown++;
    });
    document.querySelectorAll('.menu-section').forEach(section => { section.hidden = !Array.from(section.querySelectorAll('.component')).some(component => !component.hidden); });
    count.value = `${shown} component${shown === 1 ? '' : 's'}`;
    document.querySelector('#empty').hidden = shown > 0;
}
try {
    const response = await fetch('menu-atlas.json');
    if (!response.ok) throw new Error(`Inventory could not load (${response.status}).`);
    const inventory = await response.json();
    inventory.menus.forEach((menu, index) => {
        menuFilter.insertAdjacentHTML('beforeend', `<option value="${esc(menu.id)}">${esc(menu.title)}</option>`);
        const section = document.createElement('section');
        section.className = 'menu-section';
        section.id = `menu-${menu.id}`;
        const components = inventory.components.filter(component => component.menu === menu.id);
        section.innerHTML = `<div class="menu-heading"><div><span class="section-number">${String(index + 1).padStart(2, '0')} / 06</span><h2>${esc(menu.title)}</h2><p>${esc(menu.description)}</p></div></div><div class="sheet-layout"><figure class="sheet-frame"><button type="button" class="sheet-open" aria-label="Enlarge ${esc(menu.title)} concept illustration"><img src="${esc(menu.image)}" alt="Generated ${esc(menu.title.toLowerCase())} concept sheet in a navy and gold pixel tactics style" loading="${index === 0 ? 'eager' : 'lazy'}"></button><figcaption><span>Generated concept illustration · Click to enlarge</span><a href="${esc(menu.image)}" download>Download PNG ↓</a></figcaption></figure><aside class="sheet-notes"><h3>COMPONENT BREAKDOWN</h3><p>The full menu sets the direction. Try each part separately below.</p><ul>${components.map(component => `<li><a href="#component-${component.id}">${esc(component.name)}</a></li>`).join('')}</ul><p>All preview values are illustrative.</p></aside></div><div class="component-grid"></div>`;
        const componentGrid = section.querySelector('.component-grid');
        components.forEach(component => componentGrid.append(card(component)));
        section.querySelector('.sheet-open').addEventListener('click', () => {
            document.querySelector('#sheet-title').textContent = menu.title;
            const image = document.querySelector('#sheet-image');
            image.src = menu.image;
            image.alt = `${menu.title} generated concept illustration`;
            sheetDialog.showModal();
        });
        atlas.append(section);
    });
    [menuFilter, kindFilter].forEach(control => control.addEventListener('change', filter));
    search.addEventListener('input', filter);
    document.querySelector('#filters').addEventListener('reset', () => { setTimeout(filter, 0); });
    document.querySelector('#close-sheet').addEventListener('click', () => sheetDialog.close());
    sheetDialog.addEventListener('click', event => { if (event.target === sheetDialog) sheetDialog.close(); });
    filter();
    if (location.hash) requestAnimationFrame(() => document.querySelector(location.hash)?.scrollIntoView());
} catch (error) {
    atlas.innerHTML = `<p class="notice">${esc(error.message)} <a href="menu-atlas.json">Open the component inventory directly</a>.</p>`;
}
