using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class FloorTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content; static GameData data; static int checks;
    static T Clone<T>(T x) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(x, Json), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static string Save(GameSession g) { return JsonSerializer.Serialize(g.ExportSave(), Json); }
    static void Check(bool b,string text) { if(!b)throw new Exception(text);checks++;Console.WriteLine("PASS "+text); }
    static GeneratedFloorPlan Plan()
    {
        return new GeneratedFloorPlan { map = new CustomMapData { label="Continuous test",width=24,height=18,enemies=new[]{new SpawnDef{id="custom.enemy.one",label="Guard",classId="class.brawler",artId="rat",x=10,y=10,hp=1,energy=1,move=1,tags=new string[0]},new SpawnDef{id="custom.enemy.two",label="Guard",classId="class.brawler",artId="rat",x=20,y=14,hp=1,energy=1,move=1,tags=new string[0]}}}, entrance=new CellView{x=0,y=0},exit=new CellView{x=23,y=17},groups=new[]{new GeneratedEncounterGroup{id="group.one",label="Watch",kind="visible",x=10,y=12,enemyIds=new[]{"custom.enemy.one"}},new GeneratedEncounterGroup{id="group.two",label="Ambush",kind="ambush",x=20,y=14,enemyIds=new[]{"custom.enemy.two"}}},discoveries=new[]{new ExplorationPointDef{id="cache.one",label="Supplies",description="Found tonic.",kind="cache",itemId="item.health_tonic",count=1,x=1,y=0},new ExplorationPointDef{id="objective.one",label="Seal",description="Found seal.",kind="objective",x=2,y=0}}};
    }
    static void Main()
    {
        content=JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"combat-content.json")),Json);data=JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"game-content.json")),Json);
        GameSession g=Session();GameView v=g.Handle(new GameCommand{type="import_floor",floorPlan=Plan()});Check(v.screen=="explore"&&v.exploration.width==24,"larger continuous floor imports");Check(v.exploration.tiles.Any(t=>!t.revealed),"floor starts with persistent discovery fog");
        string lockedSave=Save(g);g.Handle(new GameCommand{type="explore_interact",targetId="generated.exit"});Check(Save(g)==lockedSave,"exit rejects uncleared floor without changing progress");
        GameSession compactSession=Session();compactSession.ImportSave(Clone(g.ExportSave()));
        GameView fullMove=g.Handle(new GameCommand{type="explore_step",x=1});ExplorationMovementResponse compactMove=compactSession.HandleExplorationMovement(new GameCommand{type="explore_step",x=1});
        Check(compactMove.partial && compactMove.view.customMap==null && compactMove.view.generatedDungeon.floorPlan==null && JsonSerializer.Serialize(compactMove.view.exploration,Json)==JsonSerializer.Serialize(fullMove.exploration,Json),"compact movement preserves exact exploration view without authored catalog payload");
        Check(Save(g)==Save(compactSession),"compact movement and ordinary dispatch commit identical state");
        compactMove=compactSession.HandleExplorationMovement(new GameCommand{type="explore_step",x=1,y=1});Check(compactMove.partial && compactMove.view.message.Contains("cardinal") && Save(g)==Save(compactSession),"invalid compact movement reports error without changing state");
        g.Handle(new GameCommand{type="explore_step",x=-1});
        int tonic=g.ExportSave().inventory.First(i=>i.itemId=="item.health_tonic").count;g.Handle(new GameCommand{type="explore_interact",targetId="cache.one"});Check(g.ExportSave().inventory.First(i=>i.itemId=="item.health_tonic").count==tonic+1,"cache grants authored supplies");string before=Save(g);g.Handle(new GameCommand{type="explore_interact",targetId="cache.one"});Check(Save(g)==before,"cache cannot be claimed twice");
        g.Handle(new GameCommand{type="explore_step",x=1});g.Handle(new GameCommand{type="explore_interact",targetId="objective.one"});before=Save(g);g.Handle(new GameCommand{type="return_safe"});g.Handle(new GameCommand{type="resume_floor"});Check(Save(g)==before,"safe room resume preserves party inventory position and discoveries");
        GameSession restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"exploration save roundtrip");
        GameSave invalid=Clone(g.ExportSave());invalid.generatedDungeon.defeatedGroupIds=new[]{"missing"};before=Save(g);g.ImportSave(invalid);Check(Save(g)==before,"forged encounter receipt rejected atomically");
        invalid=Clone(g.ExportSave());invalid.generatedDungeon.defeatedGroupIds=null;g.ImportSave(invalid);Check(Save(g)==before,"null receipt collection rejected safely");
        invalid=Clone(g.ExportSave());invalid.generatedDungeon.floorPlan.map.enemies[0].hp++;g.ImportSave(invalid);Check(Save(g)==before,"mismatched floor map rejected atomically");
        compactSession=Session();compactSession.ImportSave(Clone(g.ExportSave()));
        for(int i=0;i<9;i++){g.Handle(new GameCommand{type="explore_step",x=1});compactMove=compactSession.HandleExplorationMovement(new GameCommand{type="explore_step",x=1});}
        for(int i=0;i<9;i++){g.Handle(new GameCommand{type="explore_step",y=1});compactMove=compactSession.HandleExplorationMovement(new GameCommand{type="explore_step",y=1});}v=g.GetView();
        Check(!compactMove.partial && compactMove.view.screen=="battle" && compactMove.view.classes.Length>0 && Save(compactSession)==Save(g),"compact movement returns full identical battle transition view");Check(v.screen=="battle"&&v.units.Count(u=>u.team=="enemy")==1,"visible group triggers only its own tactical encounter");
        restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"active isolated encounter save roundtrip");
        AbilityView strike = v.abilities.First(a => a.enabled && a.targetIds.Contains("custom.enemy.one"));
        g.Handle(new GameCommand{type="preview",abilityId=strike.id,targetId="custom.enemy.one"});g.Handle(new GameCommand{type="confirm"});
        Check(g.GetView().screen=="victory","isolated encounter resolves through existing combat");
        restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"victory checkpoint preserves group receipt pending reward");
        g.Handle(new GameCommand{type="choose_reward",rewardId=data.rewards[0].id});g.Handle(new GameCommand{type="continue"});v=g.GetView();
        Check(v.screen=="explore"&&!v.generatedDungeon.cleared&&v.generatedDungeon.defeatedGroupIds.SequenceEqual(new[]{"group.one"}),"victory removes only the defeated group");
        restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"partially cleared floor checkpoint roundtrip");
        before=Save(g);g.Handle(new GameCommand{type="continue"});Check(Save(g)==before,"cleared encounter cannot reward again");
        // Cleared rooms remain traversable; the other group uses deterministic classic encounter checks.
        int sx=g.GetView().generatedDungeon.x,sy=g.GetView().generatedDungeon.y;
        while(sx<20&&g.GetView().screen=="explore"){g.Handle(new GameCommand{type="explore_step",x=1});sx++;}
        while(sy<12&&g.GetView().screen=="explore"){g.Handle(new GameCommand{type="explore_step",y=1});sy++;}
        for(int i=0;i<16&&g.GetView().screen=="explore";i++)g.Handle(new GameCommand{type="explore_step",x=i%2==0?-1:1});
        Check(g.GetView().screen=="battle"&&g.GetView().generatedDungeon.activeGroupId=="group.two"&&g.GetView().units.Count(u=>u.team=="enemy")==1,"step meter triggers only the remaining ambush group");
        restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"second encounter persists prior group rewards and XP");
        foreach(UnitView u in g.GetView().units.Where(u=>u.team=="player").ToArray())
        {
            v=g.Handle(new GameCommand{type="select",unitId=u.id});AbilityView hit=v.abilities.FirstOrDefault(a=>a.enabled&&a.targetIds.Contains("custom.enemy.two"));if(hit==null)continue;
            g.Handle(new GameCommand{type="preview",abilityId=hit.id,targetId="custom.enemy.two"});g.Handle(new GameCommand{type="confirm"});break;
        }
        Check(g.GetView().screen=="victory","second isolated encounter resolves normally");
        g.Handle(new GameCommand{type="choose_reward",rewardId=data.rewards[0].id});g.Handle(new GameCommand{type="continue"});Check(g.GetView().generatedDungeon.cleared,"all group receipts unlock cleared floor");
        restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"fully cleared floor XP and inventory roundtrip");
        while(g.GetView().generatedDungeon.x<23)g.Handle(new GameCommand{type="explore_step",x=1});while(g.GetView().generatedDungeon.y<17)g.Handle(new GameCommand{type="explore_step",y=1});
        Check(g.Handle(new GameCommand{type="explore_interact",targetId="generated.exit"}).screen=="complete","claimed objective and defeated groups permit floor completion");
        restored=Session();restored.ImportSave(Clone(g.ExportSave()));Check(Save(restored)==Save(g),"completed floor checkpoint roundtrip");
        Console.WriteLine("PASS "+checks+" floor checks.");
    }
}
