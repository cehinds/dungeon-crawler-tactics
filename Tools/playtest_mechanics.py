"""Browser regressions for the current campaign UI and rotated room authoring.

Run against the final published WASM: python Tools/playtest_mechanics.py --url http://127.0.0.1:5188
The editor test uses visible controls/canvas and only reads roomWorkshop for assertions.
"""
import argparse
import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:5188')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--screenshots', default='/tmp/dct-mechanics')
parser.add_argument('--suite', choices=('all','editor','campaign'), default='all')
parser.add_argument('--viewport', choices=('all','desktop','phone','landscape'), default='all')
args = parser.parse_args()

VIEWPORTS = [(1366,768),(390,844),(844,390)]


def game_view(page):
    return page.evaluate('window.dungeon.getView()')


def game_cell_click(page, x, y):
    point=page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y),b=document.querySelector('#battlefield').getBoundingClientRect();return{x:b.left+p.x,y:b.top+p.y}}''',[x,y])
    page.mouse.click(point['x'],point['y'])


def enter_battle(page):
    page.wait_for_function('window.dungeon?.getView()?.screen',timeout=60000)
    if page.locator('#welcome-dialog').evaluate('d=>d.open'): page.locator('#begin-button').click()
    if page.locator('#help-dialog').evaluate('d=>d.open'): page.locator('#help-dialog [data-close="help-dialog"]').last.click()
    page.locator('#quick-enter').click()
    page.wait_for_function("window.dungeon.getView().screen==='explore'")
    for _ in range(120):
        v=game_view(page)
        if v['screen']=='battle': return
        m=v['exploration'];door=next((p for p in m['points'] if p['kind']=='encounter' and p['canInteract']),None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click()
            page.wait_for_function("window.dungeon.getView().screen==='battle'")
            return
        frontier=[t for t in m['tiles'] if t['reachable'] and not t['revealed']]
        tile=min(frontier,key=lambda t:(abs(t['x']-m['x'])+abs(t['y']-m['y']),t['y'],t['x']))
        game_cell_click(page,tile['x'],tile['y'])
        page.wait_for_function('([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y}',arg=[tile['x'],tile['y']])
    raise AssertionError('Visible exploration path did not reach the encounter.')


def run_campaign(browser,screenshots,width,height):
    page=browser.new_page(viewport={'width':width,'height':height},is_mobile=width<500,has_touch=width<500)
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.url,wait_until='domcontentloaded',timeout=60000);enter_battle(page)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Battle UI horizontally overflows at {width}x{height}.'
    # Verify the character sheet presents live stats for the full roster, including reserve Mordecai.
    page.locator('#open-character-sheet').click();page.wait_for_function("document.querySelector('#character-sheet-dialog')?.open===true")
    roster=game_view(page)['roster'];sheet_names=[]
    for crawler in roster:
        page.locator('#sheet-crawler').select_option(crawler['id'])
        page.wait_for_function('(id)=>document.querySelector("#character-sheet-title")?.textContent===window.dungeon.getView().roster.find(x=>x.id===id)?.label',arg=crawler['id'])
        stats=page.locator('#sheet-stats').inner_text()
        assert 'Health' in stats and ('Mana' in stats or crawler['id']=='crawler.mordecai'),f"Missing stats for {crawler['id']}: {stats}"
        sheet_names.append(crawler['id'])
    assert 'crawler.mordecai' in sheet_names,'Character sheet omits Mordecai from the complete roster.'
    page.locator('#sheet-crawler').select_option('crawler.carl');page.locator('#done-character-sheet').click()

    # Action details expose authored effect, cost and target; action commit must leave movement available.
    page.locator('#open-actions').click();page.wait_for_function("document.querySelector('#action-dialog')?.open===true")
    bomb=page.locator("[data-modal-ability='ability.carl_bomb']")
    assert bomb.count()==1 and bomb.is_enabled(),f'Carl bomb unavailable: {bomb.inner_text() if bomb.count() else "missing"}'
    bomb.click();page.wait_for_function("document.querySelector('#action-dialog')?.open!==true")
    page.locator('#open-ability-details').click();page.wait_for_function("document.querySelector('#ability-details-dialog')?.open===true")
    details=page.locator('#full-ability-details')
    assert details.count()==1 and 'MP' in details.inner_text() and 'Range' in details.inner_text() and details.locator('p').inner_text(),f'Persistent ability details incomplete: {details.inner_text()}'
    assert 'Bomb' in page.locator('#full-ability-details').inner_text() or 'bomb' in page.locator('#full-ability-details').inner_text().lower()
    page.locator('#done-ability-details').click()
    v=game_view(page);legal=next((t for t in v.get('reachable',[]) if t['cost']>0),None)
    assert legal,f'No legal movement after selecting the bomb at {width}x{height}.'
    game_cell_click(page,legal['x'],legal['y']);page.wait_for_function('window.dungeon.getView().canConfirm')
    assert game_view(page)['canConfirm'],'Bomb target did not open a commit forecast.'
    page.locator('#detail-confirm-forecast').click()
    page.wait_for_function("()=>{const v=window.dungeon.getView(),u=v.units.find(x=>x.id==='crawler.carl');return !v.canConfirm&&v.selectedUnitId==='crawler.carl'&&u.acted&&!u.finished&&v.canMove}")
    after_action=game_view(page);carl=next(u for u in after_action['units'] if u['id']=='crawler.carl')
    destination=next((t for t in after_action.get('reachable',[]) if t['cost']>0),None)
    assert destination,'Carl has no remaining legal move after committing an action.'
    game_cell_click(page,destination['x'],destination['y'])
    page.wait_for_function('([x,y])=>{const u=window.dungeon.getView().units.find(x=>x.id===\'crawler.carl\');return u.x===x&&u.y===y}',arg=[destination['x'],destination['y']])
    assert next(u for u in game_view(page)['units'] if u['id']=='crawler.carl')['acted'],'Action-then-move did not preserve action state.'
    page.screenshot(path=str(screenshots/f'campaign-{width}x{height}.png'),full_page=True)

    # End Turn is an explicit actor-scoped confirmation. Escape preserves the actor; confirm advances.
    page.locator('#end-turn').click();page.wait_for_function("document.querySelector('#end-turn-dialog')?.open===true")
    before=game_view(page);before_actor=before['selectedUnitId'];page.keyboard.press('Escape')
    page.wait_for_function("document.querySelector('#end-turn-dialog')?.open!==true")
    assert game_view(page)['selectedUnitId']==before_actor and not next(u for u in game_view(page)['units'] if u['id']==before_actor)['finished']
    page.locator('#end-turn').click();page.locator('#confirm-end-turn').click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId==='crawler.donut'")
    # Advance Donut to Katia, select the whole sheet and preview a stat-changing form.
    page.locator('#end-turn').click();page.locator('#confirm-end-turn').click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId==='crawler.katia'")
    page.locator('#open-character-sheet').click();page.wait_for_function("document.querySelector('#character-sheet-dialog')?.open===true")
    page.locator('[data-sheet-section="sheet-forms"]').click()
    form=page.locator('[data-sheet-form="form.strider"]')
    assert form.count()==1 and form.is_enabled(),f'Strider form is not available on Katia sheet: {page.locator("#sheet-forms").inner_text()}'
    current=game_view(page);katia=next(u for u in current['units'] if u['id']=='crawler.katia')
    old_max,old_move=katia['maxHp'],katia.get('effectiveMove',katia['move'])
    form.click();page.wait_for_function("document.querySelector('#forecast-dialog')?.open===true")
    forecast=game_view(page);mode_delta=next((row for row in forecast.get('forecast',[]) if row.get('targetId')=='crawler.katia'),None)
    assert forecast['canConfirm'] and mode_delta and mode_delta['afterMaxHp']==mode_delta['beforeMaxHp']-4 and mode_delta['afterMove']==mode_delta['beforeMove']+1,f'Form preview did not expose its exact stat forecast: {forecast.get("forecast")}'
    forecast_text=page.locator('#forecast-dialog').inner_text()
    assert 'Maximum HP' in forecast_text and 'Movement' in forecast_text, f'Strider forecast omits maximum-stat changes: {forecast_text}'
    page.keyboard.press('Escape');page.wait_for_function("document.querySelector('#forecast-dialog')?.open!==true")
    assert next(u for u in game_view(page)['units'] if u['id']=='crawler.katia')['maxHp']==old_max,'Cancelled form preview changed actual stats.'
    if not page.locator('#character-sheet-dialog').count() or not page.locator('#character-sheet-dialog').evaluate('(d)=>d.open'):
        page.locator('#open-character-sheet').click();page.wait_for_function("document.querySelector('#character-sheet-dialog')?.open===true")
        page.locator('[data-sheet-section="sheet-forms"]').click()
    page.locator('[data-sheet-form="form.strider"]').click();page.locator('#detail-confirm-forecast').click()
    page.wait_for_function("()=>{const u=window.dungeon.getView().units.find(x=>x.id==='crawler.katia');return u.formId==='form.strider'&&u.acted&&!u.finished}")
    changed=next(u for u in game_view(page)['units'] if u['id']=='crawler.katia')
    assert changed['maxHp']==old_max-4 and changed.get('effectiveMove',changed['move'])==old_move+1, f'Committed form stats are incorrect: {changed}'
    assert 'achievement.first_form' in game_view(page).get('achievementIds',[]),'Committed form change did not award its achievement.'
    if page.locator('#done-character-sheet').count(): page.locator('#done-character-sheet').click()
    page.wait_for_function("document.querySelector('#narrator-line')?.textContent.includes('ACHIEVEMENT')",timeout=7000)
    page.locator('#save-button').click();page.locator('#menu-narrator-history').click();page.wait_for_function("document.querySelector('#narrator-history-dialog')?.open===true")
    history=page.locator('.narrator-history-list').inner_text()
    assert ('First form change' in history or 'First form or stance change' in history) and 'declares' in history, f'Narrator history missed committed events: {history}'
    page.screenshot(path=str(screenshots/f'campaign-feedback-{width}x{height}.png'),full_page=True)
    assert not errors,f'Campaign browser errors at {width}x{height}: {errors}'
    page.close()
    return {'viewport':[width,height],'rosterSheets':sheet_names,'actionThenMove':True,'formStatsForecastAndCommit':True,'achievementFeedback':True,'screenshots':[f'campaign-{width}x{height}.png',f'campaign-feedback-{width}x{height}.png']}


def run_bulwark_reload(browser,screenshots):
    context=browser.new_context(viewport={'width':1366,'height':768})
    page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.url,wait_until='domcontentloaded',timeout=60000);enter_battle(page)
    page.locator('#end-turn').click();page.locator('#confirm-end-turn').click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId==='crawler.donut'")
    page.locator('#end-turn').click();page.locator('#confirm-end-turn').click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId==='crawler.katia'")
    page.locator('#open-character-sheet').click();page.wait_for_function("document.querySelector('#character-sheet-dialog')?.open===true")
    page.locator('[data-sheet-section="sheet-forms"]').click()
    bulwark=page.locator('[data-sheet-form="form.bulwark"]')
    assert bulwark.count()==1 and bulwark.is_enabled(),'Katia Bulwark form is unavailable.'
    bulwark.click();page.wait_for_function("document.querySelector('#forecast-dialog')?.open===true")
    preview=game_view(page);delta=next(row for row in preview['forecast'] if row['targetId']=='crawler.katia')
    assert delta['afterMaxHp']==delta['beforeMaxHp']+8 and delta['afterMove']==delta['beforeMove']-1
    page.locator('#detail-confirm-forecast').click()
    page.wait_for_function("()=>{const v=window.dungeon.getView(),u=v.units.find(x=>x.id==='crawler.katia');return u.formId==='form.bulwark'&&v.achievementIds.filter(id=>id==='achievement.first_form').length===1}")
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open!==true")
    page.wait_for_timeout(500)
    committed=game_view(page);katia=next(u for u in committed['units'] if u['id']=='crawler.katia')
    assert committed.get('achievementIds',[]).count('achievement.first_form')==1
    assert not committed['message'].startswith('Save rejected'),f"Bulwark commit rejected: {committed['message']}"
    page.screenshot(path=str(screenshots/'bulwark-committed.png'),full_page=True)
    page.reload(wait_until='domcontentloaded');page.wait_for_function("window.dungeon?.getView()?.screen==='battle'",timeout=60000)
    restored=game_view(page);restored_katia=next(u for u in restored['units'] if u['id']=='crawler.katia')
    assert restored_katia['formId']=='form.bulwark' and restored.get('achievementIds',[]).count('achievement.first_form')==1, f'Bulwark or achievement did not survive actual reload: {restored_katia}, {restored.get("achievementIds")}'
    assert not restored['message'].startswith('Save rejected'),f"Reload rejected the Bulwark save: {restored['message']}"
    assert not errors,f'Bulwark browser errors: {errors}'
    page.screenshot(path=str(screenshots/'bulwark-reloaded.png'),full_page=True)
    page.close();context.close()
    return {'form':'form.bulwark','maxHp':restored_katia['maxHp'],'achievementCount':restored.get('achievementIds',[]).count('achievement.first_form'),'reloadPreserved':True,'saveRejected':False,'screenshots':['bulwark-committed.png','bulwark-reloaded.png']}


def editor_click_cell(page, x, y):
    page.locator('#room-canvas').scroll_into_view_if_needed()
    page.evaluate('''([x,y])=>{const p=window.roomWorkshop.cellToScreen(x,y),b=document.querySelector('#room-canvas').getBoundingClientRect();const screenY=b.top+p.y;window.scrollBy(0,screenY-innerHeight*.52)}''',[x,y])
    point=page.evaluate('''([x,y])=>{const p=window.roomWorkshop.cellToScreen(x,y),b=document.querySelector('#room-canvas').getBoundingClientRect();return{x:b.left+p.x,y:b.top+p.y}}''',[x,y])
    assert 0<=point['y']<=page.evaluate('innerHeight'),f'Projected grid cell ({x},{y}) is outside the visible canvas at {point}.'
    page.mouse.click(point['x'],point['y'])


def run_editor(browser, screenshots, width, height):
    page=browser.new_page(viewport={'width':width,'height':height},is_mobile=width<500,has_touch=width<500)
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.url.rstrip('/')+'/room-kit.html',wait_until='domcontentloaded',timeout=60000)
    page.wait_for_function("document.querySelector('#loading')?.hidden && window.roomWorkshop?.getRoom()",timeout=60000)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Room workshop has horizontal overflow at {width}x{height}.'
    page.locator('#seed').fill('qa-rotated-editor')
    page.locator('#size').select_option('8,6')
    page.locator('#density').fill('0')
    page.locator('#generate').click()
    baseline=page.evaluate('window.roomWorkshop.getRoom()')
    assert baseline['width']==8 and baseline['height']==6 and baseline['clearRoute']
    manifest=page.evaluate("fetch('assets/room-kit/manifest.json').then(r=>r.json())")
    asset=next(a for a in manifest['assets'] if a['layer']=='prop' and not a['blocksMovement'])
    card=page.locator(f"#asset-gallery button[title='Paint {asset['label']}']")
    assert card.count()==1, f"Gallery card for {asset['id']} is missing."
    card.click()
    painted=[];painted_cells=set()
    for rotation in range(4):
        if rotation:
            page.locator('#rotate-camera').click()
            page.locator('#rotate-piece').click()
            page.wait_for_timeout(250)
        assert page.evaluate('window.roomWorkshop.getRotation()')==rotation
        occupied={(p['x'],p['y']) for p in baseline['placements'] if p['layer']!='floor'}|painted_cells
        cell=next(( (x,y) for y in range(1,baseline['height']-1) for x in range(1,baseline['width']-1) if (x,y) not in occupied),None)
        assert cell, 'Generated room has no unoccupied interior tile for a placement test.'
        editor_click_cell(page,*cell)
        room=page.evaluate('window.roomWorkshop.getRoom()')
        result=next((p for p in room['placements'] if (p['x'],p['y'])==cell and p['assetId']==asset['id']),None)
        assert result and result.get('rotation',0)==rotation, f"Rotated canvas paint missed viewport {width}x{height} grid cell {cell} at camera rotation {rotation}: {result}"
        assert room['clearRoute'], f'Painting at rotation {rotation} unexpectedly disconnected the route.'
        painted.append({'cameraRotation':rotation,'pieceRotation':rotation,'cell':cell,'placement':result['id']});painted_cells.add(cell)
    screenshot=screenshots/f'editor-{width}x{height}.png'
    page.screenshot(path=str(screenshot),full_page=True)

    before=page.locator('#room-canvas').evaluate('c=>c.toDataURL()')
    prop_layer=page.locator('#layers button.layer-toggle').filter(has_text='prop')
    assert prop_layer.get_attribute('aria-pressed')=='true'
    prop_layer.click()
    after=page.locator('#room-canvas').evaluate('c=>c.toDataURL()')
    assert before!=after,'Hiding the prop layer did not change the editor canvas.'
    prop_layer.click()

    # Use visible JSON export, then import that actual downloaded file.
    with page.expect_download() as exported:
        page.locator('#export-json').click()
    room_file=Path(tempfile.gettempdir())/f'dct-editor-{width}x{height}.json'
    exported.value.save_as(room_file)
    exported_room=json.loads(room_file.read_text())
    assert exported_room['kind']=='dungeon-room-authoring' and len(exported_room['placements'])>=len(baseline['placements'])
    page.locator('#import-json').set_input_files(str(room_file))
    page.wait_for_function("document.querySelector('#room-summary').textContent.includes('Imported')")
    imported=page.evaluate('window.roomWorkshop.getRoom()')
    assert imported==exported_room,'Visible JSON import changed the validated room recipe.'

    with page.expect_download() as tile_export:
        page.locator('#export-game-tiles').click()
    tile_file=Path(tempfile.gettempdir())/f'dct-game-tiles-{width}x{height}.json'
    tile_export.value.save_as(tile_file)
    tiles=json.loads(tile_file.read_text())
    assert {'width','height','tiles'}<=tiles.keys() and tiles['width']==8 and tiles['height']==6
    assert all({'x','y','blocked','tags'}<=tile.keys() for tile in tiles['tiles'])
    assert not errors,f'Room editor browser errors: {errors}'
    page.close()
    return {'viewport':[width,height],'rotatedPaints':painted,'jsonPlacements':len(exported_room['placements']),
            'gameTileCount':len(tiles['tiles']),'screenshot':str(screenshot),'pageErrors':errors}


def main():
    screenshots=Path(args.screenshots);screenshots.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
        results=[]
        selected_viewports={'desktop':[(1366,768)],'phone':[(390,844)],'landscape':[(844,390)],'all':VIEWPORTS}[args.viewport]
        for width,height in selected_viewports:
            if args.suite in ('all','editor'): results.append(run_editor(browser,screenshots,width,height))
            if args.suite in ('all','campaign'): results.append(run_campaign(browser,screenshots,width,height))
        if args.suite in ('all','campaign') and args.viewport in ('all','desktop'):
            results.append(run_bulwark_reload(browser,screenshots))
        browser.close()
    for result in results:print(json.dumps(result))


if __name__=='__main__':
    main()
