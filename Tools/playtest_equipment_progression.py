"""Real WASM milestone rewards and reversible equipment comparison browser QA."""
import argparse
import copy
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_generated_adventure import command, view, position, route, walk
from playtest_continuous_floor import launch_floor
from playtest_generated_campaign import cells, save, roundtrip, win_battle


def fixture(source):
    enemy = source['map']['enemies'][0]
    plan = {'schemaVersion': 1, 'seed': 803, 'entrance': {'x': 1, 'y': 2},
            'exit': {'x': 28, 'y': 6}, 'discoveries': [], 'groups': [],
            'map': {'schemaVersion': 1, 'label': 'Equipment milestone QA', 'width': 30,
                    'height': 8, 'tiles': [], 'placements': [],
                    'playerSpawns': [{'x': x, 'y': y} for x, y in [(1,2),(2,2),(1,3),(2,3)]],
                    'enemies': []}}
    for i, x in enumerate([6, 13, 20, 27]):
        enemy_id = f'custom.enemy.gearqa{i}'
        plan['map']['enemies'].append(dict(copy.deepcopy(enemy), id=enemy_id, x=x, y=2, hp=1, move=1, energy=0))
        plan['groups'].append({'id': f'qa.gear.group{i}', 'label': 'QA weak sentry',
                               'kind': 'visible', 'x': x, 'y': 2, 'enemyIds': [enemy_id], 'rewardXp': 30})
    future = copy.deepcopy(plan)
    future['seed'] = 804
    future['map']['label'] = 'Equipment QA future depth'
    return {'schemaVersion': 1, 'id': 'qa.gear.campaign', 'label': 'Equipment rewards QA', 'seed': 803, 'floors': [plan, future]}


def open_equipment(page):
    page.locator('#field-menu-button').click()
    page.locator('[data-field-action=equipment]').click()
    page.locator('#equipment-dialog').wait_for(state='visible')


def selected(page, unit_id):
    return next(r for r in view(page)['roster'] if r['id'] == unit_id)


def responsive(page, out):
    for width, height in [(320,740),(390,844),(844,390),(1440,1000)]:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(150)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), (width, 'overflow')
        for selector in ['#confirm-equipment', '#cancel-equipment']:
            box = page.locator(selector).bounding_box()
            assert box and box['x'] >= 0 and box['y'] >= 0 and box['x']+box['width'] <= width+1 and box['y']+box['height'] <= height+1, (width,selector,box)
        page.screenshot(path=str(out/f'comparison-{width}.png'))
    page.set_viewport_size({'width':1440,'height':1000})


