# Style art pack expansion

This expansion adds 240 components to each of the three art styles: 720 new components total. Combined with the existing 120 components per style, each pack contains 360 components and the three styles contain 1,080. The new inventory has eight static collections (576 pieces across all styles) and two animation collections (144 source frames across all styles).

[`inventory.json`](inventory.json) is the authored, style-independent inventory. It defines ten collections of 24 components each:

| Collection | Type | Contents |
| --- | --- | --- |
| `arsenal` | Static | Weapons and combat tools |
| `armor` | Static | Armor, shields, and protective gear |
| `gear` | Static | Equipment and adventuring supplies |
| `settlements` | Static | Buildings and settlement details |
| `roads` | Static | Routes, crossings, and path pieces |
| `forest` | Static | Woodland terrain and props |
| `highlands` | Static | Mountain and volcanic terrain |
| `caverns` | Static | Cave terrain and underground props |
| `attacks` | Animation | Four six-frame character attack clips |
| `spells` | Animation | Four six-frame spell effect clips |

The attack clips are Carl kick, Donut cast, Katia punch, and Mongo bite. The spell clips are fire burst, frost burst, lightning strike, and healing bloom. Each source frame is one of the 240 authored components per style. The exporter derives normalized 256×256 frame PNGs, six-frame strips, and animated WebP previews for each clip. Those exports reuse the source art and are not counted again in the 720 new components.

The exporter creates a ZIP, manifest, and contact sheet for each collection, as well as a complete style ZIP. In the [art lab](../../Web/wwwroot/art-lab.html), visitors can filter by collection or category, search labels, browse 48 components at a time, and play, pause, or scrub animation previews. The gallery honors reduced-motion preferences.

These are concept-art assets. They remain separate from the existing procedural generator, which uses the production 25-room kit. They do not change runtime game or Unity Editor art and do not implement abilities. Check logical tile edges against the receiving game's grid before use, since a shared footprint or label does not guarantee seam alignment. Review animation silhouettes and registrations at the intended scale before production integration.

See the [completed validation checklist](QA.md) for counts, export checks, browser checks, and integration limits.
