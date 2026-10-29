"""Persistent generated-campaign QA against actual C# WASM (never a mocked runtime)."""
import argparse
import copy
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_generated_adventure import command, view, position, route, walk, distances
from playtest_continuous_floor import launch_floor
from playtest_procedural_maps import ready_runtime, canonical_map

SAVE_KEY = 'dungeon-crawler-tactics.save.v1'


def save(page):
    return page.evaluate('window.dungeon.getSave().then(JSON.parse)')


def roundtrip(page):
    before = save(page)
    page.evaluate('({key,value})=>localStorage.setItem(key,JSON.stringify(value))', {'key':SAVE_KEY,'value':before})
    page.reload()
    ready_runtime(page)
    after = save(page)
    for key in ['generatedCampaign','generatedDungeon','customMap','roster','inventory','equipped','development','xp','screen']:
        assert before.get(key) == after.get(key), f'Reload changed {key}'
    return after


def fixture(source):
    """Explicit small authored plans; reuse only validated enemy class and cache item IDs."""
    enemy = source['map']['enemies'][0]
    item = next(p['itemId'] for p in source['discoveries'] if p['kind']=='cache')
    floors=[]
    for depth in range(2):
        floors.append({'schemaVersion':1,'seed':701+depth,
          'entrance':{'x':1,'y':1},'exit':{'x':8,'y':6},
          'map':{'schemaVersion':1,'label':f'QA authored depth {depth+1}', 'width':10,'height':8,
            'tiles':[{'x':4,'y':y,'blocked':True,'tags':[]} for y in range(3+depth,8)],
            'placements':[], 'playerSpawns':[{'x':1,'y':1},{'x':2,'y':1},{'x':1,'y':2},{'x':2,'y':2}],
            'enemies':[dict(copy.deepcopy(enemy),id=f'custom.enemy.qa{depth}',x=6,y=2,hp=1,move=1,energy=0)]},
          'groups':[{'id':f'qa.group{depth}','label':'QA sentry','kind':'visible','x':6,'y':2,'enemyIds':[f'custom.enemy.qa{depth}']}],
          'discoveries':[{'id':f'qa.cache{depth}','label':'QA cache','description':'Supplies recovered','kind':'cache','itemId':item,'count':2,'x':2,'y':1},
                         {'id':f'qa.objective{depth}','label':'QA seal','description':'Seal recovered','kind':'objective','x':8,'y':5}]})
    return {'schemaVersion':1,'id':'qa.authored.campaign','label':'QA persistent expedition','seed':700,'floors':floors}


def assert_authored(actual, expected):
    if isinstance(expected,dict):
        for key,value in expected.items():
            assert key in actual,key
            assert_authored(actual[key],value)
    elif isinstance(expected,list):
        assert len(actual)==len(expected)
        for a,e in zip(actual,expected):assert_authored(a,e)
    else:assert actual==expected,(actual,expected)


def cells(plan):
    return {(x,y) for y in range(plan['map']['height']) for x in range(plan['map']['width'])} - {(t['x'],t['y']) for t in plan['map']['tiles'] if t.get('blocked')}


def win_battle(page):
    # Dispatch real C# previews/actions. Never alter a save or fabricate victories.
    result = page.evaluate("""async()=>{
      const send=async(type,args={})=>JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','Dispatch',JSON.stringify({type,...args})));
      let v=window.dungeon.getView(),ticks=0,actions=0;
      while(v.screen==='battle'&&ticks++<150){
        const actor=v.units.find(u=>u.team==='player'&&u.hp>0&&!u.finished);
        if(!actor)throw Error('No ready actor');
        v=await send('select',{unitId:actor.id});let best=null;
        for(const a of v.abilities.filter(a=>a.enabled&&a.target==='enemy'))for(const targetId of a.targetIds){
          const args={unitId:actor.id,abilityId:a.id,targetId};const p=await send('preview',args);
          if(p.canConfirm&&p.forecast.some(f=>f.afterHp<f.beforeHp))best=args;
        }
        if(best){await send('preview',best);v=await send('confirm');actions++;continue;}
        v=await send('cancel');
        if(v.canMove){const enemies=v.units.filter(u=>u.team==='enemy'&&u.hp>0);const distance=c=>Math.min(...enemies.map(e=>Math.abs(e.x-c.x)+Math.abs(e.y-c.y)));const next=v.reachable.filter(c=>c.cost>0).sort((a,b)=>distance(a)-distance(b)||a.cost-b.cost)[0];if(next){v=await send('move',{unitId:actor.id,x:next.x,y:next.y});continue;}}
        v=await send('end_turn',{unitId:actor.id});
      }
      if(v.screen!=='victory')throw Error('Combat failed '+v.screen+' ticks='+ticks);
      if(v.rewards.length)v=await send('choose_reward',{rewardId:v.rewards[0].id});
      v=await send('continue');await window.dungeon.loadSave(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','GetSave'));
      return {screen:v.screen,actions};
    }""")
    assert result['screen']=='explore' and result['actions']>0, result