def check_sheet_comparison(page, unit_id, gear_id):
    page.locator(f'[data-character-sheet="{unit_id}"]').click()
    page.locator('[data-sheet-section="sheet-gear"]').click()
    page.locator(f'[data-sheet-equip="{gear_id}"]').click()
    page.locator('#equipment-confirm-dialog').wait_for(state='visible')
    page.locator('#cancel-equipment').click()
    assert page.locator('#character-sheet-dialog').is_visible()
    assert not next(g for g in view(page)['equipment'] if g['id']==gear_id).get('equippedUnitId')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8775')
    parser.add_argument('--browser', default=shutil.which('google-chrome') or shutil.which('chromium'))
    parser.add_argument('--screenshots', default='/workspace/scratch/equipment-progression')
    args=parser.parse_args(); out=Path(args.screenshots);out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.add_init_script("if(!sessionStorage.qaGear){localStorage.clear();localStorage.setItem('dct.help.seen','1');sessionStorage.qaGear='1'}")
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url.rstrip('/')+'/index.html')
        source=launch_floor(page,'equipment-progression-qa')['generatedDungeon']['floorPlan']
        authored=fixture(source)
        state=command(page,'import_campaign',campaignPlan=authored)
        assert state.get('generatedCampaign',{}).get('id')==authored['id'],state.get('message')
        plan=save(page)['generatedCampaign']['plan']['floors'][0]
        assert [g['rewardXp'] for g in plan['groups']]==[30,30,30,30]
        for index, group in enumerate(plan['groups'][:3]):
            walk(page,route(position(page),(group['x']-1,group['y']),cells(plan)))
            assert view(page)['screen']=='battle',view(page).get('message')
            if index==0:
                # Let a real enemy phase injure the party before completing the fight.
                for member in list(view(page)['units']):
                    if member['team']=='player' and member['hp']>0:
                        command(page,'end_turn',unitId=member['id'])
                assert any(u['hp']<u['maxHp'] for u in view(page)['units'] if u['team']=='player'), 'Fixture enemy phase caused no injury'
            win_battle(page,finish=False)
            rewards=view(page)['rewards']; gear_choices=[r for r in rewards if r.get('equipmentId')]
            if index<2:
                assert not gear_choices, rewards
                page.locator(f'[data-reward="{rewards[0]["id"]}"]').click()
                command(page,'continue')
            else:
                assert len(gear_choices)==3 and len(rewards)==6,rewards
                page.screenshot(path=str(out/'reward-desktop.png'))
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path=str(out/'reward-390.png'))
                page.set_viewport_size({'width':1440,'height':1000})
                chosen=next((r for r in gear_choices if next(g for g in view(page)['equipment'] if g['id']==r['equipmentId']).get('abilityIds')),gear_choices[0])
                assert not next(g for g in view(page)['equipment'] if g['id']==chosen['equipmentId'])['owned']
                page.locator(f'[data-reward="{chosen["id"]}"]').click()
                claims=save(page)['equipmentRewardClaims']
                assert claims==[{'tierId':chosen['tierId'],'equipmentId':chosen['equipmentId']}],claims
                command(page,'choose_reward',rewardId=chosen['id'])
                assert save(page)['equipmentRewardClaims']==claims,'Duplicate reward granted'
                for alternative in gear_choices:
                    assert next(g for g in view(page)['equipment'] if g['id']==alternative['equipmentId'])['owned']==(alternative==chosen)
                command(page,'continue')
        roundtrip(page)
        gear=next(g for g in view(page)['equipment'] if g['id']==chosen['equipmentId'])
        open_equipment(page)
        injured=next(r for r in view(page)['roster'] if r['selected'] and r['hp']<r['maxHp'])
        page.locator('#loadout-crawler').select_option(injured['id'])
        unit_id=injured['id']; before=selected(page,unit_id)
        assert page.locator('.equipment-item.is-locked').count()==0,'Default filter displays locked gear'
        page.locator('#equipment-show-locked').check()
        assert page.locator('.equipment-item.is-locked').count()>0
        page.locator('#equipment-show-locked').uncheck()
        # A real maximum-Mana increase creates a deficit without fabricating a save.
        mana_gear=next(g for g in view(page)['equipment'] if g['owned'] and not g.get('equippedUnitId') and g['manaBonus']>0)
        command(page,'preview_equipment',unitId=unit_id,equipmentId=mana_gear['id'])
        page.locator('#confirm-equipment').click()
        before=selected(page,unit_id)
        assert before['energy']<before['maxEnergy'], 'Mana-cap increase unexpectedly refilled Mana'
        (out/'earned-equipment-save.json').write_text(json.dumps(save(page)))
        page.locator(f'[data-equipment-slot="{gear["slot"]}"]').click()
        page.screenshot(path=str(out/'inventory-desktop.png'))
        page.locator(f'[data-equip="{gear["id"]}"]').click()
        page.locator('#equipment-confirm-dialog').wait_for(state='visible')
        preview=view(page)['equipmentPreview'];assert preview['canConfirm'] and preview['unitId']==unit_id
        assert preview['gainedAbilityIds'], 'Reward weapon must add an actual new ability'
        assert preview['before']=={key:before[key] for key in ['maxHp','maxEnergy','move','hp','energy']}
        assert selected(page,unit_id)==before,'Preview mutated crawler'
        responsive(page,out)
        page.locator('#cancel-equipment').click();assert selected(page,unit_id)==before
        command(page,'preview_equipment',unitId=unit_id,equipmentId=gear['id'])
        command(page,'cancel_equipment');command(page,'confirm_equipment')
        assert selected(page,unit_id)==before,'Cancelled comparison committed'
        command(page,'preview_equipment',unitId=unit_id,equipmentId=gear['id'])
        command(page,'select',unitId=unit_id);command(page,'confirm_equipment')
        assert selected(page,unit_id)==before,'Stale comparison committed'
        command(page,'preview_equipment',unitId=unit_id,equipmentId=gear['id'])
        roundtrip(page);command(page,'confirm_equipment')
        assert selected(page,unit_id)==before,'Reload committed pending equipment'
        command(page,'preview_equipment',unitId=unit_id,equipmentId=gear['id'])
        expected=view(page)['equipmentPreview']['after'];page.locator('#confirm-equipment').click()
        after=selected(page,unit_id)
        assert all(after[k]==expected[k] for k in expected),(after,expected)
        assert after['hp']==min(before['hp'],after['maxHp']) and after['energy']==min(before['energy'],after['maxEnergy'])
        assert next(g for g in view(page)['equipment'] if g['id']==gear['id'])['equippedUnitId']==unit_id
        # A fourth encounter exposes the actual C# action list with the earned gear.
        group=plan['groups'][3]
        walk(page,route(position(page),(group['x']-1,group['y']),cells(plan)))
        assert view(page)['screen']=='battle'
        command(page,'select',unitId=unit_id)
        available={a['id'] for a in view(page)['abilities']}
        assert set(preview['gainedAbilityIds']) <= available,(preview,available)
        win_battle(page)
        command(page,'preview_unequip',unitId=unit_id,equipmentId=gear['id'])
        removal=view(page)['equipmentPreview'];assert removal['remove'] and removal['canConfirm']
        assert set(removal['lostAbilityIds'])==set(preview['gainedAbilityIds'])
        page.locator('#confirm-equipment').click()
        assert not next(g for g in view(page)['equipment'] if g['id']==gear['id']).get('equippedUnitId')
        roundtrip(page);assert save(page)['equipmentRewardClaims']==claims
        check_sheet_comparison(page,unit_id,gear['id'])
        assert not errors,errors
        browser.close()
    print('PASS actual WASM three combat wins, milestone single claim/reload, owned filters, exact preview/cancel/stale/reload, confirmed equip/unequip and four responsive comparison screenshots')


if __name__=='__main__':
    main()
