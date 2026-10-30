using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

static class MechanismTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;

    static T Clone<T>(T value)
    {
        return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json);
    }

    static GameSession Session()
    {
        return new GameSession(Clone(content), Clone(data));
    }

    static string Save(GameSession game)
    {
        return JsonSerializer.Serialize(game.ExportSave(), Json);
    }

    static void Check(bool condition, string label)
    {
        if (!condition)
            throw new Exception(label);
        checks++;
        Console.WriteLine("PASS " + label);
    }

    static void Roundtrip(GameSession game, string label)
    {
        GameSession copy = Session();
        GameView view = copy.ImportSave(Clone(game.ExportSave()));
        Check(!view.message.StartsWith("Save rejected:") && Save(copy) == Save(game), label);
    }

    static GeneratedFloorPlan Floor(int depth)
    {
        return new GeneratedFloorPlan
        {
            seed = depth,
            map = new CustomMapData
            {
                label = "Adapted expedition depth " + depth,
                width = 8,
                height = 6,
                enemies = new[]
                {
                    new SpawnDef
                    {
                        id = "custom.enemy.guard",
                        label = "Guard",
                        classId = "class.brawler",
                        artId = "rat",
                        x = 4,
                        y = 0,
                        hp = 1,
                        energy = 1,
                        move = 1,
                    },
                },
            },
            entrance = new CellView { x = 0, y = 0 },
            exit = new CellView { x = 7, y = 0 },
            groups = new[]
            {
                new GeneratedEncounterGroup
                {
                    id = "watch",
                    label = "Watch",
                    kind = "visible",
                    x = 3,
                    y = 0,
                    enemyIds = new[] { "custom.enemy.guard" },
                },
            },
            discoveries = new[]
            {
                new ExplorationPointDef
                {
                    id = "seal",
                    label = "Seal",
                    description = "Seal recovered.",
                    kind = "objective",
                    x = 0,
                    y = 0,
                },
            },
        };
    }

    static GeneratedCampaignPlan Plan()
    {
        return new GeneratedCampaignPlan
        {
            id = "test.route",
            label = "Adapted depths",
            floors = new[] { Floor(1), Floor(2), Floor(3) },
        };
    }

    static void ClearFloor(GameSession game)
    {
        game.Handle(new GameCommand { type = "explore_interact", targetId = "seal" });
        game.Handle(new GameCommand { type = "explore_step", x = 1 });
        Check(game.GetView().screen == "battle", "approach enters existing tactical combat");
        Roundtrip(game, "battle checkpoint exact");
        bool struck = false;
        foreach (UnitView unit in game.GetView().units.Where(u => u.team == "player").ToArray())
        {
            GameView view = game.Handle(new GameCommand { type = "select", unitId = unit.id });
            AbilityView hit = view.abilities.FirstOrDefault(a =>
                a.enabled && a.targetIds.Contains("custom.enemy.guard")
            );
            if (hit == null)
                continue;
            game.Handle(
                new GameCommand
                {
                    type = "preview",
                    abilityId = hit.id,
                    targetId = "custom.enemy.guard",
                }
            );
            game.Handle(new GameCommand { type = "confirm" });
            struck = true;
            break;
        }
        Check(struck && game.GetView().screen == "victory", "combat resolves normally");
        Roundtrip(game, "victory checkpoint exact");
        game.Handle(new GameCommand { type = "choose_reward", rewardId = data.rewards[0].id });
        game.Handle(new GameCommand { type = "continue" });
        Roundtrip(game, "reward return checkpoint exact");
        while (game.GetView().generatedDungeon.x < 7)
            game.Handle(new GameCommand { type = "explore_step", x = 1 });
        while (game.GetView().generatedDungeon.y > 0)
            game.Handle(new GameCommand { type = "explore_step", y = -1 });
    }

    static void Reject(GameSession game, Action<GameSave> corrupt, string label)
    {
        string before = Save(game);
        GameSave candidate = Clone(game.ExportSave());
        corrupt(candidate);
        Check(
            game.ImportSave(candidate).message.StartsWith("Save rejected:") && Save(game) == before,
            label
        );
    }

    static GeneratedCampaignPlan MechanismPlan()
    {
        GeneratedCampaignPlan plan = Plan();
        foreach (GeneratedFloorPlan floor in plan.floors)
        {
            floor.map.tiles = new[]
            {
                new TileDef
                {
                    x = 2,
                    y = 2,
                    blocked = true,
                },
            };
            floor.mechanisms = new[]
            {
                new GeneratedMechanismDef
                {
                    id = "gate.fixture",
                    label = "Oil-bound gate",
                    x = 2,
                    y = 2,
                    materialTags = new[] { "surface.oil" },
                    openCells = new[]
                    {
                        new CellView { x = 2, y = 2 },
                    },
                    solutions = new[]
                    {
                        new GeneratedMechanismSolutionDef
                        {
                            id = "fire",
                            label = "Channel fire",
                            kind = "ability",
                            x = 0,
                            y = 1,
                            abilityTag = "element.fire",
                            requiredMaterialTags = new[] { "surface.oil" },
                        },
                        new GeneratedMechanismSolutionDef
                        {
                            id = "bomb",
                            label = "Use fire bomb",
                            kind = "item",
                            x = 0,
                            y = 1,
                            abilityTag = "element.fire",
                            itemId = "item.fire_bomb",
                            itemCount = 1,
                        },
                        new GeneratedMechanismSolutionDef
                        {
                            id = "lever",
                            label = "Pull remote lever",
                            kind = "manual",
                            x = 0,
                            y = 5,
                        },
                    },
                },
            };
        }
        return plan;
    }

    static GameSession Start()
    {
        GameSession game = Session();
        GameView view = game.Handle(
            new GameCommand { type = "import_campaign", campaignPlan = MechanismPlan() }
        );
        Check(
            view.screen == "explore" && view.generatedCampaign != null,
            "mechanism campaign imports with baseline fallback"
        );
        return game;
    }

    static GameCommand Spell(string actor)
    {
        return new GameCommand
        {
            type = "preview_mechanism",
            targetId = "gate.fixture",
            solutionId = "fire",
            unitId = actor,
            abilityId = "ability.firebolt",
        };
    }

    static void RejectPlan(Action<GeneratedFloorPlan> change, string label)
    {
        GameSession game = Session();
        string before = Save(game);
        GeneratedCampaignPlan plan = MechanismPlan();
        change(plan.floors[0]);
        game.Handle(new GameCommand { type = "import_campaign", campaignPlan = plan });
        Check(Save(game) == before && game.GetView().generatedCampaign == null, label);
    }

    static void StrikeGuard(GameSession game)
    {
        foreach (UnitView unit in game.GetView().units.Where(u => u.team == "player").ToArray())
        {
            GameView view = game.Handle(new GameCommand { type = "select", unitId = unit.id });
            AbilityView hit = view.abilities.FirstOrDefault(a =>
                a.enabled && a.targetIds.Contains("custom.enemy.guard")
            );
            if (hit == null)
                continue;
            game.Handle(
                new GameCommand
                {
                    type = "preview",
                    abilityId = hit.id,
                    targetId = "custom.enemy.guard",
                }
            );
            game.Handle(new GameCommand { type = "confirm" });
            return;
        }
        throw new Exception("No legal guard attack");
    }

    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(
            File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")),
            Json
        );
        data = JsonSerializer.Deserialize<GameData>(
            File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")),
            Json
        );
        data.roster[0].innateAbilityIds = data.roster[0]
            .innateAbilityIds.Concat(new[] { "ability.firebolt" })
            .Distinct()
            .ToArray();
        string actor = data.roster[0].id;
        RejectPlan(
            f =>
            {
                f.map.tiles = f
                    .map.tiles.Concat(
                        new[]
                        {
                            new TileDef
                            {
                                x = 4,
                                y = 4,
                                blocked = true,
                            },
                        }
                    )
                    .ToArray();
                f.mechanisms[0].openCells = new[]
                {
                    new CellView { x = 2, y = 2 },
                    new CellView { x = 4, y = 4 },
                };
            },
            "disconnected opening cells rejected before mutation"
        );
        RejectPlan(
            f =>
            {
                f.map.tiles = new[]
                {
                    new TileDef
                    {
                        x = 0,
                        y = 2,
                        blocked = true,
                    },
                };
                f.mechanisms[0].x = 0;
                f.mechanisms[0].openCells[0].x = 0;
            },
            "boundary opening rejected before mutation"
        );
        RejectPlan(
            f =>
            {
                f.map.tiles = f
                    .map.tiles.Concat(
                        new[]
                        {
                            new TileDef
                            {
                                x = 1,
                                y = 2,
                                blocked = true,
                            },
                            new TileDef
                            {
                                x = 3,
                                y = 2,
                                blocked = true,
                            },
                            new TileDef
                            {
                                x = 2,
                                y = 1,
                                blocked = true,
                            },
                            new TileDef
                            {
                                x = 2,
                                y = 3,
                                blocked = true,
                            },
                        }
                    )
                    .ToArray();
            },
            "isolated hole cannot masquerade as a passage"
        );
        RejectPlan(
            f =>
            {
                f.mechanisms[0].solutions[0].x = 4;
                f.mechanisms[0].solutions[0].y = 0;
            },
            "action location overlapping an enemy rejected"
        );
        RejectPlan(
            f =>
            {
                f.mechanisms[0].solutions[0].x = 0;
                f.mechanisms[0].solutions[0].y = 0;
            },
            "action location overlapping entrance rejected"
        );
        GameSession game = Start();
        Check(
            game.GetView().mechanisms.Single().solutions.Length == 2,
            "undiscovered remote solution remains hidden"
        );
        Check(
            game.GetView().exploration.points.Count(point => point.kind == "mechanism") == 1,
            "co-located spell and item solutions share one inspection point"
        );
        string before = Save(game);
        GameView view = game.Handle(Spell(actor));
        Check(
            view.mechanismPreview != null && Save(game) == before,
            "preview leaves resources topology and receipts unchanged"
        );
        Check(
            view.mechanismPreview.manaBefore - view.mechanismPreview.manaAfter
                == content.abilities.Single(a => a.id == "ability.firebolt").cost,
            "preview uses the normal shared spell cost"
        );
        game.Handle(new GameCommand { type = "cancel_mechanism" });
        Check(
            Save(game) == before && game.GetView().mechanismPreview == null,
            "cancel changes no authoritative state"
        );
        game.Handle(Spell(actor));
        game.Handle(new GameCommand { type = "safe_room_rest" });
        game.Handle(new GameCommand { type = "confirm_mechanism" });
        Check(Save(game) == before, "even an invalid intervening command makes confirmation stale");
        game.Handle(Spell(actor));
        game.HandleExplorationMovement(new GameCommand { type = "explore_step", y = 1 });
        game.Handle(new GameCommand { type = "confirm_mechanism" });
        Check(
            game.ExportSave().generatedDungeon.mechanismReceipts.Length == 0,
            "compact movement invalidates confirmation"
        );
        game.Handle(Spell(actor));
        GameSave reload = Clone(game.ExportSave());
        game.ImportSave(reload);
        game.Handle(new GameCommand { type = "confirm_mechanism" });
        Check(
            game.ExportSave().generatedDungeon.mechanismReceipts.Length == 0,
            "reload requires a fresh preview"
        );
        GameSave wounded = Clone(game.ExportSave());
        RosterView hurt = wounded.roster.First(r => r.id == actor);
        hurt.hp--;
        Check(
            !game.ImportSave(wounded).message.StartsWith("Save rejected:"),
            "wounded campaign fixture is valid"
        );
        view = game.Handle(Spell(actor));
        MechanismPreviewView predicted = view.mechanismPreview;
        int hp = game.GetView().roster.First(r => r.id == actor).hp;
        int xp = game.GetView().xp;
        game.Handle(new GameCommand { type = "confirm_mechanism" });
        Check(
            game.ExportSave().generatedDungeon.mechanismReceipts.Single().abilityId
                == "ability.firebolt"
                && game.GetView().roster.First(r => r.id == actor).energy == predicted.manaAfter,
            "confirmation consumes forecast mana and records the selected spell once"
        );
        Check(
            game.GetView().roster.First(r => r.id == actor).hp == hp
                && game.GetView().xp == xp
                && game.GetView().progression.level == 1,
            "opening grants no healing XP or level"
        );
        Check(
            game.GetView().mechanisms.Single().solved
                && !game.GetView().exploration.tiles.Single(t => t.x == 2 && t.y == 2).blocked
                && game.ExportSave().customMap.tiles.Single().blocked,
            "opened traversal derives from receipts while original map stays immutable"
        );
        before = Save(game);
        game.Handle(new GameCommand { type = "confirm_mechanism" });
        game.Handle(Spell(actor));
        Check(
            Save(game) == before,
            "duplicate confirmation and second solution cannot charge again"
        );
        Roundtrip(game, "opened map and receipt restore exactly");
        Reject(
            game,
            save =>
                save.generatedDungeon.mechanismReceipts = new[]
                {
                    save.generatedDungeon.mechanismReceipts[0],
                    save.generatedDungeon.mechanismReceipts[0],
                },
            "duplicate receipt rejected atomically"
        );
        Reject(
            game,
            save => save.generatedDungeon.mechanismReceipts[0].mechanismId = "unknown",
            "unknown mechanism receipt rejected"
        );
        Reject(
            game,
            save => save.generatedDungeon.mechanismReceipts[0].solutionId = "unknown",
            "unknown solution receipt rejected"
        );
        Reject(
            game,
            save => save.generatedDungeon.mechanismReceipts[0].abilityId = "ability.spark",
            "receipt spell must match authored capability tag"
        );
        Reject(
            game,
            save => save.generatedCampaign.plan.floors[0].mechanisms[0].openCells[0].x++,
            "saved opening cannot rewrite its realized campaign plan"
        );
        game.Handle(new GameCommand { type = "explore_step", y = 1 });
        game.Handle(new GameCommand { type = "explore_step", x = 1 });
        view = game.Handle(new GameCommand { type = "explore_step", x = 1 });
        Check(
            view.screen == "battle"
                && !view.tiles.Single(t => t.x == 2 && t.y == 2).blocked
                && view.mechanisms.Single().solved,
            "walking through opened cell starts unchanged combat on altered geometry"
        );
        Roundtrip(game, "battle geometry with shortcut restores exactly");
        GameSave defeat = Clone(game.ExportSave());
        defeat.screen = "defeat";
        defeat.selectedUnitId = null;
        foreach (SavedUnit unit in defeat.units)
            if (unit.team == "player")
                unit.hp = 0;
        foreach (RosterView member in defeat.roster)
            if (member.selected)
                member.hp = 0;
        Check(
            !game.ImportSave(defeat).message.StartsWith("Save rejected:"),
            "defeated checkpoint retains opened geometry"
        );
        view = game.Handle(new GameCommand { type = "retry" });
        Check(
            view.screen == "battle"
                && !view.tiles.Single(t => t.x == 2 && t.y == 2).blocked
                && view.mechanisms.Single().solved,
            "retry rebuilds open battle geometry from the receipt"
        );
        Roundtrip(game, "retried battle with shortcut restores exactly");
        before = Save(game);
        game.Handle(Spell(actor));
        Check(
            Save(game) == before && game.GetView().mechanismPreview == null,
            "mechanisms cannot be used during combat"
        );
        StrikeGuard(game);
        Check(
            game.GetView().screen == "victory",
            "shortcut never bypasses mandatory combat victory"
        );
        game.Handle(new GameCommand { type = "choose_reward", rewardId = data.rewards[0].id });
        game.Handle(new GameCommand { type = "continue" });
        Check(
            game.GetView().screen == "explore"
                && !game.GetView().exploration.tiles.Single(t => t.x == 2 && t.y == 2).blocked,
            "combat return preserves opened exploration collision"
        );
        Roundtrip(game, "post-combat altered floor restores exactly");
        GameSession poor = Start();
        GameSave empty = Clone(poor.ExportSave());
        empty.roster.First(r => r.id == actor).energy = 0;
        empty.inventory.First(i => i.itemId == "item.fire_bomb").count = 0;
        Check(
            !poor.ImportSave(empty).message.StartsWith("Save rejected:"),
            "empty resource fixture loads"
        );
        before = Save(poor);
        poor.Handle(Spell(actor));
        poor.Handle(
            new GameCommand
            {
                type = "preview_mechanism",
                targetId = "gate.fixture",
                solutionId = "bomb",
                unitId = actor,
            }
        );
        Check(
            Save(poor) == before && poor.GetView().mechanismPreview == null,
            "insufficient mana and supplies reject without spending"
        );
        Check(
            poor.GetView()
                .exploration.points.Where(p => p.kind == "mechanism")
                .All(p => p.canInteract)
                && poor.GetView()
                    .mechanisms.Single()
                    .solutions.All(sol => !sol.enabled || sol.candidates.Any(c => c.enabled)),
            "unaffordable mechanism remains inspectable with candidate reasons"
        );
        empty = Clone(poor.ExportSave());
        empty.roster.First(r => r.id == actor).hp = 0;
        poor.ImportSave(empty);
        before = Save(poor);
        poor.Handle(Spell(actor));
        Check(
            Save(poor) == before && poor.GetView().mechanismPreview == null,
            "defeated actor cannot solve mechanisms"
        );
        GameSession itemGame = Start();
        int itemBefore = itemGame.GetView().items.Single(i => i.id == "item.fire_bomb").count;
        int manaBefore = itemGame.GetView().roster.First(r => r.id == actor).energy;
        itemGame.Handle(
            new GameCommand
            {
                type = "preview_mechanism",
                targetId = "gate.fixture",
                solutionId = "bomb",
                unitId = actor,
            }
        );
        Check(
            itemGame.GetView().mechanismPreview.itemCountBefore == itemBefore
                && itemGame.GetView().mechanismPreview.itemCountAfter == itemBefore - 1,
            "item preview reports exact shared inventory cost"
        );
        itemGame.Handle(new GameCommand { type = "confirm_mechanism" });
        Check(
            itemGame.GetView().items.Single(i => i.id == "item.fire_bomb").count == itemBefore - 1
                && itemGame.GetView().roster.First(r => r.id == actor).energy == manaBefore,
            "item alternative spends supplies with no mana cost"
        );
        GameSession manual = Start();
        for (int i = 0; i < 4; i++)
            manual.Handle(new GameCommand { type = "explore_step", y = 1 });
        Check(
            manual.GetView().mechanisms.Single().solutions.Any(s => s.id == "lever"),
            "physical detour discovers the free lever alternative"
        );
        manaBefore = manual.GetView().roster.First(r => r.id == actor).energy;
        manual.Handle(
            new GameCommand
            {
                type = "preview_mechanism",
                targetId = "gate.fixture",
                solutionId = "lever",
                unitId = actor,
            }
        );
        manual.Handle(new GameCommand { type = "confirm_mechanism" });
        Check(
            manual.GetView().mechanisms.Single().solved
                && manual.GetView().roster.First(r => r.id == actor).energy == manaBefore,
            "remote manual route opens the same shortcut without mana"
        );
        GameSession archive = Start();
        archive.Handle(Spell(actor));
        archive.Handle(new GameCommand { type = "confirm_mechanism" });
        ClearFloor(archive);
        archive.Handle(new GameCommand { type = "preview_descent" });
        archive.Handle(new GameCommand { type = "confirm_descent" });
        Check(
            archive
                .ExportSave()
                .generatedCampaign.archives.Single()
                .mechanismReceipts.Single()
                .mechanismId == "gate.fixture",
            "descent archives persistent shortcut receipts"
        );
        Roundtrip(archive, "archived solved mechanism survives reload");
        GameSession legacy = Session();
        GeneratedCampaignPlan old = MechanismPlan();
        foreach (GeneratedFloorPlan floor in old.floors)
            floor.mechanisms = null;
        legacy.Handle(new GameCommand { type = "import_campaign", campaignPlan = old });
        Roundtrip(legacy, "legacy missing mechanisms defaults empty");
        Console.WriteLine(checks + " mechanism checks passed.");
    }
}
