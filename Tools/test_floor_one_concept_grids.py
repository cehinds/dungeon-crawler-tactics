#!/usr/bin/env python3
"""Check grid geometry, unchanged off-grid pixels, labels, source preservation and ZIP."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/floor-one-concept-grids'


def sha(data):return hashlib.sha256(data).hexdigest()


class GridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((OUT/'manifest.json').read_text())

    def test_all_72_inputs_and_ids(self):
        panels=self.manifest['panels'];self.assertEqual(len(panels),72)
        self.assertEqual(len({(p['set'],p['id']) for p in panels}),72)
        for source_set in self.manifest['sourceSets']:
            path=OUT/source_set['manifestPath'];self.assertEqual(sha(path.read_bytes()),source_set['manifestSha256'])
            source=json.loads(path.read_text());selected=[p for p in panels if p['set']==source_set['id']]
            self.assertEqual({p['id'] for p in selected},{p['id'] for p in source['panels']})
        for panel in panels:self.assertEqual(sha((ROOT/panel['sourcePath']).read_bytes()),panel['sourceSha256'])

    def test_exact_14x14_geometry(self):
        margin=self.manifest['style']['margin']
        self.assertEqual(self.manifest['style']['divisions'],14)
        for p in self.manifest['panels']:
            w,h=p['sourceSize'];g=p['grid']
            self.assertEqual(g['xBoundaries'],[round(i*w/14) for i in range(15)])
            self.assertEqual(g['yBoundaries'],[round(i*h/14) for i in range(15)])
            for positions in (g['xBoundaries'],g['yBoundaries']):
                widths=[b-a for a,b in zip(positions,positions[1:])]
                self.assertEqual(len(widths),14);self.assertGreater(min(widths),0);self.assertLessEqual(max(widths)-min(widths),1)
            self.assertEqual(g['columns'],list('ABCDEFGHIJKLMN'));self.assertEqual(g['rows'],list(range(1,15)))
            self.assertEqual(g['contentRect'],[margin,margin,w,h]);self.assertEqual(p['size'],[w+2*margin,h+2*margin+self.manifest['style']['legendHeight']])

    def test_only_grid_lines_change_native_pixels(self):
        margin=self.manifest['style']['margin'];color=self.manifest['style']['lineColor'];a=color[3]
        for p in self.manifest['panels']:
            source=Image.open(ROOT/p['sourcePath']).convert('RGBA');output=Image.open(OUT/p['path']).convert('RGBA')
            actual=output.crop((margin,margin,margin+source.width,margin+source.height))
            xs={min(x,source.width-1) for x in p['grid']['xBoundaries']};ys={min(y,source.height-1) for y in p['grid']['yBoundaries']}
            source_pixels=source.load();actual_pixels=actual.load()
            minor_x=set(p['grid']['subgrid']['xMinorBoundaries']);minor_y=set(p['grid']['subgrid']['yMinorBoundaries'])
            unaffected_x=[x for x in range(source.width) if all(abs(x-b)>1 for b in xs) and x not in minor_x]
            unaffected_y=[y for y in range(source.height) if all(abs(y-b)>1 for b in ys) and y not in minor_y]
            for y in unaffected_y:
                for x in unaffected_x:
                    if source_pixels[x,y]!=actual_pixels[x,y]:self.fail('Non-grid pixel changed: '+p['set']+'/'+p['id'])
            for x in xs:
                y=unaffected_y[len(unaffected_y)//2];original=source_pixels[x,y]
                expected=tuple((color[c]*a+original[c]*(255-a)+127)//255 for c in range(3))+(255,)
                self.assertEqual(actual_pixels[x,y],expected)
            for y in ys:
                x=unaffected_x[len(unaffected_x)//2];original=source_pixels[x,y]
                expected=tuple((color[c]*a+original[c]*(255-a)+127)//255 for c in range(3))+(255,)
                self.assertEqual(actual_pixels[x,y],expected)

            minor=self.manifest['style']['minorLineColor'];alpha=minor[3]
            for x,y in ([(x,unaffected_y[len(unaffected_y)//2]) for x in minor_x]+[(unaffected_x[len(unaffected_x)//2],y) for y in minor_y]):
                original=source_pixels[x,y]
                expected=tuple((minor[c]*alpha+original[c]*(255-alpha)+127)//255 for c in range(3))+(255,)
                self.assertEqual(actual_pixels[x,y],expected)

    def test_subgrids_partition_each_existing_major_cell(self):
        self.assertEqual(self.manifest['schemaVersion'],2)
        self.assertEqual(self.manifest['style']['subdivisions'],3)
        self.assertLess(self.manifest['style']['minorLineColor'][3],self.manifest['style']['lineColor'][3])
        for panel in self.manifest['panels']:
            grid=panel['grid'];sub=grid['subgrid']
            self.assertEqual(sub['columns'],list('abc'));self.assertEqual(sub['rows'],[1,2,3]);self.assertEqual(sub['addressExample'],'D7.b2')
            for major_key,cells_key,minor_key in [('xBoundaries','xByMajorCell','xMinorBoundaries'),('yBoundaries','yByMajorCell','yMinorBoundaries')]:
                major=grid[major_key];cells=sub[cells_key];self.assertEqual(len(cells),14)
                expected=[]
                for (start,end),cell in zip(zip(major,major[1:]),cells):
                    self.assertEqual(cell,[start+round((end-start)*j/3) for j in range(4)])
                    widths=[b-a for a,b in zip(cell,cell[1:])];self.assertGreater(min(widths),0);self.assertLessEqual(max(widths)-min(widths),1)
                    expected.extend(cell[1:-1])
                self.assertEqual(sub[minor_key],expected);self.assertEqual(len(expected),28);self.assertEqual(len(set(major+expected)),43)

    def test_labels_in_outside_margins(self):
        margin=self.manifest['style']['margin']
        for p in self.manifest['panels']:
            output=Image.open(OUT/p['path']).convert('RGB');g=p['grid']
            legend=output.crop((0,margin+p['sourceSize'][1]+margin,output.width,output.height))
            self.assertTrue(any(pixel!=tuple(self.manifest['style']['marginColor'][:3]) for pixel in legend.get_flattened_data()))
            for a,b in zip(g['xBoundaries'],g['xBoundaries'][1:]):
                strip=output.crop((margin+a,0,margin+b,margin))
                self.assertTrue(any(r==g==b==255 for r,g,b in strip.get_flattened_data()))
            for a,b in zip(g['yBoundaries'],g['yBoundaries'][1:]):
                strip=output.crop((0,margin+a,margin,margin+b))
                self.assertTrue(any(r==g==b==255 for r,g,b in strip.get_flattened_data()))

    def test_prior_assets_preserved(self):
        for path,digest in json.loads((OUT/'baseline.json').read_text()).items():self.assertEqual(sha((ROOT/path).read_bytes()),digest,path)

    def test_output_hashes_and_archive_closure(self):
        members=json.loads((OUT/'package-manifest.json').read_text())['members'];expected={p['file']:p for p in members}
        files={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
        self.assertEqual(files,set(expected)|{'package-manifest.json','floor-one-concept-grids.zip'})
        self.assertEqual(sha((OUT/self.manifest['font']['path']).read_bytes()),self.manifest['font']['sha256'])
        for p in self.manifest['panels']:self.assertEqual(sha((OUT/p['path']).read_bytes()),p['sha256'])
        for name in ('README.md','spec.json'):self.assertEqual((OUT/name).read_bytes(),(ROOT/'Docs/FloorOneConceptGrids'/name).read_bytes())
        for name in ('build_floor_one_concept_grids.py','test_floor_one_concept_grids.py'):self.assertEqual((OUT/'tools'/name).read_bytes(),(ROOT/'Tools'/name).read_bytes())
        with zipfile.ZipFile(OUT/'floor-one-concept-grids.zip') as archive:
            self.assertEqual(set(archive.namelist()),set(expected)|{'package-manifest.json'})
            for name,record in expected.items():
                data=(OUT/name).read_bytes();self.assertEqual(sha(data),record['sha256']);self.assertEqual(len(data),record['bytes']);self.assertEqual(archive.read(name),data)
            self.assertEqual(archive.read('package-manifest.json'),(OUT/'package-manifest.json').read_bytes())


if __name__=='__main__':unittest.main()
