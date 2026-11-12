"""Local PoE1 PoB import, review and guide generation. Never executes imported code."""
import base64
from datetime import datetime, timezone
from functools import lru_cache
import html
import json
import math
import os
from pathlib import Path
import re
import threading
import sys
import uuid
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET
import zlib
from gem_acquisition import resolve as acquisition_for, snapshot as acquisition_snapshot, data_version as acquisition_version

ROOT = Path(__file__).resolve().parent
INSTALLED_POB=Path(os.environ.get('APPDATA',''))/'Path of Building Community'
POB = Path(os.environ.get('POB_DATA_DIR',str(INSTALLED_POB if (INSTALLED_POB/'TreeData').exists() else ROOT/'pob-data')))
MAX_CODE = 2_000_000
MAX_XML = 12_000_000


class ImportProblem(ValueError):
    def __init__(self,message,row=None,field=None):
        super().__init__(message);self.row=row;self.field=field


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_):
        raise ImportProblem('The build link redirected. Paste its export code instead.')


def fetch_code(link):
    url = urlsplit(link)
    if url.scheme != 'https' or url.netloc != 'pobb.in' or url.query or url.fragment:
        raise ImportProblem('Use an https://pobb.in/… share link or paste the PoB export code.')
    match = re.fullmatch(r'/([A-Za-z0-9_-]{1,100})/?', url.path)
    if not match:
        raise ImportProblem('This is not a pobb.in share link.')
    try:
        if os.name=='nt' and getattr(sys,'frozen',False):
            from windows_http import fetch_shared_code
            return fetch_shared_code(match[1],MAX_CODE).decode('utf8').strip()
        request = Request('https://pobb.in/pob/' + match[1], headers={'User-Agent': 'Local-PoB-Guide/1.0'})
        with build_opener(NoRedirect()).open(request, timeout=12) as response:
            data = response.read(MAX_CODE + 1)
        if len(data) > MAX_CODE:
            raise ImportProblem('This build is too large to import.')
        return data.decode('utf8').strip()
    except ImportProblem:
        raise
    except Exception as error:
        raise ImportProblem('Could not download this build. Check the link or paste its export code.') from error


def decode_build(value):
    if not isinstance(value, str) or len(value) > MAX_XML:
        raise ImportProblem('Paste a PoB code or XML export smaller than 12 MB.')
    value = value.strip().lstrip('\ufeff')
    if value.startswith(('https://', 'http://')):
        value = fetch_code(value)
    if value.startswith('<'):
        raw = value.encode('utf8')
    else:
        compact = re.sub(r'\s+', '', value)
        if not compact or len(compact) > MAX_CODE or not re.fullmatch(r'[A-Za-z0-9_+/=-]+', compact):
            raise ImportProblem('This is not a valid PoB export code.')
        try:
            compressed = base64.b64decode(compact.replace('-', '+').replace('_', '/') + '=' * (-len(compact) % 4), validate=True)
            decoder = zlib.decompressobj()
            raw = decoder.decompress(compressed, MAX_XML + 1)
            if len(raw) > MAX_XML or decoder.unconsumed_tail or not decoder.eof:
                raise ImportProblem('The decoded build is too large or incomplete.')
        except (ValueError, zlib.error) as error:
            raise ImportProblem('The export code could not be decoded. Copy the full code from PoB.') from error
    if len(raw) > MAX_XML or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ImportProblem('Unsupported XML export.')
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise ImportProblem('The build XML is incomplete or invalid.') from error
    if root.tag != 'PathOfBuilding':
        raise ImportProblem('This importer supports Path of Exile 1 PoB builds only.')
    return root