def clear_floor(page, plan):
    cache=plan['discoveries'][0]
    walk(page,route(position(page),(cache['x'],cache['y']),cells(plan)))
    before=next(i['count'] for i in view(page)['items'] if i['id']==cache['itemId'])
    command(page,'explore_interact',targetId=cache['id'])
    command(page,'explore_interact',targetId=cache['id'])
    assert next(i['count'] for i in view(page)['items'] if i['id']==cache['itemId'])==before+2
    group=plan['groups'][0]
    walk(page,route(position(page),(group['x']-1,group['y']),cells(plan)))
    assert view(page)['screen']=='battle',view(page).get('message')
    roundtrip(page)
    win_battle(page)
    progress=view(page)['generatedDungeon']
    assert progress['cleared'] and progress['defeatedGroupIds']==[group['id']]
    objective=plan['discoveries'][1]
    walk(page,route(position(page),(objective['x'],objective['y']),cells(plan)))
    command(page,'explore_interact',targetId=objective['id'])
    walk(page,route(position(page),(plan['exit']['x'],plan['exit']['y']),cells(plan)))
    assert view(page)['generatedCampaign']['canDescend']


def accessible(page, out, label):
    for width,height in [(390,844),(1440,1000),(320,740),(844,390)]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(150)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), 'Horizontal overflow'
        for selector in ['#confirm-descent','#cancel-descent']:
            box=page.locator(selector).bounding_box()
            assert box and box['x']>=0 and box['y']>=0 and box['x']+box['width']<=width+1 and box['y']+box['height']<=height+1,(selector,box)
            assert page.locator(selector).is_enabled()
        page.screenshot(path=str(out/f'{label}-{width}.png'))
    page.set_viewport_size({'width':1440,'height':1000})


