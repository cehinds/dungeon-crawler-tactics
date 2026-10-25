"""Focused source-to-export integration tests; all artifacts live in temp dirs."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from PIL import Image, ImageDraw

import build_book_tiles as tiles


class BookTileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.docs = Path(self.temp.name) / "Docs"
        self.output = Path(self.temp.name) / "Web"
        self.docs.mkdir()
        self.styles = [
            {"id": "pocket-dungeon", "title": "Pocket", "projection": "orthogonal", "tileWidth": 128, "tileHeight": 128},
            {"id": "ink-and-lanterns", "title": "Ink", "projection": "isometric", "tileWidth": 128, "tileHeight": 64},
        ]
        self.kit = {"id": "test-kit", "title": "Fixture", "books": [1], "columns": 6, "rows": 4,
                    "assets": [{"id": f"piece-{cell}", "label": f"Piece {cell}", "cell": cell,
                                "role": "ground" if cell < 6 else "wall" if cell < 12 else "prop",
                                "layer": "ground" if cell < 6 else "structures", "renderWidth": 96}
                               for cell in range(24)]}
        self.inventory = {"title": "Fixture tiles", "styles": self.styles,
                          "books": [{"id": 1, "title": "Book"}], "kits": [self.kit]}
        self.write_json(self.docs / "inventory.json", self.inventory)
        self.write_json(self.docs / "coverage.json", {
            "locations": [{"id": "place", "name": "Place", "books": [1], "kitIds": ["test-kit"]}],
            "coverageGaps": ["Fixture is intentionally small"],
        })
        for style in self.styles:
            sheet = Image.new("RGBA", (1536, 1024))
            draw = ImageDraw.Draw(sheet)
            reviews = []
            for cell in range(24):
                x, y = cell % 6 * 256, cell // 6 * 256
                # Vary visible color and shape. Keep true-alpha gutters in every cell.
                draw.rectangle((x + 70, y + 35, x + 100 + cell, y + 150 + cell),
                               fill=(30 + cell * 8, 50 + cell, 200 - cell * 4, 255))
                draw.point((x + 69, y + 36), fill=(180, 200, 220, 8))
                reviews.append({"cell": cell, "sourceBox": [x + 60, y + 20, x + 150, y + 200],
                                "alphaIslandSeeds": [[x + 75, y + 40]]})
            source = self.docs / "sources" / style["id"] / "test-kit.png"
            source.parent.mkdir(parents=True)
            sheet.save(source)
            self.write_json(self.docs / "crops" / f"{style['id']}.json",
                            {"style": style["id"], "sheets": {"test-kit": reviews}})

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def run_export(self, style="pocket-dungeon", check=False, catalog=False, kit=None):
        return tiles.run(style, check, catalog, self.docs, self.output, kit)

    def directory(self, style="pocket-dungeon"):
        return self.output / style / "test-kit"

    def snapshot(self, path):
        return {p.relative_to(path).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in path.rglob("*") if p.is_file()}

    def test_build_reconstructs_24_pngs_and_read_only_check(self):
        sources_before = self.snapshot(self.docs)
        self.assertEqual(self.run_export(), 24)
        manifest = tiles.read_json(self.directory() / "manifest.json")
        self.assertEqual(manifest["grid"]["anchor"], {"x": 128, "y": 192})
        self.assertEqual(len(manifest["assets"]), 24)
        ground = manifest["assets"][0]
        wall = manifest["assets"][6]
        self.assertEqual((ground["derived"]["width"], ground["derived"]["height"]), (128, 128))
        self.assertEqual(ground["derived"]["offset"], {"x": 64, "y": 128})
        # Tall walls scale proportionately to the height cap, never stretching.
        self.assertLessEqual(wall["derived"]["width"], 128)
        self.assertLessEqual(wall["derived"]["height"], 184)
        self.assertEqual(wall["derived"]["resampling"], "nearest")
        self.assertEqual(ground["source"]["alphaMask"]["method"], "connected-alpha-islands")
        for asset in manifest["assets"]:
            with Image.open(self.directory() / asset["file"]) as image:
                self.assertEqual(image.size, (256, 256))
                self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
        before = self.snapshot(self.output)
        self.assertEqual(self.run_export(check=True), 24)
        self.assertEqual(before, self.snapshot(self.output))
        self.assertEqual(sources_before, self.snapshot(self.docs))

    def test_isometric_ground_and_reviewed_anchor(self):
        crop = self.docs / "crops/ink-and-lanterns.json"
        document = tiles.read_json(crop)
        document["sheets"]["test-kit"][12]["anchor"] = {"x": 0.25, "y": 0.75}
        self.write_json(crop, document)
        self.run_export("ink-and-lanterns")
        manifest = tiles.read_json(self.directory("ink-and-lanterns") / "manifest.json")
        self.assertEqual(manifest["assets"][0]["derived"]["height"], 64)
        self.assertEqual(manifest["assets"][0]["derived"]["offset"], {"x": 64, "y": 160})
        prop = manifest["assets"][12]
        self.assertEqual(prop["source"]["normalizedAnchor"], {"x": 0.25, "y": 0.75})
        self.assertEqual(prop["derived"]["resampling"], "lanczos")
        self.assertEqual(prop["derived"]["offset"]["x"], round(128 - prop["derived"]["width"] * .25))

    def test_native_square_styles_and_mating(self):
        image = Image.new("RGBA", (100,100), "red")
        for style in self.styles + [{"id":"dungeon-after-dark","projection":"orthogonal","tileWidth":128,"tileHeight":128}]:
            style = dict(style, projection="orthogonal", tileWidth=128,tileHeight=128)
            _, derived, _ = tiles.normalize(image, {"id":"floor","role":"ground","cell":0,"squareLayout":"floor"}, style,
                                           registration={"kind":"invalid-legacy"})
            self.assertEqual((derived["width"],derived["height"]), (128,128))
            points = derived["placement"]["points"]
            self.assertEqual(points, [[64,128],[192,128],[192,256],[64,256]])
            self.assertEqual(points[1], [points[0][0]+128,points[0][1]])
            self.assertEqual(points[2], [points[3][0]+128,points[3][1]])

    def test_native_wall_and_frontal_door_contacts(self):
        image = Image.new("RGBA", (100,100), "red")
        for layout,width,height,axis,expected in (
                ("north-wall",128,64,"x",[[64,192],[192,192]]),
                ("west-wall",32,128,"y",[[128,128],[128,256]]),
                ("north-wall",128,96,"x",[[64,192],[192,192]])):
            _,derived,_ = tiles.normalize(image, {"id":"architecture","role":"door" if height==96 else "wall",
                                                   "squareLayout":layout,"renderWidth":width,"renderHeight":height}, self.styles[0])
            self.assertEqual(derived["placement"], {"kind":"wall","axis":axis,"points":expected})
        with self.assertRaisesRegex(tiles.PackError, "clip normalized canvas"):
            tiles.normalize(image, {"id":"oversize","role":"wall","squareLayout":"west-wall","renderWidth":32,"renderHeight":160}, self.styles[0])

    def test_native_full_floor_rejects_diamond_and_projection(self):
        image = Image.new("RGBA", (100,100))
        ImageDraw.Draw(image).polygon([(50,0),(99,50),(50,99),(0,50)], fill="red")
        asset = {"id":"diamond","role":"ground","cell":0,"squareLayout":"floor"}
        with self.assertRaisesRegex(tiles.PackError,"not an angled diamond"):
            tiles.normalize(image, asset, self.styles[0])
        with self.assertRaisesRegex(tiles.PackError,"orthogonal"):
            tiles.normalize(Image.new("RGBA",(100,100),"red"), asset, self.styles[1])

    def test_registered_review_roundtrips_provenance_and_placement(self):
        crop = self.docs / "crops/pocket-dungeon.json"
        document = tiles.read_json(crop)
        registration = {"kind":"floor", "points":[[0,0],[64,0],[64,180],[0,180]]}
        document["sheets"]["test-kit"][0]["registration"] = registration
        self.write_json(crop, document)
        self.run_export()
        manifest = tiles.read_json(self.directory() / "manifest.json")
        asset = manifest["assets"][0]
        self.assertEqual(asset["source"]["registration"], registration)
        self.assertEqual(asset["placement"], {"kind":"floor", "points":[[64,128],[192,128],[192,256],[64,256]]})
        self.assertEqual(asset["derived"]["sizing"], "registered-floor")
        self.run_export(check=True)

    def test_registered_floor_ignores_overhang_and_joins_adjacent_planes(self):
        from book_tile_geometry import apply
        registration = {"kind": "floor", "points": [[60,30],[100,50],[60,70],[20,50]]}
        asset = {"id": "floor", "role": "ground"}
        image = Image.new("RGBA", (120,90))
        ImageDraw.Draw(image).polygon(registration["points"], fill="red")
        _, first, _ = tiles.normalize(image, asset, self.styles[1], registration=registration)
        ImageDraw.Draw(image).rectangle((45,5,50,20), fill="green")
        exported, second, _ = tiles.normalize(image, asset, self.styles[1], registration=registration)
        self.assertEqual(first["affine"], second["affine"])
        self.assertLess(exported.getchannel("A").getbbox()[1], 160)
        corners = [apply(second["affine"], p) for p in registration["points"]]
        self.assertEqual(corners, [(128,160),(192,192),(128,224),(64,192)])
        # A neighbor at grid x+1 moves by (64,32): shared endpoints coincide.
        self.assertEqual(corners[1], tuple(v+d for v,d in zip(corners[0], (64,32))))
        self.assertEqual(corners[2], tuple(v+d for v,d in zip(corners[3], (64,32))))

    def test_registered_wall_contacts_and_vertical_scale(self):
        from book_tile_geometry import apply
        image = Image.new("RGBA", (100,100))
        ImageDraw.Draw(image).polygon([(10,20),(90,60),(90,90),(10,50)], fill="blue")
        registration = {"kind":"wall", "axis":"x", "points":[[10,50],[90,90]], "verticalScale":0.5}
        _, derived, _ = tiles.normalize(image, {"id":"wall","role":"wall"}, self.styles[1], registration=registration)
        self.assertEqual(apply(derived["affine"], (10,50)), (96,176))
        self.assertEqual(apply(derived["affine"], (90,90)), (160,208))
        base = apply(derived["affine"], (10,50))
        raised = apply(derived["affine"], (10,20))
        self.assertEqual(base[0], raised[0])
        self.assertEqual(base[1]-raised[1], 15)

    def test_registration_rejects_clipping_and_invalid_plane(self):
        image = Image.new("RGBA", (100,100), "red")
        asset = {"id":"floor","role":"ground"}
        with self.assertRaisesRegex(tiles.PackError, "clip normalized canvas"):
            tiles.normalize(image, asset, self.styles[1], registration={"kind":"floor", "points":[[50,45],[55,50],[50,55],[45,50]]})
        with self.assertRaisesRegex(tiles.PackError, "fourth corner"):
            tiles.normalize(image, asset, self.styles[1], registration={"kind":"floor", "points":[[50,0],[100,50],[70,100],[0,50]]})
        with self.assertRaisesRegex(tiles.PackError, "collinear"):
            tiles.normalize(image, asset, self.styles[1], registration={"kind":"floor", "points":[[0,0],[10,10],[20,20],[30,30]]})

    def test_zip_is_compact_and_rebuild_deterministic(self):
        self.run_export()
        with ZipFile(self.directory() / "test-kit.zip") as archive:
            self.assertEqual(len(archive.namelist()), 26)
            self.assertEqual(sum(name.startswith("components/") for name in archive.namelist()), 24)
            self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))
        with Image.open(self.directory() / "contact-sheet.png") as contact:
            self.assertEqual(contact.size, (768, 640))
        before = {name: data for name, (data, _) in self.snapshot(self.output).items()}
        self.run_export()
        self.assertEqual(before, {name: data for name, (data, _) in self.snapshot(self.output).items()})

    def test_contact_preview_fits_visible_art_without_canvas_padding(self):
        sprite = Image.new("RGBA", (256, 256))
        ImageDraw.Draw(sprite).rectangle((64, 160, 191, 223), fill=(250, 10, 20, 255))
        asset = {"id": "floor", "label": "Floor", "role": "ground"}
        contact = tiles.contact_sheet([asset], {"floor": sprite}, self.styles[0])
        artwork = Image.new("L", (128, 124))
        pixels = contact.load()
        artwork.putdata([255 if pixels[x, y] == (250, 10, 20, 255) else 0
                         for y in range(124) for x in range(128)])
        self.assertEqual(artwork.getbbox(), (8, 36, 120, 92))
        self.assertEqual(sprite.getchannel("A").getbbox(), (64, 160, 192, 224))

    def test_catalog_preserves_completed_styles_and_links(self):
        self.run_export(catalog=True)
        catalog = tiles.read_json(self.output / "catalog.json")
        self.assertEqual(set(catalog["kits"][0]["variants"]), {"pocket-dungeon"})
        self.run_export("ink-and-lanterns", catalog=True)
        catalog = tiles.read_json(self.output / "catalog.json")
        self.assertEqual(set(catalog["kits"][0]["variants"]), {"pocket-dungeon", "ink-and-lanterns"})
        for variant in catalog["kits"][0]["variants"].values():
            for path in variant.values():
                self.assertTrue((self.output / path).is_file())
        before = self.snapshot(self.output)
        self.run_export("all", check=True, catalog=True)
        self.assertEqual(before, self.snapshot(self.output))

    def test_changed_source_and_modified_export_are_rejected(self):
        self.run_export()
        component = self.directory() / "components/piece-0.png"
        with Image.open(component) as image:
            altered = image.copy()
        altered.putpixel((0, 0), (255, 0, 0, 255))
        altered.save(component)
        with self.assertRaisesRegex(tiles.PackError, "source reconstruction differs"):
            self.run_export(check=True)
        self.run_export()
        source = self.docs / "sources/pocket-dungeon/test-kit.png"
        with Image.open(source) as image:
            altered = image.copy()
        altered.putpixel((80, 50), (255, 0, 0, 255))
        altered.save(source)
        with self.assertRaisesRegex(tiles.PackError, "stale manifest"):
            self.run_export(check=True)

    def test_zip_extra_member_rejected(self):
        self.run_export()
        with ZipFile(self.directory() / "test-kit.zip", "a") as archive:
            archive.writestr("native-copy.png", b"unwanted")
        with self.assertRaisesRegex(tiles.PackError, "incorrect ZIP contents"):
            self.run_export(check=True)

    def test_missing_or_duplicate_authored_cells_rejected(self):
        changed = copy.deepcopy(self.inventory)
        changed["kits"][0]["assets"][1]["cell"] = 0
        self.write_json(self.docs / "inventory.json", changed)
        with self.assertRaisesRegex(tiles.PackError, "24 unique cells"):
            self.run_export()
        self.assertFalse(self.output.exists())

    def test_reviewed_mask_rejects_cut_island_and_overlapping_ownership(self):
        crop = self.docs / "crops/pocket-dungeon.json"
        document = tiles.read_json(crop)
        document["sheets"]["test-kit"][0]["sourceBox"][2] = 90
        self.write_json(crop, document)
        with self.assertRaisesRegex(tiles.PackError, "cropped by sourceBox"):
            self.run_export()
        document["sheets"]["test-kit"][0]["sourceBox"][2] = 150
        document["sheets"]["test-kit"][1] = dict(document["sheets"]["test-kit"][0], cell=1)
        self.write_json(crop, document)
        with self.assertRaisesRegex(tiles.PackError, "selected substantial pixels overlap"):
            self.run_export()

    def test_duplicate_visible_asset_rejected(self):
        source = self.docs / "sources/pocket-dungeon/test-kit.png"
        with Image.open(source) as image:
            altered = image.copy()
        altered.paste(altered.crop((0, 0, 256, 256)), (256, 0))
        altered.save(source)
        with self.assertRaisesRegex(tiles.PackError, "duplicate visible asset"):
            self.run_export()

    def test_bad_anchor_cannot_silently_clip(self):
        image = Image.new("RGBA", (240, 184), (255, 0, 0, 255))
        with self.assertRaisesRegex(tiles.PackError, "clip normalized canvas"):
            tiles.normalize(image, {"id": "large", "role": "prop", "renderWidth": 240}, self.styles[0], [0, 0])

    def test_opaque_source_rejected(self):
        Image.new("RGBA", (1536, 1024), "white").save(self.docs / "sources/pocket-dungeon/test-kit.png")
        with self.assertRaisesRegex(tiles.PackError, "genuine transparent background"):
            self.run_export()

    def test_catalog_unknown_location_kit_rejected(self):
        self.write_json(self.docs / "coverage.json", {"locations": [{"id": "bad", "kitIds": ["absent"]}]})
        with self.assertRaisesRegex(tiles.PackError, "unknown kit reference"):
            tiles.run(None, False, True, self.docs, self.output)
        self.assertFalse((self.output / "catalog.json").exists())

    def test_authored_architecture_normalizes_height_and_projection_width(self):
        for cell, width, ortho_width in ((6, 64, 128), (7, 128, 128), (10, 32, 48), (12, 64, 128)):
            self.kit["assets"][cell].update(role="door" if cell == 12 else "wall",
                                           renderWidth=width, renderHeight=96,
                                           orthogonalRenderWidth=ortho_width)
        self.write_json(self.docs / "inventory.json", self.inventory)
        self.run_export("all")
        for style in self.styles:
            manifest = tiles.read_json(self.directory(style["id"]) / "manifest.json")
            for cell in (6, 7, 10, 12):
                definition = self.kit["assets"][cell]
                asset = manifest["assets"][cell]
                expected_width = definition["orthogonalRenderWidth"] if style["projection"] == "orthogonal" else definition["renderWidth"]
                self.assertEqual((asset["derived"]["width"], asset["derived"]["height"]), (expected_width, 96))
                self.assertEqual(asset["derived"]["sizing"], "modular-architecture")
                self.assertEqual(asset["derived"]["offset"]["y"], 96)
                self.assertEqual(asset["derived"]["scaleY"], 96 / asset["source"]["originalHeight"])
                with Image.open(self.directory(style["id"]) / asset["file"]) as image:
                    self.assertEqual(image.getchannel("A").getbbox()[3], 192)
            prop = manifest["assets"][13]
            self.assertEqual(prop["derived"]["sizing"], "preserve-aspect")
            self.assertLessEqual(abs(prop["derived"]["scaleX"] - prop["derived"]["scaleY"]),
                                 1 / min(prop["source"]["originalWidth"], prop["source"]["originalHeight"]))

    def test_partial_kit_build_preserves_catalog_and_full_style_requires_coverage(self):
        self.run_export(catalog=True)
        unfinished = copy.deepcopy(self.kit)
        unfinished["id"] = "unfinished-kit"
        for asset in unfinished["assets"]:
            asset["id"] = "unfinished-" + asset["id"]
        self.inventory["kits"].append(unfinished)
        self.write_json(self.docs / "inventory.json", self.inventory)
        with self.assertRaisesRegex(tiles.PackError, "crop kit coverage mismatch"):
            self.run_export("ink-and-lanterns")
        self.assertEqual(self.run_export("ink-and-lanterns", kit="test-kit", catalog=True), 24)
        catalog = tiles.read_json(self.output / "catalog.json")
        self.assertEqual(set(catalog["kits"][0]["variants"]), {"pocket-dungeon", "ink-and-lanterns"})
        self.assertEqual(catalog["kits"][1]["variants"], {})
        before = self.snapshot(self.output)
        self.assertEqual(self.run_export("all", kit="test-kit", check=True, catalog=True), 48)
        self.assertEqual(before, self.snapshot(self.output))

    def test_invalid_render_height_and_kit_rejected(self):
        for value in (0, -96, True, "96", float("inf")):
            with self.subTest(value=value):
                self.kit["assets"][6]["renderHeight"] = value
                self.write_json(self.docs / "inventory.json", self.inventory)
                with self.assertRaisesRegex(tiles.PackError, "positive finite renderHeight"):
                    self.run_export()
        self.kit["assets"][6]["renderHeight"] = 96
        self.write_json(self.docs / "inventory.json", self.inventory)
        with self.assertRaisesRegex(tiles.PackError, "Unknown kit"):
            self.run_export(kit="absent")
        with self.assertRaisesRegex(tiles.PackError, "requires --style"):
            self.run_export(style=None, kit="test-kit")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
