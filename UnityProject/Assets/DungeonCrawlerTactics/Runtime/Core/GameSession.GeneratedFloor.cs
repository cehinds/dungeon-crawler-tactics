using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class GeneratedFloorPlan
    {
        public int schemaVersion = 1, seed;
        public CustomMapData map;
        public CellView entrance, exit;
        public GeneratedEncounterGroup[] groups = new GeneratedEncounterGroup[0];
        public ExplorationPointDef[] discoveries = new ExplorationPointDef[0];
    }
    [Serializable] public sealed class GeneratedEncounterGroup
    {
        public string id, label, kind;
        public int x, y;
        public string[] enemyIds = new string[0];
    }
    [Serializable] public sealed class ExplorationMovementResponse { public bool partial; public GameView view; }
    public sealed partial class GameSession
    {
        // Movement changes only exploration state. Full transitions still use the ordinary view.
        public ExplorationMovementResponse HandleExplorationMovement(GameCommand command)
        {
            bool compact = command != null && (command.type == "explore_step" || command.type == "explore_move") && screen == "explore" && generatedDungeon != null && generatedDungeon.floorPlan != null;
            GameView result = HandleCommand(command, compact);
            return new ExplorationMovementResponse { partial = compact && screen == "explore", view = result };
        }
        private GameView CommandView(bool compact)
        {
            if (!compact || screen != "explore" || generatedDungeon == null || generatedDungeon.floorPlan == null) return GetView();
            GeneratedDungeonState s = generatedDungeon;
            return new GameView { screen = screen, phase = phase, message = message, exploration = FloorExplorationView(), generatedCampaign = CampaignView(),
                generatedDungeon = new GeneratedDungeonState { x = s.x, y = s.y, entrance = CopyCell(s.entrance), exit = CopyCell(s.exit), cleared = s.cleared, steps = s.steps, activeGroupId = s.activeGroupId, defeatedGroupIds = (string[])s.defeatedGroupIds.Clone(), claimedIds = (string[])s.claimedIds.Clone(), revealed = Array.ConvertAll(s.revealed, CopyCell) } };
        }
        private static CellView CopyCell(CellView c) { return c == null ? null : new CellView { x = c.x, y = c.y }; }
        private static GeneratedFloorPlan CopyFloor(GeneratedFloorPlan f)
        {
            if (f == null) return null;
            Require(f.groups != null && f.groups.Length > 0 && f.groups.Length <= 16 && f.discoveries != null && f.discoveries.Length <= 64, "Invalid floor collections.");
            return new GeneratedFloorPlan { schemaVersion = f.schemaVersion, seed = f.seed, map = CopyCustomMap(f.map), entrance = CopyCell(f.entrance), exit = CopyCell(f.exit), groups = Array.ConvertAll(f.groups, g => g == null ? null : new GeneratedEncounterGroup { id = g.id, label = g.label, kind = g.kind, x = g.x, y = g.y, enemyIds = g.enemyIds == null ? null : (string[])g.enemyIds.Clone() }), discoveries = Array.ConvertAll(f.discoveries, p => p == null ? null : new ExplorationPointDef { id = p.id, label = p.label, description = p.description, kind = p.kind, itemId = p.itemId, count = p.count, x = p.x, y = p.y }) };
        }
        private static int FloorWins(GeneratedDungeonState s, string atScreen) { Require(s.defeatedGroupIds != null && s.defeatedGroupIds.Length <= 16, "Invalid defeated group receipts."); return s.defeatedGroupIds.Length + (atScreen == "victory" ? 1 : 0); }
        private static bool Has(string[] ids, string id) { return Array.IndexOf(ids, id) >= 0; }
        private static string[] Append(string[] ids, string id) { List<string> copy = new List<string>(ids); copy.Add(id); return copy.ToArray(); }
        private static bool Near(GeneratedDungeonState s, int x, int y) { return Math.Abs(s.x - x) + Math.Abs(s.y - y) <= 1; }
        private static void FilterFloorEnemies(EncounterDef map, GeneratedDungeonState s)
        {
            GeneratedEncounterGroup group = Array.Find(s.floorPlan.groups, g => g.id == s.activeGroupId);
            map.enemies = group == null ? new SpawnDef[0] : Array.FindAll(map.enemies, e => Has(group.enemyIds, e.id));
        }
        private void ValidateFloorSave(GameSave save, EncounterDef map)
        {
            GeneratedDungeonState s = save.generatedDungeon; GeneratedFloorPlan f = CopyFloor(s.floorPlan);
            Require(f.schemaVersion == 1 && f.entrance != null && f.exit != null && s.entrance != null && s.exit != null && s.entrance.x == f.entrance.x && s.entrance.y == f.entrance.y && s.exit.x == f.exit.x && s.exit.y == f.exit.y, "Invalid floor revision or endpoints.");
            Require(save.journey == null && save.scenario == null && save.expedition == null && save.exploration != null && save.exploration.Length == 0 && save.encounterIndex == 0, "Floor cannot combine campaign state.");
            CustomMapData authored = CopyCustomMap(f.map); EncounterDef original = BuildCustomEncounter(authored, true);
            Require(FloorMapEqual(authored, save.customMap), "Floor map differs from its authored plan.");
            List<CellView> cells = GeneratedCells(original, f.entrance.x, f.entrance.y);
            Func<int,int,bool> connected = (x,y) => cells.Exists(c => c.x == x && c.y == y);
            Require(connected(s.x,s.y) && connected(f.exit.x,f.exit.y) && !Array.Exists(original.enemies,e => e.x == f.entrance.x && e.y == f.entrance.y), "Floor endpoints must connect.");
            foreach (SpawnDef enemy in original.enemies) Require(connected(enemy.x, enemy.y), "Every floor enemy must connect to the entrance.");
            HashSet<string> ids = new HashSet<string>(), enemies = new HashSet<string>();
            foreach (GeneratedEncounterGroup g in f.groups)
            {
                Require(g != null && !string.IsNullOrEmpty(g.id) && g.id.Length <= 100 && ids.Add(g.id) && (g.kind == "visible" || g.kind == "ambush") && g.enemyIds != null && g.enemyIds.Length > 0 && g.enemyIds.Length <= 12 && connected(g.x,g.y), "Invalid encounter group.");
                foreach (string id in g.enemyIds) Require(id != null && enemies.Add(id) && Array.Exists(original.enemies,e => e.id == id), "Unknown or repeated group enemy.");
            }
            Require(enemies.Count == original.enemies.Length, "Every enemy needs exactly one group.");
            Require(s.defeatedGroupIds != null && s.defeatedGroupIds.Length <= f.groups.Length && s.claimedIds != null && s.claimedIds.Length <= f.discoveries.Length && s.revealed != null && s.revealed.Length <= map.width * map.height && s.steps >= 0 && s.steps < 8, "Invalid floor progress.");
            HashSet<string> done = new HashSet<string>(); foreach (string id in s.defeatedGroupIds) Require(id != null && ids.Contains(id) && done.Add(id), "Invalid defeated group.");
            bool inBattle = save.screen == "battle" || save.screen == "victory" || save.screen == "defeat";
            Require(inBattle ? s.activeGroupId != null && ids.Contains(s.activeGroupId) && !done.Contains(s.activeGroupId) : s.activeGroupId == null, "Invalid active encounter.");
            ids.Clear(); foreach (ExplorationPointDef p in f.discoveries) Require(p != null && !string.IsNullOrEmpty(p.id) && p.id.Length <= 100 && p.id != "generated.exit" && ids.Add(p.id) && connected(p.x,p.y) && (p.kind == "objective" || p.kind == "cache" && p.itemId != null && catalog.Items.ContainsKey(p.itemId) && p.count > 0 && p.count <= 99), "Invalid floor discovery.");
            done.Clear(); foreach (string id in s.claimedIds) Require(id != null && ids.Contains(id) && done.Add(id), "Invalid claimed discovery.");
            HashSet<string> seen = new HashSet<string>(); foreach (CellView c in s.revealed) Require(c != null && c.x >= 0 && c.y >= 0 && c.x < map.width && c.y < map.height && seen.Add(ExploreKey(c.x,c.y)), "Invalid floor visibility.");
            Require(seen.Contains(ExploreKey(s.x,s.y)) && seen.Contains(ExploreKey(f.entrance.x,f.entrance.y)), "Floor position must be discovered.");
            foreach (ExplorationPointDef p in f.discoveries) Require(!Has(s.claimedIds,p.id) || seen.Contains(ExploreKey(p.x,p.y)), "Claimed discovery must be revealed.");
            Require(s.cleared == (s.defeatedGroupIds.Length == f.groups.Length), "Floor clear state disagrees with encounters.");
            Require(save.screen != "complete" || FloorExitReady(s) && Near(s,f.exit.x,f.exit.y), "Reach the unlocked exit first.");
            FilterFloorEnemies(map,s); SetGeneratedSpawns(map,s);
        }
        // Prevent changes to encounter geometry and enemy rules inside a checkpoint.
        private static bool FloorMapEqual(CustomMapData a, CustomMapData b)
        {
            if (b == null || b.tiles == null || b.enemies == null || a.width != b.width || a.height != b.height || a.label != b.label || a.tiles.Length != b.tiles.Length || a.enemies.Length != b.enemies.Length) return false;
            for (int i=0;i<a.tiles.Length;i++) { TileDef x=a.tiles[i],y=b.tiles[i]; if(y==null||y.tags==null||x.x!=y.x||x.y!=y.y||x.blocked!=y.blocked||string.Join("|",x.tags)!=string.Join("|",y.tags)) return false; }
            for(int i=0;i<a.enemies.Length;i++) { SpawnDef x=a.enemies[i],y=b.enemies[i]; if(y==null||y.tags==null||x.id!=y.id||x.classId!=y.classId||x.x!=y.x||x.y!=y.y||x.hp!=y.hp||x.energy!=y.energy||x.move!=y.move||string.Join("|",x.tags)!=string.Join("|",y.tags)) return false; }
            return true;
        }
        private static bool FloorExitReady(GeneratedDungeonState s) { return s.cleared && Array.TrueForAll(s.floorPlan.discoveries,p => p.kind != "objective" || Has(s.claimedIds,p.id)); }
        private void RevealFloor()
        {
            HashSet<string> seen = new HashSet<string>(); List<CellView> cells = new List<CellView>(generatedDungeon.revealed); foreach(CellView c in cells) seen.Add(ExploreKey(c.x,c.y));
            // Short line-of-passage discovery respects walls, including their visible boundary.
            Queue<CellView> pending = new Queue<CellView>(); pending.Enqueue(new CellView{x=generatedDungeon.x,y=generatedDungeon.y}); HashSet<string> walked = new HashSet<string>();
            while(pending.Count>0) { CellView c=pending.Dequeue(); if(!walked.Add(ExploreKey(c.x,c.y)))continue; if(seen.Add(ExploreKey(c.x,c.y)))cells.Add(CopyCell(c)); if(c.cost>=4||!GeneratedOpen(customEncounter,c.x,c.y))continue; foreach(CellView n in new[]{new CellView{x=c.x+1,y=c.y},new CellView{x=c.x-1,y=c.y},new CellView{x=c.x,y=c.y+1},new CellView{x=c.x,y=c.y-1}}) if(n.x>=0&&n.y>=0&&n.x<customMap.width&&n.y<customMap.height){n.cost=c.cost+1;pending.Enqueue(n);} }
            generatedDungeon.revealed=cells.ToArray();
        }
        private bool TryFloorCommand(GameCommand command)
        {
            if (TryCampaignCommand(command)) return true;
            if(command.type=="import_floor")
            {
                GeneratedFloorPlan f=CopyFloor(command.floorPlan); Require(f!=null,"Choose a floor plan."); CustomMapData map=CopyCustomMap(f.map); EncounterDef encounter=BuildCustomEncounter(map,true); f.map=CopyCustomMap(map);
                Require(f.entrance!=null&&f.exit!=null,"Floor needs an entrance and exit.");
                GeneratedDungeonState state=new GeneratedDungeonState{floorPlan=f,x=f.entrance.x,y=f.entrance.y,entrance=CopyCell(f.entrance),exit=CopyCell(f.exit),revealed=new[]{CopyCell(f.entrance)}};
                ValidateFloorSave(new GameSave{generatedDungeon=state,customMap=map,screen="explore"},encounter);
                Reset(); customMap=map;customEncounter=encounter;generatedDungeon=state;RevealFloor();ResumeGenerated();message="Explore the continuous floor. Find supplies and open its exit.";return true;
            }
            if(generatedDungeon==null||generatedDungeon.floorPlan==null)return false;
            if(command.type=="retry") { Require(screen=="defeat", "Retry after defeat."); RefreshRosterStats(true); StartEncounter(); return true; }
            if(command.type=="resume_route"||command.type=="resume_floor") {Require(screen=="camp","Resume from the safe room.");Require(PartyCount()==data.partySize,"Choose a full party first.");foreach(RosterView member in roster.Values)Require(!member.selected||member.hp>0,"Rest to revive fallen party members first.");ResumeGenerated();return true;}
            if(command.type=="return_safe") {Require(screen=="explore","Return from exploration only.");screen="camp";return true;}
            if(command.type=="explore_step"||command.type=="explore_move")
            {
                Require(screen=="explore","Move during exploration."); int x=command.type=="explore_step"?generatedDungeon.x+command.x:command.x,y=command.type=="explore_step"?generatedDungeon.y+command.y:command.y;
                Require(Math.Abs((long)x-generatedDungeon.x)+Math.Abs((long)y-generatedDungeon.y)==1&&GeneratedOpen(customEncounter,x,y),"Choose one open cardinal step.");
                Require(!Array.Exists(customMap.enemies,e=>e.x==x&&e.y==y&&Array.Exists(generatedDungeon.floorPlan.groups,g=>!Has(generatedDungeon.defeatedGroupIds,g.id)&&Has(g.enemyIds,e.id))),"An enemy blocks that passage.");
                generatedDungeon.x=x;generatedDungeon.y=y;generatedDungeon.steps=(generatedDungeon.steps+1)%8;RevealFloor();
                List<CellView> nearby=GeneratedCells(customEncounter,x,y,4); GeneratedEncounterGroup trigger=Array.Find(generatedDungeon.floorPlan.groups,g=>!Has(generatedDungeon.defeatedGroupIds,g.id)&&nearby.Exists(c=>c.x==g.x&&c.y==g.y&&c.cost<=(g.kind=="visible"?3:4))&&(g.kind=="visible"||generatedDungeon.steps==0));
                if(trigger!=null){generatedDungeon.activeGroupId=trigger.id;customEncounter=BuildCustomEncounter(CopyCustomMap(customMap),true);FilterFloorEnemies(customEncounter,generatedDungeon);StartEncounter();}else message="The party advances.";return true;
            }
            if(command.type=="explore_interact")
            {
                Require(screen=="explore","Interact during exploration.");
                if(command.targetId=="generated.exit"){Require(FloorExitReady(generatedDungeon)&&Near(generatedDungeon,generatedDungeon.exit.x,generatedDungeon.exit.y),"Clear the encounters, find the objective, and reach the exit.");if (generatedCampaign != null) { message = "Exit ready. Preview descent to continue the expedition."; return true; } screen="complete";rewardChosen=true;message="Floor completed.";return true;}
                ExplorationPointDef p=Array.Find(generatedDungeon.floorPlan.discoveries,d=>d.id==command.targetId);Require(p!=null&&Near(generatedDungeon,p.x,p.y)&&Array.Exists(generatedDungeon.revealed,c=>c.x==p.x&&c.y==p.y)&&!Has(generatedDungeon.claimedIds,p.id),"Reach an unclaimed discovery first.");
                if(p.kind=="cache"){Require(inventory[p.itemId]<=10000-p.count,"Supplies are full.");inventory[p.itemId]+=p.count;}generatedDungeon.claimedIds=Append(generatedDungeon.claimedIds,p.id);message=p.description;return true;
            }
            return false;
        }
        private void FinishFloorBattle()
        {
            foreach(RosterDef member in data.roster){EntityState actor;if(battle.Entities.TryGetValue(member.id,out actor)&&actor.Hp>0){generatedDungeon.x=actor.X;generatedDungeon.y=actor.Y;break;}}
            generatedDungeon.defeatedGroupIds=Append(generatedDungeon.defeatedGroupIds,generatedDungeon.activeGroupId);generatedDungeon.activeGroupId=null;generatedDungeon.cleared=generatedDungeon.defeatedGroupIds.Length==generatedDungeon.floorPlan.groups.Length;
            rewardChosen=true;battle=new BattleState();units.Clear();timed.Clear();customEncounter=BuildCustomEncounter(CopyCustomMap(customMap),true);FilterFloorEnemies(customEncounter,generatedDungeon);RevealFloor();ResumeGenerated();
        }
        private ExplorationView FloorExplorationView()
        {
            HashSet<string> seen=new HashSet<string>();foreach(CellView c in generatedDungeon.revealed)seen.Add(ExploreKey(c.x,c.y));List<ExplorationTileView> tiles=new List<ExplorationTileView>();
            for(int y=0;y<customMap.height;y++)for(int x=0;x<customMap.width;x++)tiles.Add(new ExplorationTileView{x=x,y=y,revealed=seen.Contains(ExploreKey(x,y)),blocked=!GeneratedOpen(customEncounter,x,y),reachable=GeneratedOpen(customEncounter,x,y)&&Near(generatedDungeon,x,y)});
            List<ExplorationPointView> points=new List<ExplorationPointView>();points.Add(new ExplorationPointView{id="generated.entrance",label="Safe-room passage",kind="entrance",x=generatedDungeon.entrance.x,y=generatedDungeon.entrance.y});
            if(seen.Contains(ExploreKey(generatedDungeon.exit.x,generatedDungeon.exit.y)))points.Add(new ExplorationPointView{id="generated.exit",label="Floor exit",description="Clear every encounter and recover the objective.",kind="exit",x=generatedDungeon.exit.x,y=generatedDungeon.exit.y,canInteract=FloorExitReady(generatedDungeon)&&Near(generatedDungeon,generatedDungeon.exit.x,generatedDungeon.exit.y)});
            foreach(ExplorationPointDef p in generatedDungeon.floorPlan.discoveries)if(seen.Contains(ExploreKey(p.x,p.y)))points.Add(new ExplorationPointView{id=p.id,label=p.label,description=p.description,kind=p.kind,x=p.x,y=p.y,claimed=Has(generatedDungeon.claimedIds,p.id),canInteract=!Has(generatedDungeon.claimedIds,p.id)&&Near(generatedDungeon,p.x,p.y)});
            foreach(GeneratedEncounterGroup g in generatedDungeon.floorPlan.groups)if(!Has(generatedDungeon.defeatedGroupIds,g.id)&&seen.Contains(ExploreKey(g.x,g.y)))points.Add(new ExplorationPointView{id=g.id,label=g.label,kind=g.kind=="visible"?"enemy":"danger",description=g.kind=="visible"?"Approach to begin tactical combat.":"Danger zone: an encounter check occurs every eight steps.",x=g.x,y=g.y});
            return new ExplorationView{id="generated.floor",label=customMap.label,description="Connected passages, visible enemies and dangerous encounter zones.",width=customMap.width,height=customMap.height,x=generatedDungeon.x,y=generatedDungeon.y,tiles=tiles.ToArray(),points=points.ToArray()};
        }
    }
}
