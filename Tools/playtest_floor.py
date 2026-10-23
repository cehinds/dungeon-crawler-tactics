"""Play a full floor through the compiled browser C# engine, including exploration saves.

Optional integration check: install playwright, publish the Web project and serve it,
then run this script with --url and a local Chromium --browser path.
"""
import argparse
from pathlib import Path
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://localhost:8000')
parser.add_argument('--browser', default='/usr/bin/chromium')
args = parser.parse_args()
import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(args.url,wait_until='networkidle')
    page.wait_for_function('window.dungeon && window.dungeon.getView()',timeout=60000)
    if page.locator('#welcome-dialog').evaluate('(d)=>d.open'):
        page.locator('#begin-button').click()
    if page.locator('#help-dialog').evaluate('(d)=>d.open'):
        page.locator('#help-dialog [data-close]').last.click()
    result=page.evaluate('''async () => {
      const send = async (type,args={}) => JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','Dispatch',JSON.stringify({type,...args})));
      let v=await send('new_run'), ticks=0, victories=0, potions=0, moves=0, previewChecks=0;
      const nearest=(cell,units)=>Math.min(...units.filter(u=>u.team==='enemy'&&u.hp>0).map(u=>Math.abs(u.x-cell.x)+Math.abs(u.y-cell.y)));
      while(v.screen!=='complete' && ticks++<700){
        if(v.screen==='camp'){
          v=await send('safe_room_rest');
          if(!v.safeRoom.rested)throw Error('Safe-room rest failed');
          v=await send('start');
          if(v.screen!=='explore')throw Error('Could not leave safe room: '+v.message);
          continue;
        }
        if(v.screen==='explore'){
          const m=v.exploration;
          const nearby=m.points.find(p=>p.canInteract&&!p.claimed&&p.kind!=='encounter');
          if(nearby){v=await send('explore_interact',{targetId:nearby.id});continue;}
          const door=m.points.find(p=>p.kind==='encounter'&&p.canInteract);
          if(door){v=await send('explore_interact',{targetId:door.id});continue;}
          let next=m.tiles.filter(t=>t.reachable&&!t.revealed).sort((a,b)=>a.y-b.y||a.x-b.x)[0];
          if(!next){const goal=m.points.find(p=>p.kind==='encounter');if(!goal)throw Error('No frontier or door');next=m.tiles.filter(t=>t.reachable).sort((a,b)=>(Math.abs(a.x-goal.x)+Math.abs(a.y-goal.y))-(Math.abs(b.x-goal.x)+Math.abs(b.y-goal.y)))[0];}
          v=await send('explore_move',{x:next.x,y:next.y});
          const save=await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','GetSave');
          v=JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','LoadSave',save));
          if(v.message.startsWith('Save rejected'))throw Error(v.message);
          continue;
        }
        if(v.screen==='defeat')throw Error('Defeated encounter '+v.encounterIndex+' round '+v.round);
        if(v.screen==='victory'){
          victories++;
          if(v.rewards.length)v=await send('choose_reward',{rewardId:v.rewards[0].id});
          const s=await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','GetSave');
          v=JSON.parse(await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','LoadSave',s));
          if(v.message.startsWith('Save rejected'))throw Error(v.message);
          v=await send('continue');continue;
        }
        const actor=v.units.find(u=>u.team==='player'&&u.hp>0&&!u.finished);
        if(!actor){if(v.phase==='player')throw Error('Player phase has no unfinished crawler');continue;}
        v=await send('select',{unitId:actor.id});
        const current=v.units.find(u=>u.id===actor.id);
        // Actions no longer end a crawler's activation. Use any remaining move
        // after the action, then explicitly finish the actor's turn.
        if(current.acted){
          if(!current.moved&&v.canMove){
            const cells=v.reachable.filter(c=>c.cost>0).sort((a,b)=>nearest(a,v.units)-nearest(b,v.units)||a.cost-b.cost);
            if(cells.length){v=await send('move',{unitId:actor.id,x:cells[0].x,y:cells[0].y});moves++;continue;}
          }
          v=await send('end_turn',{unitId:actor.id});continue;
        }
        const desired=Math.max(...v.abilities.filter(a=>a.target==='enemy').map(a=>a.range));
        if(v.canMove&&nearest(actor,v.units)>desired){
          const base=v;
          const candidates=v.reachable.filter(c=>c.cost>0).sort((a,b)=>{
            const score=c=>nearest(c,base.units)+(base.tiles.some(t=>t.x===c.x&&t.y===c.y&&t.tags.includes('surface.burning'))?4:0);
            return score(a)-score(b)||a.cost-b.cost;
          });
          if(candidates.length){v=await send('move',{unitId:actor.id,x:candidates[0].x,y:candidates[0].y});moves++;}
        }
        const wounded=v.units.filter(u=>u.team==='player'&&u.hp>0&&u.maxHp-u.hp>=10).sort((a,b)=>a.hp-b.hp)[0];
        if(wounded&&v.items.some(i=>i.id==='item.health_tonic'&&i.count>0)){
          v=await send('preview',{unitId:actor.id,targetId:wounded.id,itemId:'item.health_tonic'});
          if(v.canConfirm){v=await send('confirm');potions++;continue;}
        }
        const base=v,abilities=base.abilities.filter(a=>a.enabled);
        let best=null,bestScore=-1;
        for(const ability of abilities)for(const targetId of ability.targetIds){
          const args={unitId:actor.id,targetId,abilityId:ability.id};
          const preview=await send('preview',args);
          if(!preview.canConfirm)continue;
          previewChecks++;
          const score=preview.forecast.reduce((sum,f)=>sum+(base.units.some(u=>u.id===f.targetId&&u.team==='enemy')?(f.beforeHp-f.afterHp)*10+(f.beforeHp>0&&f.afterHp===0?200:0):(f.afterHp-f.beforeHp)*5),0);
          if(score>bestScore){bestScore=score;best=args;}
        }
        if(best&&bestScore>0){
          const preview=await send('preview',best);
          v=await send('confirm');
          // Last activation may include automatic enemy phase; compare immediate result only before that boundary.
          if(v.round===base.round&&v.screen==='battle'&&v.phase==='player'&&v.units.filter(u=>u.team==='player'&&u.hp>0&&!u.acted).length>0){
            for(const f of preview.forecast){const u=v.units.find(u=>u.id===f.targetId);if(u&&u.hp!==f.afterHp)throw Error('forecast mismatch '+f.targetId);}
          }
          continue;
        }
        v=await send('cancel');
        if(v.canMove){
          const base=v,cells=v.reachable.filter(c=>c.cost>0).sort((a,b)=>nearest(a,base.units)-nearest(b,base.units)||a.cost-b.cost);
          if(cells.length){v=await send('move',{unitId:actor.id,x:cells[0].x,y:cells[0].y});moves++;continue;}
        }
        v=await send('wait',{unitId:actor.id});
      }
      if(v.screen!=='complete'||victories!==3||v.xp!==150)throw Error('Bad final state '+JSON.stringify({screen:v.screen,victories,xp:v.xp,ticks}));
      if(v.progression.level!==4)throw Error('Full floor did not reach level 4');
      const save=await DotNet.invokeMethodAsync('DungeonCrawlerTactics.Web','GetSave');
      await window.dungeon.loadSave(save);
      return {screen:v.screen,victories,xp:v.xp,ticks,moves,potions,previewChecks,saveBytes:save.length};
    }''')
    page.screenshot(path=str(Path(tempfile.gettempdir()) / 'dungeon-floor-complete.png'), full_page=True)
    print(json.dumps({'fullRun':result,'pageErrors':errors}))
    assert not errors
    page.reload(wait_until='networkidle')
    page.wait_for_function('window.dungeon && window.dungeon.getView().screen === "complete"',timeout=60000)
    print('PASS completed floor survived browser refresh')
    browser.close()
