"""Actual shared-C# WASM QA for optional environmental shortcuts and saved receipts."""
import argparse
import copy
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_continuous_floor import launch_floor
from playtest_generated_adventure import command, view, position, route, walk, distances
from playtest_generated_campaign import save, roundtrip, cells, win_battle


def fixture(source, item_id, kind='ability'):
    floors=[]
    for depth in range(2):
        enemy=dict(copy.deepcopy(source['map']['enemies'][0]),id=f'custom.enemy.mechanism{depth}',x=9,y=2,hp=1,move=1,energy=0)
        solutions=[{'id':'qa.burn','label':'Burn the oil binding','description':'Apply a learned fire skill.',
                    'kind':'ability','x':4,'y':2,'abilityTag':'element.fire','requiredMaterialTags':['surface.oil']},
                   {'id':'qa.item','label':'Use a fire flask','description':'Consume one shared supply.',
                    'kind':'item','x':4,'y':2,'abilityTag':'element.fire','itemId':item_id,'itemCount':1,'requiredMaterialTags':[]},
                   {'id':'qa.lever','label':'Pull the remote lever','description':'A longer walk costs no resource.',
                    'kind':'manual','x':2,'y':5,'requiredMaterialTags':[]},
                   {'id':'qa.blocked','label':'Douse a wet binding','description':'No deployed crawler knows the required water skill.',
                    'kind':'ability','x':4,'y':2,'abilityTag':'element.water','requiredMaterialTags':['surface.oil']}]
        solutions=[s for s in solutions if s['id']!='qa.item'] if kind=='ability' else [s for s in solutions if s['kind']==kind]
        floors.append({'schemaVersion':1,'seed':991+depth,'entrance':{'x':2,'y':2},'exit':{'x':10,'y':6},
            'map':{'schemaVersion':1,'label':f'QA shortcut depth {depth+1}','width':12,'height':8,
                   'tiles':[{'x':5,'y':y,'blocked':True,'tags':[]} for y in range(7)],'placements':[],
                   'playerSpawns':[{'x':2,'y':2},{'x':3,'y':2},{'x':2,'y':3},{'x':3,'y':3}], 'enemies':[enemy]},
            'groups':[{'id':f'qa.guard{depth}','label':'QA weak guard','kind':'visible','x':9,'y':2,'enemyIds':[enemy['id']],'rewardXp':30}],
            'discoveries':[], 'mechanisms':[{'id':'qa.shortcut','label':'Oil-bound gate','description':'A wall gate has a long southern detour and a free remote lever.',
                'x':5,'y':2,'materialTags':['surface.oil'],'openCells':[{'x':5,'y':2}],'solutions':solutions}]})
    return {'schemaVersion':1,'id':f'qa.mechanism.{kind}','label':'QA optional gate','seed':991,'floors':floors}


def mechanism(page):
    return next(m for m in view(page)['mechanisms'] if m['id']=='qa.shortcut')


def resources(page):
    return {'party':[(r['id'],r['hp'],r['energy']) for r in view(page)['roster']],
            'items':[(i['id'],i['count']) for i in view(page)['items']]}


def approach(page, plan, solution_id):
    solution=next(s for s in mechanism(page)['solutions'] if s['id']==solution_id)
    walk(page,route(position(page),(solution['x'],solution['y']),cells(plan)))


def inspect(page):
    point=next(p for p in view(page)['exploration']['points'] if p.get('mechanismId')=='qa.shortcut' and p.get('canInteract'))
    page.locator(f'[data-explore-interact="{point["id"]}"]').click()
    page.locator('#mechanism-dialog').wait_for(state='visible')


def preview_ui(page, solution_id, candidate):
    inspect(page)
    page.locator('#mechanism-actor').select_option(candidate['unitId'])
    selector=f'[data-mechanism-preview="{solution_id}"][data-mechanism-unit="{candidate["unitId"]}"]'
    if candidate.get('abilityId'):selector+=f'[data-mechanism-ability="{candidate["abilityId"]}"]'
    page.locator(selector).click()
    page.locator('#mechanism-confirm-dialog').wait_for(state='visible')
    return view(page)['mechanismPreview']