def literal_lua(text):
    """Read generated PoB data tables as literals, without running Lua."""
    token = re.compile(r'\s+|--[^\n]*|"(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|[{}\[\]=,;]')
    tokens = [m[0] for m in token.finditer(text) if not m[0].isspace() and not m[0].startswith('--')]
    position = 1 if tokens and tokens[0] == 'return' else 0

    def value():
        nonlocal position
        t = tokens[position]
        position += 1
        if t == '{':
            array, obj = [], {}
            while tokens[position] != '}':
                if tokens[position] == '[':
                    position += 1
                    key = value()
                    if tokens[position:position+2] != [']', '=']:
                        raise ImportProblem('Unsupported local PoB data table.')
                    position += 2
                    obj[str(key)] = value()
                elif position+1 < len(tokens) and tokens[position+1] == '=':
                    key = tokens[position]
                    position += 2
                    obj[key] = value()
                else:
                    array.append(value())
                if tokens[position] in (',', ';'):
                    position += 1
            position += 1
            if obj:
                obj.update({str(i+1): x for i, x in enumerate(array)})
                return obj
            return array
        if t.startswith('"'):
            return json.loads(t)
        if t in ('true', 'false', 'nil'):
            return {'true': True, 'false': False, 'nil': None}[t]
        try:
            return float(t) if any(c in t for c in '.eE') else int(t)
        except ValueError as error:
            raise ImportProblem('Unsupported local PoB data value.') from error
    return value()


@lru_cache(maxsize=1)
def effect_catalog():
    effects = {}
    for path in (POB / 'Data/Skills').glob('*.lua'):
        for sid, block in re.findall(r'skills\["([^"]+)"\] = \{(.*?)(?=\nskills\[|\Z)', path.read_text(encoding='utf8'), re.S):
            levels = {int(n): int(l) for n, l in re.findall(r'\[(\d+)\] = \{[^\n]*?levelRequirement = (\d+)', block)}
            color = re.search(r'\bcolor = (\d+)', block)
            name = re.search(r'\bname = "([^"]+)"',block)
            effects[sid] = {'minLevel': levels.get(1), 'levels': levels, 'color': int(color[1]) if color else 0,
                            'isSupport': bool(re.search(r'\bsupport = true', block)), 'effectName':name[1] if name else sid}
    return effects


@lru_cache(maxsize=1)
def gem_catalog():
    catalog = json.loads((ROOT / 'source/gem-meta.json').read_text(encoding='utf8'))
    bundled=ROOT/'source/gem-registry.json'
    if bundled.exists():
        catalog.update(json.loads(bundled.read_text(encoding='utf8')))
    effects = effect_catalog()
    gems_path = POB / 'Data/Gems.lua'
    if gems_path.exists():
        for gem_id, gem in literal_lua(gems_path.read_text(encoding='utf8')).items():
            name, effect, variant = gem.get('name'),gem.get('grantedEffectId'),gem.get('variantId','')
            tags = gem.get('tags',{})
            if name and effect:
                color=effects.get(effect,{}).get('color')
                if not color:
                    requirements=[gem.get('reqStr',0),gem.get('reqDex',0),gem.get('reqInt',0)]
                    color=requirements.index(max(requirements))+1 if max(requirements)>0 else 4
                catalog[name] = dict(effects.get(effect, {}), skillId=effect, gemId=gem_id, gameId=gem.get('gameId'),variantId=variant,
                                     itemGranted=False, transfigured=bool(re.search(r'Alt[A-Z]',variant)) and not name.endswith(' of Trarthus'),
                                     trarthus=name.endswith(' of Trarthus'),
                                     vaal=bool(gem.get('vaalGem') or tags.get('vaal')), awakened=bool(tags.get('awakened')),
                                     exceptional=bool(tags.get('exceptional')),isSupport=bool(tags.get('support')),color=color)
    return catalog


def normalize_gem(gem, group_source=''):
    """Resolve PoB names and identifiers; retain unsupported gems instead of hiding them."""
    gem=dict(gem)
    catalog=gem_catalog()
    name=gem.get('nameSpec','')
    canonical=next((n for n,m in catalog.items() if gem.get('variantId') and m.get('variantId')==gem['variantId']),None)
    if not canonical:
        canonical=next((n for n in catalog if n.casefold()==name.casefold()),None)
    if not canonical:
        canonical=next((n for n in catalog if n.casefold()==name.removesuffix(' Support').casefold()),None)
    if not canonical:
        for field in ('variantId','skillId','gemId'):
            value=gem.get(field)
            canonical=next((n for n,m in catalog.items() if value and m.get(field)==value),None)
            if canonical:
                break
    if canonical:
        name=canonical
        meta=dict(catalog[name])
    else:
        effect=effect_catalog().get(gem.get('skillId'),{})
        name=name or effect.get('effectName') or gem.get('skillId') or gem.get('gemId') or 'Unrecognized skill'
        meta=dict(effect,skillId=gem.get('skillId'),itemGranted=bool(effect and not gem.get('gemId')))
    effect=effect_catalog().get(gem.get('skillId'),{})
    if not gem.get('gemId') and effect and gem.get('skillId')!=meta.get('skillId'):
        meta=dict(effect,skillId=gem.get('skillId'),itemGranted=True)
    if group_source and re.search(r'\bItem\b',group_source,re.I) and not gem.get('gemId'):
        meta['itemGranted']=True
    meta.setdefault('minLevel',None)
    meta.setdefault('color',0)
    meta.setdefault('isSupport',False)
    meta.setdefault('itemGranted',False)
    try:
        level=int(gem.get('level','1'))
        required=meta.get('levels',{}).get(level,meta.get('levels',{}).get(str(level)))
    except ValueError:
        required=None
    meta.pop('levels',None)
    gem.update(meta,nameSpec=name,requiredLevel=required)
    for key,value in [('enabled','true'),('level','1'),('quality','0')]:
        gem.setdefault(key,value)
    return gem,meta


