# Character correction art brief

Status: reference acquisition blocked; no generation or visual QA claimed. Updated 2026-10-31.

## Deliverable

Five labeled designs, each with a complete full-body tactical illustration and a matching portrait: `carl`, `donut`, `katia-standard`, `katia-strong`, `mongo-grown`. These are static fan interpretations; no animation, official endorsement, or exact novel-stage reconstruction is implied.

Use readable pixel illustration with deliberate clusters, strong silhouettes and complete outlines. Each cutout needs generous transparent margins; every toe, tail tip, hair crest and feather stays inside its cell. Neutral three-quarter tactical poses. Portraits must repeat the same face, palette and costume as their full bodies. No labels, UI, scenery, glow, floor, drop shadow or overlapping silhouettes in the generated atlas. In particular, do not use prior erroneous character pictures as anatomy reference. Existing exploration sprite work may inform pixel treatment only.

## Required identity constraints

| ID | Required visual identity | Prohibited drift |
| --- | --- | --- |
| carl | Muscular adult human man, short brown hair, completely clean-shaven face, bare feet, white boxers with red hearts; equipped interpretation with a shirt, dark leather jacket and cloak | Beard, mustache, stubble, dark beard-shaped chin shading, boots, default bare torso |
| donut | Fluffy tortoiseshell Persian cat, broad flat face, compact stout body, mottled black/beige/white long fur; regal presentation | Ginger tabby stripes, long pointed muzzle, generic round shorthair |
| katia-standard | Pale human-looking adult woman in a Book 3 purple-mohawk combat presentation, dark leather clothing and black boots, rounded human ears, light wide-set eyes | Green skin, elf ears, generic long purple hairstyle; claiming this is her original human appearance |
| katia-strong | The same face, eyes, purple mohawk and pale human skin as katia-standard, transformed to an eight-foot massively muscular build; matching costume adapted to size | Marvel character anatomy/costume, green skin, unrelated face, ogre/elf traits |
| mongo-grown | Pink feathered bipedal velociraptor body with red/blue feather accents, long horizontal counterbalancing tail, powerful clawed hind legs, sickle claws, visible teeth, short feathered clawed forelimbs; black collar | Parrot body, toothless hooked bill, pterosaur/bat membranes, separate pair of fantasy back wings |

Carl gear is an equipped fan presentation, not a claim that every item coexists on a specified floor. Katia's two designs deliberately depict the same chosen Book 3 presentation at different muscular scales. Mongo's forelimb feathers may read as small wings, but the exact origin date of wing terminology is unresolved. Do not assign that event to Books 3–4 without primary text.

## Evidence and provenance

See [Katia/Mongo research](research-katia-mongo.md) for book locators and explicit evidence limits. Secondary transcription is not direct primary-text inspection.

- Primary prose target: [Penguin's authorized Book 1 sample](https://cdn.penguin.co.uk/dam-assets/books/9780241816264/9780241816264-sample.pdf), opening chapter, for Donut's Persian breed, flat face and mottled coat. Root coordinator independently verified this sample; this art agent's download was blocked.
- [Author's official book index](https://mattdinniman.com/books/) links Book 3's cover illustration at [official author-hosted cover image](https://i0.wp.com/mattdinniman.com/wp-content/uploads/2026/01/3DBooks_Style2Thin_03.png?resize=423%2C627&ssl=1). Web connector fetched the image URL but exposed only a text `<<ImageDisplayed>>` marker; no pixels available to this agent. Artist credit for this particular edition not independently verified; do not invent one.
- [Renegade official RPG page](https://dungeoncrawlercarl.renegadegamestudios.com/games) links [official RPG image](https://i.shgcdn.com/a5790550-93d7-41e9-aa7f-0464206abaa8/). Same image-pixel access limitation. Individual artist attribution not established by the fetched page.
- [Renegade official Royal Court set](https://renegadegamestudios.com/dungeon-crawler-carl-rpg-royal-court-minis-set/) and its [official product image](https://cdn11.bigcommerce.com/s-kftzvkkgjv/images/stencil/500x659/products/4702/8476/RGS_02992_Dungeon_Crawler_Carl_Miniatures_Set_1-_The_Royal_Court__86737.1779832218.png?c=1) are official adaptation reference candidates. The linked image returned a placeholder rather than inspectable pixels for this brief; visual review remains pending. Sculpt/paint artist attribution unverified.
- [Carl secondary character reference](https://www.dccdatabase.com/wiki/carl/) supports short brown hair, muscular build, six-foot-three stature and daily shaving as reported to this agent by coordinator. The user's explicit clean-shaven correction controls the art.

Original official reference downloads belong outside the game repository at `/workspace/scratch/character-references/`. They are for reference only and must not be included in redistributed art packs. At this point attempted urllib downloads failed with proxy tunnel 403; no originals were saved. Current enforced environment policy permits package-manager hosts, not these publisher domains. Do not bypass that policy.

## Generation gate and review

Before generation, actually view official book illustration pixels and official TTRPG reference pixels. Use real local `referenced_image_paths` when available; otherwise the image tool's recent-image mechanism is valid only when actual reference images are present in conversation. A text placeholder is insufficient visual evidence. Then inspect generated art for clean-shaven Carl, Persian Donut, identical pale Katia identity, and raptor Mongo before handing off extraction to Jev.

Final supported acquisition check: official-domain-restricted image search returned no results. A broader image search found a second [Renegade official product photograph](https://cdn11.bigcommerce.com/s-kftzvkkgjv/images/stencil/1280x1280/products/4702/8461/Dungeon_Crawler_Carl_-_Mini_Groups_-013__25884.1778866599.jpg?c=1), but again returned only a text placeholder and a descriptive caption, not actual image content. Captions do not substitute for viewing the illustration. Generation remains blocked pending attached references or supported publisher-domain network access.