def responsive(page, out):
    while page.locator('.toast-dismiss:visible').count():page.locator('.toast-dismiss:visible').last.click()
    for width,height in [(320,740),(390,844),(844,390),(1440,1000)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(width,'overflow')
        for selector in ['#confirm-mechanism','#cancel-mechanism']:
            box=page.locator(selector).bounding_box()
            assert box and box['x']>=0 and box['y']>=0 and box['x']+box['width']<=width+1 and box['y']+box['height']<=height+1,(width,selector,box)
        page.screenshot(path=str(out/f'mechanism-preview-{width}.png'))
    page.set_viewport_size({'width':1440,'height':1000})


def preview_args(candidate, solution_id):
    return {'targetId':'qa.shortcut','solutionId':solution_id,'unitId':candidate['unitId'],'abilityId':candidate.get('abilityId')}


def production_art(page, plan, out):
    safe=cells(plan)
    for group in plan['groups']:
        safe-=set(c for c,d in distances((group['x'],group['y']),cells(plan)).items() if d<=4)
    accessible=distances(position(page),safe)
    options=[(m,s) for m in plan['mechanisms'] for s in m['solutions'] if s['kind']=='ability' and (s['x'],s['y']) in accessible]
    assert options, 'Generated first depth needs a safely reachable local shortcut for native-art QA'
    gate,solution=options[0]
    path=route(position(page),(solution['x'],solution['y']),safe)
    print({'productionLocalRouteSteps':len(path),'gate':gate['id']},flush=True)
    walk(page,path)
    page.wait_for_function("window.dungeon.scene?.getNativeArtStatus().state==='ready'")
    assert page.evaluate('window.dungeon.scene.getNativeArtStatus().projection')=='orthogonal'
    actual=next(m for m in view(page)['mechanisms'] if m['id']==gate['id'])
    actual_solution=next(s for s in actual['solutions'] if s['id']==solution['id'])
    actor=next(c for c in actual_solution['candidates'] if c['enabled'])
    before=resources(page)
    page.locator('#camera-toggle').click()
    for rotation in range(4):
        page.screenshot(path=str(out/f'production-closed-rotation{rotation}.png'))
        page.locator('#rotate-right').click()
    command(page,'preview_mechanism',targetId=gate['id'],solutionId=solution['id'],unitId=actor['unitId'],abilityId=actor['abilityId'])
    cost=view(page)['mechanismPreview']
    page.locator('#confirm-mechanism').click()
    after=resources(page)
    assert before['items']==after['items'] and [(r[0],r[1]) for r in before['party']]==[(r[0],r[1]) for r in after['party']]
    assert next(r for r in after['party'] if r[0]==actor['unitId'])[2]==cost['manaAfter']
    if not page.locator('#rotate-right').is_visible():page.locator('#camera-toggle').click()
    for rotation in range(4):
        page.screenshot(path=str(out/f'production-open-rotation{rotation}.png'))
        page.locator('#rotate-right').click()
    roundtrip(page)
    assert next(m for m in view(page)['mechanisms'] if m['id']==gate['id'])['solved']


def run(args):
    out=Path(args.screenshots);out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.add_init_script("if(!sessionStorage.qaMechanisms){localStorage.clear();localStorage.setItem('dct.help.seen','1');sessionStorage.qaMechanisms='1'}")
        page.goto(args.url.rstrip('/')+'/index.html')
        launched=launch_floor(page,'mechanism-browser-qa');generated=save(page)['generatedCampaign']['plan']['floors']
        assert len(generated)==3 and all(len(f.get('mechanisms',[]))==1 for f in generated),'Every generated depth needs one optional shortcut'
        source=launched['generatedDungeon']['floorPlan']
        production_art(page,source,out)
        print('PASS production native local gate closed/open four UI rotations and receipt reload',flush=True)
        item_id=next(i['id'] for i in view(page)['items'] if i['id']=='item.fire_bomb')
        authored=fixture(source,item_id);state=command(page,'import_campaign',campaignPlan=authored)
        assert state.get('generatedCampaign',{}).get('id')==authored['id'],state.get('message')
        plan=save(page)['generatedCampaign']['plan']['floors'][0]
        print('PASS authored mechanism fixture import',flush=True)
        approach(page,plan,'qa.burn');assert (5,2) not in cells(plan)
        page.screenshot(path=str(out/'world-closed.png'))
        solution=next(s for s in mechanism(page)['solutions'] if s['id']=='qa.burn')
        candidate=next(c for c in solution['candidates'] if c['enabled'])
        for option in solution['candidates']:
            if option['enabled']:
                owner=next(r for r in view(page)['roster'] if r['id']==option['unitId'])
                assert owner['selected'] and owner['hp']>0 and owner.get('deployable',True)
        # Increasing a real equipment cap produces injured HP without editing a save.
        gear=next(g for g in view(page)['equipment'] if g['owned'] and not g.get('equippedUnitId') and g['hpBonus']>0)
        command(page,'preview_equipment',unitId=candidate['unitId'],equipmentId=gear['id']);command(page,'confirm_equipment')
        actor=next(r for r in view(page)['roster'] if r['id']==candidate['unitId'])
        assert actor['hp']<actor['maxHp']
        baseline=resources(page);progress_before=(save(page)['xp'],copy.deepcopy(save(page).get('development')))
        args_preview=preview_args(candidate,'qa.burn')
        # A globally known spell is insufficient unless this actor actually knows it.
        command(page,'preview_mechanism',**dict(args_preview,abilityId='ability.firebolt'))
        assert not view(page).get('mechanismPreview') and resources(page)==baseline
        outsider=next(r for r in view(page)['roster'] if not r['selected'])
        command(page,'preview_mechanism',**dict(args_preview,unitId=outsider['id']))
        assert not view(page).get('mechanismPreview')
        blocked=next(s for s in mechanism(page)['solutions'] if s['id']=='qa.blocked')
        assert not blocked['enabled'] and blocked.get('disabledReason'),blocked
        preview=preview_ui(page,'qa.burn',candidate)
        assert preview['canConfirm'] and preview['manaBefore']-preview['manaAfter']==candidate['manaCost']>0
        assert preview['openedCells']==[{'x':5,'y':2,'cost':0}] or [(c['x'],c['y']) for c in preview['openedCells']]==[(5,2)]
        assert resources(page)==baseline and not mechanism(page)['solved']
        responsive(page,out)
        page.locator('#cancel-mechanism').click();assert page.locator('#mechanism-dialog').is_visible()
        assert resources(page)==baseline and not mechanism(page)['solved']
        page.locator('#done-mechanism').click()
        command(page,'preview_mechanism',**args_preview);command(page,'cancel_mechanism');command(page,'confirm_mechanism')
        assert resources(page)==baseline and not mechanism(page)['solved']
        command(page,'preview_mechanism',**args_preview);command(page,'select',unitId=candidate['unitId']);command(page,'confirm_mechanism')
        assert resources(page)==baseline and not mechanism(page)['solved'],'Stale preview committed'
        command(page,'preview_mechanism',**args_preview);roundtrip(page);command(page,'confirm_mechanism')
        assert resources(page)==baseline and not mechanism(page)['solved'],'Reload retained preview'
        preview_ui(page,'qa.burn',candidate);page.locator('#confirm-mechanism').click()
        assert mechanism(page)['solved'];after=resources(page)
        assert (save(page)['xp'],save(page).get('development'))==progress_before,'Shortcut granted combat progression'
        actor_before=next(r for r in baseline['party'] if r[0]==candidate['unitId']);actor_after=next(r for r in after['party'] if r[0]==candidate['unitId'])
        assert actor_after[1]==actor_before[1] and actor_after[2]==preview['manaAfter']
        assert baseline['items']==after['items']
        assert [(r[0],r[1]) for r in baseline['party']]==[(r[0],r[1]) for r in after['party']], 'Mechanism healed a crawler'
        command(page,'confirm_mechanism');assert resources(page)==after,'Duplicate commit charged twice'
        receipt=save(page)['generatedDungeon']['mechanismReceipts'];assert len(receipt)==1
        page.screenshot(path=str(out/'world-open.png'));roundtrip(page)
        assert save(page)['generatedDungeon']['mechanismReceipts']==receipt and mechanism(page)['solved']
        # The newly opened cell participates in normal movement and the actual combat board.
        walk(page,[(5,2)]);assert position(page)==(5,2) and view(page)['screen']=='explore'
        walk(page,[(6,2)]);assert position(page)==(6,2) and view(page)['screen']=='battle'
        roundtrip(page)
        tile=next(t for t in view(page)['tiles'] if (t['x'],t['y'])==(5,2));assert not tile.get('blocked')
        win_battle(page);roundtrip(page)
        walk(page,route(position(page),(10,6),cells(plan)|{(5,2)}))
        command(page,'preview_descent');command(page,'confirm_descent')
        assert view(page)['generatedCampaign']['floorIndex']==1
        archived=save(page)['generatedCampaign']['archives'][0]
        assert archived['mechanismReceipts']==receipt,archived
        roundtrip(page)
        # Independent authored plans exercise a shared item cost and the free fallback.
        for kind,solution_id in [('item','qa.item'),('manual','qa.lever')]:
            authored=fixture(source,item_id,kind);state=command(page,'import_campaign',campaignPlan=authored)
            assert state.get('generatedCampaign',{}).get('id')==authored['id'],state.get('message')
            plan=save(page)['generatedCampaign']['plan']['floors'][0];approach(page,plan,solution_id)
            candidate=next(c for c in mechanism(page)['solutions'][0]['candidates'] if c['enabled']);before=resources(page)
            cost=preview_ui(page,solution_id,candidate)
            assert cost['manaBefore']==cost['manaAfter']
            if kind=='item':assert cost['itemCountBefore']-cost['itemCountAfter']==1
            page.locator('#confirm-mechanism').click();assert mechanism(page)['solved']
            if kind=='manual':assert resources(page)==before
            committed=resources(page);command(page,'confirm_mechanism');assert resources(page)==committed,'Duplicate item/manual commit changed resources'
            roundtrip(page)
            assert len(save(page)['generatedDungeon']['mechanismReceipts'])==1
        assert not errors,errors
        browser.close()
    print('PASS actual WASM generated optional shortcuts; learned actor eligibility; exact Mana/item/free previews; cancel/stale/reload; confirmed canonical movement/combat collision; duplicate safety; descent receipt archives; four responsive viewports')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8776')
    parser.add_argument('--browser',default=shutil.which('google-chrome') or shutil.which('chromium'))
    parser.add_argument('--screenshots',default='/workspace/scratch/mechanisms')
    run(parser.parse_args())


if __name__=='__main__':main()
