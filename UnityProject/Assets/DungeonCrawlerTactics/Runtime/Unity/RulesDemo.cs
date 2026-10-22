using System;
using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    // Attach to an empty GameObject and assign starter-content.json as a TextAsset.
    public sealed class RulesDemo : MonoBehaviour
    {
        [SerializeField] private TextAsset contentJson;
        private void Start()
        {
            if (contentJson == null) { Debug.LogError("Assign starter-content.json to RulesDemo.", this); return; }
            try
            {
                Content content = JsonUtility.FromJson<Content>(contentJson.text);
                RulesEngine engine = new RulesEngine(new Catalog(content));
                BattleState battle = new BattleState();
                battle.Entities.Add("hero", new EntityState { Id = "hero", ClassId = "class.pyromancer", Team = "party", Hp = 30, MaxHp = 30, Energy = 10, X = 0, Y = 0 });
                EntityState oil = new EntityState { Id = "tile.1.0", IsTile = true, X = 1, Y = 0 };
                oil.Tags.Add("surface.oil"); battle.Entities.Add(oil.Id, oil);
                ActionResult preview = engine.Preview(battle, "hero", "ability.fire_surface", oil.Id);
                Debug.Log("Preview: " + string.Join(" → ", preview.Log) + "; burns=" + preview.State.Entities[oil.Id].Tags.Contains("surface.burning"), this);
                battle = engine.Execute(battle, "hero", "ability.fire_surface", oil.Id).State;
                Debug.Log("Committed: burning=" + battle.Entities[oil.Id].Tags.Contains("surface.burning") + "; hero energy=" + battle.Entities["hero"].Energy, this);
            }
            catch (Exception ex) { Debug.LogException(ex, this); }
        }
    }
}
