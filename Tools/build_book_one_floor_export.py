#!/usr/bin/env python3
"""Package the actual First Floor atlas modules and authored data in one HTML file."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'Web/wwwroot'
MODULES = ('room-kit.js', 'procedural-map.js', 'whole-object-map.js',
           'book-one-floor.js', 'book-one-playable-floor.js', 'book-one-floor-one.js')
DATA = {'book-one-rules': 'data/procedural-object-room-rules.json',
        'book-one-canonical': 'assets/room-kit/manifest.json',
        'book-one-catalog': 'data/book-one-floor-one.json',
        'book-one-archetypes': 'data/book-one-location-archetypes.json'}


def script_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def build(out):
    html = (WEB / 'book-one-floor-one.html').read_text()
    css = (WEB / 'book-one-floor-one.css').read_text()
    if '</style' in css.lower():
        raise ValueError('Unexpected style closing tag')
    sources = {name: (WEB / name).read_text() for name in MODULES}
    for name, source in sources.items():
        imports = re.findall(r'\bfrom\s+[\'\"](\.[^\'\"]+)[\'\"]', source)
        allowed = set(MODULES[:MODULES.index(name)])
        if any(path.removeprefix('./') not in allowed for path in imports):
            raise ValueError('Unexpected module dependency in ' + name)
    link_match = re.findall(r'<link\s+rel="stylesheet"\s+href="book-one-floor-one\.css"\s*/?>', html)
    entry = '<script type="module" src="book-one-floor-one.js"></script>'
    if len(link_match) != 1 or html.count(entry) != 1:
        raise ValueError('Unexpected atlas stylesheet or module entry')
    html = html.replace(link_match[0], '<style>' + css + '</style>')
    data = ''.join('<script id="' + ident + '" type="application/json">' +
                   script_json(json.loads((WEB / path).read_text())) + '</script>'
                   for ident, path in DATA.items())
    loader = '''const sources=SOURCE_DATA,urls=new Map();
for(const [name,original] of Object.entries(sources)){
  let code=original;
  for(const [dependency,url] of urls){
    code=code.replaceAll("'./"+dependency+"'",JSON.stringify(url));
    code=code.replaceAll('"./'+dependency+'"',JSON.stringify(url));
  }
  urls.set(name,URL.createObjectURL(new Blob([code],{type:'text/javascript'})));
}
await import(urls.get('book-one-floor-one.js'));
'''.replace('SOURCE_DATA', script_json(sources))
    html = html.replace(entry, data + '<script type="module">' + loader + '</script>')
    html = html.replace('<head>', '<head><meta name="book-one-floor-mode" content="standalone">', 1)
    html = re.sub(r'<a href="procedural-object-maps\.html">Object foundry</a\s*>', '', html)
    html = html.replace('<a class="brand" href="index.html">', '<a class="brand" href="https://github.com/cehinds/dungeon-crawler-tactics/tree/dev" target="_blank" rel="noopener">')
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return {'file': str(out), 'bytes': out.stat().st_size, 'modules': list(sources),
            'embeddedData': list(DATA.values()), 'remoteArt': 'Pinned whole-object manifest and PNGs require internet access.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'Docs/BookOneFloorOne/standalone.html')
    args = parser.parse_args()
    print(json.dumps(build(args.out), indent=2))
