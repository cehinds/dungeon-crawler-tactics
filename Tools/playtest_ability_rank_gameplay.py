"""Real published C# WASM rank regression. No view/DOM/runtime substitution.

A generated map is legally imported with one authored 80HP test enemy. Serialized
save fixtures explicitly seed practice and legal positions; seeded ranks are NOT
earned-play evidence. Only the rank 1→2 transition is earned by an actual cast.
"""
import argparse
import json
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright
from playtest_procedural_maps import ready_runtime


def current(page):
    return page.evaluate('window.dungeon.getView()')


def command(page, kind, **args):
    page.evaluate("async ({kind,args})=>{await window.dungeon.command(kind,args);}", dict(kind=kind,args=args))
    return current(page)


def practice(state, ability):
    return next(s for s in state['development']['practice'] if s['unitId']=='crawler.donut' and s['abilityId']=='ability.donut_'+ability)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8771')
    parser.add_argument('--browser',default=shutil.which('chromium') or shutil.which('google-chrome'))
    parser.add_argument('--output',default='/tmp/dct-rank-runtime')
    args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    results=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,args=['--no-sandbox'])
        context=browser.new_context(viewport=dict(width=1440,height=1000))
        context.add_init_script("localStorage.setItem('dct.help.seen','1')")
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url+'/index.html');ready_runtime(page)
        for selector in ['#begin-button','[data-close="help-dialog"]']:
            if page.locator(selector).last.is_visible():page.locator(selector).last.click()
        base=page.evaluate('''async()=>{
          const {generateDungeon,getPlayableMap}=await import('./procedural-map.js');
          const manifest=await fetch('assets/room-kit/manifest.json').then(r=>r.json());
          const rules=await fetch('assets/map-generation-rules.json').then(r=>r.json());
          const map=getPlayableMap(generateDungeon(manifest,{seed:'ability-ranks-runtime',width:16,height:12,layout:'chambers'},rules),manifest);
          map.enemies[0].hp=80;map.enemies[0].label='Rank regression target';
          await window.dungeon.command('import_map',{customMap:map});
          return JSON.parse(await window.dungeon.getSave());
        }''')
        assert current(page)['screen']=='battle'
        # The importer validates these positions and practice records against real content.
        donut=next(u for u in base['units'] if u['id']=='crawler.donut')
        occupied={(u['x'],u['y']) for u in base['units'] if u['team']=='player'}
        near=next(t for t in base['tiles'] if not t['blocked'] and (t['x'],t['y']) not in occupied
                  and abs(t['x']-donut['x'])+abs(t['y']-donut['y'])==1)
        enemy=next(u for u in base['units'] if u['team']=='enemy');enemy.update(x=near['x'],y=near['y'])
        base['selectedUnitId']='crawler.donut'
        mongo=next(u for u in base['units'] if u['id']=='crawler.mongo');mongo['hp']-=3
        def load_seed(entries):
            seed=json.loads(json.dumps(base));seed['development']['practice']=[dict(unitId='crawler.donut',abilityId='ability.donut_'+ability,uses=uses) for ability,uses in entries.items()]
            page.evaluate('save=>window.dungeon.loadSave(JSON.stringify(save))',seed)
            state=current(page)
            assert state['screen']=='battle' and state['selectedUnitId']=='crawler.donut'
            assert not state.get('events'), 'Import must not synthesize earned-rank events'
            return state
        state=load_seed({})
        assert all(s['rank']==1 and s['uses']==0 and len(s['ranks'])==20 for s in state['development']['practice'])
        assert {a['id'] for a in state['abilities']} <= {s['abilityId'] for s in state['development']['practice'] if s['unitId']=='crawler.donut'}
        results.append('Unpracticed known abilities expose rank 1, zero uses and 20 shared-core rows in actual battle.')
        # Seed exactly one use before rank2 using the core-authored threshold, not a JS formula.
        threshold=practice(state,'magic_missile')['ranks'][1]['requiredUses']
        state=load_seed({'magic_missile':threshold-1})
        before=page.evaluate('window.dungeon.getSave()')
        preview=command(page,'preview',abilityId='ability.donut_magic_missile',targetId=enemy['id'])
        assert preview['canConfirm'] and practice(preview,'magic_missile')['uses']==threshold-1
        command(page,'cancel')
        assert page.evaluate('window.dungeon.getSave()')==before
        results.append('Actual C# preview and cancel preserve the entire committed save and near-threshold practice.')
        command(page,'preview',abilityId='ability.donut_magic_missile',targetId=enemy['id'])
        attained=command(page,'confirm')
        assert practice(attained,'magic_missile')['rank']==2 and practice(attained,'magic_missile')['uses']==threshold
        assert any(e['type']=='skill_practice' and e['before']==1 and e['after']==2 for e in attained['events'])
        assert page.locator('.game-toast').filter(has_text='SKILL RANK UP').count()>0
        page.click('#open-actions')
        card=page.locator('[data-modal-ability="ability.donut_magic_missile"]')
        assert 'Rank 2/15' in card.inner_text() and 'uses to rank 3' in card.inner_text()
        assert card.locator('progress').count()==1
        page.screenshot(path=str(output/'earned-rank2-desktop.png'))
        page.click('#close-actions')
        results.append('One legal confirmed cast earns rank 2 and updates action badge, progress and attained-only toast.')
        saved=page.evaluate('window.dungeon.getSave()')
        page.evaluate('save=>localStorage.setItem("dungeon-crawler-tactics.save.v1",save)',saved)
        page.reload();ready_runtime(page)
        assert practice(current(page),'magic_missile')['rank']==2 and practice(current(page),'magic_missile')['uses']==threshold
        results.append('Real page reload restores the earned rank 2 and exact committed use count.')
        # Later-rank tests use explicit imported seeds, never claim those ranks were earned.
        rank10=practice(state,'magic_missile')['ranks'][9]['requiredUses']
        state=load_seed({'magic_missile':rank10})
        preview=command(page,'preview',abilityId='ability.donut_magic_missile',targetId=enemy['id'])
        assert preview['canConfirm']
        target=next(f for f in preview['forecast'] if f['targetId']==enemy['id'])
        assert 'status.burning' in target['afterTags'] and target['afterHp']>0
        state=command(page,'confirm')
        target=next(u for u in state['units'] if u['id']==enemy['id'])
        assert 'status.burning' in target['tags'] and any(s['tag']=='status.burning' and s['remainingRounds']==2 for s in target['statuses'])
        results.append('Seeded rank 10 Magic Missile previews and commits real two-round Burning on a surviving target.')
        state=load_seed({})
        heal=next(a for a in state['abilities'] if a['id']=='ability.donut_heal_critter')
        assert heal['targetIds']==['crawler.mongo'],heal
        assert not command(page,'preview',abilityId=heal['id'],targetId='crawler.carl')['canConfirm']
        assert command(page,'preview',abilityId=heal['id'],targetId='crawler.mongo')['canConfirm']
        command(page,'cancel')
        results.append('Heal Critter lists only the pet, rejects a crawler and accepts Mongo through actual C# targeting.')
        rank5=practice(state,'puddle_jumper')['ranks'][4]['requiredUses']
        state=load_seed({'puddle_jumper':rank5})
        puddle=next(a for a in state['abilities'] if a['id']=='ability.donut_puddle_jumper')
        base_range=practice(state,'puddle_jumper')['ranks'][0]['range']
        occupied={(u['x'],u['y']) for u in state['units'] if u['hp']>0}
        tile=next(t for t in state['tiles'] if not t['blocked'] and (t['x'],t['y']) not in occupied
                  and base_range<abs(t['x']-donut['x'])+abs(t['y']-donut['y'])<=puddle['range'])
        preview=command(page,'preview',abilityId=puddle['id'],targetId=tile['id'])
        assert preview['canConfirm'] and practice(preview,'puddle_jumper')['uses']==rank5
        command(page,'cancel')
        results.append('Seeded rank 5 Puddle Jumper legally previews a tile beyond its rank 1 range without training on preview.')
        load_seed({})
        for width,height in [(1440,1000),(390,844)]:
            page.set_viewport_size(dict(width=width,height=height))
            page.click('#open-character-sheet');page.click('[data-sheet-section="sheet-skills"]')
            card=page.locator('#sheet-skills .skill-row').filter(has_text='Magic Missile').first
            card.locator('summary').click()
            assert card.locator('.ability-rank-row').count()==20
            assert card.locator('.ability-rank-row.locked').count()==5
            card.locator('.ability-rank-row').last.scroll_into_view_if_needed()
            assert page.locator('#done-character-sheet').is_visible()
            page.screenshot(path=str(output/f'seeded-inspector-{width}.png'))
            page.click('#done-character-sheet')
        results.append('Desktop and phone actual battle sheets disclose all 20 ranks with 16–20 permission locked and fixed Back control.')
        assert not errors,errors
        browser.close()
    report=dict(runtime='Actual published .NET WASM; C# GameSession and RulesEngine',provenance=__doc__,checks=results,failures=errors)
    (output/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(output=str(output),checks=len(results),failures=errors),indent=2))

if __name__=='__main__':main()
