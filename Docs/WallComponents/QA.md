# Wall components QA

Independent validation is in `Tools/test_wall_components.py` (Pillow and NumPy). Run `python3 Tools/test_wall_components.py` from the repository root after rebuilding the pack.

The checks independently reconstruct all 16 connection-mask silhouettes and compare every cap alpha pixel, including solid centers, terminal arms, L turns, T junctions and the cross. They compare actual cap edge RGBA values for every compatible facing pair, rather than accepting material tags as proof of geometry. Every flattened tile must replay from its shadow, face and cap layers.

Each of the three supplied room JSONs is replayed independently using its referenced assets and integer offsets; the result must equal its PNG. The layouts must differ, and each declared connection must meet a reciprocal neighbor. Archive paths must be safe, unique, complete, and byte-identical to the loose package files. Construction source and exported asset SHA-256 digests must match; the package inventory records each member digest and byte count. The doorway must retain substantial masonry, both jambs, and a clear central passage; its construction layers must reproduce the whole arch.

The session also snapshots 3,344 files in `completed-layers`, `map-grid-pass`, `reference-layers`, `hud-components` and `hud-reusable` before new pack generation. Their SHA-256 hashes are checked against `/tmp/wall-components-prior-hashes.json`. This local snapshot is an additional session check and is skipped when unavailable on another machine.

Final validation: all six independent checks passed on 2026-10-31. Visual review inspected the network contact sheet, layer breakdown, rectangular doorway room, L-shaped room, corridor/junction layout and arch. The revised build separates the top cap from the blue vertical face and preserves 24px southward face projection on a 64×96 canvas. The doorway now has a substantial arch, clear opening and complete three-part reconstruction. The three layouts visibly differ. Repeated material is apparent; these are stylized assembled geometry, not newly painted perspective wall designs.

The rectangle deliberately uses a native arch across a two-cell opening. Its declared west/east adapters are checked against neighboring network tags, but those adapters are visual overlaps rather than pixel-identical network sockets. The exact facing-pixel comparison applies to the 16 network caps. RGB beneath fully transparent pixels is ignored when comparing rendered replays.

These checks establish the documented cap socket contract and recipe reproducibility. They do not establish perspective consistency, a seam-free visual result, runtime collision, navigation, Unity integration, or publication. Native 128px boundary overlays and the doorway require separate placement and are not covered by the network socket contract. Human art review remains necessary at intended display sizes.
