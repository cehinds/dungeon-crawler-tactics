"""Author bounded runtime rank profiles; all numeric curves are tactical adaptations.

JSON remains the shipped source of truth. This optional authoring helper rebuilds
profiles and their registered tag variants from readable effect families and
explicit signature overrides. It does not run in the game or calculate forecasts.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'UnityPackage/Runtime/Data'
TIERS = (5, 10, 15, 16, 20)
BOOK_SAMPLE = 'https://cdn.penguin.co.uk/dam-assets/books/9780241816219/9780241816219-sample.pdf'


def build():
    combat = json.loads((DATA / 'combat-content.json').read_text())
    game = json.loads((DATA / 'game-content.json').read_text())
    abilities = {a['id']: a for a in combat['abilities']}
    tags = {t['id']: t for t in combat['tags']}
    rules = {t['tag']: t for t in game['tagRules']}
    reactions = {r['id']: r for r in combat['reactions']}
    guard = reactions['reaction.guarded_blocks']

    def tag_rule(tag, label, **rule):
        tags[tag] = dict(id=tag, label=label)
        rules[tag] = dict(tag=tag, **rule)

    tag_rule('status.burning', 'Burning', durationRounds=2, turnDamage=2)
    families = {}
    for base, label in [('status.guarded', 'Guarded'), ('status.rushing', 'Rushing'),
                        ('surface.trap_shock', 'Shock trap')]:
        families[base] = []
        for index, rank in enumerate(TIERS):
            tag = f'{base}_rank{rank}'
            families[base].append(tag)
            rule = copy.deepcopy(rules[base])
            rule.pop('tag')
            if base == 'status.guarded':
                rule['durationRounds'] = 2 + index // 2
                reaction = copy.deepcopy(guard)
                reaction['id'] = f'reaction.guarded_rank{rank}_blocks'
                reaction['damageReduction'] = (8, 10, 12, 15, 18)[index]
                reaction['target']['all'] = [tag]
                reaction['consumeTags'] = [tag]
                reactions[reaction['id']] = reaction
            elif base == 'status.rushing':
                rule['moveBonus'] = (3, 4, 5, 6, 7)[index]
                rule['durationRounds'] = 2 + index // 2
            elif base == 'surface.trap_shock':
                rule['entryDamage'] = (7, 9, 12, 15, 18)[index]
            tag_rule(tag, f'{label} · tier {rank}', **rule)

    profiles = []
    for ability in combat['abilities']:
        effects = ability['effects']
        operations = {e['op'] for e in effects}
        profile = dict(
            abilityId=ability['id'], practiceMultiplierPercent=100,
            damagePerRank=1 if 'Damage' in operations else 0,
            healPerRank=1 if 'Heal' in operations else 0,
            costReductionPerRank=1 if ability['cost'] else 0,
            damageBonusCap=80, healBonusCap=60, costReductionCap=min(2, ability['cost']),
            rangePerRank=0, rangeBonusCap=6, pushPerRank=0, pushBonusCap=3,
            summonHpPerRank=1 if 'DuplicatePet' in operations else 0,
            summonHpBonusCap=60, summonMovePerRank=0, summonMoveBonusCap=3,
            summonRoundsPerRank=0, summonRoundsBonusCap=5,
            description='Tactical adaptation: committed uses train this ability. Milestones refine its existing effects; consumable casts do not train or receive rank bonuses.',
            canonNotes='No complete book rank table verified for this game ability. Its costs, board ranges, thresholds and bonuses are game tuning.',
            sourceUrls=[], milestones=[])
        for index, rank in enumerate(TIERS):
            milestone = dict(rank=rank, description=f'Tier {rank}: tactical refinement.')
            if 'Damage' in operations:
                milestone['damageBonus'] = (1, 2, 3, 4, 6)[index]
            if 'Heal' in operations:
                milestone['healBonus'] = (1, 2, 3, 4, 6)[index]
            if 'Teleport' in operations or ability['range'] > 1:
                milestone['rangeBonus'] = 1
            if 'Push' in operations and rank in (10, 15, 20):
                milestone['pushBonus'] = 1
            if 'DuplicatePet' in operations:
                milestone['summonHpBonus'] = (2, 3, 4, 5, 7)[index]
                milestone['summonRoundsBonus'] = 1
                if rank in (10, 15, 20):
                    milestone['summonMoveBonus'] = 1
            replacements = [dict(fromTag=e['tag'], toTag=families[e['tag']][index])
                            for e in effects if e['op'] == 'AddTag' and e.get('tag') in families]
            if replacements:
                milestone['tagReplacements'] = replacements
            # Do not manufacture a milestone without an actual effect.
            if len(milestone) > 2:
                profile['milestones'].append(milestone)
        profiles.append(profile)
    by_id = {p['abilityId']: p for p in profiles}

    def evidence(ability, note, *urls):
        by_id[ability]['canonNotes'] = note
        by_id[ability]['sourceUrls'] = list(urls)

    def milestone(ability, rank):
        rows = by_id[ability]['milestones']
        row = next((r for r in rows if r['rank'] == rank), None)
        if row is None:
            row = dict(rank=rank, description=f'Tier {rank}: tactical refinement.')
            rows.append(row)
            rows.sort(key=lambda r: r['rank'])
        return row

    strike = by_id['ability.carl_powerful_strike']
    strike['damagePerRank'] = 2
    evidence(strike['abilityId'], 'Secondary book reference: Powerful Strike amplifies unarmed damage. This action converts that identity to bounded damage and push; neither these numbers nor its full rank table are canon.',
             'https://dungeon-crawler-carl.fandom.com/wiki/Powerful_Strike_Skill')
    missile = 'ability.donut_magic_missile'
    milestone(missile, 10)['addTags'] = ['status.burning']
    milestone(missile, 10)['description'] = 'Igniting missile: applies Burning for two rounds. Deterministic tactical adaptation of the reported rank-10 ignition effect.'
    evidence(missile, 'Secondary chapter-cited anchors: rank 5 permits variable Mana expenditure; rank 10 can ignite targets. The game uses fixed casting cost and guaranteed short Burning at rank 10, not the book chance or selectable cast power. Other ranks are extrapolated.',
             'https://www.dccdatabase.com/wiki/magic_missile/')
    evidence('ability.donut_puddle_jumper', 'Book summaries describe group transport, cast delay and cooldown, with rank-5 and rank-15 changes. This board adaptation teleports one actor immediately; its growing tile range is extrapolated, not a canon distance or timer.',
             'https://dungeon-crawler-carl.fandom.com/wiki/Puddle_Jumper_Spell')
    abilities['ability.donut_heal_critter']['requiredTargetTag'] = 'trait.pet'
    evidence('ability.donut_heal_critter', 'Book target identity: heals a nearby pet or familiar, not a crawler. The game requires the Pet tag. Healing numbers and rank progression are extrapolated.',
             'https://www.dccdatabase.com/wiki/heal_critter/')
    evidence('ability.donut_clockwork_triplicate', 'Book identity: duplicates a pet or minion. The game keeps two temporary copies; rank-scaled HP, movement and lifetime are tactical extrapolations, not a verified book rank table.',
             'https://www.dccfansite.com/entry/clockwork-triplicate/')
    evidence('ability.katia_shapeshift', 'Katia changes physical shape, subject to mass, without copying powers. The game uses preset forms; trained ranks improve protection granted by guarded forms. Preset stat bonuses and rank tiers are adaptations.',
             'https://www.novelpantheon.com/novels/dungeon-crawler-carl/characters/katia')
    for form in game.get('forms', []):
        if form.get('rosterId') == 'crawler.katia':
            form['practiceAbilityId'] = 'ability.katia_shapeshift'
    evidence('ability.katia_rush', 'Rush is reported for Katia; no full rank-effect table verified. Movement and duration tiers are tactical adaptations.',
             'https://www.dccdatabase.com/wiki/book_3_chapter_summaries/')
    for ability in ('ability.carl_tripwire', 'ability.carl_freeze_trap', 'ability.carl_dynamite'):
        evidence(ability, 'Explosives and trapmaking fit Carl’s class identity. This named battlefield action and all numeric rank effects are game-authored.', BOOK_SAMPLE)
    for ability in by_id:
        if ability.startswith('ability.mongo_'):
            evidence(ability, 'Mongo is a pet companion. These controllable attack/leap practice tracks are game adaptations, not a documented crawler skill-rank system for him.')
    # New Look and cleansing remain cleanses; higher tiers remove more debuffs.
    for ability in ('ability.katia_new_look', 'ability.cleanse'):
        milestone(ability, 5)['removeTags'] = ['status.burning']
        milestone(ability, 5)['description'] = 'Cleansing refinement: also extinguishes Burning. Tactical adaptation.'
        if ability == 'ability.katia_new_look':
            milestone(ability, 10)['removeTags'] = ['status.wet']
            milestone(ability, 10)['description'] = 'Cleansing refinement: also removes Wet. Tactical adaptation.'
        by_id[ability]['description'] += ' Cleanse strength changes at milestones; intervening ranks may have the same combat effect.'

    practice = game['development']['practice']
    practice['abilityProfiles'] = profiles
    # Retain early save-compatible thresholds; high ranks remain long-term goals.
    # A slower post-10 curve is intentional, not a claim about novel XP formulas.
    game['development']['description'] = game['development']['description'].replace(
        'rank bonuses affect direct ability damage/healing and mana costs, never reaction damage or items.',
        'rank profiles improve direct damage/healing, Mana cost, range, push, ranked tags and temporary summons. Reaction damage and consumable casts do not receive direct rank bonuses. All numeric curves are tactical adaptations.')
    combat['tags'] = list(tags.values())
    combat['reactions'] = list(reactions.values())
    game['tagRules'] = list(rules.values())
    for filename, data in [('combat-content.json', combat), ('game-content.json', game)]:
        (DATA / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(f'Authored {len(profiles)} rank profiles and {len(families)} ranked tag families.')


if __name__ == '__main__':
    build()