def level_from_title(title):
    if re.search(r'\bact\s*\d|\b\d+\s*(?:points?|links?)\b',title,re.I):
        return None
    match = re.search(r'(?:\bl(?:evel|vl)?\.?\s*|^\s*)(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?', title, re.I)
    return int(match[1]) if match and 1 <= int(match[1]) <= 100 else None


def normalized(title):
    return re.sub(r'[^a-z0-9]', '', title.lower())


def parse_build(root):
    build = root.find('Build')
    if build is None:
        raise ImportProblem('This export has no Build record.')
    if build.get('targetVersion', '3_0').startswith('4_'):
        raise ImportProblem('PoE 2 builds are not supported yet.')
    skills, trees, items = root.find('Skills'), root.find('Tree'), root.find('Items')
    skill_sets = list(skills.findall('SkillSet')) if skills is not None else []
    if not skill_sets and skills is not None and skills.findall('Skill'):
        skill_sets = [skills]
    if not skill_sets:
        raise ImportProblem('This PoB has no skill sets. Add a skill setup in PoB before importing.')
    all_items = {x.get('id'): (x.text or '').strip() for x in items.findall('Item')} if items is not None else {}
    item_sets = list(items.findall('ItemSet')) if items is not None else []
    if not item_sets and items is not None and items.findall('Slot'):
        item_sets = [items]
    specs = list(trees.findall('Spec')) if trees is not None else []
    build_info=dict(build.attrib)
    if build_info.get('ascendClassName') in ('None','none','0'):
        build_info['ascendClassName']=''
    draft = {'build': build_info, 'notes': (root.findtext('Notes') or '')[:200_000],
             'skills': [], 'trees': [], 'items': [], 'warnings': []}
    for index, skill_set in enumerate(skill_sets):
        groups = []
        for group_index,group in enumerate(skill_set.findall('Skill'),1):
            gems = [normalize_gem(g.attrib,group.get('source',''))[0] for g in group.findall('Gem') if any(g.get(k) for k in ('nameSpec','gemId','skillId','variantId'))]
            if gems:
                groups.append({'label': group.get('label') or group.get('slot') or gems[0]['nameSpec'],
                               'enabled': group.get('enabled', 'true'), 'slot': group.get('slot', ''), 'source':group.get('source',''),
                               'main':group.get('includeInFullDPS')=='true' or str(group_index)==build.get('mainSocketGroup'), 'gems': gems})
        draft['skills'].append({'id': str(index), 'title': skill_set.get('title') or 'Main setup', 'groups': groups})
    for index, spec in enumerate(specs):
        draft['trees'].append({'id': str(index), 'title': spec.get('title') or 'Main tree',
                               'version': spec.get('treeVersion', 'unknown'), 'nodes': spec.get('nodes', ''),
                               'level':spec.get('level') or spec.get('characterLevel'),
                               'masteries': spec.get('masteryEffects', ''), 'url': spec.findtext('URL') or '',
                               'sockets': [dict(x.attrib) for x in spec.findall('Sockets/Socket')]})
    for index, item_set in enumerate(item_sets):
        slots = [{'slot': x.get('name', ''), 'item': all_items[x.get('itemId')]}
                 for x in item_set.findall('Slot') if x.get('itemId') in all_items and 'Swap' not in x.get('name', '')]
        draft['items'].append({'id': str(index), 'title': item_set.get('title') or 'Main equipment', 'slots': slots})
    draft['allItems'] = all_items
    if not specs:
        draft['warnings'].append('No passive tree was included. The guide will show that it is missing.')
    if len(skill_sets) == 1:
        draft['warnings'].append('One skill set found. This generates a reference setup, not an invented leveling progression.')
    if len(skill_sets) > 20:
        raise ImportProblem('This build has more than 20 skill sets. Export a smaller guide first.')
    return draft


