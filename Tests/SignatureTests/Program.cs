using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class SignatureTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content; static GameData data; static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static void Check(bool ok, string label) { if (!ok) throw new Exception(label); checks++; Console.WriteLine("PASS " + label); }
    static string Save(GameSession g) { return JsonSerializer.Serialize(g.ExportSave(), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static GameView Cmd(GameSession g, string type, string unit = null, string ability = null, string target = null, string classId = null, int x = 0, int y = 0) { return g.Handle(new GameCommand { type=type,unitId=unit,abilityId=ability,targetId=target,classId=classId,x=x,y=y }); }
    static void Round(GameSession game) { int round = game.GetView().round; for (int i=0;i<12 && game.GetView().round == round && game.GetView().screen == "battle";i++) Cmd(game,"end_turn"); }
    static CustomMapData Map() { return new CustomMapData { width=10,height=8,playerSpawns=new[]{new CellView{x=1,y=1},new CellView{x=1,y=3},new CellView{x=1,y=5},new CellView{x=3,y=3}}, enemies=new[]{new SpawnDef{id="custom.enemy.watch",label="Watcher",classId=data.encounters[0].enemies[0].classId,x=8,y=6,hp=500,energy=0,move=1}} }; }
    static GameSession Battle(bool unlocked=true)
    {
        var config=Clone(data);
        if(unlocked) config.progression.skillUnlocks.Single(s=>s.abilityId=="ability.donut_clockwork_triplicate").level=1;
        var game=new GameSession(Clone(content),config); game.Handle(new GameCommand{type="import_map",customMap=Map()}); return game;
    }
    static void Main()
    {
        content=JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"combat-content.json")),Json);
        data=JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory,"game-content.json")),Json);
        var game=Battle(false); var view=game.GetView();
        Check(view.units.Single(u=>u.id=="crawler.carl").abilityIds.Contains("ability.carl_tripwire") && !view.units.Single(u=>u.id=="crawler.carl").abilityIds.Contains("ability.carl_dynamite"),"Initial Carl kit has reusable trap without granting later explosive unlocks");
        Check(!view.units.Single(u=>u.id=="crawler.donut").abilityIds.Contains("ability.donut_clockwork_triplicate"),"Initial kit keeps Triplicate level-locked");
        string stable=Save(game); view=Cmd(game,"preview","crawler.carl","ability.carl_tripwire","tile.1.1"); Check(!view.canConfirm&&Save(game)==stable,"Ability trap rejects occupied target atomically");
        view=Cmd(game,"preview","crawler.carl","ability.carl_tripwire","tile.2.1"); Check(view.canConfirm&&Save(game)==stable&&view.forecast.Any(f=>f.afterTags.Contains("surface.trap_shock")),"Carl trap previews actual persistent terrain without spending");
        Cmd(game,"cancel");Check(Save(game)==stable,"Trap cancel is free");
        Cmd(game,"preview","crawler.carl","ability.carl_tripwire","tile.2.1");view=Cmd(game,"confirm");int hp=view.units.Single(u=>u.id=="crawler.carl").hp;int energy=view.units.Single(u=>u.id=="crawler.carl").energy;
        view=Cmd(game,"move","crawler.carl",x:2,y:1);Check(view.units.Single(u=>u.id=="crawler.carl").hp==hp-5&&!view.tiles.Single(t=>t.id=="tile.2.1").tags.Contains("surface.trap_shock")&&energy<view.units.Single(u=>u.id=="crawler.carl").maxEnergy,"Committed mana-funded tripwire triggers on ally and is consumed");
        game=Battle(); Cmd(game,"select","crawler.donut"); stable=Save(game);view=Cmd(game,"preview","crawler.donut","ability.donut_clockwork_triplicate","crawler.carl");Check(!view.canConfirm&&Save(game)==stable,"Triplicate rejects non-pet allies");
        view=Cmd(game,"preview","crawler.donut","ability.donut_clockwork_triplicate","crawler.mongo");Check(view.canConfirm&&view.forecast.Count(f=>f.targetId.StartsWith("clockwork."))==2&&Save(game)==stable,"Triplicate forecast includes two real copies without mutating save");
        Cmd(game,"cancel");Check(Save(game)==stable,"Triplicate cancel is free");
        Cmd(game,"preview","crawler.donut","ability.donut_clockwork_triplicate","crawler.mongo");view=Cmd(game,"confirm");var copies=view.units.Where(u=>u.id.StartsWith("clockwork.")).ToArray();
        Check(copies.Length==2&&copies.All(u=>u.hp==12&&u.move==3&&u.energy==0&&u.artId=="mongo"&&u.abilityIds.Contains("ability.mongo_bite")),"Triplicate commits controllable pet copies with adapted stats and pet art/free attacks");
        var config2=Clone(data);config2.progression.skillUnlocks.Single(s=>s.abilityId=="ability.donut_clockwork_triplicate").level=1;var loaded=new GameSession(Clone(content),config2);stable=Save(game);view=loaded.ImportSave(Clone(game.ExportSave()));Check(!view.message.StartsWith("Save rejected")&&Save(loaded)==stable,"Clockwork lifetime and actions roundtrip exactly");
        var malformed=Clone(game.ExportSave());malformed.units.Single(u=>u.id==copies[0].id).duplicateRounds=99;loaded.ImportSave(malformed);Check(Save(loaded)==stable,"Malformed summon lifetime rejected atomically");
        malformed=Clone(game.ExportSave());malformed.units.Single(u=>u.id==copies[0].id).permanentTags=null;loaded.ImportSave(malformed);Check(Save(loaded)==stable,"Null clone tag arrays reject without crashing");
        malformed=Clone(game.ExportSave());malformed.units=malformed.units.Where(u=>u.id!=copies[1].id).ToArray();loaded.ImportSave(malformed);Check(Save(loaded)==stable,"Missing clockwork sibling rejects incomplete pair");
        var recast=Clone(game.ExportSave());recast.units.Single(u=>u.id=="crawler.donut").acted=false;game.ImportSave(recast);stable=Save(game);view=Cmd(game,"preview","crawler.donut","ability.donut_clockwork_triplicate","crawler.mongo");Check(!view.canConfirm&&Save(game)==stable,"Active pair prevents a second summon even with action and Mana available");
        var combat=Clone(game.ExportSave());combat.units.Single(u=>u.team=="enemy").x=4;combat.units.Single(u=>u.team=="enemy").y=2;game.ImportSave(combat);loaded.ImportSave(combat);
        Cmd(game,"select",copies[0].id);view=game.GetView();Check(view.selectedUnitId==copies[0].id&&view.canMove&&view.canAct&&view.abilities.Any(a=>a.id=="ability.mongo_bite"),"Clockwork copy receives an actual independent activation");
        int foe=game.GetView().units.Single(u=>u.team=="enemy").hp;view=Cmd(game,"preview",copies[0].id,"ability.mongo_bite","custom.enemy.watch");Check(view.canConfirm&&view.forecast.Any(f=>f.targetId=="custom.enemy.watch"&&f.beforeHp-f.afterHp==7),"Clockwork free pet attack forecasts genuine damage");Cmd(game,"confirm");Check(game.GetView().units.Single(u=>u.team=="enemy").hp==foe-7,"Independent clockwork attack commits exact damage");loaded.ImportSave(Clone(game.ExportSave()));
        Cmd(loaded,"select",copies[0].id); Round(game);Round(loaded);Check(Save(game)==Save(loaded),"Copies remain deterministic across reload and first expiry tick");
        Check(game.GetView().units.Count(u=>u.id.StartsWith("clockwork."))==2,"Copies persist through first round");
        Round(game);Check(!game.GetView().units.Any(u=>u.id.StartsWith("clockwork.")),"Both copies despawn after two round ticks");
        game=Session();Cmd(game,"set_specialty","crawler.donut",classId:"class.cryomancer");view=game.GetView();Check(view.roster.Single(r=>r.id=="crawler.donut").specialtyClassId=="class.cryomancer"&&view.roster.Single(r=>r.id=="crawler.donut").classId=="class.former_child_actor","Character Actor records specialty without replacing permanent class");
        stable=Save(game);Cmd(game,"set_specialty","crawler.donut",classId:"class.cleric");Check(Save(game)==stable,"Specialty can be selected only once per floor");
        loaded=Session();loaded.ImportSave(Clone(game.ExportSave()));Check(Save(loaded)==stable,"Specialty choice and receipt survive reload");
        var old=Clone(new GameSession(Clone(content),Clone(data)).ExportSave());foreach(var r in old.roster){r.specialtyClassId=null;r.specialtyFloor=0;}Check(!loaded.ImportSave(old).message.StartsWith("Save rejected"),"Saves without specialty selection remain compatible");
        game=Session();Cmd(game,"start_journey");stable=Save(game);Cmd(game,"set_specialty","crawler.donut",classId:"class.cleric");Check(Save(game)==stable&&!game.GetView().roster.Single(r=>r.id=="crawler.donut").specialtyAvailable,"Story specialty selection stays locked before floor three");
        var story=Clone(game.ExportSave());story.journey.floorIndex=2;story.encounterIndex=2;story.home=null;story.xp=data.journey.floors[0].encounter.xp+data.journey.floors[1].encounter.xp;int growth=data.progression.xpThresholds.Count(t=>t<=story.xp)-1;foreach(var r in story.roster){r.maxHp+=growth*data.progression.hpPerLevel;r.maxEnergy+=growth*data.progression.manaPerLevel;}view=game.ImportSave(story);Check(!view.message.StartsWith("Save rejected")&&view.roster.Single(r=>r.id=="crawler.donut").specialtyAvailable,"Character Actor becomes available on story floor three: "+view.message);
        Cmd(game,"set_specialty","crawler.donut",classId:"class.cryomancer");story=Clone(game.ExportSave());story.journey.floorIndex=3;story.encounterIndex=3;stable=Save(game);game.ImportSave(story);Check(Save(game)==stable,"A specialty from another floor cannot be smuggled into a save");
        var rushConfig=Clone(data);rushConfig.progression.skillUnlocks.Single(s=>s.abilityId=="ability.katia_rush").level=1;game=new GameSession(Clone(content),rushConfig);game.Handle(new GameCommand{type="import_map",customMap=Map()});Cmd(game,"select","crawler.katia");stable=Save(game);int walking=game.GetView().units.Single(u=>u.id=="crawler.katia").effectiveMove;view=Cmd(game,"preview","crawler.katia","ability.katia_rush","crawler.katia");Check(view.canConfirm&&Save(game)==stable&&view.forecast.Any(f=>f.targetId=="crawler.katia"&&f.afterMove-f.beforeMove==2),"Rush previews real movement bonus without mutating resources");view=Cmd(game,"confirm");Check(view.units.Single(u=>u.id=="crawler.katia").effectiveMove==walking+2&&view.canMove&&!view.canAct,"Rush spends action while preserving boosted movement");loaded=new GameSession(Clone(content),Clone(rushConfig));stable=Save(game);loaded.ImportSave(Clone(game.ExportSave()));Check(Save(loaded)==stable,"Rush timed movement roundtrips exactly");Round(game);Round(game);Check(game.GetView().units.Single(u=>u.id=="crawler.katia").effectiveMove==walking&&!game.GetView().units.Single(u=>u.id=="crawler.katia").tags.Contains("status.rushing"),"Rush movement bonus expires after two round ticks");
        Console.WriteLine("PASS "+checks+" signature checks.");
    }
}
