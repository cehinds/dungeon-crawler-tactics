# Map grid comparison audit

Reference and implementation are both 1536 × 1024. The comparison uses the same screen coordinates, with A–F columns, rows 1–4, 256px cells and NW/NE/SW/SE 128px quadrants. The procedural scene intentionally used another layout; this audit evaluates the reference composition as the current target.

The source has three visible waterfall outlets, three horizontal floor grates, and one tall wall grate inset. The purple-haired character is described visually as the gauntlet fighter. Existing cutout masks describe visible pixels only; none prove the hidden surface behind a sprite, vine, frame, or HUD. Hidden extensions below are proposals, explicitly inferred.

## Highest priority changes

1. Restore the asymmetric room, raised perimeter walls, stepped foreground and lower floor apron.
2. Use large irregular blue masonry, pale capstones, cracks and local moss instead of repeated fine brick courses.
3. Build the left bent canal and right waterfall basin, bridge and downstream channel.
4. Restore three outlet arches, falling streams, foam rings and their surrounding bank walls.
5. Rebuild the north pipe bank, orange lamp, red controls and recessed metal panels.
6. Place the gold exit at the reference position with two external torches and warm floor spill.
7. Place each character and enemy at its reference location before tuning sprite scale and grounding.
8. Add three floor grates, the wall grate inset, damp tiles and localized gold reflections.
9. Restore cyan route tiles, yellow selected tile, red target frame/chevron and Strike bubble.
10. Preserve the mostly matching HUD while restoring the visible masonry backdrop around it.

## Acceptance method

Every checkbox is deliberately open. Render the revised composition at exactly 1536 × 1024 and compare without cropping or rescaling. Complete each quadrant criterion in comparison.json, then check seams across neighboring quadrants and cells. Use semitransparent overlays for alignment and direct side-by-side inspection for texture, silhouettes, light and negative space. A low HUD severity means broadly matching at this inspection scale, not pixel identity.

Only visible reference features can be matched directly. Extend tiles, masonry courses, water and pipe forms behind occluders from neighboring evidence; record these surfaces as inferred. Do not stretch a cutout edge or claim exact hidden details. Fully opaque HUD interiors do not require fabricated environment pixels unless later movement reveals them.

## Cell checklist

### A1 — [0, 0, 256, 256]

- [ ] **A1-NW** (high): Objective lantern and parchment over dark large masonry. Implementation: Banner matches closely; background tiny brick courses replace dark blocks. Components: objective-banner, large-wall-block. Hidden: Stone courses behind parchment are inferred from exposed margins.
- [ ] **A1-NE** (high): OPEN THE EXIT parchment and upper blue wall. Implementation: Banner close; missing irregular wall texture below. Components: objective-banner, large-wall-block. Hidden: Continue wall behind banner only as inferred substrate.
- [ ] **A1-SW** (high): Vines, left elbow pipe, dark stone water arch edge. Implementation: Flat brick field and straight canal omit pipe and arch. Components: bronze-elbow-pipe, vine-cluster, outlet-arch. Hidden: Arch jamb behind pipe needs inferred continuation.
- [ ] **A1-SE** (high): Glowing upper-left falling water, circular foam, blue pool. Implementation: Straight vertical canal has no raised outlet or circular splash. Components: waterfall-outlet, splash-ring, pool-water. Hidden: Pool beneath falling stream is inferred water texture.

### B1 — [256, 0, 256, 256]

- [ ] **B1-NW** (high): Pale vertical stone jamb beside pipes and blue upper wall. Implementation: Pale cap runs horizontally across replacement brick wall. Components: wall-capstone, large-wall-block. Hidden: No substantial hidden surface required.
- [ ] **B1-NE** (high): Twin tall bronze pipe sections and wall fixtures. Implementation: Tiny uniform brick field replaces pipe machinery. Components: vertical-pipe, pipe-collar, machinery-shadow. Hidden: Wall behind pipes inferred from adjoining blue blocks.
- [ ] **B1-SW** (high): Left chamber wall jamb, vines and damp floor transition. Implementation: Canal/floor boundary displaced left; missing raised jamb. Components: wall-jamb, floor-edge, vine-cluster. Hidden: Floor behind jamb is inferred continuation.
- [ ] **B1-SE** (high): Orange control lamp, red switches, dark metal cabinet, pipe feet. Implementation: Bird and open floor occupy machinery band. Components: control-cabinet, lamp, pipe-foot. Hidden: Stone behind cabinet inferred; fixture backs unobserved.