def review_draft(draft):
    def match(title, choices):
        exact = next((x['id'] for x in choices if normalized(x['title']) == normalized(title)), None)
        return exact if exact is not None else (choices[0]['id'] if len(choices) == 1 else '')
    from poe_tree import estimate_level
    tree_summaries=[]
    for spec in draft['trees']:
        estimate=None
        try:estimate=estimate_level(spec,tree_data(spec['version']),draft['build'].get('bandit','None'))
        except (ImportProblem,OSError,ValueError,IndexError):pass
        explicit=spec.get('level')
        explicit=int(explicit) if str(explicit).isdigit() and 1<=int(explicit)<=100 else None
        tree_summaries.append({'id':spec['id'],'title':spec['title'],'estimate':estimate,'labelLevel':level_from_title(spec['title']) or explicit})
    summaries = lambda choices: [{'id': x['id'], 'title': x['title']} for x in choices]
    rows = []
    for skill in draft['skills']:
        level = level_from_title(skill['title'])
        tree_id=match(skill['title'],draft['trees'])
        tree_summary=next((t for t in tree_summaries if t['id']==tree_id),None)
        source='Label' if level else ''
        if not level and tree_summary and tree_summary['labelLevel']:
            level=tree_summary['labelLevel'];source='Tree label'
        if not level and len(draft['skills'])==1:
            level=int(draft['build'].get('level',1));source='PoB character level'
        if not level and tree_summary and tree_summary['estimate']:
            level=tree_summary['estimate']['level'];source='Estimated from tree'
        rows.append({'label': skill['title'], 'startLevel': level,'levelSource':source or 'Please enter a level',
                     'levelExplanation':tree_summary['estimate']['explanation'] if tree_summary and tree_summary['estimate'] else '',
                     'skillSetId': skill['id'], 'treeId': tree_id,
                     'itemSetId': match(skill['title'], draft['items']),
                     'included': not (len(draft['skills']) > 1 and level == 100),
                     'gemCount': sum(len(g['gems']) for g in skill['groups'])})
    return {'className': draft['build'].get('className', 'Unknown'), 'ascendancy': draft['build'].get('ascendClassName', ''),
            'warnings': draft['warnings'], 'skills': summaries(draft['skills']), 'trees': tree_summaries,
            'items': summaries(draft['items']), 'milestones': rows}


@lru_cache(maxsize=4)
def tree_data(version):
    if not re.fullmatch(r'\d+_\d+(?:_ruthless)?', version):
        raise ImportProblem('Unsupported tree version.')
    path = POB / 'TreeData' / version / 'tree.lua'
    if not path.exists():
        raise ImportProblem('Install the matching tree data in Path of Building to render this version.')
    return literal_lua(path.read_text(encoding='utf8'))


