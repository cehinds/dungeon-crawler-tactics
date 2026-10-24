# Style art packs

The art lab presents three visual directions as separate component libraries:

| Style | Direction |
| --- | --- |
| `pocket-dungeon` | Overhead pixel art with compact silhouettes and crisp tile edges. |
| `ink-and-lanterns` | Painted gouache with warm lantern light and visible brush texture. |
| `dungeon-after-dark` | Graphic-novel art with bold ink contours and cyan, coral and yellow accents. |

Each style has 360 transparent PNG components: the existing 120-piece library and 240 new pieces. Across all three styles that is 1,080 components, including 576 new static pieces and 144 native animation frames. The styles use the same inventory so corresponding pieces can be compared. Browse and download them in the [art lab](../Web/wwwroot/art-lab.html). The authored, style-independent expansion list is [inventory.json](AssetExpansion/inventory.json); collection descriptions and counts are in the [asset expansion guide](AssetExpansion/README.md).

## New collections

Each style adds 24 pieces to each of ten collections: **arsenal**, **armor**, **gear**, **settlements**, **roads**, **forest**, **highlands**, **caverns**, **attacks**, and **spells**. The first eight collections are static illustrations (192 new pieces per style). Attacks and spells each contain four six-frame clips (48 source components per style). The clips are Carl kick, Donut cast, Katia punch, Mongo bite, fire burst, frost burst, lightning strike, and healing bloom. The shared inventory assigns frame order, playback rate, and registration anchors.

The three styles therefore contain 24 clips in all. Exported 256×256 normalized frame PNGs, six-frame strips, and animated WebP previews are derived presentation files. They reuse the source frames and do not add to the 720-piece expansion count.

The exporter writes a ZIP, manifest, and contact sheet for each collection, plus a complete ZIP per style. The art lab offers collection and category filters, text search, and a component gallery that loads 48 results at a time. Animation previews can play, pause, and scrub; playback stops when the visitor requests reduced motion.

## Source art and export contract

The component PNGs are extracted from generated transparent atlases. Extraction preserves the selected source pixels, adds transparent padding, and records source bounds, dimensions, anchors, collection, and render layer in the manifest. Animation exports use a shared scale and registration point to fit each clip's six frames into 256×256 canvases; strips and WebP previews are derived from those normalized frames.

The assets are a separate concept-art library. They do not replace the production 25-room kit, change the procedural generator's production assets, modify runtime game art, or add gameplay abilities. Labels describe images and do not define canonical characters, equipment, or mechanics. Treat the frames as motion studies until their silhouettes and registrations have had final animation review.

## Placement and alignment

Use each component's manifest anchor to align its placement point with the receiving map cell or UI position. Keep the original PNG dimensions, proportions, and transparent padding; silhouettes can extend beyond a logical tile. For tile pieces, confirm the receiving project's logical tile size and check adjoining edges at the actual camera scale. A manifest's logical footprint is an authoring hint, not proof that artwork seams line up with production tiles.

Draw the ground first, then terrain, structures, props, and actors. Depth-sort structures, props, and actors by ground contact; place effects above scenery and UI above the map. The manifest's layer and anchor values are the placement contract.

For Unity use, import the PNGs as Sprites while preserving dimensions and alpha. Keep a consistent Pixels Per Unit value for the receiving grid. Point filtering suits `pocket-dungeon`; Bilinear can suit the painted and inked styles when scaled. Review filtering, compression, tile alignment, sorting, and animation registration in the target camera before production use. Unity scene or prefab placement, interaction code, and runtime integration are separate work.

## Rebuild

```sh
python3 -m pip install -r Tools/requirements.txt
python3 Tools/build_style_packs.py --style all
python3 Tools/build_style_packs.py --style all --check
```

The exporter reads `Web/wwwroot/assets/style-packs/catalog.json` for style atlas definitions and collection metadata. Each style's `source/` directory preserves the source atlases. Where needed, reviewed `sourceBox` rectangles handle layouts that drift from equal grid cells, and `alphaIslandSeeds` select disconnected source silhouettes. The exporter checks source coverage, clipping, pixel ownership, collection contents, animation frames, and archive contents. All three expanded packs passed export validation and desktop/mobile gallery checks. See the [validation checklist](AssetExpansion/QA.md).
