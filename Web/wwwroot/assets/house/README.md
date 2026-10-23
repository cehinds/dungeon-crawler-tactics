# House menu components

Eight independent transparent PNGs, generated using the safe-room concept as
the visual reference. These illustrate services in the live house menu; they
are not collision tiles or claims about the canonical layout of the house.

Each component uses a 384 × 400 canvas and floor-tip anchor (192, 392). The
consistent scale lets the menu rearrange rooms at different viewport widths.
Use CSS state treatment for available, selected and locked rooms.

`source/rooms.png` preserves the generated 4 × 2 atlas. Rebuild components and
the downloadable kit with `python3 Tools/build_interface_assets.py` from the
repository root. `manifest.json` records each original source cell.

For procedural walkable dungeon maps, use `../room-kit/manifest.json` instead.