def tree_view(spec):
    warnings, notables, ascendancy, masteries = [], [], [], []
    if not spec:
        text = 'No passive tree supplied'
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900"><rect width="900" height="900" fill="#101723"/><text x="450" y="450" text-anchor="middle" fill="#b0bfd1" font-size="24">{text}</text></svg>'
        return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode(), notables, ascendancy, masteries, [text]
    selected = set(re.findall(r'\d+', spec['nodes']))
    try:
        tree = tree_data(spec['version'])
    except (ImportProblem, ValueError, IndexError, OSError):
        result = tree_view(None)
        return (*result[:4], ['Tree version ' + spec['version'] + ' is unavailable; allocations are retained but not drawn.'])
    nodes, groups, constants = tree['nodes'], tree['groups'], tree['constants']
    positions = {}
    sixteen = [0,30,45,60,90,120,135,150,180,210,225,240,270,300,315,330]
    forty = sorted(set(range(0,360,10)) | {45,135,225,315})
    for nid, node in nodes.items():
        group = groups.get(str(node.get('group')), {})
        orbit, index = node.get('orbit', 0), node.get('orbitIndex', 0)
        if 'x' not in group or orbit >= len(constants['orbitRadii']):
            continue
        count = constants['skillsPerOrbit'][orbit]
        degrees = (sixteen if count == 16 else forty if count == 40 else [360*i/count for i in range(count)])[index % count]
        angle, radius = math.radians(degrees), constants['orbitRadii'][orbit]
        positions[nid] = (group['x'] + math.sin(angle)*radius, group['y'] - math.cos(angle)*radius)
        if nid in selected and (node.get('isNotable') or node.get('isKeystone')):
            record = {'id': nid, 'name': node.get('name', nid), 'stats': node.get('stats', [])}
            (ascendancy if node.get('ascendancyName') else notables).append(record)
    allocated = selected & positions.keys()
    missing = selected - positions.keys()
    if missing:
        warnings.append(f'{len(missing)} allocated nodes are outside the base tree (for example cluster jewels) and are not drawn.')
    bounds = [positions[n] for n in allocated if not nodes[n].get('ascendancyName')] or [positions[n] for n in allocated] or [(0,0)]
    xs, ys = zip(*bounds)
    left, top = min(xs)-350, min(ys)-350
    width, height = max(max(xs)-min(xs)+700,900), max(max(ys)-min(ys)+700,900)
    scale = max(width,height)/1200
    visible = {n for n,(x,y) in positions.items() if left <= x <= left+width and top <= y <= top+height and not nodes[n].get('ascendancyName')}
    lines, circles, labels, edges = [], [], [], set()
    for nid in visible:
        node, (x,y) = nodes[nid], positions[nid]
        for other in node.get('out', []):
            other = str(other)
            edge = tuple(sorted((nid,other)))
            if other in visible and edge not in edges:
                edges.add(edge)
                ox, oy = positions[other]
                active = nid in allocated and other in allocated
                lines.append(f'<path d="M{x:.1f} {y:.1f}L{ox:.1f} {oy:.1f}" stroke="{"#e6c68e" if active else "#29384b"}" stroke-width="{(3 if active else 1)*scale:.1f}"/>')
        active = nid in allocated
        radius = ((8 if node.get('isKeystone') else 6 if node.get('isNotable') else 4) if active else 2)*scale
        name = html.escape(node.get('name', nid))
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{"#e6c68e" if active else "#26384c"}" stroke="{"#fff1cf" if active else "#476078"}" stroke-width="{scale:.1f}"><title>{name}</title></circle>')
        if active and (node.get('isNotable') or node.get('isKeystone')):
            labels.append(f'<text x="{x+9*scale:.1f}" y="{y-7*scale:.1f}" fill="#fff1cf" font-size="{13*scale:.1f}" paint-order="stroke" stroke="#101723" stroke-width="{3*scale:.1f}">{name}</text>')
    for nid, eid in re.findall(r'\{(\d+),(\d+)\}', spec['masteries']):
        node = nodes.get(nid, {})
        effect = next((e for e in node.get('masteryEffects', []) if str(e.get('effect')) == eid), None)
        if effect:
            masteries.append({'name': node.get('name', 'Mastery'), 'stats': effect.get('stats', [])})
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="{left:.1f} {top:.1f} {width:.1f} {height:.1f}"><rect x="{left:.1f}" y="{top:.1f}" width="{width:.1f}" height="{height:.1f}" fill="#101723"/>{"".join(lines+circles+labels)}</svg>'
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode(), notables, ascendancy, masteries, warnings


@lru_cache(maxsize=1)
def weapon_bases():
    path=ROOT/'source/weapon-bases.json'
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else {}


def weapon_metadata(base):
    bases=weapon_bases()
    if base in bases:return dict(bases[base])
    # Magic items include prefixes/suffixes in the name. Match a complete base,
    # longest first, so short base names cannot override more specific ones.
    for name in sorted(bases,key=len,reverse=True):
        if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',base):return dict(bases[name])
    return {}


def refresh_item_metadata(data):
    for setup in data.get('sets',[]):
        for item in setup.get('items',[]):
            item.update(weapon_metadata(item.get('base') or item.get('name','')))
    return data


