"""Use the canonical art repository's metadata rules when rebuilding its exports.

Small unit fixtures without a reusable catalog keep their existing schemas. A
hydrated full library requires its canonical helper, checked out by Pages before
validation; no rule implementation is duplicated in the game repository.
"""
from functools import lru_cache
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def helper():
    lock = json.loads((ROOT / 'art-assets.lock.json').read_text())
    candidates = [ROOT / '.art-source', ROOT.parent / 'AI-Art', ROOT / '.git/art-assets' / lock['commit']]
    for source in candidates:
        path = source / 'tools/asset_attachment_tags.py'
        if path.is_file():
            spec = importlib.util.spec_from_file_location('canonical_art_attachment_tags', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ValueError('Hydrated reusable metadata requires the pinned AI-Art checkout (restore art before validating).')


@lru_cache(maxsize=16)
def catalog(index):
    document = json.loads(Path(index).read_text())
    return {asset['id']: asset for asset in document['assets']}


def enrich_expected(document, pack):
    pack = Path(pack)
    index = pack / 'reusable/index.json'
    if index.is_file():
        module = helper()
        return module.enrich_document(document, module.style_of(pack), catalog(str(index)))
    # The aggregate catalog lives one level above the three registered books.
    if any((pack / style / 'reusable/index.json').is_file() for style in ('pocket-dungeon', 'ink-and-lanterns', 'dungeon-after-dark')):
        return helper().enrich_document(document, 'gameplay', {})
    return document