### C1 — [512, 0, 256, 256]

- [ ] **C1-NW** (high): Dark upper masonry, bronze pipes and vine growth. Implementation: Flat brick courses omit vertical pipe and foliage depth. Components: vertical-pipe, vine-cluster, large-wall-block. Hidden: Continue wall behind foliage as inferred stone.
- [ ] **C1-NE** (high): Blue wall blocks, narrow recessed machinery and vines. Implementation: Flat brick wall interrupted by relocated exit edge. Components: recessed-panel, vine-cluster, large-wall-block. Hidden: Panel backing behind vines inferred.
- [ ] **C1-SW** (high): Pipe elbow and machinery base over raised floor edge. Implementation: Purple fighter appears too far upper-left on open tiles. Components: pipe-base, metal-panel, floor-edge. Hidden: Floor under pipe foot inferred.
- [ ] **C1-SE** (high): Open damp stone floor; fighter health bar starts near bottom. Implementation: Blank regular floor and left edge of displaced exit. Components: floor-tile, wet-patch, health-bar. Hidden: Floor behind health bar inferred from adjoining tile.

### D1 — [768, 0, 256, 256]

- [ ] **D1-NW** (high): Blue stone exit-side pier, torch glow and door left jamb. Implementation: Exit occupies left part of cell and lacks external torch pier. Components: exit-jamb, torch-sconce, wall-pier. Hidden: Stone behind torch flame inferred.
- [ ] **D1-NE** (high): Gold exit lintel, ceiling lamp and stair recess. Implementation: Upper exit aligns differently and remainder is flat wall. Components: exit-lintel, exit-stairs, lamp. Hidden: Recess beyond visible steps remains inferred darkness.
- [ ] **D1-SW** (high): Left torch, hazard trim, exit threshold and gold spill. Implementation: Broad displaced exit floor and otherwise plain tiles. Components: torch-sconce, hazard-trim, gold-reflection. Hidden: Floor underneath spill can use inferred adjacent stone.
- [ ] **D1-SE** (high): Exit arrow grate and right jamb, warm threshold. Implementation: Exit ends earlier; crate intrudes lower-right area. Components: exit-arrow-grate, exit-jamb, gold-reflection. Hidden: Floor behind grate/door frame inferred.

### E1 — [1024, 0, 256, 256]

- [ ] **E1-NW** (high): Right exit pier, torch and dark top masonry. Implementation: Tiny brick courses and top cap replace heavy pier. Components: wall-pier, torch-sconce, large-wall-block. Hidden: Stone hidden by flame inferred from pier edges.
- [ ] **E1-NE** (high): Upper-right outlet arch and partial phase-banner overlay. Implementation: Banner matches; arch absent under it. Components: outlet-arch, waterfall-outlet, phase-banner. Hidden: Arch crown hidden by banner is inferred.
- [ ] **E1-SW** (high): Warm exit apron blending into floor, vines at wall seam. Implementation: Crate and regular dry tiles replace reflections and seam. Components: gold-reflection, floor-tile, vine-cluster. Hidden: Floor beneath crate is visible elsewhere but reconstruction inferred.
- [ ] **E1-SE** (high): Upper-right falling stream and pool bounded by blue blocks. Implementation: Solid brick wall replaces water recess. Components: waterfall-outlet, splash-ring, pool-water, basin-wall. Hidden: Water directly under splash inferred.

### F1 — [1280, 0, 256, 256]

