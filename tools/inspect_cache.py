import json, pathlib, collections, sys

cache = pathlib.Path('.cache/repoe/mods.json')
if not cache.exists():
    print('ERROR: .cache/repoe/mods.json not found. Run Update from RePoE.bat first.')
    sys.exit(1)

data = json.loads(cache.read_text(encoding='utf-8'))
item_mods = {k: v for k, v in data.items()
             if v.get('domain') == 'item'
             and v.get('generation_type') in ('prefix', 'suffix')}
print(f"Total domain=item prefix/suffix mods: {len(item_mods)}")
print()

# ── 1. Every unique positive-tag COMBINATION (sorted, excluding default) ────
print("=== ALL UNIQUE POSITIVE TAG COMBINATIONS (domain=item prefix/suffix) ===")
tag_patterns = collections.Counter()
for v in item_mods.values():
    tags = frozenset(
        s['tag'] for s in v.get('spawn_weights', [])
        if s.get('weight', 0) > 0 and s['tag'] != 'default'
    )
    tag_patterns[tags] += 1

print(f"Total unique patterns: {len(tag_patterns)}")
print()
print("-- Patterns used by 10+ mods (common slot definitions) --")
for pattern, cnt in sorted(tag_patterns.items(), key=lambda x: -x[1]):
    if cnt < 10:
        continue
    print(f"  {cnt:4}x  {sorted(pattern)}")

print()
print("-- Patterns used by 1-9 mods (rare / specific) first 40 --")
rare = [(p, c) for p, c in tag_patterns.items() if c < 10]
for pattern, cnt in sorted(rare, key=lambda x: -x[1])[:40]:
    print(f"  {cnt:4}x  {sorted(pattern)}")

print()

# ── 2. Specific groups with known tier explosion ─────────────────────────────
CHECK_GROUPS = [
    'IncreasedEvasionRating', 'IncreasedArmour', 'IncreasedEnergyShield',
    'IncreasedLife', 'IncreasedMana', 'FireResistance',
    'IncreasedPhysicalDamage', 'Strength', 'Dexterity', 'Intelligence',
]
print("=== PER-GROUP TIER ANALYSIS ===")
for grp in CHECK_GROUPS:
    mods = [v for v in item_mods.values()
            if (v.get('groups') or [''])[0] == grp
            and v.get('generation_type') == 'prefix']
    if not mods:
        mods = [v for v in item_mods.values()
                if (v.get('groups') or [''])[0] == grp
                and v.get('generation_type') == 'suffix']
    if not mods:
        continue
    # What unique tag combos does this group use?
    combos = collections.Counter()
    for m in mods:
        tags = frozenset(
            s['tag'] for s in m.get('spawn_weights', [])
            if s.get('weight', 0) > 0 and s['tag'] != 'default'
        )
        combos[tags] += 1
    print(f"  {grp}: {len(mods)} tiers, {len(combos)} unique tag combos")
    for tag_combo, cnt in sorted(combos.items(), key=lambda x: -x[1]):
        print(f"    {cnt}x {sorted(tag_combo)}")

print()

# ── 3. Show one full mod entry for each major slot-defining tag pattern ───────
print("=== ONE FULL EXAMPLE PER MAJOR TAG PATTERN ===")
seen_patterns = set()
for k, v in item_mods.items():
    tags = frozenset(
        s['tag'] for s in v.get('spawn_weights', [])
        if s.get('weight', 0) > 0 and s['tag'] != 'default'
    )
    if tags in seen_patterns:
        continue
    if tag_patterns[tags] < 5:  # only show patterns used by 5+ mods
        continue
    seen_patterns.add(tags)
    stats = v.get('stats', [{}])
    grp = (v.get('groups') or ['?'])[0]
    print(f"  Pattern: {sorted(tags)}")
    print(f"    mod_id={k}  group={grp}  gen={v.get('generation_type')}")
    print(f"    stat: {stats[0].get('id','?')}  min={stats[0].get('min')}  max={stats[0].get('max')}")
    all_sw = [(s['tag'], s['weight']) for s in v.get('spawn_weights', [])]
    print(f"    all spawn_weights: {all_sw}")
    print()

print("=== DONE ===")
