using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

static class RankTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static void Check(bool value, string label) { if (!value) throw new Exception("FAILED: " + label); checks++; Console.WriteLine("PASS " + label); }
    static string Snapshot(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static GameView Command(GameSession game, string type, string owner = null, string ability = null, string target = null, string node = null, string classId = null)
    {
        GameView view = game.Handle(new GameCommand { type = type, unitId = owner, abilityId = ability, targetId = target, nodeId = node, classId = classId });
        if (type != "start") return view;
        for (int attempt = 0; view.screen == "explore" && attempt < 100; attempt++)
        {
            ExplorationView map = view.exploration;
            ExplorationPointView door = map.points.FirstOrDefault(p => p.kind == "encounter" && p.canInteract);
            if (door != null) return game.Handle(new GameCommand { type = "explore_interact", targetId = door.id });
            ExplorationTileView tile = map.tiles.Where(t => t.reachable && !t.revealed).OrderBy(t => Math.Abs(t.x - map.x) + Math.Abs(t.y - map.y)).ThenBy(t => t.y).ThenBy(t => t.x).FirstOrDefault();
            if (tile == null) { door = map.points.First(p => p.kind == "encounter"); tile = map.tiles.Where(t => t.reachable).OrderBy(t => Math.Abs(t.x - door.x) + Math.Abs(t.y - door.y)).First(); }
            view = game.Handle(new GameCommand { type = "explore_move", x = tile.x, y = tile.y });
        }
        return view;
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        Tables(); CastModes(); SavedSummonFloorGate(); AuthoredProfiles(); RankEffects(); DefinitionValidation(); ClassPointBudget(); TrainingAndResolver(); ClassOwnershipAndCheckpoints();
        Console.WriteLine(checks + " rank/class progression checks passed.");
    }
    static void SavedSummonFloorGate()
    {
        const string spell="ability.donut_clockwork_triplicate";GameData config=Clone(data);RosterDef carl=config.roster.Single(r=>r.id=="crawler.carl");carl.innateAbilityIds=carl.innateAbilityIds.Concat(new[]{spell}).Distinct().ToArray();carl.maxSkillRank=20;
        GameSession game=new GameSession(Clone(content),config);Command(game,"start_journey");Command(game,"start");GameSave save=game.ExportSave();
        Check(save.screen=="battle"&&save.journey.floorIndex==0,"summon floor-gate fixture starts a real floor-one battle");
        save.development.practice=new[]{new SkillPracticeSave{unitId="crawler.carl",abilityId=spell,uses=SkillRankProgression.Thresholds(config.development.practice,spell)[19]}};Check(!game.ImportSave(save).message.StartsWith("Save rejected"),"legacy overtrained Primal uses remain importable before floor three");
        Command(game,"select","crawler.carl");var preview=Command(game,"preview","crawler.carl",spell,"crawler.mongo");Check(preview.canConfirm,"innate summon is legal before floor-three class unlock");Command(game,"confirm");save=game.ExportSave();
        Check(!game.ImportSave(Clone(save)).message.StartsWith("Save rejected"),"legitimate rank-fifteen copies reload before floor three despite saved rank-twenty practice");
        var expected=AbilityScaling.Apply(content.abilities.Single(a=>a.id==spell),AuthoredRank(spell,20)).effects.Single(e=>e.op=="DuplicatePet");var forged=Clone(save);foreach(var unit in forged.units.Where(u=>u.duplicateSourceId!=null)){unit.maxHp=expected.summonHp;unit.hp=expected.summonHp;unit.move=expected.summonMove;unit.duplicateRounds=expected.summonRounds;}
        string stable=Snapshot(game);var rejected=game.ImportSave(forged);Check(rejected.message.StartsWith("Save rejected")&&Snapshot(game)==stable,"floor-one import rejects forged rank-twenty summon stats atomically");
    }
    static ActionModifiers AuthoredRank(string ability, int rank) { return AbilityScaling.Modifiers(SkillRankProgression.Table(data.development.practice, ability)[rank - 1]); }
    static BattleState AuthoredBoard()
    {
        BattleState state = new BattleState();
        for (int y=0;y<8;y++) for(int x=0;x<10;x++) state.Entities.Add("tile."+x+"."+y,new EntityState{Id="tile."+x+"."+y,IsTile=true,X=x,Y=y});
        EntityState caster=new EntityState{Id="caster",ClassId=content.classes[0].id,Team="player",Hp=100,MaxHp=100,Energy=100,X=1,Y=1};
        caster.GrantedAbilities.UnionWith(content.abilities.Select(a=>a.id));state.Entities.Add(caster.Id,caster);
        EntityState enemy=new EntityState{Id="foe",ClassId=content.classes[0].id,Team="enemy",Hp=500,MaxHp=500,Energy=100,X=2,Y=1};enemy.GrantedAbilities.UnionWith(content.abilities.Select(a=>a.id));state.Entities.Add(enemy.Id,enemy);
        EntityState pet=new EntityState{Id="pet",ClassId=content.classes[0].id,Team="player",Hp=1,MaxHp=100,Energy=0,X=1,Y=2};pet.Tags.Add("trait.pet");state.Entities.Add(pet.Id,pet);return state;
    }
    static void AuthoredProfiles()
    {
        Check(data.development.practice.abilityProfiles.Length==95&&data.development.practice.abilityProfiles.Select(p=>p.abilityId).Distinct().Count()==95,"all 95 authored abilities have distinct explicit rank profiles");
        Check(content.abilities.All(a=>{var rows=SkillRankProgression.Table(data.development.practice,a.id);return rows.Length==20&&rows.Zip(rows.Skip(1),(l,r)=>r.requiredUses>l.requiredUses).All(v=>v);}),"every authored profile expands to twenty increasing practice thresholds");
        Catalog catalog=new Catalog(content);catalog.ConfigureRankTags(data.development.practice);RulesEngine engine=new RulesEngine(catalog);BattleState state=AuthoredBoard();
        const string missile="ability.donut_magic_missile";
        var nine=engine.Execute(state,"caster",missile,"foe",AuthoredRank(missile,9));var ten=engine.Execute(state,"caster",missile,"foe",AuthoredRank(missile,10));
        Check(!nine.State.Entities["foe"].Tags.Contains("status.burning")&&ten.State.Entities["foe"].Tags.Contains("status.burning")&&state.Entities["foe"].Hp==500,"authored rank-ten missile executes ignition while rank nine and preview input remain unburned");
        Check(data.tagRules.Single(r=>r.tag=="status.burning").turnDamage>0&&data.tagRules.Single(r=>r.tag=="status.burning").durationRounds==2,"missile ignition uses a real two-round damaging status rule");
        const string teleport="ability.donut_puddle_jumper";bool rejected=false;try{engine.Execute(state,"caster",teleport,"tile.5.1",AuthoredRank(teleport,1));}catch(ArgumentException){rejected=true;}
        var jumped=engine.Execute(state,"caster",teleport,"tile.5.1",AuthoredRank(teleport,5));Check(rejected&&jumped.State.Entities["caster"].X==5&&state.Entities["caster"].X==1,"authored rank-five teleport reaches a tile rejected at rank one");
        const string summon="ability.donut_clockwork_triplicate";var fifteen=engine.Execute(state,"caster",summon,"pet",AuthoredRank(summon,15));var twenty=engine.Execute(state,"caster",summon,"pet",AuthoredRank(summon,20));var oldCopy=fifteen.State.Entities.Values.First(e=>e.DuplicateSourceId!=null);var newCopy=twenty.State.Entities.Values.First(e=>e.DuplicateSourceId!=null);
        Check(newCopy.MaxHp>oldCopy.MaxHp&&newCopy.DuplicateRounds>oldCopy.DuplicateRounds&&AuthoredRank(summon,20).summonRoundsBonus<=SkillRankProgression.Profile(data.development.practice,summon).summonRoundsBonusCap,"authored rank-twenty summons execute stronger capped copies than rank fifteen");
        const string guard="ability.imani_wing_guard";var weak=engine.Execute(state,"caster",guard,"caster",AuthoredRank(guard,1));var strong=engine.Execute(state,"caster",guard,"caster",AuthoredRank(guard,20));
        var weakHit=engine.Execute(weak.State,"foe","ability.strike","caster");var strongHit=engine.Execute(strong.State,"foe","ability.strike","caster");Check(strongHit.State.Entities["caster"].Hp>weakHit.State.Entities["caster"].Hp,"authored guard rank variants prevent more actual incoming damage");
        const string heal="ability.donut_heal_critter";rejected=false;try{engine.Execute(state,"caster",heal,"caster");}catch(ArgumentException){rejected=true;}
        var healed=engine.Execute(state,"caster",heal,"pet");Check(rejected&&healed.State.Entities["pet"].Hp>1,"canonical Heal Critter rejects a crawler and actually restores a pet");
        // Link an isolated inventory record to the unchanged authored spell, exercising the real item resolver path.
        Content withItem=Clone(content);withItem.items=withItem.items.Concat(new[]{new ItemDef{id="item.authored_rank_test",label="Spell fixture",abilityId=missile}}).ToArray();var itemEngine=new RulesEngine(new Catalog(withItem));var itemCast=itemEngine.ExecuteItem(state,"caster","item.authored_rank_test","foe");
        Check(!itemCast.State.Entities["foe"].Tags.Contains("status.burning")&&itemCast.State.Entities["foe"].Hp>ten.State.Entities["foe"].Hp,"item casting the same authored spell receives neither learned damage nor rank-ten ignition");
        Check(data.forms.All(f=>f.practiceAbilityId=="ability.katia_shapeshift")&&data.stances.All(s=>string.IsNullOrEmpty(s.practiceAbilityId)),"actual authored forms train Shapeshift while ordinary stances have no training alias");
        var missileGame=AuthoredPracticeBattle("crawler.donut",missile,10);var missileSave=missileGame.ExportSave();missileSave.units.Single(u=>u.team=="enemy").x=4;missileSave.units.Single(u=>u.team=="enemy").y=3;missileGame.ImportSave(missileSave);string stable=Snapshot(missileGame);var missileView=Command(missileGame,"preview","crawler.donut",missile,"custom.enemy.rank");int predicted=missileView.forecast.Single(f=>f.targetId=="custom.enemy.rank").afterHp;Check(missileView.canConfirm&&Snapshot(missileGame)==stable&&missileView.forecast.Single(f=>f.targetId=="custom.enemy.rank").afterTags.Contains("status.burning"),"authored rank-ten missile forecasts actual ignition without changing save");missileView=Command(missileGame,"confirm");Check(missileView.units.Single(u=>u.id=="custom.enemy.rank").hp==predicted&&missileGame.ExportSave().timedTags.Any(t=>t.entityId=="custom.enemy.rank"&&t.tag=="status.burning"&&t.remainingRounds==2),"authored missile commit matches forecast and stores real two-round Burning lifetime");
        AuthoredMovementAndTrap();
    }
    static GameSession AuthoredPracticeBattle(string owner,string ability,int rank, GameData source = null)
    {
        GameData config=Clone(source ?? data);foreach(var unlock in config.progression.skillUnlocks)if(unlock.abilityId==ability)unlock.level=1;
        GameSession game=new GameSession(Clone(content),config);game.Handle(new GameCommand{type="import_map",customMap=new CustomMapData{width=10,height=8,playerSpawns=new[]{new CellView{x=1,y=1},new CellView{x=1,y=3},new CellView{x=1,y=5},new CellView{x=3,y=3}},enemies=new[]{new SpawnDef{id="custom.enemy.rank",label="Rank opponent",classId=data.encounters[0].enemies[0].classId,x=8,y=6,hp=500,energy=0,move=1}}}});
        GameSave save=game.ExportSave();save.development.practice=rank==1?new SkillPracticeSave[0]:new[]{new SkillPracticeSave{unitId=owner,abilityId=ability,uses=SkillRankProgression.Thresholds(data.development.practice,ability)[rank-1]}};Check(!game.ImportSave(save).message.StartsWith("Save rejected"),"authored practice battlefield imports rank "+rank+" "+ability);game.Handle(new GameCommand{type="select",unitId=owner});return game;
    }
    static void CastModes()
    {
        const string spell = "ability.donut_magic_missile", owner = "crawler.donut", enemy = "custom.enemy.rank";
        GameData config = Clone(data);
        var profile = config.development.practice.abilityProfiles.Single(p => p.abilityId == spell);
        profile.castModes = new[] { new AbilityCastModeDef { id = "mode.economy", label = "Economy", minimumRank = 5, manaCost = 1, damageBonus = -2 }, new AbilityCastModeDef { id = "mode.power", label = "Power", minimumRank = 5, manaCost = 6, damageBonus = 4 } };
        GameSession game = AuthoredPracticeBattle(owner, spell, 5, config);
        GameSave save = game.ExportSave(); save.units.Single(u => u.id == enemy).x = 4; save.units.Single(u => u.id == enemy).y = 3; save.units.Single(u => u.id == owner).energy = 1;
        Check(!game.ImportSave(save).message.StartsWith("Save rejected"), "cast mode fixture imports low Mana");
        string stable = Snapshot(game);
        var ability = game.GetView().abilities.Single(a => a.id == spell);
        var cheap = ability.castModes.Single(m => m.id == "mode.economy");
        Check(ability.enabled && cheap.enabled && cheap.cost == 1 && cheap.targetIds.Contains(enemy) && !ability.castModes.Single(m => m.id == "mode.power").enabled, "affordable low-cost mode keeps ability selectable with mode-specific legal targets");
        var bad = game.Handle(new GameCommand { type = "preview", unitId = owner, abilityId = spell, targetId = enemy, castModeId = "mode.unknown" });
        Check(!bad.canConfirm && Snapshot(game) == stable, "unknown mode rejects without resources or practice");
        bad = game.Handle(new GameCommand { type = "preview", unitId = owner, abilityId = spell, targetId = enemy, castModeId = "mode.power" });
        Check(!bad.canConfirm && Snapshot(game) == stable, "unaffordable mode rejects atomically");
        var preview = game.Handle(new GameCommand { type = "preview", unitId = owner, abilityId = spell, targetId = enemy, castModeId = cheap.id });
        int hp = preview.forecast.Single(f => f.targetId == enemy).afterHp;
        Check(preview.canConfirm && preview.forecast.Single(f => f.targetId == owner).afterEnergy == 0 && Snapshot(game) == stable, "selected mode forecasts exact absolute Mana without spending");
        Command(game, "cancel"); Check(Snapshot(game) == stable, "mode preview cancellation preserves checkpoint");
        game.Handle(new GameCommand { type = "preview", unitId = owner, abilityId = spell, targetId = enemy, castModeId = cheap.id });
        var committed = Command(game, "confirm");
        Check(committed.units.Single(u => u.id == enemy).hp == hp && committed.units.Single(u => u.id == owner).energy == 0 && committed.units.Single(u => u.id == owner).acted && !committed.units.Single(u => u.id == owner).moved, "mode commit matches forecast, spends action and preserves movement");
        Check(game.ExportSave().development.practice.Single(p => p.unitId == owner && p.abilityId == spell).uses == save.development.practice.Single(p => p.unitId == owner && p.abilityId == spell).uses + 1, "mode commit trains learned ability exactly once");
        game = AuthoredPracticeBattle(owner, spell, 4, config); save = game.ExportSave(); save.units.Single(u => u.id == enemy).x = 4; save.units.Single(u => u.id == enemy).y = 3; game.ImportSave(save); stable = Snapshot(game);
        bad = game.Handle(new GameCommand { type = "preview", unitId = owner, abilityId = spell, targetId = enemy, castModeId = cheap.id });
        Check(!bad.canConfirm && Snapshot(game) == stable && !bad.abilities.Single(a => a.id == spell).castModes.Single(m => m.id == cheap.id).enabled, "rank-four learned spell rejects rank-five mode in resolver and view");
        game = AuthoredPracticeBattle(owner, spell, 4, config); save = game.ExportSave();
        save.units.Single(u => u.id == enemy).x = 4; save.units.Single(u => u.id == enemy).y = 3;
        save.development.practice.Single(p => p.unitId == owner && p.abilityId == spell).uses = SkillRankProgression.Thresholds(config.development.practice, spell)[4] - 1;
        game.ImportSave(save); stable = Snapshot(game);
        bad = game.Handle(new GameCommand { type = "preview", unitId = owner, itemId = "item.health_tonic", targetId = owner, castModeId = cheap.id });
        Check(!bad.canConfirm && Snapshot(game) == stable, "consumable casts cannot bypass mode restrictions");
        var normal = Command(game, "preview", owner, spell, enemy); Check(normal.canConfirm, "last rank-four normal earned use can preview");
        var ranked = Command(game, "confirm");
        Check(ranked.development.practice.Single(p => p.unitId == owner && p.abilityId == spell).rank == 5 && ranked.development.practice.Single(p => p.unitId == owner && p.abilityId == spell).castModes.All(c => c.enabled), "ordinary committed practice unlocks rank-five modes immediately");
        var m = AuthoredRank(spell, 5); m.hasCastMode = true; m.castModeCost = 6; m.castModeDamageBonus = -100;
        Check(AbilityScaling.Apply(content.abilities.Single(a => a.id == spell), m).effects.Where(e => e.op == "Damage").All(e => e.amount == 0), "negative mode damage is bounded at zero");
    }
    static void AuthoredMovementAndTrap()
    {
        const string rush="ability.katia_rush";GameSession low=AuthoredPracticeBattle("crawler.katia",rush,1),high=AuthoredPracticeBattle("crawler.katia",rush,15);
        int lowBefore=low.GetView().units.Single(u=>u.id=="crawler.katia").effectiveMove,highBefore=high.GetView().units.Single(u=>u.id=="crawler.katia").effectiveMove;
        string stable=Snapshot(high);var forecast=Command(high,"preview","crawler.katia",rush,"crawler.katia");Check(forecast.canConfirm&&Snapshot(high)==stable,"authored ranked Rush forecasts without granting practice");Command(high,"cancel");Check(Snapshot(high)==stable,"authored ranked Rush cancellation preserves save");Command(high,"preview","crawler.katia",rush,"crawler.katia");var highView=Command(high,"confirm");Command(low,"preview","crawler.katia",rush,"crawler.katia");var lowView=Command(low,"confirm");
        Check(highView.units.Single(u=>u.id=="crawler.katia").effectiveMove-highBefore>lowView.units.Single(u=>u.id=="crawler.katia").effectiveMove-lowBefore,"authored Rush variant grants more real movement after exact preview and commit");
        var shaped=AuthoredPracticeBattle("crawler.katia","ability.katia_shapeshift",5);int previousUses=shaped.GetView().development.practice.Single(p=>p.unitId=="crawler.katia"&&p.abilityId=="ability.katia_shapeshift").uses;stable=Snapshot(shaped);
        var shapePreview=shaped.Handle(new GameCommand{type="preview",unitId="crawler.katia",formId="form.bulwark"});Check(shapePreview.canConfirm&&Snapshot(shaped)==stable&&shapePreview.forecast.Any(f=>f.targetId=="crawler.katia"&&f.afterTags.Contains("status.guarded_rank5")),"authored Bulwark mapping previews the trained Shapeshift guard variant");Command(shaped,"cancel");Check(Snapshot(shaped)==stable,"authored form cancellation leaves practice unchanged");shaped.Handle(new GameCommand{type="preview",unitId="crawler.katia",formId="form.bulwark"});var shapedView=Command(shaped,"confirm");Check(shapedView.units.Single(u=>u.id=="crawler.katia").tags.Contains("status.guarded_rank5")&&shapedView.development.practice.Single(p=>p.unitId=="crawler.katia"&&p.abilityId=="ability.katia_shapeshift").uses==previousUses+1,"authored form commits ranked guard and trains its mapped ability once");
        const string trap="ability.carl_tripwire";low=AuthoredPracticeBattle("crawler.carl",trap,1);high=AuthoredPracticeBattle("crawler.carl",trap,15);
        foreach(var game in new[]{low,high}){Command(game,"preview","crawler.carl",trap,"tile.2.1");Command(game,"confirm");}
        int lowHp=low.GetView().units.Single(u=>u.id=="crawler.carl").hp,highHp=high.GetView().units.Single(u=>u.id=="crawler.carl").hp;
        lowView=low.Handle(new GameCommand{type="move",unitId="crawler.carl",x=2,y=1});highView=high.Handle(new GameCommand{type="move",unitId="crawler.carl",x=2,y=1});
        Check(highHp-highView.units.Single(u=>u.id=="crawler.carl").hp>lowHp-lowView.units.Single(u=>u.id=="crawler.carl").hp&&!highView.tiles.Single(t=>t.id=="tile.2.1").tags.Any(t=>t.StartsWith("surface.trap_shock")),"authored shock-trap rank variant deals greater real entry damage and is consumed");
    }
    static void RankEffects()
    {
        Content definitions = Clone(content); GameData config = Clone(data);
        var ability = definitions.abilities.First(a => a.effects.Any(e => e.op == "Teleport"));
        config.development.practice.abilityProfiles = new[] { new AbilityRankProfile { abilityId = ability.id, damagePerRank = 0, healPerRank = 0, costReductionPerRank = 0, rangePerRank = 1, rangeBonusCap = 12, milestones = new[] { new RankMilestoneDef { rank = 2, description = "Cleanse adaptation", removeTags = new[] { "status.wet" } } } } };
        SkillRankView row = SkillRankProgression.Table(config.development.practice, ability.id)[1];
        AbilityDef effective = AbilityScaling.Apply(ability, AbilityScaling.Modifiers(row));
        Check(effective.range == ability.range + 1 && effective.effects.Any(e => e.op == "RemoveTag" && e.tag == "status.wet"), "rank range and milestone status operations use one effective ability");
        Check(ability.range + 1 == effective.range && ability.effects.All(e => e.op != "RemoveTag"), "rank transformation preserves authored base definitions");
        ability.requiredTargetTag = "trait.pet";
        Catalog targetCatalog = new Catalog(definitions);
        EntityState actor = new EntityState { Id = "actor", ClassId = definitions.classes[0].id, Team = "player", Hp = 10, MaxHp = 10, Energy = 100 };
        actor.GrantedAbilities.Add(ability.id);
        EntityState target = new EntityState { Id = "tile", IsTile = true, X = 0, Y = 0 };
        BattleState state = new BattleState(); state.Entities.Add(actor.Id, actor); state.Entities.Add(target.Id, target);
        bool rejected = false;
        try { new RulesEngine(targetCatalog).Execute(state, actor.Id, ability.id, target.Id); } catch (ArgumentException) { rejected = true; }
        Check(rejected, "required target trait is enforced by the pure resolver before commitment");
        AbilityDef petHeal = new AbilityDef { id = "ability.pet_heal_fixture", label = "Pet healing", target = "ally", range = 1, requiredTargetTag = "trait.pet", effects = new[] { new EffectDef { op = "Heal", amount = 3 } } };
        definitions.abilities = definitions.abilities.Concat(new[] { petHeal }).ToArray(); actor.GrantedAbilities.Add(petHeal.id);
        EntityState pet = new EntityState { Id = "pet", ClassId = actor.ClassId, Team = "player", Hp = 1, MaxHp = 10, X = 1 }; pet.Tags.Add("trait.pet"); state.Entities.Add(pet.Id, pet);
        var petResult = new RulesEngine(new Catalog(definitions)).Execute(state, actor.Id, petHeal.id, pet.Id);
        Check(petResult.State.Entities[pet.Id].Hp == 4 && state.Entities[pet.Id].Hp == 1, "required pet trait allows actual pet healing without modifying preview input");
        ability.requiredTargetTag = "";
        var summon = definitions.abilities.First(a => a.effects.Any(e => e.op == "DuplicatePet"));
        EffectDef original = summon.effects.First(e => e.op == "DuplicatePet");
        EffectDef scaled = AbilityScaling.Apply(summon, new ActionModifiers { summonHpBonus = 5, summonMoveBonus = 1, summonRoundsBonus = 2 }).effects.First(e => e.op == "DuplicatePet");
        Check(scaled.summonHp == original.summonHp + 5 && scaled.summonMove == original.summonMove + 1 && scaled.summonRounds == original.summonRounds + 2, "summon rank growth changes actual effect parameters");
        Catalog catalog = new Catalog(definitions); catalog.ConfigureRankTags(new SkillProgressionDef { abilityProfiles = new[] { new AbilityRankProfile { milestones = new[] { new RankMilestoneDef { tagReplacements = new[] { new TagReplacementDef { fromTag = "status.wet", toTag = "status.frozen" } } } } } } });
        var tags = new System.Collections.Generic.HashSet<string> { "status.wet", "status.frozen" }; Check(catalog.HasStackedRankTags(tags), "saved tag validation detects stacked rank variants"); catalog.RemoveTagFamily(tags, "status.wet");
        Check(tags.Count == 0, "cleansing a base tag removes all authored ranked family variants");
    }
    static void Tables()
    {
        SkillProgressionDef config = new SkillProgressionDef();
        SkillRankView[] table = SkillRankProgression.Table(config, "ability.fixture");
        Check(table.Length == 20 && table[0].requiredUses == 0 && table[1].requiredUses == 3 && table[2].requiredUses == 8, "rank 1–20 retains the established first three training thresholds");
        Check(table.Zip(table.Skip(1), (a, b) => b.requiredUses > a.requiredUses).All(x => x) && table[10].requiredUses - table[9].requiredUses > table[9].requiredUses - table[8].requiredUses, "training thresholds increase and slow more sharply beyond rank ten");
        Check(SkillRankProgression.Rank(config, "ability.fixture", 100000, 15) == 15 && SkillRankProgression.Rank(config, "ability.fixture", 100000, 20) == 20 && table.Count(r => r.trainable) == 15, "normal eligibility caps training at fifteen while eligible profiles reach twenty");
        config.abilityProfiles = new[] { new AbilityRankProfile { abilityId = "ability.fixture", practiceMultiplierPercent = 200, damagePerRank = 2, healPerRank = 0, costReductionCap = 1, milestones = new[] { new RankMilestoneDef { rank = 10, damageBonus = 3, description = "Adapted mastery" } } } };
        SkillRankView[] tuned = SkillRankProgression.Table(config, "ability.fixture", 20);
        Check(tuned[1].requiredUses == 6 && tuned[1].damageBonus == 2 && tuned[1].healBonus == 0 && tuned[19].damageBonus == 20 && tuned[19].costReduction == 1 && tuned[9].milestones.Single() == "Adapted mastery", "per-ability training, effect caps, and milestone descriptions use one bounded table");
    }
    static bool RejectsData(Action<GameData> change)
    {
        GameData candidate = Clone(data); change(candidate);
        try { GameDataValidator.Validate(candidate, new Catalog(Clone(content))); return false; }
        catch (ArgumentException) { return true; }
    }
    static bool RejectsProfile(Action<AbilityRankProfile> change)
    {
        return RejectsData(candidate => {
            AbilityRankProfile profile = new AbilityRankProfile { abilityId = content.abilities[0].id };
            candidate.development.practice.abilityProfiles = new[] { profile }; change(profile);
        });
    }
    static void DefinitionValidation()
    {
        GameDataValidator.Validate(Clone(data), new Catalog(Clone(content)));
        Check(RejectsData(d => d.roster[0].maxSkillRank = 14) && RejectsData(d => d.roster[0].maxSkillRank = 21), "rank eligibility rejects values outside the supported fifteen-to-twenty interval");
        Check(RejectsProfile(p => p.abilityId = "ability.unknown") && RejectsData(d => d.development.practice.abilityProfiles = new[] { new AbilityRankProfile { abilityId = content.abilities[0].id }, new AbilityRankProfile { abilityId = content.abilities[0].id } }), "rank definitions reject unknown and duplicate ability profiles");
        Check(RejectsProfile(p => p.castModes = new[] { new AbilityCastModeDef { id = "mode.bad", label = "Bad", minimumRank = 21 } }) && RejectsProfile(p => p.castModes = new[] { new AbilityCastModeDef { id = "mode.bad", label = "Bad", damageBonus = -101 } }) && RejectsProfile(p => p.castModes = new[] { new AbilityCastModeDef { id = "mode.bad", label = "Bad", manaCost = 101 } }), "cast mode definitions reject invalid unlock ranks, damage and Mana bounds");
        Check(RejectsProfile(p => p.practiceMultiplierPercent = 0) && RejectsProfile(p => p.damagePerRank = -2) && RejectsProfile(p => p.healBonusCap = 101), "rank definitions reject malformed training rates and effects beyond resolver limits");
        Check(RejectsProfile(p => p.milestones = new[] { new RankMilestoneDef { rank = 21, damageBonus = 1, description = "Invalid" } }) && RejectsProfile(p => p.milestones = new[] { new RankMilestoneDef { rank = 10, damageBonus = 1, description = "First" }, new RankMilestoneDef { rank = 10, healBonus = 1, description = "Duplicate" } }) && RejectsProfile(p => p.milestones = new[] { new RankMilestoneDef { rank = 10, damageBonus = -1, description = "Negative" } }), "rank milestones reject unsupported ranks, duplicate tiers, and negative effects");
        Check(RejectsData(d => d.classSkillTrees[0].classId = content.classes.First(c => !c.playerSelectable).id) && RejectsData(d => d.classSkillTrees[0].rosterId = d.roster[0].id), "class trees require a selectable class and cannot claim a personal-tree owner");
        Check(RejectsData(d => d.classSkillTrees[1].classId = d.classSkillTrees[0].classId) && RejectsData(d => d.classSkillTrees[0].nodes[0].id = d.skillTrees[0].nodes[0].id), "class trees reject repeated class profiles and node IDs shared with personal trees");
        Check(RejectsData(d => { SkillNodeDef first = d.classSkillTrees[0].nodes[0], second = d.classSkillTrees[0].nodes[1]; first.prerequisiteIds = new[] { second.id }; second.prerequisiteIds = new[] { first.id }; first.level = second.level = 1; }) && RejectsData(d => d.classSkillTrees[0].nodes[0].prerequisiteIds = new[] { d.classSkillTrees[1].nodes[0].id }), "class graphs reject cycles and prerequisites owned by another class");
        Check(RejectsData(d => d.classSkillTrees[0].nodes[0].level = 51) && RejectsData(d => d.classSkillTrees[0].nodes[0].hpBonus = 7) && RejectsData(d => d.classSkillTrees[0].nodes[0].abilityIds = new[] { "ability.unknown" }), "class nodes reject unsupported levels, excessive effects, and unknown ability grants");
        Content invalidClasses = Clone(content); invalidClasses.classes[0].minimumFloor = 19;
        bool rejected = false; try { GameDataValidator.Validate(Clone(data), new Catalog(invalidClasses)); } catch (ArgumentException) { rejected = true; }
        Check(rejected, "class availability cannot point beyond the eighteenth floor");
    }
    static void ClassPointBudget()
    {
        Content definitions = Clone(content); GameData config = Clone(data); config.journey = null; config.neighborhood = null;
        GameSession game = new GameSession(definitions, config);
        var tree = game.GetView().skillTree.classTrees.First();
        Check(tree.nodes.Length == 14 && tree.unspentPoints == 1, "fourteen-node class starts with one point for its two root choices");
        Command(game, "preview_skill_node", tree.rosterId, node: tree.nodes.First(n => n.enabled).id);
        GameView view = Command(game, "confirm_skill_node");
        tree = view.skillTree.classTrees.First(t => t.rosterId == tree.rosterId);
        Check(tree.unspentPoints == 0 && tree.nodes.Where(n => n.level == 1 && !n.unlocked).All(n => !n.enabled), "buying one class root spends the shared tier point and blocks its alternative");
        Check(config.classSkillTrees.All(t => t.nodes.Select(n => n.level).Distinct().Count() == 7), "each authored class offers seven earned tiers for fourteen nodes through level fifty");
    }
    static GameData Fixture(Content definitions)
    {
        GameData config = Clone(data); config.journey = null; config.neighborhood = null; config.classSkillTrees = new SkillTreeDef[0];
        config.progression.xpThresholds = new[] { 0, 30, 70, 120 };
        config.development.practice.abilityProfiles = new AbilityRankProfile[0];
        config.development.practice.useThresholds = new[] { 0, 3, 8 };
        config.roster.Single(r => r.id == "crawler.carl").maxSkillRank = 20;
        AbilityDef ability = new AbilityDef { id = "ability.rank_fixture", label = "Rank fixture", target = "ally", range = 0, cost = 3, incomingTags = new string[0], effects = new[] { new EffectDef { op = "Heal", amount = 1 } } };
        definitions.abilities = definitions.abilities.Concat(new[] { ability }).ToArray();
        config.roster.Single(r => r.id == "crawler.carl").innateAbilityIds = new[] { ability.id };
        EncounterDef room = config.encounters[0]; room.tiles = new TileDef[0];
        room.enemies = new[] { new SpawnDef { id = "enemy.rank_fixture", label = "Rank fixture opponent", classId = "class.brawler", x = 8, y = 7, hp = 100, energy = 0, move = 1 } };
        return config;
    }
    static void TrainingAndResolver()
    {
        Content definitions = Clone(content); GameData config = Fixture(definitions);
        GameSession game = new GameSession(definitions, config);
        GameSave save = game.ExportSave(); int threshold = SkillRankProgression.Thresholds(config.development.practice, "ability.rank_fixture")[19];
        save.development.practice = new[] { new SkillPracticeSave { unitId = "crawler.carl", abilityId = "ability.rank_fixture", uses = threshold - 1 } };
        Check(!game.ImportSave(save).message.StartsWith("Save rejected"), "training checkpoint just below rank twenty validates");
        Command(game, "start"); save = game.ExportSave(); save.units.Single(u => u.id == "crawler.carl").hp = 1; Check(!game.ImportSave(save).message.StartsWith("Save rejected"), "wounded rank fixture validates");
        string before = Snapshot(game); GameView view = Command(game, "preview", "crawler.carl", "ability.rank_fixture", "crawler.carl");
        Check(view.canConfirm && before == Snapshot(game), "high-rank action forecast is side-effect free");
        ForecastView forecast = view.forecast.Single(f => f.targetId == "crawler.carl");
        Check(forecast.afterHp - forecast.beforeHp == 19 && forecast.beforeEnergy - forecast.afterEnergy == 1, "rank nineteen applies actual healing and bounded mana discount in shared resolver");
        Command(game, "cancel"); Check(before == Snapshot(game), "canceling high-rank forecast grants no training");
        Command(game, "preview", "crawler.carl", "ability.rank_fixture", "crawler.carl"); view = Command(game, "confirm");
        SkillPracticeView trained = view.development.practice.Single(p => p.abilityId == "ability.rank_fixture");
        Check(view.units.Single(u => u.id == "crawler.carl").hp == forecast.afterHp && trained.rank == 20 && trained.atCap && trained.uses == threshold && trained.nextRankUses == 0, "confirmed forecast matches commit and the committed use reaches rank twenty");
        int round = view.round;
        for (int i = 0; i < config.partySize && game.GetView().round == round; i++) Command(game, "end_turn");
        Command(game, "preview", "crawler.carl", "ability.rank_fixture", "crawler.carl"); view = Command(game, "confirm");
        Check(view.development.practice.Single(p => p.unitId == "crawler.carl" && p.abilityId == "ability.rank_fixture").uses == threshold && view.events.All(e => e.type != "skill_practice"), "further committed uses at the rank cap grant no extra training");
        round = view.round;
        for (int i = 0; i < config.partySize && game.GetView().round == round; i++) Command(game, "end_turn");
        view = game.Handle(new GameCommand { type = "preview", unitId = "crawler.carl", itemId = "item.health_tonic", targetId = "crawler.carl" });
        Check(view.canConfirm, "item fixture has a legal committed use");
        view = Command(game, "confirm");
        Check(game.ExportSave().development.practice.Length == 1 && view.development.practice.Single(p => p.unitId == "crawler.carl" && p.abilityId == "ability.rank_fixture").uses == threshold && view.events.All(e => e.type != "skill_practice"), "committed item use creates no ability training");
        GameSession restored = new GameSession(Clone(definitions), Clone(config));
        Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && restored.GetView().development.practice.Single(p => p.unitId == "crawler.carl" && p.abilityId == "ability.rank_fixture").rank == 20, "rank twenty persists through checkpoint reload");
        config.roster.Single(r => r.id == "crawler.carl").maxSkillRank = 15;
        restored = new GameSession(Clone(definitions), config); view = restored.ImportSave(Clone(game.ExportSave()));
        Check(!view.message.StartsWith("Save rejected") && view.development.practice.Single(p => p.unitId == "crawler.carl" && p.abilityId == "ability.rank_fixture").rank == 15, "eligibility changes safely cap a legacy over-trained checkpoint");
    }
    static void ClassOwnershipAndCheckpoints()
    {
        Content definitions = Clone(content); GameData config = Fixture(definitions);
        string classId = config.roster.Single(r => r.id == "crawler.carl").classId;
        config.encounters[0].xp = 4900;
        string granted = definitions.abilities.First(a => a.target == "enemy" && !definitions.classes.Single(c => c.id == classId).abilityIds.Contains(a.id)).id;
        config.classSkillTrees = new[] { new SkillTreeDef { id = "classtree.fixture", classId = classId, label = "Fixture class", description = "Adapted class progression", nodes = new[] {
            new SkillNodeDef { id = "classnode.fixture_root", label = "Root", description = "Damage training", damageBonus = 1, abilityIds = new[] { granted } },
            new SkillNodeDef { id = "classnode.fixture_child", label = "Child", description = "HP training", level = 5, hpBonus = 2, prerequisiteIds = new[] { "classnode.fixture_root" } },
            new SkillNodeDef { id = "classnode.fixture_capstone", label = "Capstone", description = "Level fifty training", level = 50, hpBonus = 2, prerequisiteIds = new[] { "classnode.fixture_child" } }
        } } };
        if (config.progression.xpThresholds.Length < 50) config.progression.xpThresholds = Enumerable.Range(0, 50).Select(i => i * 100).ToArray();
        GameSession game = new GameSession(definitions, config); string before = Snapshot(game);
        GameView view = Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_root");
        Check(view.skillTree.canConfirm && view.skillTree.forecast.afterDamageBonus == view.skillTree.forecast.beforeDamageBonus + 1 && before == Snapshot(game), "selected class-node preview reports the same runtime modifier without spending");
        Command(game, "cancel_skill_node"); Check(before == Snapshot(game), "canceling class-node learning preserves checkpoint");
        Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_root"); view = Command(game, "confirm_skill_node");
        Check(game.ExportSave().skillTree.unlockedIds.Contains("crawler.carl::classnode.fixture_root") && view.skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.First().unlocked, "class-node learning saves explicit per-crawler ownership");
        before = Snapshot(game); view = Command(game, "preview_skill_node", "crawler.donut", node: "classnode.fixture_root");
        Check(!view.skillTree.canConfirm && before == Snapshot(game), "a different selected class cannot buy another class profile");
        GameSave forged = Clone(game.ExportSave()); forged.skillTree.unlockedIds = new[] { "crawler.donut::classnode.fixture_child" };
        Check(game.ImportSave(forged).message.StartsWith("Save rejected") && before == Snapshot(game), "class checkpoint prerequisites must belong to the same crawler");
        forged = Clone(game.ExportSave()); forged.skillTree.unlockedIds = new[] { "classnode.fixture_root" };
        Check(game.ImportSave(forged).message.StartsWith("Save rejected"), "class checkpoint cannot omit its crawler owner");
        view = Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_capstone"); Check(!view.skillTree.canConfirm, "level fifty class capstone remains locked at the starting level");
        GameSave learned = Clone(game.ExportSave()); GameSession restored = new GameSession(Clone(definitions), Clone(config));
        Check(!restored.ImportSave(learned).message.StartsWith("Save rejected") && restored.GetView().skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.First().unlocked, "owned class skills round-trip through save validation");
        string replacement = definitions.classes.First(c => c.playerSelectable && c.id != classId).id;
        Command(game, "set_class", "crawler.carl", classId: replacement); Check(game.ExportSave().skillTree.unlockedIds.Contains("crawler.carl::classnode.fixture_root") && !game.GetView().skillTree.classTrees.Any(t => t.rosterId == "crawler.carl"), "class switching preserves learned ownership while deactivating its profile");
        Command(game, "set_class", "crawler.carl", classId: classId); Check(game.GetView().skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.First().unlocked, "returning to a class restores its learned profile");
        Command(game, "start"); GameSave battle = Clone(game.ExportSave()); SavedUnit enemy = battle.units.Single(u => u.id == "enemy.rank_fixture"); enemy.x = 2; enemy.y = 1; enemy.hp = 1;
        Check(!game.ImportSave(battle).message.StartsWith("Save rejected"), "level fifty reward fixture validates before battle");
        Command(game, "preview", "crawler.carl", "ability.carl_powerful_strike", "enemy.rank_fixture"); view = Command(game, "confirm");
        Check(view.screen == "victory" && view.progression.level == 50, "an earned encounter reward reaches actual runtime level fifty");
        game.Handle(new GameCommand { type = "choose_reward", rewardId = config.rewards[0].id }); Command(game, "continue");
        Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_child"); Command(game, "confirm_skill_node");
        int beforeHp = game.GetView().roster.Single(r => r.id == "crawler.carl").maxHp;
        view = Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_capstone");
        Check(view.skillTree.canConfirm && view.skillTree.forecast.afterHp == beforeHp + 2, "level fifty capstone previews its actual stat effect after prerequisites");
        view = Command(game, "confirm_skill_node");
        Check(view.roster.Single(r => r.id == "crawler.carl").maxHp == beforeHp + 2 && view.skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.Last().unlocked, "level fifty capstone commits its real stat effect");
        restored = new GameSession(Clone(definitions), Clone(config));
        Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected"), "earned level fifty class build round-trips with derived stat validation");
        Command(game, "start"); restored = new GameSession(Clone(definitions), Clone(config));
        GameView imported = restored.ImportSave(Clone(game.ExportSave()));
        Check(!imported.message.StartsWith("Save rejected") && imported.units.Single(u => u.id == "crawler.carl").abilityIds.Contains(granted), "imported active class profile grants its learned ability through the shared progression path");
    }
}