- [ ] **F1-NW** (high): Phase banner left portion over dark wall. Implementation: Banner close; wall below is fine brick texture. Components: phase-banner, large-wall-block. Hidden: Wall behind opaque banner inferred.
- [ ] **F1-NE** (high): Phase banner right portion with round count. Implementation: Banner close; upper boundary otherwise flat. Components: phase-banner, large-wall-block. Hidden: Banner-hidden masonry inferred.
- [ ] **F1-SW** (high): Right basin wall, vines and bronze elbow pipe. Implementation: Flat blue brick field omits arch-side wall depth. Components: basin-wall, vine-cluster, bronze-elbow-pipe. Hidden: Wall behind elbow inferred.
- [ ] **F1-SE** (high): Large elbow pipe and blue block column. Implementation: Featureless small brick courses replace pipe/column. Components: bronze-elbow-pipe, wall-column. Hidden: Column behind pipe inferred.

### A2 — [0, 256, 256, 256]

- [ ] **A2-NW** (high): Blue capstones over left crate, wall and canal edge. Implementation: Straight canal with no inset wall/crate. Components: wall-capstone, crate, canal-edge. Hidden: Crate-hidden wall inferred from side blocks.
- [ ] **A2-NE** (high): Crate right edge, vine curtain and left canal bend. Implementation: Open floor and cat shifted into this region. Components: crate, vine-cluster, bent-canal. Hidden: Blue stone beneath vine curtain inferred.
- [ ] **A2-SW** (high): Left vertical wall face, moss and tall inset grate top. Implementation: Small bricks continue beside straight canal. Components: large-wall-block, moss, tall-wall-grate. Hidden: Masonry behind grate frame inferred.
- [ ] **A2-SE** (high): Bright winding canal with dark blue border stones. Implementation: Plain floor and selected rat replace water bend. Components: canal-water, canal-edge, foam. Hidden: Rat-hidden tile in implementation irrelevant to reference.

### B2 — [256, 256, 256, 256]

- [ ] **B2-NW** (high): Chamber jamb, pipe edge and wet floor near cat. Implementation: Bird/cat arrangement shifted and floor dry. Components: wall-jamb, wet-floor. Hidden: No substantial hidden surface required.
- [ ] **B2-NE** (high): Crowned cat on cyan tile with green health bar. Implementation: Red barrel occupies floor to right of shifted cat. Components: cat-sprite, cyan-selection, health-bar. Hidden: Selected tile beneath cat inferred stone.
- [ ] **B2-SW** (high): Bronze pipe elbow and blue wall over canal bank. Implementation: Selected rat and open floor replace bank. Components: bronze-elbow-pipe, bank-wall, vine-cluster. Hidden: Wall behind elbow inferred.
- [ ] **B2-SE** (high): Carl upper body and pack; green bar above yellow tile. Implementation: Plain floor and rat tail replace Carl position. Components: carl-sprite, health-bar, yellow-selection. Hidden: Tile beneath Carl inferred from tile edges.

### C2 — [512, 256, 256, 256]

- [ ] **C2-NW** (high): Purple-haired gauntlet fighter over damp blue tiles. Implementation: Open floor and rat shifted into fighter position. Components: fighter-sprite, damp-tile. Hidden: Tiles beneath fighter inferred.
- [ ] **C2-NE** (high): Fighter right gauntlet, clear central floor seams. Implementation: Rat sprite and health bar occupy central tiles. Components: fighter-sprite, floor-tile. Hidden: Floor behind gauntlet inferred from neighboring seams.
- [ ] **C2-SW** (high): Dark blue wet tile then cyan route tile lower edge. Implementation: Plain regular tiles replace wet patch and route. Components: wet-patch, cyan-route-tile. Hidden: Underlying route tile stone inferred.
- [ ] **C2-SE** (high): Strike bubble pointer, red chevron and target health bar. Implementation: Carl upper body occupies intended target approach. Components: strike-bubble, target-chevron, health-bar. Hidden: Floor behind opaque bubble inferred.

