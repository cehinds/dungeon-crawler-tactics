#!/usr/bin/env python3
"""Embed the real procedural-map modules and authored data in one HTML file."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'Web/wwwroot'
MODULES = ('room-kit.js', 'procedural-map.js', 'whole-object-map.js', 'procedural-object-maps.js')


def script_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def build(out):
    html = (WEB / 'procedural-object-maps.html').read_text()
    css = (WEB / 'procedural-object-maps.css').read_text()
    if '</style' in css.lower(): raise ValueError('Unexpected style closing tag')
    rules = json.loads((WEB / 'data/procedural-object-room-rules.json').read_text())
    canonical = json.loads((WEB / 'assets/room-kit/manifest.json').read_text())
    sources = {name: (WEB / name).read_text() for name in MODULES}
    for name, source in sources.items():
        imports = re.findall(r'\bfrom\s+[\'\"](\.[^\'\"]+)[\'\"]', source)
        allowed = set(MODULES[:MODULES.index(name)])
        if any(path.removeprefix('./') not in allowed for path in imports):
            raise ValueError('Unexpected module dependency in ' + name)
    link = '<link rel="stylesheet" href="procedural-object-maps.css">'
    if html.count(link) != 1: raise ValueError('Unexpected stylesheet entry')
    html = html.replace(link, '<style>' + css + '</style>')
    entry = '<script type="module" src="procedural-object-maps.js"></script>'
    if html.count(entry) != 1: raise ValueError('Unexpected application module entry')
    data = '<script id="map-rules" type="application/json">' + script_json(rules) + '</script>'
    data += '<script id="canonical-manifest" type="application/json">' + script_json(canonical) + '</script>'
    # Preserve each actual ES module. Rewriting only its known import specifiers
    # avoids concatenation collisions and keeps the generator's export contract.
    loader = '''const sources=SOURCE_DATA,urls=new Map();
for(const [name,original] of Object.entries(sources)){
  let code=original;
  for(const [dependency,url] of urls){
    code=code.replaceAll("'./"+dependency+"'",JSON.stringify(url));
    code=code.replaceAll('"./'+dependency+'"',JSON.stringify(url));
  }
  urls.set(name,URL.createObjectURL(new Blob([code],{type:'text/javascript'})));
}
await import(urls.get('procedural-object-maps.js'));
'''.replace('SOURCE_DATA', script_json(sources))
    html = html.replace(entry, data + '<script type="module">' + loader + '</script>')
    html = html.replace('<head>', '<head><meta name="object-map-mode" content="standalone">', 1)
    html = html.replace('<a href="dungeon-generator.html">Classic foundry</a>', '')
    html = html.replace('<a class="brand" href="index.html">', '<a class="brand" href="https://github.com/cehinds/dungeon-crawler-tactics/tree/dev" target="_blank" rel="noopener">')
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(html)
    return {'file': str(out), 'bytes': out.stat().st_size, 'modules': list(sources)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'Docs/ProceduralObjectMaps/standalone.html')
    args = parser.parse_args()
    print(json.dumps(build(args.out), indent=2))
