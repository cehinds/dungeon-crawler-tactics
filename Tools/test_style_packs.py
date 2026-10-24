"""Extraction/packaging regression checks using small synthetic alpha fixtures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from PIL import Image

from build_style_packs import (LAYERS, PADDING, PackError, SHEETS, build_pack,
                               cell_box, claim_region, extract_cell, main,
                               isolate_alpha_islands, preview_resampling, validate_pack)


class StylePackTests(unittest.TestCase):
    def fixture(self, root):
        style = {"id": "test-pack", "title": "Test pack", "description": "Technical fixture", "assets": []}
        source = root / "test-pack/source"
        source.mkdir(parents=True)
        for sheet_name, (columns, rows) in SHEETS.items():
            sheet = Image.new("RGBA", (columns * 32, rows * 32))
            for index in range(columns * rows):
                left, top, _, _ = cell_box(sheet.size, columns, rows, index)
                # Distinct pixels and partial transparency catch lossy extraction.
                patch = Image.new("RGBA", (12, 15), ((index * 31) % 256, 120, 80, 190))
                patch.putpixel((0, 0), (10, 40, 200, 1))
                sheet.paste(patch, (left + 8, top + 7))
                layer = "ui" if sheet_name == "ui" else LAYERS[index % 6]
                style["assets"].append({"id": f"{sheet_name}-{index}", "label": f"Component {index}",
                                        "category": "fixture", "layer": layer,
                                        "sheet": sheet_name, "cell": index})
            sheet.save(source / f"{sheet_name}.png")
        return style

    def test_native_pixels_alpha_and_source_bounds_are_preserved(self):
        sheet = Image.new("RGBA", (64, 32))
        source = Image.new("RGBA", (9, 11), (13, 67, 201, 127))
        source.putpixel((0, 0), (2, 3, 4, 1))
        sheet.paste(source, (7, 8))
        sprite, bounds = extract_cell(sheet, (2, 1), 0)
        self.assertEqual(bounds, {"x": 7, "y": 8, "width": 9, "height": 11})
        self.assertEqual(sprite.size, (9 + 2 * PADDING, 11 + 2 * PADDING))
        self.assertEqual(sprite.crop((PADDING, PADDING, PADDING + 9, PADDING + 11)).tobytes(), source.tobytes())
        self.assertEqual(sprite.getpixel((0, 0)), (0, 0, 0, 0))

    def test_content_crossing_an_internal_seam_fails_with_diagnostic(self):
        sheet = Image.new("RGBA", (64, 32))
        sheet.paste(Image.new("RGBA", (10, 10), "red"), (28, 8))
        with self.assertRaisesRegex(PackError, "grid seam"):
            extract_cell(sheet, (2, 1), 0, "fixture")
        with self.assertRaisesRegex(PackError, "grid seam"):
            extract_cell(sheet, (2, 1), 1, "fixture")

    def test_empty_cell_fails(self):
        with self.assertRaisesRegex(PackError, "empty generated component"):
            extract_cell(Image.new("RGBA", (64, 32)), (2, 1), 0)

    def test_explicit_region_can_preserve_art_crossing_logical_grid(self):
        sheet = Image.new("RGBA", (96, 48))
        source = Image.new("RGBA", (20, 18), (40, 100, 230, 190))
        sheet.paste(source, (40, 12))
        sprite, bounds = extract_cell(sheet, (2, 1), 0, source_box=[34, 6, 66, 36])
        self.assertEqual(bounds, {"x": 40, "y": 12, "width": 20, "height": 18})
        self.assertEqual(sprite.crop((PADDING, PADDING, PADDING + 20, PADDING + 18)).tobytes(), source.tobytes())

    def test_overlapping_regions_and_region_clipping_are_rejected(self):
        regions = []
        claim_region(regions, "world", (0, 0, 30, 30), "first")
        with self.assertRaisesRegex(PackError, "overlaps first"):
            claim_region(regions, "world", (29, 0, 60, 30), "second")
        claim_region(regions, "world", (30, 0, 60, 30), "adjacent")
        claim_region(regions, "ui", (0, 0, 30, 30), "other-sheet")
        sheet = Image.new("RGBA", (96, 48))
        sheet.paste(Image.new("RGBA", (20, 18), "red"), (40, 12))
        with self.assertRaisesRegex(PackError, "region boundary"):
            extract_cell(sheet, (2, 1), 0, source_box=[40, 6, 66, 36])
        with self.assertRaisesRegex(PackError, "outside source image"):
            extract_cell(sheet, (2, 1), 0, source_box=[-1, 6, 66, 36])

    def test_pixel_art_previews_use_nearest_neighbor(self):
        self.assertEqual(preview_resampling({"id": "pocket-dungeon"}), Image.Resampling.NEAREST)
        self.assertEqual(preview_resampling({"id": "ink-and-lanterns"}), Image.Resampling.LANCZOS)

    def test_pack_records_reviewed_region_and_validates_it_without_grid_assumptions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            style["assets"][0]["sourceBox"] = [2, 1, 26, 28]
            manifest = build_pack(style, root)
            self.assertEqual(manifest["assets"][0]["source"]["region"], [2, 1, 26, 28])
            self.assertEqual(manifest["assets"][0]["source"]["cell"], {"column": 0, "row": 0, "index": 0})
            self.assertTrue(manifest["generation"]["explicitSourceRegions"])
            validate_pack(root / "test-pack")

    def test_overlapping_regions_with_disjoint_seeded_islands_build_and_validate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            for index, seed in ((0, [9, 8]), (1, [41, 8])):
                style["assets"][index]["sourceBox"] = [2, 1, 62, 28]
                style["assets"][index]["alphaIslandSeeds"] = [seed]
            manifest = build_pack(style, root)
            mask = manifest["assets"][0]["source"]["mask"]
            self.assertEqual(mask, {"method": "connected-alpha-islands", "threshold": 16,
                                    "connectivity": 8, "seeds": [[9, 8]], "fringePixels": 2})
            self.assertTrue(manifest["generation"]["explicitAlphaIslands"])
            validate_pack(root / "test-pack")

    def test_selecting_neighbor_or_reusing_substantial_pixels_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            for index in (0, 1):
                style["assets"][index]["sourceBox"] = [2, 1, 62, 28]
                style["assets"][index]["alphaIslandSeeds"] = [[9, 8]]
            with self.assertRaisesRegex(PackError, "selected substantial pixels overlap"):
                build_pack(style, root)

    def test_cropped_island_and_empty_seed_are_rejected(self):
        sheet = Image.new("RGBA", (64, 48))
        sheet.paste(Image.new("RGBA", (12, 12), (10, 20, 30, 200)), (8, 8))
        with self.assertRaisesRegex(PackError, "Selected alpha island is cropped"):
            isolate_alpha_islands(sheet, (9, 2, 30, 30), [[10, 10]])
        with self.assertRaisesRegex(PackError, "empty or below"):
            isolate_alpha_islands(sheet, (0, 0, 64, 48), [[0, 0]])

    def test_island_selection_preserves_original_rgba_and_only_two_pixel_faint_fringe(self):
        sheet = Image.new("RGBA", (64, 48))
        sheet.paste(Image.new("RGBA", (12, 12), (10, 20, 30, 200)), (8, 8))
        sheet.paste(Image.new("RGBA", (12, 12), (100, 120, 130, 220)), (40, 8))
        sheet.putpixel((6, 10), (55, 99, 177, 12))
        sheet.putpixel((5, 10), (44, 88, 166, 12))
        isolated = isolate_alpha_islands(sheet, (0, 0, 64, 48), [[10, 10]])
        self.assertEqual(isolated.getpixel((10, 10)), sheet.getpixel((10, 10)))
        self.assertEqual(isolated.getpixel((6, 10)), sheet.getpixel((6, 10)))
        self.assertEqual(isolated.getpixel((5, 10)), (0, 0, 0, 0))
        self.assertEqual(isolated.getpixel((41, 10)), (0, 0, 0, 0))

    def test_proportional_cell_boundaries_partition_odd_dimensions(self):
        boxes = [cell_box((101, 77), 6, 4, index) for index in range(24)]
        self.assertEqual(sum((right - left) * (bottom - top) for left, top, right, bottom in boxes), 101 * 77)
        for row in range(4):
            self.assertEqual(boxes[row * 6][0], 0)
            self.assertEqual(boxes[row * 6 + 5][2], 101)
            for column in range(5):
                self.assertEqual(boxes[row * 6 + column][2], boxes[row * 6 + column + 1][0])

    def test_pack_is_complete_reproducible_and_check_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"styles": [style]}))
            manifest = build_pack(style, root)
            directory = root / style["id"]
            self.assertEqual(len(manifest["assets"]), 36)
            self.assertEqual([layer["id"] for layer in manifest["preview"]["layers"]], list(LAYERS))
            before = {str(path.relative_to(root)): (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
                      for path in root.rglob("*") if path.is_file()}
            self.assertEqual(main(["--catalog", str(catalog), "--check"]), 0)
            after = {str(path.relative_to(root)): (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
                     for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            archive = (directory / manifest["download"]).read_bytes()
            build_pack(style, root)
            self.assertEqual((directory / manifest["download"]).read_bytes(), archive)

    def test_duplicate_cell_assignment_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            style["assets"][1]["cell"] = 0
            with self.assertRaisesRegex(PackError, "Duplicate source cell"):
                build_pack(style, root)

    def test_scene_metadata_and_available_concepts_are_packaged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            directory = root / style["id"]
            concepts = directory / "concepts"
            concepts.mkdir()
            for name, key in (("original", "concept"), ("new", "newConcept"), ("combat", "combatConcept")):
                # Solid fixture pixels are sufficient to verify lossless archive inclusion.
                Image.new("RGB", (16, 12), "navy").save(concepts / f"{name}.png")
                style[key] = f"assets/style-packs/test-pack/concepts/{name}.png"
            manifest = build_pack(style, root)
            for key in ("concept", "newConcept", "combatConcept"):
                self.assertEqual(manifest[key], style[key])
            self.assertEqual(manifest["conceptFiles"], ["concepts/combat.png", "concepts/new.png", "concepts/original.png"])
            with ZipFile(directory / manifest["download"]) as archive:
                for relative in manifest["conceptFiles"]:
                    self.assertEqual(archive.read(relative), (directory / relative).read_bytes())

    def test_component_pixel_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            manifest = build_pack(style, root)
            directory = root / style["id"]
            path = directory / manifest["assets"][0]["file"]
            with Image.open(path) as source:
                changed = source.copy()
            changed.putpixel((PADDING + 1, PADDING + 1), (255, 0, 0, 255))
            changed.save(path)
            with self.assertRaisesRegex(PackError, "differs from native source pixels"):
                validate_pack(directory)

    def test_changed_source_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            style = self.fixture(root)
            build_pack(style, root)
            directory = root / style["id"]
            with Image.open(directory / "source/world.png") as source:
                changed = source.copy()
            changed.putpixel((10, 10), (1, 2, 3, 255))
            changed.save(directory / "source/world.png")
            with self.assertRaisesRegex(PackError, "source fingerprint changed"):
                validate_pack(directory)


if __name__ == "__main__":
    unittest.main()
