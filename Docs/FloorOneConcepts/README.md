# Floor One concept art coverage

This brief tracks 36 concept-art panels in six batches of six for known visited, mentioned, and generic Floor 1 places in *Dungeon Crawler Carl*. The list is an evidence-backed selection, not a complete atlas of every room in the novel or dungeon. [coverage.json](coverage.json) is the authoritative panel order, ID list, status, visual anchor, and source index.

## Reading the coverage

`status` describes the evidence for the place or view. `visited` means the story shows the party there; `visited_sub_location` is part of a larger place; `visited_route` is a traversed route; `mentioned` and `mentioned_area` are reported or described without an established Carl visit; and `generic` is a reusable place type, not a claim that a specific named room exists. `layout: inferred` means the panel composes the described cues into an illustration, rather than documenting a measured canonical plan.

The false Tutorial Guild alley and Murder Dozer ambush are two concept views of one encounter sequence, not two separate canon locations. Tally’s play area belongs to Tally’s safe room. The Ball of Swine switch chamber, Speedbump construction area, revealed arena, and stair are sub-areas/states of one boss complex. The Scatterer territory and Hoarder’s lair are connected; the art must not imply two unrelated nests. The DMV panel combines the waiting room, curtained cots, and experience-cookie encounter rather than inventing a second cookie refuge.

Territory labels such as Goblin, Llama, Scatterer, green-slime, Rot-Sticker, troglodyte, and Scat Thug describe creatures or areas, not official town names. The Waffle House and candy-vending rest area are mentioned locations without an established Carl visit. The other guilds panel is generic; do not invent guide names or distinct occupants. The last panel is a generic safe-room bedroom/bathroom concept and does not name or locate a separate safe room.

## Art direction and limits

Use a consistent GBA-inspired pixel-art treatment and consistent materials. Camera views may vary to suit each concept, including overhead orthogonal rooms and frontal or perspective views for alleys, stairs, and encounters. Keep architectural edges square and orthogonal where visible; do not impose one camera angle across every scene. These are concept illustrations, not snap-ready tiles or playable maps. Keep panels environment-focused; tiny generic creatures or boss silhouettes may support a scene, but creature forms are not verified reference models. Named party-character designs are outside this pass. Book 2 locations and characters are also outside scope.

The source links in [coverage.json](coverage.json) support the named place, visit/mention status, and the concise visual anchors to the level stated in each source. They do not establish full dimensions, room adjacency beyond the stated links, complete floorplans, or the appearance of every architectural detail. Any such choices are art adaptation and remain clearly marked `inferred`; do not present a concept image as a canonical floor map. Generic panels should use restrained, reusable architecture and must not introduce additional named places.

## Panel count

The coverage contains exactly 36 panels in six ordered batches of six. `order` is the overall sequence; `batch` groups each consecutive set. The research base for the Floor 1 records is [Book 1–2 location research](../BookLocationTiles/research-books-1-2.json), whose stated scope is an evidence-backed working inventory rather than an exhaustive concordance.

## Delivered files and use

The approved concept set is delivered in the [ZIP package](../../Web/wwwroot/assets/floor-one-concepts/floor-one-concepts.zip). It contains all 36 full-resolution panel crops, the six source sheets, six labeled group previews, an overview, `manifest.json`, the coverage and spec files, and package hashes. The [overview](../../Web/wwwroot/assets/floor-one-concepts/previews/overview.png) and [group previews](../../Web/wwwroot/assets/floor-one-concepts/previews/) are for browsing; the individual PNGs are in [panels](../../Web/wwwroot/assets/floor-one-concepts/panels/). The [manifest](../../Web/wwwroot/assets/floor-one-concepts/manifest.json) maps each image to its coverage ID, source sheet and crop rectangle, and records dimensions, provenance, and hashes.

For local use, download and extract the ZIP, then browse `previews/overview.png` or a `previews/group-XX.png`; open a named file in `panels/` for its full-resolution concept. Keep the PNG intact as a standalone illustration. The panels have different camera views and inferred compositions, so they are references for environment design and are not seamless tiles, orthogonal map crops, or playable maps. To verify the package after extraction, compare its files with `package-manifest.json` and SHA-256 values.

Delivery status: **complete**. The package contains all 36 IDs from this coverage, six approved source sheets, and the generated previews and manifests. Its manifest states that it is static concept art with no gameplay integration.
