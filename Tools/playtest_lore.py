"""Browser checks for the story unlocks, safe-room economy, class trees and lore codex.

Run against the published WASM page, for example:
  python3 Tools/playtest_lore.py --url http://127.0.0.1:5188

Campaign progression uses only committed public game commands. UI assertions use
the visible controls and keep a separate clean browser profile per viewport.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:5188')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--screenshots', default='/tmp/dct-lore-qa')
args = parser.parse_args()
OUT = Path(args.screenshots)
OUT.mkdir(parents=True, exist_ok=True)
GAME_DATA = json.loads((Path(__file__).resolve().parents[1] / 'UnityPackage/Runtime/Data/game-content.json').read_text())


def wait(page, expression, timeout=30000):
    page.wait_for_function(expression, timeout=timeout)


def view(page):
    return page.evaluate('window.dungeon.getView()')


def save(page):
    raw = page.evaluate('window.dungeon.getSave()')
    return json.loads(raw) if isinstance(raw, str) else raw


def boot(page):
    page.goto(args.url, wait_until='domcontentloaded')
    wait(page, 'window.dungeon && window.dungeon.getView()')
    if page.locator('#welcome-dialog').evaluate('(d)=>d.open'):
        page.locator('#begin-button').click()
    if page.locator('#help-dialog').evaluate('(d)=>d.open'):
        page.locator('#help-dialog [data-close]').last.click()
    wait(page, "!document.querySelector('dialog[open]')")


def send(page, kind, **args_):
    page.evaluate('([kind,args])=>window.dungeon.command(kind,args)', [kind, args_])


def grid_click(page, x, y):
    point = page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y),b=document.querySelector('#battlefield').getBoundingClientRect();return{x:b.left+p.x,y:b.top+p.y}}''', [x, y])
    page.mouse.click(point['x'], point['y'])


def advance_story_to(page, target_floor):
    """Play campaign floors up to target_floor with legal moves and commits."""
    result = page.evaluate('''async()=>{
      const send=async(type,args={})=>JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','Dispatch',JSON.stringify({type,...args})));
      const sync=async()=>{const raw=await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','GetSave');await window.dungeon.loadSave(raw);return window.dungeon.getView();};
      let v=window.dungeon.getView(),steps=0,commits=0;
      const nearest=(c,us)=>Math.min(...us.filter(u=>u.team==='enemy'&&u.hp>0).map(u=>Math.abs(u.x-c.x)+Math.abs(u.y-c.y)));
      while(v.journey.floorNumber<${target_floor}&&steps++<800){
        if(v.screen==='camp'){
          if(!v.safeRoom.rested) v=await send('safe_room_rest');
          v=await send('start');continue;
        }
        if(v.screen==='explore'){
          const m=v.exploration;
          const point=m.points.find(p=>p.canInteract&&p.kind!=='encounter');
          if(point){v=await send('explore_interact',{targetId:point.id});continue;}
          const door=m.points.find(p=>p.canInteract&&p.kind==='encounter');
          if(door){v=await send('explore_interact',{targetId:door.id});continue;}
          let tile=m.tiles.filter(t=>t.reachable&&!t.blocked&&!t.revealed).sort((a,b)=>a.y-b.y||a.x-b.x)[0];
          if(!tile){const goal=m.points.find(p=>p.kind==='encounter');if(!goal)throw Error('Exploration has no encounter door');tile=m.tiles.filter(t=>t.reachable&&!t.blocked).sort((a,b)=>(Math.abs(a.x-goal.x)+Math.abs(a.y-goal.y))-(Math.abs(b.x-goal.x)+Math.abs(b.y-goal.y)))[0];}
          if(!tile)throw Error('No legal exploration destination');
          v=await send('explore_move',{x:tile.x,y:tile.y});continue;
        }
        if(v.screen==='defeat')throw Error('Defeat on story floor '+v.journey.floorNumber);
        if(v.screen==='victory'){
          if(v.rewards?.length)v=await send('choose_reward',{rewardId:v.rewards[0].id});
          v=await send('continue');continue;
        }
        if(v.screen!=='battle')throw Error('Unexpected story screen '+v.screen);
        const actor=v.units.find(u=>u.team==='player'&&u.hp>0&&!u.finished);
        if(!actor){v=await send('end_turn');continue;}
        v=await send('select',{unitId:actor.id});
        let current=v.units.find(u=>u.id===actor.id);
        if(current.acted){
          if(!current.moved&&v.canMove){const cell=v.reachable.filter(c=>c.cost>0).sort((a,b)=>nearest(a,v.units)-nearest(b,v.units)||a.cost-b.cost)[0];if(cell){v=await send('move',{unitId:actor.id,x:cell.x,y:cell.y});continue;}}
          v=await send('end_turn',{unitId:actor.id});continue;
        }
        const maxRange=Math.max(1,...v.abilities.filter(a=>a.target==='enemy'&&a.enabled).map(a=>a.range));
        if(v.canMove&&nearest(actor,v.units)>maxRange){const cell=v.reachable.filter(c=>c.cost>0).sort((a,b)=>nearest(a,v.units)-nearest(b,v.units)||a.cost-b.cost)[0];if(cell){v=await send('move',{unitId:actor.id,x:cell.x,y:cell.y});}}
        let chosen=null,score=-1;
        for(const ability of v.abilities.filter(a=>a.enabled))for(const targetId of ability.targetIds??[]){
          const preview=await send('preview',{unitId:actor.id,targetId,abilityId:ability.id});
          if(!preview.canConfirm)continue;
          const value=(preview.forecast??[]).reduce((sum,f)=>sum+(v.units.some(u=>u.id===f.targetId&&u.team==='enemy')?(f.beforeHp-f.afterHp)*10+(f.beforeHp>0&&f.afterHp===0?200:0):(f.afterHp-f.beforeHp)*5),0);
          if(value>score){score=value;chosen={unitId:actor.id,targetId,abilityId:ability.id};}
        }
        if(chosen&&score>0){v=await send('preview',chosen);if(!v.canConfirm)throw Error('Selected forecast became illegal');v=await send('confirm');commits++;continue;}
        v=await send('cancel');
        if(v.canMove){const cell=v.reachable.filter(c=>c.cost>0).sort((a,b)=>nearest(a,v.units)-nearest(b,v.units)||a.cost-b.cost)[0];if(cell){v=await send('move',{unitId:actor.id,x:cell.x,y:cell.y});continue;}}
        v=await send('wait',{unitId:actor.id});
      }
      if(v.screen!=='camp'||v.journey.floorNumber!==${target_floor})throw Error('Did not reach legal floor-'+${target_floor}+' safe room: '+v.screen+' floor '+v.journey?.floorNumber+' after '+steps+' commands');
      v=await sync();
      return {screen:v.screen,floor:v.journey.floorNumber,xp:v.xp,gold:v.home?.gold,steps,commits};
    }'''.replace('${target_floor}', str(target_floor)))
    return result


def check_journey_and_home(page, output):
    before = save(page)
    page.locator('#open-journey').click()
    wait(page, "document.querySelector('#journey-dialog')?.open")
    page.screenshot(path=str(output / 'journey-start.png'), full_page=True)
    page.locator('#review-journey-start').click()
    assert page.locator('#journey-start-warning').is_visible(), 'Journey reset confirmation did not explain replacement.'
    page.locator('#cancel-journey-start').click()
    assert save(page) == before, 'Canceling journey replacement changed the current run.'
    page.locator('#review-journey-start').click()
    page.locator('#confirm-journey-start').click()
    wait(page, "window.dungeon.getView().journey.active&&window.dungeon.getView().journey.floorNumber===1")
    page.locator('.safe-party > summary.panel-head').click()
    assert page.locator('#class-select').is_disabled(), 'Classes should remain locked on floor one.'
    assert 'Floor 3' in page.locator('label[for="class-select"]').inner_text(), 'Floor-one class lock should name its unlock floor.'
    page.locator('#class-search').fill('bard')
    filtered=page.locator('#class-select').evaluate('(s)=>Array.from(s.options).filter(o=>!o.hidden).length')
    assert 0 < filtered < page.locator('#class-select option').count(), 'Class search did not narrow the class choices.'
    page.screenshot(path=str(output / 'floor1-class-lock.png'), full_page=True)
    floor3=advance_story_to(page,3)
    assert floor3['floor']==3
    assert not page.locator('#class-select').is_disabled(), 'Class selection should unlock on Floor 3.'
    assert any(c['enabled'] for c in view(page)['classes']), 'No class choices became available on Floor 3.'
    page.locator('#class-search').fill('Bard')
    page.locator('#class-select').select_option('class.lore_bard')
    wait(page,"window.dungeon.getView().roster.find(r=>r.id==='crawler.carl').classId==='class.lore_bard'")
    page.screenshot(path=str(output / 'floor3-class-selected.png'), full_page=True)
    progression = advance_story_to(page,4)
    assert progression['floor'] == 4 and progression['commits'] > 0
    assert view(page)['home']['available'], 'Personal home must open at story floor four.'
    assert view(page)['home']['gold'] >= 50000
    page.locator('#open-home').click()
    wait(page, "document.querySelector('#home-dialog')?.open")
    initial = save(page)
    initial_gold = view(page)['home']['gold']
    personal = page.locator('[data-home-upgrade="home.personal_space"]')
    personal.click()
    wait(page, "window.dungeon.getView().home.forecast?.type==='upgrade'")
    assert view(page)['home']['forecast']['afterGold'] == initial_gold - 50000
    page.screenshot(path=str(output / 'home-purchase-forecast.png'), full_page=True)
    page.locator('#cancel-home-purchase').click()
    assert save(page) == initial, 'Canceling a home purchase changed the save or gold.'
    page.locator('[data-home-upgrade="home.personal_space"]').click()
    page.locator('#confirm-home-purchase').click()
    wait(page, "window.dungeon.getView().home.upgrades.find(u=>u.id==='home.personal_space').purchased")
    assert view(page)['home']['gold'] == initial_gold - 50000
    assert any(r['unlocked'] for r in view(page)['home']['rooms'] if r['kind']=='bedroom'), 'Space purchase did not unlock bedrooms.'
    page.screenshot(path=str(output / 'home-unlocked.png'), full_page=True)

    # Install the core rooms available from the real three-floor earnings.
    # The 255k studio is intentionally purchased after Floor 4's gold award.
    for upgrade_id in ('home.engineer_table', 'home.training', 'home.social_screen'):
        row = next(u for u in view(page)['home']['upgrades'] if u['id'] == upgrade_id)
        if not row['enabled']:
            continue
        page.locator(f'[data-home-upgrade="{upgrade_id}"]').click()
        wait(page, "window.dungeon.getView().home.forecast!==null")
        page.locator('#confirm-home-purchase').click()
        wait(page, f"window.dungeon.getView().home.upgrades.find(u=>u.id==={json.dumps(upgrade_id)}).purchased")
    # A trained crawler can only buy one session on the current floor.
    training_room = next((r for r in view(page)['home']['rooms'] if r['kind']=='training'), None)
    if training_room and training_room['unlocked']:
        page.locator(f'[data-home-room="{training_room["id"]}"]').click()
        page.locator('.home-training details summary').first.click()
        option = next((t for t in view(page)['home']['training'] if t['enabled']),None)
        if option:
            selector=f'[data-home-training-unit="{option["unitId"]}"][data-home-training-ability="{option["abilityId"]}"]'
            gold_before=view(page)['home']['gold']; uses_before=option['beforeUses']
            page.locator(selector).click()
            page.locator('#cancel-home-purchase').click()
            assert view(page)['home']['gold']==gold_before and next(t for t in view(page)['home']['training'] if t['unitId']==option['unitId'] and t['abilityId']==option['abilityId'])['beforeUses']==uses_before
            if not page.locator('.home-training details').first.evaluate('(d)=>d.open'):
                page.locator('.home-training details summary').first.click()
            page.locator(selector).click()
            page.locator('#confirm-home-purchase').click()
            wait(page, "window.dungeon.getView().home.forecast===null")
            trained=next(t for t in view(page)['home']['training'] if t['unitId']==option['unitId'] and t['abilityId']==option['abilityId'])
            assert not trained['enabled'] and ('floor' in trained['disabledReason'].lower() or 'already' in trained['disabledReason'].lower()), 'Training remains purchasable twice on the same floor.'
            page.screenshot(path=str(output / 'training-committed-once.png'), full_page=True)

    # Earn the next fixed campaign payout through Floor 4, then install the
    # studio and check that the committed recipe gives its actual bonus unit.
    if page.locator('#home-dialog').evaluate('(d)=>d.open'):
        page.locator('#done-home').click()
    floor5=advance_story_to(page,5)
    assert floor5['floor']==5 and floor5['gold']>=300000, f'Floor 4 victory did not supply the studio purchase: {floor5}'
    page.locator('#open-home').click()
    wait(page,"document.querySelector('#home-dialog')?.open")
    studio=next(u for u in view(page)['home']['upgrades'] if u['id']=='home.crafting_studio')
    assert studio['enabled'], f"Crafting Studio unexpectedly disabled: {studio['disabledReason']}"
    page.locator('[data-home-upgrade="home.crafting_studio"]').click()
    page.locator('#confirm-home-purchase').click()
    wait(page,"window.dungeon.getView().home.upgrades.find(u=>u.id==='home.crafting_studio').purchased")
    craft_room=next(r for r in view(page)['home']['rooms'] if r['kind']=='crafting')
    page.locator(f'[data-home-room="{craft_room["id"]}"]').click()
    page.locator('#done-home').click()
    page.locator('#open-development').click()
    wait(page,"document.querySelector('#development-dialog')?.open")
    page.locator('[data-development-tab="craft"]').click()
    recipes=view(page)['development']['recipes']
    recipe=next((r for r in recipes if r['enabled']),None)
    assert recipe, 'No crafting recipe is available with the story campaign supplies.'
    authored_recipe=next(r for r in GAME_DATA['development']['recipes'] if r['id']==recipe['id'])
    assert recipe['outputs'][0]['count']==authored_recipe['outputs'][0]['count']+1, 'Crafting Studio output forecast does not include its +1 bonus.'
    item_id=recipe['outputs'][0]['itemId']
    old_count=next((i['count'] for i in view(page)['items'] if i['id']==item_id),0)
    page.locator(f'[data-craft-recipe="{recipe["id"]}"]').click()
    page.locator('#confirm-development-operation').click()
    wait(page,f"window.dungeon.getView().items.find(i=>i.id==={json.dumps(item_id)}).count>{old_count}")
    item=next(i for i in view(page)['items'] if i['id']==item_id)
    assert item['count']==old_count+recipe['outputs'][0]['count'], 'Committed crafting result did not match its bonus-inclusive forecast.'
    page.screenshot(path=str(output/'craft-tool-bonus-committed.png'),full_page=True)
    page.locator('#done-development').click()

    home_save=save(page)
    page.reload(wait_until='domcontentloaded')
    wait(page,'window.dungeon && window.dungeon.getView().screen')
    assert save(page)==home_save, 'Home purchases or services did not survive reload.'
    page.screenshot(path=str(output / 'floor4-home-reloaded.png'), full_page=True)
    return progression


def check_tree_and_codex(page, output):
    # Runtime class branches unlock at floor three and expose all fourteen nodes.
    page.locator('#open-skill-tree').click()
    wait(page,"document.querySelector('#skill-tree-dialog')?.open")
    class_trees=view(page)['skillTree'].get('classTrees',[])
    assert class_trees, 'No class-specific skill trees appeared after floor three.'
    tree=next((t for t in class_trees if len(t['nodes'])==14),None)
    assert tree, f'Expected a 14-node class tree; counts={[len(t["nodes"]) for t in class_trees]}'
    page.locator('[data-tree-kind="class"]').click()
    page.locator('#skill-tree-crawler').select_option(tree['rosterId'])
    assert page.locator('[data-skill-node]').count()==14
    page.screenshot(path=str(output/'class-tree-floor3.png'),full_page=True)
    page.locator('#done-skill-tree').click()

    codex=page.context.new_page()
    errors=[];codex.on('pageerror',lambda e:errors.append(str(e)))
    codex.goto(args.url.rstrip('/')+'/codex.html#classes',wait_until='domcontentloaded')
    wait(codex,"document.querySelector('#codex-count')?.textContent.includes('classes')")
    class_status=codex.locator('#codex-count').inner_text()
    class_count=int(class_status.split(' of ')[1].split(' ')[0])
    assert class_count>=118 and codex.locator('.codex-card').count()==class_count, f'Codex class directory count/card mismatch: {class_status}'
    codex.locator('#codex-search').fill('Bard')
    assert codex.locator('.codex-card').count()>0,'Codex class search produced no result.'
    codex.locator('#codex-search').fill('')
    codex.locator('#codex-level').select_option('50')
    assert codex.locator('.codex-tree-node').count()>=14*class_count, 'Codex should expose fourteen nodes for each documented class profile.'
    codex.screenshot(path=str(output/'codex-classes-desktop.png'),full_page=True)
    codex.goto(args.url.rstrip('/')+'/codex.html#skills',wait_until='domcontentloaded')
    wait(codex,"document.querySelector('#codex-count')?.textContent.includes('88 of 88')")
    assert codex.locator('.codex-card').count()==88
    codex.locator('#codex-rank').select_option('20')
    codex.goto(args.url.rstrip('/')+'/codex.html#floors',wait_until='domcontentloaded')
    wait(codex,"document.querySelector('#codex-count')?.textContent.includes('18 of 18')")
    assert codex.locator('.codex-card').count()==18
    codex.goto(args.url.rstrip('/')+'/codex.html#enemies',wait_until='domcontentloaded')
    wait(codex,"document.querySelector('#codex-count')?.textContent.includes('16 of 16')")
    assert codex.locator('.codex-card').count()==16
    assert not errors,f'Codex browser errors: {errors}'
    codex.close()


def check_codex_mobile(browser):
    context=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
    page=context.new_page(); boot(page)
    page.goto(args.url.rstrip('/')+'/codex.html#classes',wait_until='domcontentloaded')
    wait(page,"document.querySelector('#codex-count')?.textContent.includes('classes')")
    rect=page.locator('#codex-nav').bounding_box()
    assert rect and rect['x']>=0 and rect['x']+rect['width']<=390,'Codex section navigation clips on phone.'
    class_status=page.locator('#codex-count').inner_text()
    class_count=int(class_status.split(' of ')[1].split(' ')[0])
    assert class_count>=118 and page.locator('.codex-card').count()==class_count
    page.screenshot(path=str(OUT/'codex-classes-phone.png'),full_page=True)
    page.goto(args.url.rstrip('/')+'/codex.html#skills',wait_until='domcontentloaded')
    wait(page,"document.querySelector('#codex-count')?.textContent.includes('88 of 88')")
    assert page.locator('.codex-card').count()==88
    context.close()


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1366,'height':768},device_scale_factor=1)
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        boot(page)
        progression=check_journey_and_home(page,OUT)
        check_tree_and_codex(page,OUT)
        assert not errors,f'Game page browser errors: {errors}'
        print(json.dumps({'floor4Journey':progression,'screenshots':str(OUT),'gameErrors':errors},indent=2))
        context.close()
        check_codex_mobile(browser)
        browser.close()


if __name__=='__main__':
    main()
