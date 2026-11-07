namespace DccRebuild;
public class LevelRow
{
    public int level, totalXp, hpGain, manaGain, powerGain, armorGain;
}
public class ProgressionRules
{
    public LevelRow[] levels = [];
    public int practicePerUse = 1;
}
public class SkillRank
{
    public int rank = 1, practiceRequired, power, cost, range = 1, manaPowerPerPoint = 1;
    public double powerMultiplier = 1;
    public int[] manaOptions = [];
}
public class SkillProgress
{
    public string targetKind = "enemy";
    public string skillId = "",
                nextEffect = "",
                resource = "Mana",
                effect = "",
                disabledReason = "";
    public int trainedRank, effectiveRank, effectRank, gearBonusRank, temporaryBonusRank, permissionMaxRank, rankCapacity, practice, practiceToNext, maxRank, cost;
    public double practiceProgressPercent;
    public bool canUse;
    public int[] manaOptions = [];
}
public sealed class Progression
{
    readonly Content content;
    public Progression(Content content)
    {
        this.content = content;
        if (content.progression == null || content.progression.levels == null || content.skills == null || content.encounters == null)
            throw new InvalidOperationException("Missing progression rules.");
        if (content.progression.levels.Length == 0)
            content.progression.levels = Enumerable.Range(1, 20).Select(n => new LevelRow { level = n, totalXp = (n - 1) * 30, hpGain = n == 1 ? 0 : 8, manaGain = n == 1 ? 0 : 2, powerGain = n == 1 ? 0 : 2 }).ToArray();
        var rows = content.progression.levels;
        if (rows.Length != 20 || content.progression.practicePerUse is < 1 or > 100 || rows.Where((r, i) => r == null || r.level != i + 1 || r.totalXp < 0 || (i == 0 && r.totalXp != 0) || (i > 0 && r.totalXp <= rows[i - 1].totalXp) || r.totalXp > 100000 || r.hpGain is < 0 or > 40 || r.manaGain is < 0 or > 40 || r.powerGain is < 0 or > 40 || r.armorGain is < 0 or > 40 || (i == 0 && (r.hpGain != 0 || r.manaGain != 0 || r.powerGain != 0 || r.armorGain != 0))).Any())
            throw new InvalidOperationException("Invalid character progression table.");
        foreach (var k in content.skills)
        {
            if (k == null || k.ranks == null)
                throw new InvalidOperationException("Missing skill rank rows.");
            if (k.ranks.Length == 0)
                k.ranks = [new() { rank = k.startingRank, power = k.power,
                cost = k.cost, range = k.range }];
            if (k.startingRank < 1 || k.startingRank > k.permissionMaxRank || k.ranks[0] == null || k.ranks[0].rank != k.startingRank || k.ranks[0].practiceRequired != 0 || k.ranks.Where((r, i) => r == null || r.rank != k.startingRank + i || r.rank > k.rankCapacity || r.practiceRequired < 0 || (i > 0 && r.practiceRequired <= k.ranks[i - 1].practiceRequired) || r.practiceRequired > 1000000 || r.cost is < 0 or > 100 || r.power is < 0 or > 1000 || r.range is < 1 or > 100 || !double.IsFinite(r.powerMultiplier) || r.powerMultiplier <= 0 || r.powerMultiplier > 10 || r.manaOptions == null || r.manaOptions.Any(m => m < r.cost || m > 100) || r.manaOptions.Distinct().Count() != r.manaOptions.Length || (r.manaOptions.Length > 0 && !r.manaOptions.Contains(r.cost)) || r.manaPowerPerPoint is < 0 or > 100).Any())
                throw new InvalidOperationException("Invalid skill progression: " + k.id);
        }
        if (content.encounters.Any(e => e == null || e.xpReward < 0 || e.xpReward > 100000 || e.goldReward < 0 || e.goldReward > 100000))
            throw new InvalidOperationException("Invalid encounter rewards.");
    }
    public int EffectiveRank(Unit unit, Skill skill)
    {
        int gear = content.items.FirstOrDefault(i => i.id == unit.equipment)?.rankModifiers.GetValueOrDefault(skill.id) ?? 0;
        int temporary = TemporaryBonus(unit, skill.id);
        return Math.Clamp(unit.ranks.GetValueOrDefault(skill.id, skill.startingRank) + gear + temporary, 1, skill.permissionMaxRank);
    }
    public int TemporaryBonus(Unit unit, string skillId) => unit.temporaryRankModifiers.GetValueOrDefault(skillId) + content.temporaryModifiers.Where(d => d.skillId == skillId && unit.statuses.Any(status => status.id == d.id && status.duration > 0)).Sum(d => d.amount);
    public SkillRank Row(Skill skill, int rank) => skill.ranks.LastOrDefault(r => r.rank <= rank) ?? new()
    {
        rank = skill.startingRank,
        power = skill.power,
        cost = skill.cost,
        range = skill.range
    };
    public void Refresh(Unit u, bool inBattle = false)
    {
        u.nextLevelEffect = u.level >= 20 ? "Character level cap reached" : $"+{content.progression.levels[u.level].hpGain} HP, +{content.progression.levels[u.level].manaGain} mana, +{content.progression.levels[u.level].powerGain} power, +{content.progression.levels[u.level].armorGain} armor";
        int floor = content.progression.levels[u.level - 1].totalXp;
        u.xpProgressPercent = u.level >= 20 ? 100 : Math.Clamp(100.0 * (u.xp - floor) / (content.progression.levels[u.level].totalXp - floor), 0, 100);
        u.xpToNext = u.level >= 20 ? 0 : Math.Max(0, content.progression.levels[u.level].totalXp - u.xp);
        u.skillProgress = u.skills.Select(id =>
        {
            var k = content.skills.FirstOrDefault(k => k.id == id) ?? new Skill { id = id };
            int rank = u.ranks.GetValueOrDefault(id, k.startingRank),
                practice = u.skillPractice.GetValueOrDefault(id);
            var next = k.ranks.FirstOrDefault(r => r.rank > rank && r.rank <= k.permissionMaxRank);
            var trainedRow = Row(k, rank);
            int effective = EffectiveRank(u, k);
            var row = Row(k, effective);
            return new SkillProgress
            {
                skillId = id,
                targetKind = k.targetKind,
                trainedRank = rank,
                temporaryBonusRank = TemporaryBonus(u, id),
                permissionMaxRank = k.permissionMaxRank,
                rankCapacity = k.rankCapacity,
                effectiveRank = effective,
                gearBonusRank = content.items.FirstOrDefault(i => i.id == u.equipment)?.rankModifiers.GetValueOrDefault(id) ?? 0,
                effectRank = row.rank,
                cost = row.cost,
                resource = "Mana",
                effect = $"Power {row.power}; multiplier {row.powerMultiplier:0.##}; range {row.range}" + (rank > row.rank ? $". Trained rank {rank}; current effect rank {row.rank}." : ""),
                canUse = u.hp > 0 && u.mp >= row.cost && (!inBattle || (!u.acted && !u.ended)),
                disabledReason = u.hp <= 0 ? "Crawler is down" : u.mp < row.cost ? "Not enough mana" : inBattle && (u.acted || u.ended) ? "Action unavailable" : "",
                practiceProgressPercent = next == null ? 100 : Math.Clamp(100.0 * (practice - trainedRow.practiceRequired) / (next.practiceRequired - trainedRow.practiceRequired), 0, 100),
                practice = practice,
                practiceToNext = next == null ? 0 : Math.Max(0, next.practiceRequired - practice),
                maxRank = Math.Min(k.permissionMaxRank, k.ranks.LastOrDefault()?.rank ?? rank),
                manaOptions = row.manaOptions,
                nextEffect = next == null ? "Early mastery complete" : $"Rank {next.rank}: power {next.power}, multiplier {next.powerMultiplier:0.##}, mana {next.cost}, range {next.range}"
            };
        }).ToArray();
    }
    public void Practice(Unit u, Skill k)
    {
        u.skillPractice[k.id] = Math.Min(1000000, u.skillPractice.GetValueOrDefault(k.id) + content.progression.practicePerUse);
        foreach (var row in k.ranks.Where(r => r.rank <= k.permissionMaxRank && r.practiceRequired <= u.skillPractice[k.id]))
            u.ranks[k.id] = Math.Max(u.ranks.GetValueOrDefault(k.id, k.startingRank), row.rank);
        Refresh(u);
    }
    public void Reward(Unit u, int xp)
    {
        u.xp = Math.Min(100000, u.xp + xp);
        while (u.level < 20 && u.xp >= content.progression.levels[u.level].totalXp)
        {
            var row = content.progression.levels[u.level++];
            int oldMaxHp = u.maxHp, oldMaxMp = u.maxMp;
            u.maxHp = Math.Min(1000, u.maxHp + row.hpGain);
            u.maxMp = Math.Min(1000, u.maxMp + row.manaGain);
            u.power = Math.Min(1000, u.power + row.powerGain);
            u.armor = Math.Min(1000, u.armor + row.armorGain);
            u.hp = Math.Min(u.maxHp, u.hp + u.maxHp - oldMaxHp);
            u.mp = Math.Min(u.maxMp, u.mp + u.maxMp - oldMaxMp);
        }
        Refresh(u);
    }
    public bool ValidMastery(Unit u)
    {
        if ((u.xp < content.progression.levels[u.level - 1].totalXp || (u.level < 20 && u.xp >= content.progression.levels[u.level].totalXp)))
            return false;
        if (u.skillPractice == null || u.skillPractice.Count != u.skills.Length || u.skillPractice.Any(p => !u.skills.Contains(p.Key) || p.Value < 0 || p.Value > 1000000))
            return false;
        foreach (var id in u.skills)
        {
            var k = content.skills.FirstOrDefault(k => k.id == id);
            if (k == null)
                continue;
            int rank = u.ranks[id];
            if (rank < k.startingRank || rank > k.rankCapacity)
                return false;
            if (u.skillPractice[id] < Row(k, rank).practiceRequired)
                return false;
            if (rank <= k.ranks.Last().rank && rank != k.ranks.Last(r => r.rank <= k.permissionMaxRank && r.practiceRequired <= u.skillPractice[id]).rank)
                return false;
        }
        return true;
    }
    public void Migrate(Unit u)
    {
        // Rebase the old 30-XP level interval without changing earned level or stats.
        int oldFloor = (u.level - 1) * 30;
        int partial = Math.Clamp(u.xp - oldFloor, 0, 29);
        int newFloor = content.progression.levels[u.level - 1].totalXp;
        u.xp = u.level == 20 ? Math.Max(newFloor, u.xp) : newFloor + (int)((long)partial * (content.progression.levels[u.level].totalXp - newFloor) / 30);
        u.skillPractice = new();
        foreach (var id in u.skills)
        {
            var k = content.skills.FirstOrDefault(k => k.id == id);
            if (k == null)
            {
                u.skillPractice[id] = 0;
                continue;
            }
            u.ranks[id] = Math.Max(k.startingRank, u.ranks[id]);
            u.skillPractice[id] = Row(k, u.ranks[id]).practiceRequired;
        }
        Refresh(u);
    }
}