def open_descent(page):
    page.locator('[data-explore-interact="generated.exit"]').click()
    page.locator('#descent-dialog').wait_for(state='visible')
    assert view(page)['generatedCampaign']['canConfirmDescent']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://localhost:8774')
    parser.add_argument('--browser',default=shutil.which('google-chrome') or shutil.which('chromium') or '/usr/bin/google-chrome')
    parser.add_argument('--screenshots',default='/workspace/scratch/generated-campaign')
    args=parser.parse_args();out=Path(args.screenshots);out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.add_init_script("if(!sessionStorage.qaCampaign){localStorage.clear();localStorage.setItem('dct.help.seen','1');sessionStorage.qaCampaign='1'}")
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url.rstrip('/')+'/index.html')
        launched=launch_floor(page,'persistent-campaign-browser-qa')
        assert launched.get('generatedCampaign',{}).get('totalFloors')==3,'Hub must launch three-depth campaign'
        initial=save(page);plans=initial['generatedCampaign']['plan']['floors']
        initial_bytes=len(json.dumps(initial,separators=(',',':')).encode())
        print({'defaultCampaignSaveBytes':initial_bytes,'floors':len(plans)},flush=True)
        assert len({json.dumps(f['map'],sort_keys=True) for f in plans})==3,'Depth maps must differ'
        assert len({f['seed'] for f in plans})==3,'Depth seeds must differ'
        page.screenshot(path=str(out/'launched-desktop.png'))
        roundtrip(page)
        # Real held movement and home/resume retain every realized future plan.
        plan=plans[0];safe=cells(plan)
        for enemy in plan['map']['enemies']:
            safe-=set(c for c,d in distances((enemy['x'],enemy['y']),cells(plan)).items() if d<=5)
        reachable=distances(position(page),safe)
        runs=[(c,dx,dy,key) for c in reachable for dx,dy,key in [(1,0,'d'),(-1,0,'a'),(0,1,'s'),(0,-1,'w')] if all((c[0]+dx*i,c[1]+dy*i) in safe for i in (1,2))]
        assert runs,'No safe two-step hold run'
        anchor,dx,dy,key=min(runs,key=lambda r:reachable[r[0]])
        walk(page,route(position(page),anchor,safe));page.locator('#battlefield').focus();page.keyboard.down(key)
        page.wait_for_function('p=>{const d=window.dungeon.getView().generatedDungeon;return Math.abs(d.x-p[0])+Math.abs(d.y-p[1])>=2}',arg=list(anchor),timeout=10000)
        page.keyboard.up(key);page.wait_for_timeout(400);stopped=position(page);page.wait_for_timeout(400)
        assert stopped==position(page),'Released hold continued moving'
        progress=save(page)['generatedDungeon']
        page.locator('#field-menu-button').click();page.locator('[data-field-action=home]').click()
        page.wait_for_function("window.dungeon.getView().screen==='camp'")
        page.locator('[data-hub-station=depart]').click();page.wait_for_function("window.dungeon.getView().screen==='explore'")
        assert save(page)['generatedDungeon']==progress
        assert save(page)['generatedCampaign']['plan']['floors']==plans
        authored=fixture(plans[0]);state=command(page,'import_campaign',campaignPlan=authored)
        assert state.get('generatedCampaign',{}).get('id')==authored['id'],state.get('message')
        accepted=save(page)['generatedCampaign']['plan']
        assert_authored(accepted,authored)
        authored=accepted
        # Equip through field UI and observe actual stats, without healing.
        before=view(page);owner=next(r for r in before['roster'] if r['selected'])
        gear=next(g for g in before['equipment'] if g['owned'] and not g.get('equippedUnitId') and (g['hpBonus'] or g['manaBonus'] or g['moveBonus']))
        page.locator('#field-menu-button').click();page.locator('[data-field-action=equipment]').click()
        page.locator(f'[data-equip="{gear["id"]}"]').click()
        page.wait_for_function('id=>window.dungeon.getView().equipment.some(g=>g.id===id&&g.equippedUnitId)',arg=gear['id'])
        after=next(r for r in view(page)['roster'] if r['id']==owner['id'])
        assert (after['hp'],after['energy'])==(owner['hp'],owner['energy'])
        assert after['maxHp']==owner['maxHp']+gear['hpBonus']
        assert after['maxEnergy']==owner['maxEnergy']+gear['manaBonus']
        assert after['move']==owner['move']+gear['moveBonus']
        page.locator('#done-loadout').click()
        clear_floor(page,authored['floors'][0]);roundtrip(page)
        baseline=save(page)
        assert baseline['development']['practice'],'Actual combat recorded no practice'
        readiness=page.evaluate("async()=>JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','Dispatch',JSON.stringify({type:'explore_interact',targetId:'generated.exit'})))")
        assert readiness['generatedCampaign']['floorIndex']==0 and not readiness['generatedCampaign']['canConfirmDescent'],'Core exit interaction skipped preview'
        open_descent(page);accessible(page,out,'descent')
        page.locator('#cancel-descent').click();page.locator('#descent-dialog').wait_for(state='hidden')
        assert save(page)['generatedCampaign']==baseline['generatedCampaign']
        assert not view(page)['generatedCampaign']['canConfirmDescent']
        # An intervening command invalidates a real preview, and reload never restores it.
        command(page,'preview_descent');command(page,'explore_step',x=0,y=-1);command(page,'explore_step',x=0,y=1);command(page,'confirm_descent')
        assert view(page)['generatedCampaign']['floorIndex']==0,'Changed revision accepted stale confirmation'
        command(page,'preview_descent');roundtrip(page);command(page,'confirm_descent')
        assert view(page)['generatedCampaign']['floorIndex']==0,'Reload retained preview token'
        open_descent(page);carried=save(page);page.locator('#confirm-descent').click()
        page.wait_for_function('window.dungeon.getView().generatedCampaign.floorIndex===1')
        descended=save(page)
        assert len(descended['generatedCampaign']['archives'])==1
        archived=copy.deepcopy(descended['generatedCampaign']['archives'][0])
        assert archived.get('floorPlan') is None,'Archive duplicated realized floor plan'
        archived['floorPlan']=descended['generatedCampaign']['plan']['floors'][0]
        assert archived==carried['generatedDungeon'], {k:(archived.get(k),v) for k,v in carried['generatedDungeon'].items() if archived.get(k)!=v}
        assert descended['generatedCampaign']['plan']==authored
        assert canonical_map(descended['customMap'])==canonical_map(authored['floors'][1]['map'])
        for key in ['roster','inventory','equipped','development','xp']:
            assert descended[key]==carried[key],f'Descent changed/healed {key}'
        command(page,'confirm_descent')
        assert save(page)['generatedCampaign']==descended['generatedCampaign'],'Double confirmation duplicated descent'
        roundtrip(page);clear_floor(page,authored['floors'][1]);open_descent(page)
        page.locator('#confirm-descent').click();page.wait_for_function("window.dungeon.getView().screen==='complete'")
        assert view(page)['generatedCampaign']['complete'] and view(page)['generatedCampaign']['completedFloors']==2
        roundtrip(page);page.screenshot(path=str(out/'complete-desktop.png'))
        old=command(page,'import_floor',floorPlan=authored['floors'][0])
        assert old['screen']=='explore' and not old.get('generatedCampaign'),'Standalone floor import regressed'
        assert canonical_map(old['customMap'])==canonical_map(authored['floors'][0]['map'])
        assert not errors,errors
        browser.close()
    print('PASS real WASM three-depth UI launch; motion/home/reload; authored two-depth combat/rewards/cache/objective; actual gear; cancel/stale/reload/double-confirm safety; exact plans/archives/resources; final completion; desktop/phone descent controls; standalone compatibility')

if __name__=='__main__':main()