### D2 — [768, 256, 256, 256]

- [ ] **D2-NW** (high): Red bird tail/wings and damp floor. Implementation: Plain tile field above displaced rat. Components: bird-sprite, wet-floor. Hidden: Floor under wings inferred.
- [ ] **D2-NE** (high): Bird body, talons, green health bar and gold-lit floor. Implementation: Plain floor and crate replace bird location. Components: bird-sprite, health-bar, gold-reflection. Hidden: Tile seams beneath bird inferred.
- [ ] **D2-SW** (high): Strike 2 Mana bubble over dark floor and gold flecks. Implementation: Rat and Carl route area replace bubble. Components: strike-bubble, gold-reflection, floor-tile. Hidden: Bubble-hidden floor is inferred, text remains visible-only.
- [ ] **D2-SE** (high): Warm/wet floor; rat at far-right edge with red health bar. Implementation: Crate sits where floor reflection should continue. Components: wet-patch, gold-reflection, rat-sprite. Hidden: Rat-hidden tile inferred.

### E2 — [1024, 256, 256, 256]

- [ ] **E2-NW** (high): Floor grate left edge and stone walkway. Implementation: Open dry floor and wall edge replace grate. Components: floor-grate, floor-tile. Hidden: Dark grate interior inferred between visible bars.
- [ ] **E2-NE** (high): Upper-right canal bottom, wall lip and side crate. Implementation: Brick field replaces canal; extra barrel appears below. Components: canal-water, wall-capstone, crate. Hidden: Water behind bank wall inferred only within basin.
- [ ] **E2-SW** (high): Rat with glowing red eye and curved pink tail. Implementation: Extra barrel and small bricks occupy rat region. Components: rat-sprite, health-bar, floor-tile. Hidden: Tile under rat inferred.
- [ ] **E2-SE** (high): Blue wall dividing playfield from right basin, vine cracks. Implementation: Continuous small-brick wall lacks raised bank. Components: bank-wall, vine-cluster. Hidden: Stone behind vines inferred.

### F2 — [1280, 256, 256, 256]

- [ ] **F2-NW** (high): Wood crate beside blue pier and vertical side pipes. Implementation: Small brick field without crate or side pipe. Components: crate, wall-pier, vertical-pipe. Hidden: Wall behind crate inferred.
- [ ] **F2-NE** (high): Rightmost tall bronze pipe and wall recess. Implementation: Small flat brick courses replace metal and recess. Components: vertical-pipe, pipe-collar, wall-recess. Hidden: Pipe rear faces not observable; infer only needed silhouette fill.
- [ ] **F2-SW** (high): Lower small crate over pipe outlet basin wall. Implementation: Small brick field replaces crate/outlet staging. Components: small-crate, outlet-arch, basin-wall. Hidden: Wall under crate inferred.
- [ ] **F2-SE** (high): Pipe column continuing down right edge. Implementation: Flat brick field omits column silhouette. Components: vertical-pipe, pipe-collar. Hidden: Rear pipe surface inferred.

### A3 — [0, 512, 256, 256]

- [ ] **A3-NW** (high): Inset tall grate and bronze vertical pipe in left wall. Implementation: Straight canal and blue brick strip omit inset. Components: tall-wall-grate, vertical-pipe, large-wall-block. Hidden: Dark inset depth inferred between bars.
- [ ] **A3-NE** (high): Canal lower bend capstones, mossy inner wall. Implementation: Open tiles replace bent water/wall enclosure. Components: wall-capstone, canal-water, moss. Hidden: Moss-covered stone inferred.
- [ ] **A3-SW** (high): Dark lower-left wall blocks and rising vines. Implementation: Horizontal small-brick wall replaces dimensional masonry. Components: large-wall-block, vine-cluster. Hidden: Stone behind leaves inferred.
- [ ] **A3-SE** (high): Foreground capstones and blue faces above portraits. Implementation: Flat small-brick field replaces raised foreground edge. Components: wall-capstone, foreground-wall. Hidden: Portrait-hidden lower wall inferred.

