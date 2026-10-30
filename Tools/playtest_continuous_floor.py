"""Actual WASM smoke coverage for the continuous-floor hub and field lifecycle."""
import argparse
from playwright.sync_api import sync_playwright
from playtest_generated_adventure import command, view, position, distances, route, walk, reload_roundtrip
from playtest_procedural_maps import ready_runtime


def launch_floor(page, seed='continuous-floor-browser-qa'):
    ready_runtime(page)
    for selector in ['#begin-button', '[data-close="help-dialog"]']:
        button = page.locator(selector).last
        if button.is_visible():
            button.click()
    page.locator('[data-hub-station=depart]').click()
    page.locator('#generated-adventure-dialog').wait_for(state='visible', timeout=30000)
    page.locator('#adventure-seed').fill(seed)
    assert page.locator('#adventure-layout').input_value() == 'chambers'
    page.locator('#begin-generated-adventure').click()
    page.wait_for_function("window.dungeon.getView().generatedDungeon?.floorPlan || document.querySelector('#generated-adventure-status').textContent.startsWith('Could not')", timeout=120000)
    assert view(page).get('generatedDungeon', {}).get('floorPlan'), page.locator('#generated-adventure-status').inner_text()
    page.locator('#generated-adventure-dialog').wait_for(state='hidden')
    ready_runtime(page, native=True)
    assert (view(page)['customMap']['width'], view(page)['customMap']['height']) == (40, 32)
    return view(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8774')
    parser.add_argument('--browser', default='/usr/bin/google-chrome')
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.add_init_script("if(!sessionStorage.qaFloor){localStorage.clear();localStorage.setItem('dct.help.seen','1');sessionStorage.qaFloor='1'}")
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/index.html')
        state=launch_floor(page)
        expected=state['customMap']
        reload_roundtrip(page,expected)
        floor_before=view(page)['generatedDungeon']
        page.locator('#field-menu-button').click()
        page.locator('[data-field-action=home]').click()
        page.wait_for_function("window.dungeon.getView().screen==='camp'")
        assert view(page)['screen']=='camp'
        page.locator('[data-hub-station=depart]').click()
        page.wait_for_function("window.dungeon.getView().screen==='explore'",timeout=30000)
        assert view(page)['screen']=='explore'
        assert view(page)['generatedDungeon']==floor_before, 'Safe-room return changed floor progress'
        cells={(x,y) for y in range(32) for x in range(40)}-{(t['x'],t['y']) for t in expected['tiles'] if t.get('blocked')}
        # Stay far from authored encounter triggers while testing held input.
        plan=state['generatedDungeon']['floorPlan']
        danger=set()
        for enemy in expected['enemies']:
            danger.update(c for c,d in distances((enemy['x'],enemy['y']),cells).items() if d<=5)
        safe=cells-danger
        reachable=distances(position(page),safe)
        runs=[(c,dx,dy,key) for c in reachable for dx,dy,key in [(1,0,'d'),(-1,0,'a'),(0,1,'s'),(0,-1,'w')] if all((c[0]+dx*i,c[1]+dy*i) in safe for i in (1,2))]
        assert runs,'No safe input run'
        anchor,dx,dy,key=min(runs,key=lambda r:reachable[r[0]])
        walk(page,route(position(page),anchor,safe))
        long_runs=[]
        for c in reachable:
            for sx,sy,sk in [(1,0,'d'),(-1,0,'a'),(0,1,'s'),(0,-1,'w')]:
                length=0
                while (c[0]+sx*(length+1),c[1]+sy*(length+1)) in safe:
                    length+=1
                long_runs.append((length,c,sx,sy,sk))
        length,anchor,dx,dy,key=max(long_runs,key=lambda r:r[0])
        assert length>=6,'Fixture needs six safe cardinal steps for movement cadence'
        walk(page,route(position(page),anchor,safe))
        page.evaluate("""()=>{window.qaFrames=[];window.qaFrameRunning=true;let previous=performance.now();function frame(now){window.qaFrames.push(now-previous);previous=now;if(window.qaFrameRunning)requestAnimationFrame(frame)}requestAnimationFrame(frame)}""")
        page.locator('#battlefield').focus()
        page.keyboard.down(key)
        page.wait_for_timeout(1000)
        page.keyboard.up(key)
        page.evaluate('window.qaFrameRunning=false')
        moved=abs(position(page)[0]-anchor[0])+abs(position(page)[1]-anchor[1])
        timing=page.evaluate('({frames:qaFrames.length,maxGapMs:Math.max(...qaFrames),meanGapMs:qaFrames.reduce((a,b)=>a+b,0)/qaFrames.length})')
        elapsed=timing['frames']*timing['meanGapMs']/1000
        print({'requestedHoldSeconds':1,'observedSeconds':round(elapsed,3),'steps':moved,'stepsPerSecond':round(moved/elapsed,2),'frameTiming':timing},flush=True)
        assert moved>=4 and moved<=8, f'Held movement cadence regressed: {moved} steps/second'
        # Resume the shorter hold/release assertion at its new position.
        walk(page,route(position(page),anchor,safe))
        page.locator('#battlefield').focus()
        page.keyboard.down(key)
        page.wait_for_function('p=>{const s=window.dungeon.getView().generatedDungeon;return Math.abs(s.x-p[0])+Math.abs(s.y-p[1])>=2}',arg=list(anchor),timeout=10000)
        page.keyboard.up(key)
        page.wait_for_timeout(400)
        stopped=position(page)
        page.wait_for_timeout(500)
        assert position(page)==stopped,'Released keyboard kept moving'
        autosaved=page.evaluate("JSON.parse(localStorage.getItem('dungeon-crawler-tactics.save.v1'))")
        assert (autosaved['generatedDungeon']['x'],autosaved['generatedDungeon']['y'])==stopped, 'Settled movement was not autosaved'
        page.locator('#field-menu-button').click()
        page.locator('#field-menu').wait_for(state='visible')
        page.keyboard.down(key)
        page.wait_for_timeout(600)
        page.keyboard.up(key)
        assert position(page)==stopped,'Menu allowed walking'
        page.locator('#field-menu [data-close-field]').click()
        for width,height in [(390,844),(1440,1000),(320,740),(844,390)]:
            page.set_viewport_size({'width':width,'height':height})
            page.wait_for_timeout(150)
            for selector in ['#battlefield','#field-map-button','#field-menu-button','.walk-pad']:
                box=page.locator(selector).bounding_box()
                assert box and box['x']>=-1 and box['y']>=-1 and box['x']+box['width']<=width+1 and box['y']+box['height']<=height+1,(width,height,selector,box)
        # Equip through the real field dialog; maximum stats change without healing.
        page.set_viewport_size({'width':1440,'height':1000})
        before=view(page)
        owner=next(r for r in before['roster'] if r['selected'])
        gear=next(g for g in before['equipment'] if g['owned'] and not g.get('equippedUnitId') and (g['hpBonus'] or g['manaBonus'] or g['moveBonus']))
        page.locator('#field-menu-button').click()
        page.locator('[data-field-action=equipment]').click()
        page.locator(f'[data-equipment-slot="{gear["slot"]}"]').click()
        page.locator(f'[data-equip="{gear["id"]}"]').click()
        page.locator('#equipment-confirm-dialog').wait_for(state='visible')
        page.locator('#confirm-equipment').click()
        page.wait_for_function('id=>window.dungeon.getView().equipment.some(g=>g.id===id&&g.equippedUnitId)',arg=gear['id'])
        after=next(r for r in view(page)['roster'] if r['id']==owner['id'])
        assert after['hp']==owner['hp'] and after['energy']==owner['energy'], 'Field equipment healed party'
        assert after['maxHp']==owner['maxHp']+gear['hpBonus']
        assert after['maxEnergy']==owner['maxEnergy']+gear['manaBonus']
        assert after['move']==owner['move']+gear['moveBonus']
        page.locator('#done-loadout').click()
        # Validated checkpoint placement isolates cache claims from encounter routing.
        saved=page.evaluate('window.dungeon.getSave().then(JSON.parse)')
        cache=next(p for p in plan['discoveries'] if p['kind']=='cache')
        saved['generatedDungeon']['x']=cache['x']; saved['generatedDungeon']['y']=cache['y']
        if not any(c['x']==cache['x'] and c['y']==cache['y'] for c in saved['generatedDungeon']['revealed']):
            saved['generatedDungeon']['revealed'].append({'x':cache['x'],'y':cache['y']})
        page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))',saved)
        assert position(page)==(cache['x'],cache['y']),view(page).get('message')
        count=next(i['count'] for i in view(page)['items'] if i['id']==cache['itemId'])
        command(page,'explore_interact',targetId=cache['id'])
        command(page,'explore_interact',targetId=cache['id'])
        assert next(i['count'] for i in view(page)['items'] if i['id']==cache['itemId'])==count+cache['count']
        assert view(page)['generatedDungeon']['claimedIds'].count(cache['id'])==1
        reload_roundtrip(page,expected)
        # Explicit weak-enemy authored fixture exercises real C# combat, without mocked results.
        import copy
        combat_plan=copy.deepcopy(plan)
        for enemy in combat_plan['map']['enemies']:
            enemy['hp']=1
            enemy['move']=1
        state=command(page,'import_floor',floorPlan=combat_plan)
        assert state['screen']=='explore',state.get('message')
        assert state['generatedDungeon']['floorPlan']==combat_plan, state.get('message')
        group=combat_plan['groups'][0]
        state=walk(page,route(position(page),(group['x'],group['y']),cells))
        assert state['screen']=='battle',state.get('message')
        active=state['generatedDungeon']['activeGroupId']
        active_group=next(g for g in combat_plan['groups'] if g['id']==active)
        assert {u['id'] for u in state['units'] if u['team']=='enemy'}==set(active_group['enemyIds'])
        result=page.evaluate("""async()=>{
          const send=async(type,args={})=>JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','Dispatch',JSON.stringify({type,...args})));
          let v=window.dungeon.getView(),ticks=0,actions=0;
          while(v.screen==='battle'&&ticks++<150){
            const actor=v.units.find(u=>u.team==='player'&&u.hp>0&&!u.finished);
            if(!actor)throw Error('No ready actor');
            v=await send('select',{unitId:actor.id});
            let best=null;
            for(const a of v.abilities.filter(a=>a.enabled&&a.target==='enemy'))for(const targetId of a.targetIds){
              const args={unitId:actor.id,abilityId:a.id,targetId};
              const p=await send('preview',args);
              if(p.canConfirm&&p.forecast.some(f=>f.afterHp<f.beforeHp))best=args;
            }
            if(best){await send('preview',best);v=await send('confirm');actions++;continue;}
            v=await send('cancel');
            if(v.canMove){const enemies=v.units.filter(u=>u.team==='enemy'&&u.hp>0);const distance=c=>Math.min(...enemies.map(e=>Math.abs(e.x-c.x)+Math.abs(e.y-c.y)));const next=v.reachable.filter(c=>c.cost>0).sort((a,b)=>distance(a)-distance(b)||a.cost-b.cost)[0];if(next){v=await send('move',{unitId:actor.id,x:next.x,y:next.y});continue;}}
            v=await send('end_turn',{unitId:actor.id});
          }
          if(v.screen!=='victory')throw Error('Real combat did not win '+v.screen+' ticks='+ticks);
          if(v.rewards.length)v=await send('choose_reward',{rewardId:v.rewards[0].id});
          v=await send('continue');
          await window.dungeon.loadSave(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','GetSave'));
          return {screen:v.screen,actions,ticks};
        }""")
        assert result['screen']=='explore' and result['actions']>0,result
        done=view(page)['generatedDungeon']
        assert done['defeatedGroupIds']==[active] and not done['cleared']
        assert len(combat_plan['groups'])>1 and done['activeGroupId'] is None
        reload_roundtrip(page,combat_plan['map'])
        assert not errors,errors
        browser.close()
    print('PASS actual WASM hub auto-approach, seeded 40x32 floor, exact reload, safe-room resume, held/released keyboard, menu pause, four responsive viewports, field equipment actual stats/no healing, cache exactly once, real weak-enemy combat clears only its group')

if __name__=='__main__':
    main()