def item_record(slot, raw):
    lines = raw.splitlines()
    rarity = (lines[0].split(':',1)[-1].strip().upper() if lines else 'NORMAL')
    if rarity not in ('NORMAL','MAGIC','RARE','UNIQUE','RELIC'):
        rarity = 'NORMAL'
    name = lines[1] if len(lines)>1 else 'Imported item'
    base = lines[2] if rarity in ('RARE','UNIQUE','RELIC') and len(lines)>2 else name
    selected = {int(v) for v in re.findall(r'^Selected (?:Alt Variant Two|Alt Variant|Variant): (\d+)', raw, re.M)} or {1}
    clean = []
    for line in lines:
        if re.match(r'(?:Variant|Selected .*Variant|Unique ID|Prefix|Suffix|Crafted|Source|League|Has Alt Variant|Has Alt Variant Two):', line):
            continue
        variant = re.search(r'\{variant:([^}]+)\}', line)
        if variant and not selected.intersection(map(int, variant[1].split(','))):
            continue
        roll = re.search(r'\{range:([\d.]+)\}', line)
        if roll:
            def resolved(match):
                low, high = float(match[1]), float(match[2])
                value = low+(high-low)*float(roll[1])
                return str(round(value, 2)).rstrip('0').rstrip('.') if '.' in match[1]+match[2] else str(math.floor(value+.5))
            line = re.sub(r'\((-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)\)', resolved, line)
        clean.append(re.sub(r'\{[^}]*\}', '', line))
    requirement = re.search(r'^LevelReq: (\d+)', raw, re.M)
    return {'slot': slot, 'item': raw, 'rarity': rarity, 'name': name, 'base': base, 'clean': '\n'.join(clean),
            'requirement': int(requirement[1]) if requirement else None, 'highlights': clean[-4:], **weapon_metadata(base)}