### B3 — [256, 512, 256, 256]

- [ ] **B3-NW** (high): Left floor grate and vertical pipe beside floor. Implementation: Open dry floor lacks grate and chamber edge. Components: floor-grate, vertical-pipe, floor-tile. Hidden: Grate recess inferred; floor under pipe inferred.
- [ ] **B3-NE** (high): Carl feet on yellow tile and cyan path beginning. Implementation: Cyan lower exit begins beneath otherwise plain floor. Components: carl-sprite, yellow-selection, cyan-route-tile. Hidden: Tile beneath feet inferred.
- [ ] **B3-SW** (high): Foreground blue wall course and pipe ending. Implementation: Blank dark void plus brick strip replaces tall front wall. Components: foreground-wall, pipe-foot, wall-capstone. Hidden: Hidden lower wall behind portraits inferred.
- [ ] **B3-SE** (high): Stepped front wall and crate at narrow floor apron. Implementation: Blank void and displaced cyan exit replace apron. Components: foreground-wall, crate, floor-apron. Hidden: Floor hidden by crate inferred.

### C3 — [512, 512, 256, 256]

- [ ] **C3-NW** (high): Cyan route continues toward red-framed rat. Implementation: Lower cyan exit and empty floor replace route. Components: cyan-route-tile, red-target-frame, rat-sprite. Hidden: Tile underneath rat inferred.
- [ ] **C3-NE** (high): Selected rat, red frame, adjacent wet floor. Implementation: Lower exit and regular tile field replace target. Components: rat-sprite, red-target-frame, wet-patch. Hidden: Floor behind selected rat inferred.
- [ ] **C3-SW** (high): Wet floor tile and front wall step near grate. Implementation: Dark empty region replaces apron. Components: wet-patch, foreground-wall, floor-apron. Hidden: Front stone behind opaque UI inferred.
- [ ] **C3-SE** (high): Floor grate, gray-blue apron and pale step stones. Implementation: Open dry floor ending in blank void replaces grate/steps. Components: floor-grate, floor-apron, wall-capstone. Hidden: Grate darkness inferred between bars.

### D3 — [768, 512, 256, 256]

- [ ] **D3-NW** (high): Rat left edge and red bar beside wet tiles and floor-grate edge. Implementation: Plain floor beneath relocated actors. Components: rat-sprite, health-bar, floor-grate, wet-patch. Hidden: Tile behind rat inferred.
- [ ] **D3-NE** (high): Red fire barrel, gold flecks and damp floor. Implementation: Dry tile field without barrel at source location. Components: explosive-barrel, gold-reflection, wet-patch. Hidden: Floor beneath barrel inferred from tile perimeter.
- [ ] **D3-SW** (high): Gold-flecked wet apron and irregular foreground step. Implementation: Dark void and horizontal small-brick wall replace apron. Components: gold-reflection, floor-apron, foreground-wall. Hidden: Substrate behind reflections inferred stone.
- [ ] **D3-SE** (high): Vines around pale foreground capstones and tall blue wall. Implementation: Small horizontal bricks replace height changes. Components: vine-cluster, wall-capstone, foreground-wall. Hidden: Stone beneath foliage inferred.

### E3 — [1024, 512, 256, 256]

- [ ] **E3-NW** (high): Right floor wet tile and raised bank beside lower basin. Implementation: Small bricks replace bank and water boundary. Components: wet-patch, bank-wall, basin-water. Hidden: Wall/water beneath lip inferred.
- [ ] **E3-NE** (high): Lower-right waterfall, white splash and bright basin. Implementation: Small brick field replaces waterfall and basin. Components: waterfall-outlet, splash-ring, basin-water. Hidden: Water beneath stream inferred.
- [ ] **E3-SW** (high): Raised blue wall, bridge approach and bronze supports. Implementation: Small brick field replaces wall/bridge structure. Components: foreground-wall, bridge, bronze-support. Hidden: Back faces of support inferred.
- [ ] **E3-SE** (high): Wooden bridge across blue water with pipe framing. Implementation: Flat brick field omits bridge and channel. Components: bridge, canal-water, bronze-support. Hidden: Water below bridge inferred, never copied visible-source claim.

