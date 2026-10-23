"""Regenerate the review gallery data and Markdown checklist from the feature inventory below."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
groups=[
('Readable tactical combat',[
(True,'Move and act in either order','One move and one action per crawler; End Turn explicitly advances the party.'),
(True,'Selected ability descriptions','Persistent cost, range, target and effect text, plus a full details dialog for touch and keyboard.'),
(True,'Complete ability book','Expose personal, class, unlocked and equipment actions instead of relying on a few quick slots.'),
(True,'Exact preview before committing','Show HP, Mana, tags and stat-cap changes; cancel spends nothing.'),
(True,'Enemy movement and declarations','Play movement and action events with an enemy-phase banner and original narration.'),
(True,'Impact layer above sprites','Fire, projectiles, reaction effects and floating combat text draw after units and walls.'),
(True,'Party turn state','Separate move used, action used and turn finished; enemy team follows all finished allies.'),
(True,'Scenario intent before the next round','Scenario-specific warnings display the authored threat used by C# execution. A universal intent planner remains planned.'),
(False,'Area effects and chain reactions','Shared resolver must preview all affected cells, friendly fire and bounded spread.'),
(False,'Potion cooldowns','Add readable cooldown/overuse rules with book-grounded terminology and tested balance.')]),
('Characters, shapes and progression',[
(True,'Katia chooses a form','Baseline, Bulwark, Strider and Focused presets with explicit HP/Mana/movement tradeoffs. Tactical adaptations.'),
(True,'Every crawler has a character sheet','Inspect stats, current stance, skills, equipment, party level and XP; Mordecai remains an advisor.'),
(True,'Three tactical stances','Balanced, Defensive and Mobile. These are game rules, not a canonical universal stance system.'),
(True,'Party levels and skill unlocks','Current compact demo reaches levels 1–4 and unlocks personal skills at authored thresholds.'),
(True,'Equipment changes actual stats','Weapon, armor and charm ownership, granted abilities and save persistence.'),
(True,'All eight characters have directional walking art','Four directions with idle and walking frames; base identities retained.'),
(False,'Distinct form animation sets','Author a full directional/attack set per Katia shape, with a mass/silhouette budget. Current form stats do not imply new authored sprites.'),
(True,'Five stats and allocated points','Strength, Intelligence, Constitution, Dexterity and Charisma modify real actions/stats. Three points per level per crawler; safe-room preview/confirm/cancel. Early unlock is an accelerated adaptation.'),
(True,'Individual skill practice ranks','Committed non-item ability uses train that crawler/ability at 3 and 8 uses, granting direct effect bonuses and Mana discounts. Broader training sources and race/gear cap modifiers remain planned.'),
(False,'Race and class milestone selection','Introduce prerequisite previews and save-safe choices at a deliberate campaign stage.'),
(False,'Katia momentum and engineering','Model equipped mass, Rush, bracing and carried platforms; verify timing and costs before authoring.'),
(False,'Expanded personal kits','Carl traps/improvised explosives, Donut spell progression and social abilities, Mongo companion commands; each needs resolver support and source notes.')]),
('Narrator, exploration and rewards',[
(True,'Compact original System narration','Queue committed actor/action/target and impact messages; dismiss and revisit history.'),
(True,'NEW ACHIEVEMENT notices','Five first-time milestones are saved per run; previews and reloads do not repeatedly award them.'),
(True,'Protected preparation hub','Safe-room Rest, equipment and skills access; actual HP/Mana restoration.'),
(True,'Objective journal and discoveries','Floor progress, encounter door, optional caches/notes and enemy defeats reflect game state.'),
(True,'Owned boxes and safe-room opening','Earn fixed-content achievement and victory boxes; inspect rewards and opened state. Ownership and once-only opening persist; randomized rarity and pet rewards remain planned.'),
(True,'Safe-room supply recipes','Two authored recipes display ingredients/results; shared C# validates and consumes inputs atomically. Portable crafting and specialized workbenches remain planned.'),
(False,'Audience and sponsor rewards','Visible, bounded reward rules tied to achievements and choices; avoid hidden compulsory popularity gates.'),
(False,'Companion progression','Separate Mongo/pet growth, gear and commands from crawler race/class allocation.'),
(False,'Floor clock and descent pressure','Communicate collapse risk and evacuation objectives without punishing time spent in menus.'),
(False,'Interactive environmental puzzles','Levers, doors, destructible supports, traps and discovery descriptions must affect shared state.')]),
('Book-grounded boss scenarios — playable adaptations',[
(True,'Hoarder: stockpile and Scatterers','Capped Scatterer slots, visible emergence warnings, interrupting statuses and action-cost garbage clearing. Ordinary damage also works; mechanics are adaptations.'),
(True,'Juicer: gym and flaming weight plates','Locked throw lanes can be dodged or interrupted; action-cost toppled benches intercept one throw. Original tactical adaptation.'),
(True,'Ball of Swine: cooperative Speedbump','Eight-cell rolling route, three-cell warning, carried parts, a three-part barricade and recoverable helpers. Construction consumes actions; exact rules are adaptations.'),
(True,'Scenario briefing and adaptation labels','Choose a scenario at camp, inspect its objective and invented mechanics, and return to the preserved campaign afterwards.'),
(False,'Large-unit occupancy and boss phases','All current bosses occupy one logical tile. Multi-cell occupancy, a universal phase system and general large-unit collision remain planned.')]),
('Tile authoring and delivery',[
(True,'Shared tile footprint and anchors','Use measured room-kit PNG anchors in both runtime and workshop; one 128×64 logical diamond grid.'),
(True,'Paint and erase room components','Choose an asset and layer, place or erase cells, and rotate components.'),
(True,'Four camera orientations','Rotate the map while preserving world coordinates, picking and screen-relative movement.'),
(True,'Room recipe import/export','Keep visual placements and rotation in a validated JSON authoring recipe.'),
(True,'Game-compatible tile export','Export collision/surface data for authoring or a playable room with visual placements for runtime import.'),
(True,'Play edited rooms without rebuilding','Play this room or import playable JSON. C# validates bounds, assets, layers, actors and connectivity before starting a standalone room; full visual components persist in saves. A valid import replaces the active run.'),
(False,'Procedural playable campaign','Generate connected rooms, objectives, enemy budgets and rewards through the same validated format.'),
(False,'Full Unity presentation parity','Port the browser character sheets, effects, editor and narration UI into native Unity, then run Editor/Web export checks.')])]
art=[
('forms-and-stances.png','Choose a shape','Form selection, character sheets and stance tradeoffs. Illustrative names/bonuses may differ from the tested implementation.'),
('progression-safe-room.png','Grow, equip, prepare','Concept treatment for now-playable stat allocation, separate skill practice, owned boxes and crafting. Consult the actual menus for supported numbers and recipes.'),
('combat-feedback.png','Every action has an answer','Selected-ability information, separate move/action budgets, intent, impacts and compact AI feedback. Numbers are mock data.'),
('tile-authoring.png','Build the room','Tile anchors, layers, piece rotation and camera rotation. Use the real exporter schema, not text drawn inside the concept image.'),
('boss-hoarder-concept.png','Hoarder','Book 1 scenario concept: stockpile, giant human-ish boss and Scatterer minions. The separate playable scenario adapts this concept; art is not a screenshot or exact specification.'),
('boss-juicer-concept.png','Juicer','Book 1 gym scenario concept: scaly boss and flaming weight plates. The separate playable scenario adapts this concept; art is not a screenshot or exact specification.'),
('boss-swine-concept.png','Ball of Swine','Book 1 cooperative Speedbump scenario concept with Meadow Lark helpers. The separate playable scenario adapts this concept; art is not a screenshot or exact specification.')]
data={'title':'Closer to the books. Clearer to play.','summary':'A source-linked mechanics review, seven GPT-generated concept sheets, and an implementation checklist. Checked means implemented in the browser source/build workflow; unchecked means planned. Validation evidence is reported separately, and native Unity parity is not implied. Concept images are design targets, not screenshots or exact specifications.', 'groups':[{'title':title,'items':[{'done':done,'title':title,'detail':detail} for done,title,detail in items]} for title,items in groups], 'art':[{'file':'assets/concepts/'+f,'title':title,'caption':caption} for f,title,caption in art], 'sources':[
{'title':'Publisher Book 2 sample: classes, skill training and Primal cap','url':'https://cdn.penguin.co.uk/dam-assets/books/9780241816219/9780241816219-sample.pdf'},
{'title':'Katia: mass-conserving reshaping (secondary; later spoilers on page)','url':'https://www.novelpantheon.com/novels/dungeon-crawler-carl/characters/katia'},
{'title':'Five core stats and allocation timing (secondary)','url':'https://www.dccdatabase.com/wiki/player_stats/'},
{'title':'Three points per level (secondary)','url':'https://www.dungeoncrawlercarl.nl/en/news/the-five-player-stats-explained/'},
{'title':'Hoarder (secondary)','url':'https://www.dccdatabase.com/wiki/hoarder/'},
{'title':'Juicer (secondary)','url':'https://www.dccdatabase.com/wiki/juicer/'},
{'title':'Ball of Swine (secondary)','url':'https://dungeon-crawler-carl.fandom.com/wiki/Ball_of_Swine'}]}
(root/'Web/wwwroot/mechanics-review.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
lines=['# Book fidelity and playability checklist','',data['summary'],'','The demo mixes early dungeon settings with later characters/classes. Lore examples stay within Books 1–4; linked fan pages may contain later spoilers. Form bonuses, stances, combat ranges and XP thresholds are tactical adaptations.','']
for title,items in groups:
 lines += ['## '+title,'']
 lines += [f"- [{'x' if done else ' '}] **{label}** — {detail}" for done,label,detail in items]
 lines+=['']
lines += ['## Concept gallery','']+[f'- [{title}](../Web/wwwroot/assets/concepts/{f}) — {caption}' for f,title,caption in art]
lines += ['','See [lore review](Lore-Mechanics-Review.md), [boss scenarios](Boss-Concepts.md), and [implementation plan](Mechanics-Plan.md).','']
(root/'Docs/Book-Fidelity-Checklist.md').write_text('\n'.join(lines))
(root/'Web/wwwroot/book-fidelity-checklist.md').write_text('\n'.join(lines).replace('../Web/wwwroot/','').replace('(Lore-Mechanics-Review.md)','(https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Lore-Mechanics-Review.md)').replace('(Boss-Concepts.md)','(https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Boss-Concepts.md)').replace('(Mechanics-Plan.md)','(https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Mechanics-Plan.md)'))