def make_guide(draft, rows, name):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
        raise ImportProblem('Include between 1 and 20 milestones.')
    if not isinstance(name, str) or not name.strip() or len(name)>120:
        raise ImportProblem('Give the guide a name (up to 120 characters).')
    skills = {x['id']: x for x in draft['skills']}
    trees = {x['id']: x for x in draft['trees']}
    equipment = {x['id']: x for x in draft['items']}
    data = {'imported': True, 'name': name.strip(), 'build': draft['build'], 'notes': draft['notes'],
            'sets': [], 'meta': {}, 'acquisition': {}, 'acquisitionOptions':{},'acquisitionNotes':{},'warnings': list(draft['warnings'])}
    previous = 0
    for index, row in enumerate(rows):
        if not isinstance(row,dict):raise ImportProblem('A milestone could not be read. Open the preview again.')
        label=str(row.get('label','Step '+str(index+1)))
        if type(row.get('startLevel')) is not int or not 1<=row['startLevel']<=100:
            raise ImportProblem(f'Enter a starting level for “{label}” between 1 and 100. Tree suggestions are estimates you can edit.',index,'level')
        if row['startLevel']<=previous:
            prior=str(rows[index-1].get('label','previous step'))
            raise ImportProblem(f'“{label}” starts at level {row["startLevel"]}, but “{prior}” above starts at {previous}. Give this step a higher level, or untick it if it is an alternative setup.',index,'level')
        previous = row['startLevel']
        label = str(row.get('label', '')).strip()
        if not label or len(label)>160:
            raise ImportProblem('Each milestone needs a label up to 160 characters.')
        skill = skills.get(str(row.get('skillSetId')))
        spec = trees.get(str(row.get('treeId')))
        gear = equipment.get(str(row.get('itemSetId')))
        if trees and row.get('treeId') == '':
            raise ImportProblem(f'Choose the passive tree for “{label}”, or select “No passive tree”.',index,'tree')
        if not skill or (row.get('treeId') not in ('',None,'none') and not spec) or (row.get('itemSetId') and not gear):
            raise ImportProblem('A selected skill, tree or item set was not found in this import.')
        image, notables, ascendancy, masteries, warnings = tree_view(spec)
        groups = []
        for group in skill['groups']:
            gems = []
            for gem in group['gems']:
                gem,meta = normalize_gem(gem,group.get('source',''))
                n = gem['nameSpec']
                gems.append(gem)
                data['meta'][n] = meta
                acquisition,options,note = acquisition_for(n,meta,draft['build'].get('className',''))
                data['acquisition'][n] = acquisition
                data['acquisitionOptions'][n]=options
                data['acquisitionNotes'][n]=note
            groups.append(dict(group, gems=gems))
        records = [item_record(x['slot'], x['item']) for x in gear['slots']] if gear else []
        if spec:
            for socket in spec['sockets']:
                raw = draft['allItems'].get(socket.get('itemId'))
                if raw and socket.get('nodeId') in spec['nodes'].split(','):
                    records.append(item_record('Tree jewel '+socket.get('nodeId',''), raw))
        slot_order = ['Weapon 1','Weapon 2','Helmet','Body Armour','Gloves','Boots','Amulet','Ring 1','Ring 2','Belt']
        records.sort(key=lambda x:slot_order.index(x['slot']) if x['slot'] in slot_order else 50)
        caution = ['Imported set matches: skills '+skill['title']+'; tree '+(spec['title'] if spec else 'not supplied')+'; equipment '+(gear['title'] if gear else 'not supplied')+'.']
        caution += warnings
        caution += ['Tree drawing uses native base-tree nodes. Cluster expansions, Timeless transformations and damage calculations are not reconstructed.']
        nav = re.sub(r'^\s*(?:L(?:vl|evel)?\.?\s*)?\d+(?:\s*[-–]\s*\d+)?\s*', '', label, flags=re.I).strip(' ()-') or label
        data['sets'].append({'title':label, 'key': 'import-'+str(index), 'short':str(previous), 'startLevel':previous,
                            'nav':nav, 'navSub':'', 'heading':label, 'description':'Imported PoB setup',
                            'groups':groups, 'items':records, 'treeImage':image, 'notables':notables, 'ascendancy':ascendancy,
                            'masteryDetails':masteries, 'treeVersion':spec['version'].replace('_','.') if spec else 'unknown',
                            'cautionTitle':'Imported guide · review notes', 'cautions':caution,
                            'quickNote':warnings[0] if warnings else 'Follow the saved links and tree. Review unverified acquisition routes before buying.'})
        data['sets'][-1]['treeSpec']=spec
    data['names'] = sorted(data['meta'])
    data['acquisitionVersion']=acquisition_version()
    unverified = sum(1 for r in data['acquisition'].values() if r[3]=='unknown')
    if unverified:
        data['warnings'].append(f'{unverified} gem acquisition routes need review; no vendor or quest has been guessed.')
    from poe_tree import enrich
    return enrich(data)


def refresh_acquisition(data):
    """Upgrade saved imports in memory; preserve milestones, trees, gear and purchases."""
    refresh_item_metadata(data)
    if data.get('acquisitionVersion')==acquisition_version():
        return data
    data['meta'],data['acquisition'],data['acquisitionOptions'],data['acquisitionNotes']={},{},{},{}
    for setup in data['sets']:
        for group in setup['groups']:
            normalized_gems=[]
            for gem in group['gems']:
                gem,meta=normalize_gem(gem,group.get('source',''))
                name=gem['nameSpec'];normalized_gems.append(gem);data['meta'][name]=meta
                route,options,note=acquisition_for(name,meta,data['build'].get('className',''))
                data['acquisition'][name]=route;data['acquisitionOptions'][name]=options;data['acquisitionNotes'][name]=note
            group['gems']=normalized_gems
    data['names']=sorted(data['meta'])
    data['warnings']=[w for w in data.get('warnings',[]) if not ('acquisition routes need review' in w or 'vendor routes are not verified for this class' in w)]
    unknown=sum(r[3]=='unknown' for r in data['acquisition'].values())
    if unknown:
        data['warnings'].append(f'{unknown} acquisition records are unavailable for this data version; check their source.')
    data['acquisitionVersion']=acquisition_version()
    return data