### F3 — [1280, 512, 256, 256]

- [ ] **F3-NW** (high): Lower basin right wall, vines and right pipe edge. Implementation: Small brick field replaces enclosing wall and pipe. Components: basin-wall, vine-cluster, vertical-pipe. Hidden: Wall behind foliage inferred.
- [ ] **F3-NE** (high): Right wall dark blocks with pipe highlights. Implementation: Small brick field lacks large stone and pipe. Components: large-wall-block, vertical-pipe. Hidden: Pipe rear face inferred.
- [ ] **F3-SW** (high): Downstream canal, bronze elbow and foliage curtain. Implementation: Small brick field over upper area, dark void below. Components: canal-water, bronze-elbow-pipe, vine-cluster. Hidden: Water beneath pipe inferred.
- [ ] **F3-SE** (high): Heavy outer wall with trailing bright green vines. Implementation: Dark void replaces wall/vines. Components: outer-wall, vine-cluster. Hidden: Stone behind trailing leaves inferred.

### A4 — [0, 768, 256, 256]

- [ ] **A4-NW** (high): Carl and cat portrait upper portions with gold frames. Implementation: Portrait placement and scale close. Components: party-portrait, gold-frame. Hidden: Background behind portraits inferred dark wall.
- [ ] **A4-NE** (high): Cat portrait and dark stone backdrop. Implementation: Portrait close; backdrop is empty dark fill. Components: party-portrait, dark-wall-backdrop. Hidden: Opaque portrait backs need no visible reconstruction.
- [ ] **A4-SW** (low): Carl portrait, gold HUD edge and dark panel. Implementation: HUD close; lower margin is flat dark fill. Components: hud-panel, carl-portrait, dark-wall-backdrop. Hidden: Panel-hidden environment inferred only outside panel.
- [ ] **A4-SE** (low): Name, HP/Mana labels and bars in dark panel. Implementation: HUD close; verify bar lengths/text at pixel review. Components: hud-status, hp-bar, mana-bar. Hidden: No hidden surface reconstruction required inside authored HUD.

### B4 — [256, 768, 256, 256]

- [ ] **B4-NW** (high): Purple fighter and bird portraits above gold HUD rule. Implementation: Portraits close; surrounding foreground wall absent. Components: party-portrait, foreground-wall. Hidden: Wall behind portraits inferred.
- [ ] **B4-NE** (high): Bird portrait and blue front wall/crate behind it. Implementation: Portrait close; background empty dark fill. Components: party-portrait, foreground-wall, crate. Hidden: Crate/wall covered by portrait inferred only at exposed edges.
- [ ] **B4-SW** (low): HP/Mana bar ends, boot icon and 4 Move indicator. Implementation: HUD close with matching layout. Components: hud-status, boot-icon, move-count. Hidden: No hidden surface reconstruction required.
- [ ] **B4-SE** (low): Boot/Move count right edge and glowing Move action. Implementation: HUD close; bottom backdrop flatter than source. Components: move-action, gold-glow, dark-wall-backdrop. Hidden: Environment behind HUD is inferred.

### C4 — [512, 768, 256, 256]

- [ ] **C4-NW** (high): Front wall capstone steps and pale floor apron above HUD. Implementation: Empty dark gap replaces structural stone band. Components: foreground-wall, wall-capstone, floor-apron. Hidden: Stone lower continuation behind HUD inferred.
- [ ] **C4-NE** (high): Blue foreground wall descending beside center apron. Implementation: Empty dark gap replaces blocks. Components: foreground-wall, large-wall-block. Hidden: HUD-hidden wall continuation inferred.
- [ ] **C4-SW** (low): Move and Strike gold action buttons. Implementation: Buttons closely aligned. Components: move-action, strike-action. Hidden: No hidden surface reconstruction required.
- [ ] **C4-SE** (low): Strike and Skills buttons with sword/purple skill icon. Implementation: Buttons close to source. Components: strike-action, skills-action. Hidden: No hidden surface reconstruction required.

