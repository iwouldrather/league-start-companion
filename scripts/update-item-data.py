"""Snapshot PoB weapon base types without executing Lua."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pob_import import POB
HANDS={'One Handed Sword':1,'One Handed Axe':1,'One Handed Mace':1,'Dagger':1,'Claw':1,'Sceptre':1,'Wand':1,'Two Handed Sword':2,'Two Handed Axe':2,'Two Handed Mace':2,'Bow':2,'Staff':2,'Fishing Rod':2}
bases={}
for path in (POB/'Data/Bases').glob('*.lua'):
    for name,kind in re.findall(r'itemBases\["([^"]+)"\]\s*=\s*\{\s*type\s*=\s*"([^"]+)"',path.read_text(encoding='utf8')):
        if kind in HANDS:bases[name]={'weaponType':kind,'hands':HANDS[kind]}
if not bases:raise SystemExit('No PoB weapon bases found.')
(ROOT/'source/weapon-bases.json').write_text(json.dumps(bases,indent=2,sort_keys=True)+'\n',encoding='utf8')
print(f'Saved {len(bases)} weapon bases.')
