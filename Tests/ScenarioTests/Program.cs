using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class ScenarioTests
{
    static readonly JsonSerializerOptions Json=new JsonSerializerOptions{IncludeFields=true};
    static Content content; static GameData data; static int checks;
    static T Copy<T>(T x){return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(x,Json),Json);}
    static GameSession New(){return new GameSession(Copy(content),Copy(data));}
    static void Check(bool x,string label){if(!x)throw new Exception(label);checks++;Console.WriteLine("PASS "+label);}
    static GameView Do(GameSession s,string type,string unit=null,string target=null,int x=0,int y=0){return s.Handle(new GameCommand{type=type,unitId=unit,targetId=target,x=x,y=y});}
    static GameView Start(GameSession s,string kind){return Do(s,"scenario_start",target:"scenario."+kind);}
    static GameView Round(GameSession s){var v=s.GetView();int n=v.round;for(int i=0;i<20&&v.screen=="battle"&&v.round==n;i++)v=Do(s,"end_turn");return v;}
    static void Main()
    {
        content=JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"combat-content.json")),Json);
        data=JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"game-content.json")),Json);
        Isolation();Hoarder();Juicer();Swine();InvalidSaves();DefeatRetry();LegalVictories();Console.WriteLine(checks+" scenario checks passed.");
    }
    static void Isolation()
    {
        var s=New();var original=JsonSerializer.Serialize(s.ExportSave(),Json);
        foreach(var kind in new[]{"hoarder","juicer","swine"})
        {
            var v=Start(s,kind);Check(v.screen=="battle"&&v.scenario.id=="scenario."+kind,"start isolated "+kind);
            Check(v.scenario.description.Contains("ADAPTATION")&&v.scenario.intent.cells.Length>0,"briefing and authoritative intent "+kind);
            var saved=Copy(s.ExportSave());var loaded=New();v=loaded.ImportSave(saved);
            Check(!v.message.StartsWith("Save rejected")&&JsonSerializer.Serialize(loaded.ExportSave().scenario.intent,Json)==JsonSerializer.Serialize(saved.scenario.intent,Json),"mid-phase exact intent reload "+kind);
            Do(s,"scenario_return");Check(JsonSerializer.Serialize(s.ExportSave(),Json)==original,"return restores exact campaign "+kind);
        }
    }
    static void Hoarder()
    {
        var s=New();var v=Start(s,"hoarder");Check(v.units.Count(u=>u.id.StartsWith("scatterer.")&&u.hp>0)==0,"Scatterers begin dormant");
        v=Round(s);Check(v.units.Count(u=>u.id.StartsWith("scatterer.")&&u.hp>0)==2,"emergence obeys living cap");
        var saved=Copy(s.ExportSave());saved.units.Single(u=>u.id=="boss.hoarder").tags=new[]{"status.frozen"};
        // Frozen is timed: use a legal frost consumable instead of forging a missing duration layer.
        var fresh=New();v=Start(fresh,"hoarder");
        var donor=v.units.First(u=>u.team=="player");
        v=Do(fresh,"move",donor.id,x:4,y:2);
        v=fresh.Handle(new GameCommand{type="preview",unitId=donor.id,itemId="item.frost_vial",targetId="boss.hoarder"});
        if(v.canConfirm){Do(fresh,"confirm");v=Round(fresh);Check(v.log.Any(l=>l.Contains("emergence is interrupted")),"legal frost interrupts emergence");}
        else throw new Exception("Frost interruption setup: "+v.message);
        var snap=Copy(s.ExportSave());var restored=New();Check(!restored.ImportSave(snap).message.StartsWith("Save rejected"),"spawned minion state reloads");
    }
    static void Juicer()
    {
        var s=New();var v=Start(s,"juicer");var lane=v.scenario.intent.cells;
        Check(lane.All(c=>c.y==3)&&lane.Last().x==0,"plate lane is complete and locked");
        string unit=v.selectedUnitId;v=Do(s,"move",unit,x:4,y:2);v=Do(s,"scenario_interact",unit,"gym.bench");
        Check(v.scenario.interactables.Single(o=>o.id=="gym.bench").hp==0,"bench topples through legal action");
        v=Round(s);Check(v.log.Any(l=>l.Contains("destroys the toppled bench")),"cover intercepts actual plate resolution");
        var old=s.ExportSave();var saved=Copy(old);saved.scenario.intent.cells[0].y=1;
        Check(New().ImportSave(saved).message.StartsWith("Save rejected"),"forged plate lane rejected");
        Check(old.scenario.objects.Single(o=>o.id=="gym.bench").hp==-1,"cover destruction persisted");
    }
    static void Swine()
    {
        var s=New();var v=Start(s,"swine");string unit=v.selectedUnitId;
        v=Do(s,"scenario_interact",unit,"speedbump.parts");Check(v.scenario.carryingUnitIds.Contains(unit)&&!v.canAct&&v.canMove,"collect part spends only action");
        var checkpoint=Copy(s.ExportSave());var loaded=New();Check(!loaded.ImportSave(checkpoint).message.StartsWith("Save rejected")&&loaded.GetView().scenario.carryingUnitIds.Contains(unit),"carried component reloads");
        v=Do(s,"move",unit,x:4,y:3);v=Round(s);v=Do(s,"scenario_interact",unit,"speedbump.barrier");
        Check(v.scenario.progress>=1&&!v.scenario.carryingUnitIds.Contains(unit),"brace consumes component");
        var partial=New();Check(!partial.ImportSave(Copy(s.ExportSave())).message.StartsWith("Save rejected")&&partial.GetView().scenario.progress==v.scenario.progress,"partial construction checkpoint reloads");
        v=Do(s,"move",unit,x:4,y:2);
        string second=v.units.First(u=>u.team=="player"&&u.id!=unit&&!u.acted&&!u.finished).id;
        v=Do(s,"select",second);v=Do(s,"move",second,x:3,y:3);v=Do(s,"scenario_interact",second,"speedbump.parts");
        v=Round(s);v=Do(s,"select",second);v=Do(s,"move",second,x:4,y:3);v=Do(s,"scenario_interact",second,"speedbump.barrier");v=Do(s,"move",second,x:4,y:2);
        for(int i=0;i<6&&v.screen=="battle";i++)v=Round(s);
        Check(v.log.Any(l=>l.Contains("completed Speedbump stops"))||v.units.Single(u=>u.id=="boss.swine").hp<60,"helper recovery creates real rolling collision damage");
        Check(v.scenario.helpers<=2&&v.scenario.progress<=3,"construction is bounded");
    }
    static void InvalidSaves()
    {
        var s=New();Start(s,"swine");var original=JsonSerializer.Serialize(s.ExportSave(),Json);var bad=Copy(s.ExportSave());bad.scenario.progress=4;
        Check(s.ImportSave(bad).message.StartsWith("Save rejected")&&JsonSerializer.Serialize(s.ExportSave(),Json)==original,"invalid progress rejected atomically");
        bad=Copy(s.ExportSave());bad.scenario.campaign.scenario=new ScenarioSave();Check(s.ImportSave(bad).message.StartsWith("Save rejected"),"recursive scenario backup rejected");
        bad=Copy(s.ExportSave());bad.scenario.campaign.roster[0].hp=-1;Check(s.ImportSave(bad).message.StartsWith("Save rejected"),"invalid campaign backup rejected");
        bad=Copy(s.ExportSave());bad.scenario.objects[0]=null;Check(s.ImportSave(bad).message.StartsWith("Save rejected"),"null scenario object rejected");
        bad=Copy(s.ExportSave());bad.units[0]=null;Check(s.ImportSave(bad).message.StartsWith("Save rejected"),"null scenario unit rejected");
        var detached=s.ExportSave();detached.scenario.campaign.roster[0].hp=0;Check(s.ExportSave().scenario.campaign.roster[0].hp>0,"exported campaign backup does not alias live state");
        Round(s);Check(detached.scenario.turns==0,"exported scenario snapshot does not alias live state");
    }
    static void DefeatRetry()
    {
        var s=New();var v=Start(s,"hoarder");for(int i=0;i<100&&v.screen=="battle";i++)v=Round(s);
        Check(v.screen=="defeat","ordinary waits can lose scenario");
        var loaded=New();Check(!loaded.ImportSave(Copy(s.ExportSave())).message.StartsWith("Save rejected"),"defeat checkpoint reloads");
        v=Do(loaded,"retry");Check(v.screen=="battle"&&v.round==1&&v.scenario.progress==0&&v.units.Where(u=>u.team=="player").All(u=>u.hp==u.maxHp),"scenario retry resets phase and roster without campaign loss");
        v=Do(loaded,"scenario_return");Check(v.screen=="camp"&&v.scenario==null,"return after retry restores campaign");
    }
    static void LegalVictories()
    {
        foreach(var kind in new[]{"hoarder","juicer","swine"})
        {
            var s=New();var v=Start(s,kind);
            for(int step=0;step<1200&&v.screen=="battle";step++)
            {
                var actor=v.units.Single(u=>u.id==v.selectedUnitId);
                bool committed=false;
                if(!actor.acted)
                {
                    // Preview every legal enemy ability and choose the actual shared-resolver damage forecast.
                    GameCommand best=null;int damage=0;
                    foreach(var a in v.abilities.Where(a=>a.enabled&&a.target=="enemy"))foreach(var target in a.targetIds)
                    {
                        var p=s.Handle(new GameCommand{type="preview",unitId=actor.id,abilityId=a.id,targetId=target});
                        int dealt=p.forecast.Where(f=>v.units.Any(u=>u.id==f.targetId&&u.team=="enemy")).Sum(f=>Math.Max(0,f.beforeHp-f.afterHp));
                        if(p.canConfirm&&dealt>damage){damage=dealt;best=new GameCommand{type="preview",unitId=actor.id,abilityId=a.id,targetId=target};}
                        Do(s,"cancel");
                    }
                    if(best!=null){s.Handle(best);v=Do(s,"confirm");committed=true;}
                }
                if(v.screen!="battle")break;
                if(!committed&&!actor.moved)
                {
                    v=Do(s,"select",actor.id);var enemies=v.units.Where(u=>u.team=="enemy"&&u.hp>0).ToArray();
                    var cell=v.reachable.OrderBy(c=>enemies.Min(e=>Math.Abs(c.x-e.x)+Math.Abs(c.y-e.y))).ThenBy(c=>c.cost).FirstOrDefault();
                    if(cell!=null&&(cell.x!=actor.x||cell.y!=actor.y)){v=Do(s,"move",actor.id,x:cell.x,y:cell.y);continue;}
                }
                if(!committed)v=Do(s,"end_turn",actor.id);
            }
            Check(v.screen=="victory","ordinary legal commands complete "+kind+" ("+v.message+")");
            var load=New();var loaded=load.ImportSave(Copy(s.ExportSave()));Check(!loaded.message.StartsWith("Save rejected"),"victory checkpoint reloads "+kind+" "+loaded.message);
        }
    }
}