### D4 — [768, 768, 256, 256]

- [ ] **D4-NW** (high): Center floor apron and foreground step stones. Implementation: Dark gap replaces apron and large stone courses. Components: floor-apron, wall-capstone, foreground-wall. Hidden: Lower wall behind HUD inferred.
- [ ] **D4-NE** (high): High foreground blue wall with gold-lit upper blocks. Implementation: Dark gap replaces wall face. Components: foreground-wall, wall-capstone. Hidden: HUD-hidden wall inferred from visible course.
- [ ] **D4-SW** (low): Skills button and Items bag action. Implementation: HUD buttons closely aligned. Components: skills-action, items-action. Hidden: No hidden surface reconstruction required.
- [ ] **D4-SE** (low): Items bag and left edge of rat damage preview. Implementation: HUD close; compare icon edges only. Components: items-action, damage-preview. Hidden: No hidden surface reconstruction required.

### E4 — [1024, 768, 256, 256]

- [ ] **E4-NW** (high): High blue foreground wall and bronze bridge support. Implementation: Empty dark band replaces raised wall. Components: foreground-wall, bronze-support. Hidden: Lower wall behind HUD inferred.
- [ ] **E4-NE** (high): Water channel below bridge and right pipe frame. Implementation: Empty dark band replaces water/metal. Components: canal-water, bronze-support. Hidden: Water beyond HUD occlusion inferred.
- [ ] **E4-SW** (low): Rat damage preview with Rat and 12 damage text. Implementation: HUD close to source. Components: damage-preview, rat-icon. Hidden: No hidden surface reconstruction required.
- [ ] **E4-SE** (low): Right end of damage panel and End Carl’s turn left edge. Implementation: HUD close to source. Components: damage-preview, end-turn-button. Hidden: No hidden surface reconstruction required.

### F4 — [1280, 768, 256, 256]

- [ ] **F4-NW** (high): Right canal edge, dark blue stone and vine curtain. Implementation: Empty dark band replaces scene detail. Components: canal-edge, outer-wall, vine-cluster. Hidden: Lower vine/stone continuation behind HUD inferred.
- [ ] **F4-NE** (high): Far-right dark foreground masonry and foliage. Implementation: Empty dark band replaces masonry. Components: outer-wall, vine-cluster. Hidden: HUD-hidden stone inferred.
- [ ] **F4-SW** (low): End Carl’s turn button label and gold border. Implementation: Button closely matches source placement. Components: end-turn-button. Hidden: No hidden surface reconstruction required.
- [ ] **F4-SE** (low): End-turn arrow, outer gold panel corner and dark masonry below. Implementation: HUD close; lower backdrop flat and lacks stone texture. Components: end-turn-button, hud-panel, dark-wall-backdrop. Hidden: Stone below and behind panel inferred from exposed edges.


## Component coverage after expansion

The inventory now contains 24 base modules and 120 authored expansion designs, plus 52 derived views (196 exported modules total). Derived views are not counted as new authored designs. `component-coverage.json` maps every one of the 96 quadrants and 256 semantic need instances to actual generated IDs and same-coordinate existing source layer IDs. The mapping records 58 available motif instances and 198 partial instances; the latter includes 53 UI and 12 actor instances excluded from the environment expansion. “Available” means a reusable motif exists, not that the reference composition is complete.

Specialized machine assemblies, exact doorway architecture, bank/cap end joins, bridge/support interfaces, water silhouettes and full scene placement remain open. Source IDs prove only visible fragments. No runtime integration or quadrant visual acceptance is claimed: all 96 visual acceptance checks remain unchecked.
