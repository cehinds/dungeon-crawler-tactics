# Style art packs

Three visual directions are available as separate component packs:

| Style | Direction |
| --- | --- |
| `pocket-dungeon` | Overhead pixel art with compact silhouettes and crisp tile edges. |
| `ink-and-lanterns` | Painted gouache with warm lantern light and visible brush texture. |
| `dungeon-after-dark` | Graphic-novel art with bold ink contours and cyan, coral and yellow accents. |

Each style contains 84 individually labeled transparent PNG components. The original 36-piece inventory (24 world pieces and 12 UI pieces) is joined by 48 expansion pieces, for 252 components across all three styles. The styles share a component inventory so their pieces can be compared or used as alternatives. Open the [art lab](../Web/wwwroot/art-lab.html) to preview the pieces and download each pack ZIP; browse by style and component label. The pack files and their source material are kept with the web assets in `Web/wwwroot/assets/`.

The first expansion adds four groups of six: environment pieces (wood-floor, wall-corner, stone-pillar, broken-barricade, spike-trap, pressure-plate); house and activity props (safe-bed, crafting-bench, alchemy-table, training-dummy, social-screen, armchair); creature concepts (rat-scout, rat-guard, slime, cave-bat, spider-drone, mimic); and effects (fire-patch, lightning-arc, ice-burst, poison-cloud, healing-ring, bomb-burst). The supplies expansion adds four more groups of six: equipment (iron-sword, round-shield, iron-helmet, leather-armor, gem-ring, arcane-wand); loot (health-potion, mana-potion, antidote, gold-pouch, dungeon-key, reward-box); connections (iron-gate-open, iron-gate-closed, floor-hatch-open, floor-hatch-closed, wood-ladder, rope-bridge); and interactables (lever-off, lever-on, wall-switch-off, wall-switch-on, campfire, blacksmith-anvil). These are static illustrative PNG components. Their labels describe art subjects and do not establish canonical items, characters, or gameplay.

## Concept art and component art

The concept images show the intended mood and how pieces might work together. They are flattened illustrations, not layered source documents. Individual components were reconstructed from the concepts with image generation, then mechanically sliced into transparent PNGs. The resulting PNGs are useful components, but they do not preserve editable paint layers from the concept image. Keep the original concepts and generated source images alongside the extracted assets when revising a style.

Each component is a static art element. The pack does not provide frame-by-frame animation, a complete game scene, or a finished runtime implementation. Movement, animation, interaction, collision, and live text need to be supplied by the game.

The delivery contains **252 component PNGs**, **21 full-canvas layer PNGs**, and
**six new scene concepts**. Each style ZIP contains its 84 components, seven
layers, composed preview, labeled contact sheet, manifest, README, original
style study and two new scene concepts. The new scenes are Clockwork Market /
Market Ambush, Lantern Archive / Defend the Lantern, and Backstage Access /
The Crusher Live. These are proposed original scenarios, not implemented levels
or claims about named book events.

The layer PNGs share a 1200×900 canvas and composite in manifest order. They
rebuild the component demonstration, not the original flattened illustration.
Labels stay outside the source art: filenames, contact sheets and manifest
records identify every piece without baking text into a usable sprite.

The art lab separates the two 24-piece expansions into **Rooms & creatures**
and **New additions** filters. The latter shows the supplies components. The
seven compositing layers and three concept images per style are unchanged. Each
style's full-pack contact sheet covers all 84 components.

## Rebuild and validate

```sh
python3 -m pip install -r Tools/requirements.txt
python3 Tools/build_style_packs.py --style all
python3 Tools/build_style_packs.py --style all --check
python3 -m unittest discover -s Tools -p 'test_style_packs.py'
```

The editable inventory is `Web/wwwroot/assets/style-packs/catalog.json`.
Each style's `source/` directory preserves its generated world/UI atlases.
Reviewed `sourceBox` rectangles account for generated layouts that drift from
equal cells. Where two transparent silhouettes have overlapping bounding boxes,
`alphaIslandSeeds` separate their disconnected alpha components; retained pixels
keep their original RGBA values. The manifest records the source fingerprint,
logical slot, crop, mask, PNG dimensions, placement anchor and draw layer.
Extraction validates clipping, ownership, transparency and archive contents.

## Placement and draw order

Use each pack's manifest for its component label, file, layer, dimensions, and crop anchor. Anchors refer to the component's placement point inside its PNG; align that point with the target grid cell or UI position. Preserve the authored transparent padding and image proportions. Component PNG dimensions may extend beyond one logical map tile.

For a map, draw the ground first, followed by terrain, structures, props, and actors. Depth-sort structures, props, and actors by their ground contact so nearer pieces cover farther ones. Draw effects above the actors and scenery. Place UI above the map. Use the manifest's layer and anchor values as the placement contract; the suggested order is ground, terrain, structures, props, actors, effects, then UI.

## Unity import

Import each PNG as a Sprite (2D and UI), preserving its pixel dimensions and transparency. Use a consistent Pixels Per Unit value across a pack and the project's chosen logical tile scale; the final PPU and tile measurements should be taken from the pack manifest or the receiving project's map grid. Do not resize sprites to force every silhouette into one tile. Set Point filtering for `pocket-dungeon` to keep pixels crisp. Use Bilinear filtering for the painted `ink-and-lanterns` and inked `dungeon-after-dark` artwork when smooth scaling is needed. Choose compression only after checking that it does not damage fine outlines, gradients, or alpha edges.

The components are art inputs for a renderer. Unity still needs scene or prefab placement, sorting configuration, animation and interaction code, and visual review at the intended camera scale before the pieces can be treated as an integrated game scene.

## Delivery checks

- [x] All three expanded packs contain 84 labeled component PNGs, seven layers
  and three concept images; archives and retained source pixels validate.
- [x] Twenty-one extraction and packaging tests pass, including legacy 36-piece
  packs, optional expansion sheets, alpha ownership and reproducible archives.
- [x] Chromium at 1440×900 and 390×844 verifies all three styles, 84-piece totals,
  both 24-piece filters, Equipment/Loot filters, Mana potion search and PNG downloads,
  image decoding, and no horizontal overflow or JavaScript errors.
- [ ] Runtime animation, directional sprite sets, final tile-seam calibration
  and Unity Editor integration remain future production work.

The current checks use the local static gallery. Hosting deployment is verified
separately through GitHub Actions. The earlier delivery screenshots show the
original 36-piece gallery; the expanded gallery includes the new-additions filter.