class BuildLibrary:
    def __init__(self, directory):
        self.directory = Path(directory)/'builds'
        self.lock = threading.Lock()

    def path(self, build_id, draft=False):
        if not isinstance(build_id,str) or not re.fullmatch(r'[0-9a-f]{32}', build_id):
            raise ImportProblem('Invalid build identifier.')
        return self.directory / ('draft-'+build_id+'.json' if draft else build_id+'.json')

    def write(self, path, data):
        self.directory.mkdir(exist_ok=True)
        temporary = path.with_suffix('.tmp')
        with self.lock:
            temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
            os.replace(temporary,path)

    def preview(self, value):
        draft = parse_build(decode_build(value))
        draft_id = uuid.uuid4().hex
        self.write(self.path(draft_id,True),draft)
        return dict(review_draft(draft),draftId=draft_id)

    def create(self, draft_id, rows, name):
        try:
            draft = json.loads(self.path(draft_id,True).read_text(encoding='utf8'))
        except FileNotFoundError as error:
            raise ImportProblem('Import preview not found. Paste the build again.') from error
        data = make_guide(draft,rows,name)
        build_id = uuid.uuid4().hex
        data.update(id=build_id,sourceDraftId=draft_id,createdAt=datetime.now(timezone.utc).isoformat())
        self.write(self.path(build_id),data)
        return {'id':build_id,'warnings':data['warnings'],'name':data['name']}

    def load(self, build_id):
        try:
            data=refresh_acquisition(json.loads(self.path(build_id).read_text(encoding='utf8')))
            if not all('treeSpec' in s for s in data['sets']):
                candidates=[self.path(data['sourceDraftId'],True)] if data.get('sourceDraftId') else list(self.directory.glob('draft-*.json'))
                for path in candidates:
                    draft=json.loads(path.read_text(encoding='utf8'))
                    if draft.get('build',{}).get('className')!=data['build'].get('className') or draft.get('notes','')!=data.get('notes',''):continue
                    for setup in data['sets']:
                        if 'treeSpec' in setup:continue
                        label=setup['title']
                        caution=(setup.get('cautions') or [''])[0]
                        matched=re.search(r'; tree (.*?); equipment ',caution)
                        if matched:label=matched[1]
                        spec=next((t for t in draft['trees'] if normalized(t['title'])==normalized(label)),None)
                        if spec:setup['treeSpec']=spec
                    if all('treeSpec' in s for s in data['sets']):break
            from poe_tree import enrich
            return enrich(data)
        except FileNotFoundError as error:
            raise ImportProblem('Saved guide not found.') from error
        except (OSError,ValueError) as error:
            raise ImportProblem('Saved guide could not be read. Import its PoB again to create a fresh guide.') from error

    def list(self, removed=False):
        result = []
        directory=self.directory/'removed' if removed else self.directory
        for path in directory.glob('*.json'):
            if path.name.startswith('draft-'):
                continue
            try:
                data = json.loads(path.read_text(encoding='utf8'))
                result.append({k:data[k] for k in ('id','name','createdAt')})
            except (ValueError,KeyError,OSError):
                continue
        return sorted(result,key=lambda x:x['createdAt'],reverse=True)

    def rename(self, build_id, name):
        path=self.path(build_id)
        if not isinstance(name,str) or not name.strip() or len(name)>120:
            raise ImportProblem('Enter a build name between 1 and 120 characters.')
        with self.lock:
            try:data=json.loads(path.read_text(encoding='utf8'))
            except FileNotFoundError as error:raise ImportProblem('Saved guide not found. Refresh the library.') from error
            data['name']=name.strip()
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
            os.replace(temporary,path)
        return {'id':build_id,'name':data['name']}

    def remove(self, build_id):
        path=self.path(build_id)
        with self.lock:
            trash=self.directory/'removed'
            trash.mkdir(parents=True,exist_ok=True)
            if not path.exists():raise ImportProblem('Saved guide not found. Refresh the library.')
            os.replace(path,trash/path.name)
        return {'id':build_id,'removed':True}

    def restore(self, build_id):
        path=self.path(build_id)
        with self.lock:
            removed=self.directory/'removed'/path.name
            if path.exists():raise ImportProblem('This build is already in your library.')
            if not removed.exists():raise ImportProblem('This removed build could not be found.')
            os.replace(removed,path)
        return {'id':build_id,'restored':True}

    def render(self, template, build_id):
        data = self.load(build_id)
        payload = json.dumps(data,ensure_ascii=False).replace('</',r'<\/')
        return re.sub(r'(<script id="guideData" type="application/json">).*?(</script>)',
                      lambda m:m[1]+payload+m[2],template,count=1,flags=re.S)
