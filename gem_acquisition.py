"""Class-aware, offline acquisition routes for the complete PoB gem catalog."""
from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
CLASSES=('Marauder','Witch','Scion','Ranger','Duelist','Shadow','Templar')
QUESTS=['The Twilight Strand','Enemy at the Gate','Mercy Mission','Breaking Some Eggs','The Caged Brute',"The Siren's Cadence",'Intruders in Black','Sharp and Cruel','The Root of the Problem','Lost in Love',"Victario's Secrets",'Sever the Right Hand','A Fixture of Fate','Breaking the Seal','An Indomitable Spirit','The Eternal Nightmare','Return to Oriath','Fallen from Grace']


@lru_cache(maxsize=1)
def snapshot():
    path=ROOT/'source/gem-acquisition.json'
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else {'gems':{}}


@lru_cache(maxsize=1)
def special_routes():
    data=json.loads((ROOT/'source/acquisition.json').read_text(encoding='utf8'))
    return {n:r for n,r in data.items() if r[3] in ('item','drop','transfigured')}

@lru_cache(maxsize=1)
def cost_snapshot():
    path=ROOT/'source/gem-costs.json'
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}

def gem_costs():return cost_snapshot().get('gems',{})

def data_version():return snapshot().get('checkedAt','unversioned')+'|prices:'+cost_snapshot().get('checkedAt','unverified')+'|2'


def order(route):
    return (route['act'],QUESTS.index(route['quest']) if route['quest'] in QUESTS else 99,0 if route['kind']=='starter' else 1 if route['kind']=='vendor' else 2)


def resolve(name,meta,class_name):
    record=snapshot()['gems'].get(name,{})
    source=record.get('source') or 'https://poedb.tw/us/'+quote((name+(' Support' if meta.get('isSupport') else '')).replace(' ','_'))
    known=special_routes().get(name)
    if name=='Earthbreaker':
        return [0,'Legacy gem / trade','Removed from quest rewards and vendors in 3.25','legacy',source],[], 'Earthbreaker Support is a legacy gem; do not plan to buy it from Siosa.'
    if meta.get('itemGranted'):
        return [0,'Granted by equipment','Equip the item that grants this skill','item',source],[],''
    if meta.get('trarthus') or name.endswith(' of Trarthus'):
        return [0,'Mercenary rewards / trade','Trarthan gem; not a Divine Font result','trarthus',source],[],''
    if meta.get('transfigured'):
        return [0,'Labyrinth / trade','Divine Font: transfigured gem','transfigured',source],[],''
    if meta.get('vaal'):
        return [0,'Corruption / Vaal areas / trade','Vaal gem; not a normal campaign purchase','vaal',source],[],''
    if known:
        return list(known[:4])+[known[4] if len(known)>4 else source],[],''
    if meta.get('awakened'):
        return [0,'Boss drops / trade','Awakened support; no campaign vendor','awakened',source],[],''
    if meta.get('exceptional'):
        return [0,'Special drops / trade','Exceptional gem; no campaign vendor','drop',source],[],''
    routes=record.get('routes',[])
    options=[dict(r) for r in routes if class_name in r['classes']]
    vendors=[r for r in routes if r['kind'] in ('vendor','reward','starter')]
    if vendors:
        earliest=min(vendors,key=order)
        if earliest['act']<=3:
            options.append({'act':3,'vendor':'Siosa','quest':'A Fixture of Fate','kind':'vendor','classes':list(CLASSES),
                            'note':'Also complete the original gem-unlock quest: '+earliest['quest']+'.',
                            'cost':gem_costs().get(name)})
        options.append({'act':6,'vendor':'Lilly Roth','quest':'Fallen from Grace','kind':'vendor','classes':list(CLASSES)})
    for option in options:
        if option['vendor']=='Siosa':option['cost']=gem_costs().get(name)
    # Prefer a purchase (or starting chest), while retaining free quest rewards as alternatives.
    purchases=[r for r in options if r['kind'] in ('vendor','starter')]
    choices=sorted(purchases or options,key=order)
    if choices:
        first=choices[0]
        vendor=first['vendor']+(' · free reward' if first['kind']=='reward' else '')
        primary=[first['act'],vendor,first['quest'],first['kind'],first.get('source',source)]
        return primary,sorted(options,key=order),first.get('note','')
    if record.get('status')=='no-quest-route':
        return [0,'No campaign vendor listed','Special acquisition / trade; see source','special',source],[], 'No quest purchase or reward is listed in the current source. Check recipes, drop restrictions and league availability.'
    return [0,'Acquisition data unavailable','Check the gem source before buying','unknown',source],[], 'This gem was not present in the acquisition snapshot or its source could not be read.'
