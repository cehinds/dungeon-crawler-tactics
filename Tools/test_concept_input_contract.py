#!/usr/bin/env python3
"""Adversarial authored-input fixtures; no canonical outputs are changed."""
import copy
import json
import tempfile
from pathlib import Path
from PIL import Image
from jsonschema import Draft202012Validator, ValidationError
from rebuild_combat_concept import validate_regions, mask_for
ROOT = Path(__file__).resolve().parents[1]

def rejects(label, operation):
    try: operation()
    except (ValueError,ValidationError,FileNotFoundError): return
    raise AssertionError('Accepted malformed input: '+label)

def main():
    docs = ROOT/'Docs/ConceptReconstruction'
    validator = Draft202012Validator(json.loads((docs/'schema.json').read_text()))
    scene = json.loads((docs/'scene-regions.json').read_text())
    validator.validate(scene)
    wrong = copy.deepcopy(scene); wrong['regions'][0]['shape']['bounds'] = [0,0,-1,10]
    rejects('negative crop',lambda:validator.validate(wrong))
    recipe = json.loads((docs/'procedural-recipe.json').read_text())
    rv = Draft202012Validator(json.loads((docs/'procedural-recipe.schema.json').read_text())); rv.validate(recipe)
    for key in ['entities','board','state']:
        wrong = copy.deepcopy(recipe); wrong[key] = 'invalid'
        rejects('recipe '+key, lambda:rv.validate(wrong))
    region = {'id':'one','category':'floor','shape':{'type':'rect','bounds':[0,0,1,1]}}
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        one=copy.deepcopy(region);one['parentId']='missing'
        rejects('missing parent',lambda:validate_regions([(one,base)],(16,16)))
        two=copy.deepcopy(region);two['id']='two';two['parentId']='one';one['parentId']='two'
        rejects('parent cycle',lambda:validate_regions([(one,base),(two,base)],(16,16)))
        one=copy.deepcopy(region);one['shape']['bounds']=[15,15,2,2]
        rejects('outside crop',lambda:validate_regions([(one,base)],(16,16)))
        one=copy.deepcopy(region);one['shape']={'type':'mask','src':'missing.png','bounds':[0,0,2,2]}
        rejects('missing mask',lambda:mask_for(one,(16,16),base,base))
        Image.new('L',(3,3),255).save(base/'missing.png')
        rejects('wrong mask dimensions',lambda:mask_for(one,(16,16),base,base))
        Image.new('L',(2,2),128).save(base/'missing.png')
        rejects('nonbinary mask',lambda:mask_for(one,(16,16),base,base))
    print('PASS authored schemas and ten malformed crop/parent/recipe/mask fixtures')

if __name__ == '__main__':main()
