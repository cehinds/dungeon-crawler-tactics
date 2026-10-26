"""Final public-UI regression: legal campaign, real canvas picking and modal commits."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_neighborhood import boot,view,save,wait,approach

def select_ability(page, ability_id):
    """Choose a primary shortcut or open the complete action book."""
    shortcut = page.locator('[data-ability="' + ability_id + '"]')
    if shortcut.count():
        shortcut.click()
    else:
        page.locator('#open-actions').click()
        page.locator('[data-modal-ability="' + ability_id + '"]').click()


def snap(page,out,name):
    page.wait_for_timeout(150)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow: '+name
    page.screenshot(path=str(out/(name+'.png')),full_page=True)

def cell(page,x,y):
    page.locator('#battlefield').scroll_into_view_if_needed()
    p=page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y),b=document.querySelector('#battlefield').getBoundingClientRect();return {x:p.x+b.left,y:p.y+b.top}}''',[x,y])
    page.mouse.click(p['x'],p['y'])

def end(page):
    page.locator('#end-turn').click();wait(page,"document.querySelector('#end-turn-dialog')?.open")
    page.locator('#confirm-end-turn').click()

def run(browser,args,w,h):
    out=Path(args.screenshots)/str(w);out.mkdir(parents=True,exist_ok=True)
    context=browser.new_context(viewport={'width':w,'height':h},is_mobile=w<600,has_touch=w<600)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    try:
        boot(page,args.url);initial=save(page);snap(page,out,'camp')
        # Actual safe-room menus, compared with the separately authored menu atlas.
        for selector,name in [('[data-equipment]','equipment'),('[data-skills]','skills')]:
            page.locator(selector).first.click();snap(page,out,name)
            page.keyboard.press('Escape');wait(page,"!document.querySelector('dialog[open]')")
        page.locator('#open-development').click();page.locator('[data-development-tab="craft"]').click()
        for recipe,item in [('recipe.coolant_snare','item.coolant_snare'),('recipe.shock_snare','item.shock_snare')]:
            button=page.locator('[data-craft-recipe="'+recipe+'"]');assert button.is_enabled()
            before=save(page);button.click();snap(page,out,recipe+'-preview')
            assert save(page)==before
            page.locator('#cancel-development-operation').click();assert save(page)==before
            button.click();page.locator('#confirm-development-operation').click()
            wait(page,'window.dungeon.getView().items.some(i=>i.id==='+json.dumps(item)+'&&i.count>0)')
        page.locator('#done-development').click()
        page.locator('#quick-enter').click();wait(page,"window.dungeon.getView().screen==='explore'")
        snap(page,out,'exploration')
        door=approach(page,'@encounter');page.locator('[data-explore-interact="'+door['id']+'"]').click()
        wait(page,"window.dungeon.getView().screen==='battle'")
        # Four actual pointer picks after camera rotation, maintaining the same actor.
        rotations=[]
        for r in range(4):
            if r and page.locator('#camera-toggle').count() and not page.locator('#zoom-in').is_visible(): page.locator('#camera-toggle').click()
            if r: page.locator('#rotate-right').click()
            selected=view(page)['selectedUnitId'];u=next(u for u in view(page)['units'] if u['id']==selected)
            projected=page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y);return window.dungeon.scene.screenToCell(p.x,p.y)}''',[u['x'],u['y']])
            assert projected['x']==u['x'] and projected['y']==u['y'],projected
            cell(page,u['x'],u['y']);assert view(page)['selectedUnitId']==selected
            rotations.append(page.locator('#compass-label').inner_text())
        snap(page,out,'battle-rotated')
        # Self terrain action uses the same pointer picking path as a player.
        page.locator('#open-actions').click();snap(page,out,'action-book')
        page.locator('[data-modal-ability="ability.carl_bomb"]').click()
        actor=view(page)['selectedUnitId'];u=next(u for u in view(page)['units'] if u['id']==actor)
        target=next(t for t in view(page)['reachable'] if t['cost']>0)
        before=save(page);cell(page,target['x'],target['y']);wait(page,'window.dungeon.getView().canConfirm')
        snap(page,out,'action-preview');assert save(page)==before,'Action preview mutated save'
        page.locator('#detail-cancel-forecast').click();assert save(page)==before,'Cancel mutated save'
        select_ability(page, 'ability.carl_bomb');cell(page,target['x'],target['y']);wait(page,'window.dungeon.getView().canConfirm')
        page.locator('#detail-confirm-forecast').click();wait(page,'!window.dungeon.getView().canConfirm')
        assert view(page)['canMove'] and next(u for u in view(page)['units'] if u['id']==actor)['acted']
        tile=next(t for t in view(page)['reachable'] if t['cost']>0);cell(page,tile['x'],tile['y'])
        wait(page,'!window.dungeon.getView().canMove')
        # Enemy phase may not run before the entire party finishes.
        round_before=view(page)['round'];finished=[]
        for _ in range(4):
            current=view(page);actor=current['selectedUnitId'];finished.append(actor)
            if actor=='crawler.donut':
                item=next(i for i in current['items'] if i['id']=='item.shock_snare')
                tile=next(t for t in current['reachable'] if t['cost']==1 and 'tile.'+str(t['x'])+'.'+str(t['y']) in item['targetIds'])
                old_hp=next(u['hp'] for u in current['units'] if u['id']==actor)
                page.locator('[data-drawer="items"]').click();page.locator('[data-item="item.shock_snare"]').click();cell(page,tile['x'],tile['y']);wait(page,'window.dungeon.getView().canConfirm')
                snap(page,out,'shock-trap-preview');page.locator('#detail-confirm-forecast').click();wait(page,'!window.dungeon.getView().canConfirm')
                snap(page,out,'shock-trap-placed');cell(page,tile['x'],tile['y']);wait(page,'!window.dungeon.getView().canMove')
                changed=next(u for u in view(page)['units'] if u['id']==actor)
                assert changed['hp']==old_hp-5 and 'status.shocked' in changed['tags'],changed
                assert 'surface.trap_shock' not in next(t['tags'] for t in view(page)['tiles'] if t['x']==tile['x'] and t['y']==tile['y'])
                snap(page,out,'shock-trap-triggered')
            if actor=='crawler.katia':
                select_ability(page, 'ability.katia_shapeshift')
                wait(page,"document.querySelector('#character-sheet-dialog')?.open")
                forms=page.locator('[data-sheet-form]');assert forms.count()==4 and sum(f['id']!='form.baseline' for f in view(page)['forms'])==3, 'Katia must have three alternate form choices plus baseline'
                before=save(page);page.locator('[data-sheet-form="form.strider"]').click();wait(page,'window.dungeon.getView().canConfirm')
                snap(page,out,'form-preview');assert save(page)==before
                page.locator('#detail-cancel-forecast').click();assert save(page)==before
                if page.locator('#character-sheet-dialog').count() and page.locator('#character-sheet-dialog').evaluate('d=>d.open'): page.locator('#done-character-sheet').click()
            if len(finished)<4: assert current['round']==round_before,'Enemy acted before party finished'
            end(page)
        wait(page,'window.dungeon.getView().round>'+str(round_before))
        assert len(set(finished))==4,finished
        snap(page,out,'after-enemy-phase')
        # Save is produced by real committed commands; reload via the actual origin.
        page.wait_for_timeout(600);checkpoint=save(page)
        page.reload(wait_until='domcontentloaded');wait(page,'window.dungeon?.getView()?.screen')
        assert save(page)==checkpoint,'Actual campaign reload changed state'
        snap(page,out,'reloaded')
        atlas=context.new_page();atlas.goto(args.url+'/menu-atlas.html');atlas.screenshot(path=str(out/'menu-atlas.png'),full_page=True);atlas.close()
        assert not errors,errors
        return {'viewport':[w,h],'rotations':rotations,'partyBeforeEnemy':finished,'previewCancelCommit':True,'craftedTrapPlacedAndTriggered':True,'formChoices':3,'reload':True,'browserErrors':errors,'screenshots':str(out)}
    except Exception:
        page.screenshot(path=str(out/'failure.png'),full_page=True)
        (out/'failure-view.json').write_text(json.dumps(view(page),indent=2));raise
    finally:context.close()

def run_favor(browser,args,w,h):
    out=Path(args.screenshots)/str(w);context=browser.new_context(viewport={'width':w,'height':h});page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    try:
        boot(page,args.url)
        authored={'schemaVersion':1,'label':'Public workshop reaction QA','width':8,'height':8,'tiles':[{'x':2,'y':2,'blocked':False,'tags':['surface.oil']}],'playerSpawns':[{'x':1,'y':1},{'x':0,'y':1},{'x':1,'y':0},{'x':0,'y':0}],'enemies':[],'placements':[]}
        path=out/'legal-workshop.json';path.write_text(json.dumps(authored))
        page.locator('#save-button').click();page.locator('#import-map-file').set_input_files(str(path));wait(page,"window.dungeon.getView().screen==='battle'")
        if page.locator('#save-dialog').evaluate('d=>d.open'):page.locator('#save-dialog [data-close]').last.click()
        select_ability(page, 'ability.carl_bomb');cell(page,2,2);wait(page,'window.dungeon.getView().canConfirm')
        assert save(page)['screen']=='battle'
        page.locator('#detail-confirm-forecast').click();wait(page,'window.dungeon.getView().audience.favor===1')
        assert next(c for c in view(page)['audience']['challenges'] if c['id']=='sponsor.reaction')['earned']
        page.locator('#save-button').click();page.locator('#menu-game-tools [data-open-audience]').click();snap(page,out,'audience-earned')
        def choose():
            utility=page.locator('.audience-utility').filter(has=page.locator('[data-preview-favor][data-item-id="item.oil_flask"]'))
            utility.locator('summary').click();utility.locator('[data-preview-favor]').first.click();wait(page,'window.dungeon.getView().canConfirm')
        before=save(page);count=next(i['count'] for i in view(page)['items'] if i['id']=='item.oil_flask');choose();snap(page,out,'favor-preview');assert save(page)==before
        page.locator('#detail-cancel-forecast').click();assert save(page)==before
        page.locator('#save-button').click();page.locator('#menu-game-tools [data-open-audience]').click();choose();page.locator('#detail-confirm-forecast').click();wait(page,'!window.dungeon.getView().canConfirm')
        assert view(page)['audience']['favor']==0
        assert next(i['count'] for i in view(page)['items'] if i['id']=='item.oil_flask')==count-1
        carl=next(u for u in view(page)['units'] if u['id']=='crawler.carl');assert carl['acted'] and not carl['moved'] and not carl['finished']
        snap(page,out,'favor-committed');page.wait_for_timeout(600);checkpoint=save(page);page.reload();wait(page,'window.dungeon?.getView()?.screen');assert save(page)==checkpoint
        assert not errors,errors
        return {'viewport':[w,h],'workshopImportedThroughUI':True,'earnedFavorReaction':True,'sponsorReceipt':True,'favorPreviewCancelCommit':True,'actionAndMovePreserved':True,'reload':True,'browserErrors':errors}
    finally:context.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:5188');p.add_argument('--screenshots',default='/tmp/dct-finish-qa');p.add_argument('--browser',default='/usr/bin/chromium');a=p.parse_args()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
        results=[run(browser,a,1440,900),run(browser,a,390,844),run_favor(browser,a,1440,900),run_favor(browser,a,390,844)];browser.close()
    Path(a.screenshots,'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':main()
