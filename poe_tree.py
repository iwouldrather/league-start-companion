"""Asset-backed passive/ascendancy views, using the user's local PoB installation."""
import base64
from functools import lru_cache
import html
import io
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

VIEW_VERSION=8


def selected(spec):
    return set(re.findall(r'\d+',spec.get('nodes',''))) if spec else set()


def point_counts(spec,tree):
    normal=asc=missing=0
    for nid in selected(spec):
        node=tree['nodes'].get(nid)
        if node is None:
            normal+=1;missing+=1
        elif 'classStartIndex' not in node and not node.get('isAscendancyStart'):
            if node.get('ascendancyName'):
                asc+=not node.get('isMultipleChoiceOption',False)
            else:
                normal+=1
    return normal,asc,missing


def estimate_level(spec,tree,bandit='None'):
    """PoB's EstimatePlayerProgress heuristic; not an exact character-level claim."""
    points,asc,missing=point_counts(spec,tree)
    acts=[(1,0),(12,2),(22,4),(32,6),(40,7),(44,9),(50,12),(54,15),(60,18),(64,20),(67,23)]
    extra=1 if bandit in ('None','Kill All','Kill all') else 0
    for i,(minimum,quests) in enumerate(acts):
        level=min(max(points+1-quests-(extra if i>=2 else 0),minimum),100)
        if i==10 or level<=acts[i+1][0]:
            break
    return {'level':level,'points':points,'ascendancyPoints':asc,'approximate':True,'missingNodes':missing,
            'explanation':f'Estimated from {points} passive points using PoB’s campaign/quest-point assumptions. Ascendancy points are excluded; quest rewards and bonus points can change the actual level.'}


@lru_cache(maxsize=8)
def sprite_data(version):
    from pob_import import POB,literal_lua
    path=POB/'TreeData'/version/'sprites.lua'
    return literal_lua(path.read_text(encoding='utf8')).get('sprites',{}) if path.exists() else {}


@lru_cache(maxsize=20)
def sheet(path):
    from PIL import Image
    return Image.open(path).convert('RGBA')


@lru_cache(maxsize=8000)
def sprite(version,kind,key):
    from pob_import import POB
    try:
        entry=sprite_data(version).get(kind,{})
        box=entry.get('coords',{}).get(key)
        if not box:return None
        path=POB/'TreeData'/version/Path(urlsplit(entry['filename']).path).name
        image=sheet(str(path)).crop((box['x'],box['y'],box['x']+box['w'],box['y']+box['h']))
        buffer=io.BytesIO();image.save(buffer,format='WEBP',quality=86,method=4)
        return 'data:image/webp;base64,'+base64.b64encode(buffer.getvalue()).decode()
    except (OSError,ValueError,ImportError,KeyError):
        return None


@lru_cache(maxsize=100)
def local_art(name):
    from pob_import import POB
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.png',name):return None
    path=POB/'TreeData'/name
    if not path.exists():return None
    try:
        image=sheet(str(path)).copy();image.thumbnail((320,320) if name.startswith('Classes') else (128,128))
        buffer=io.BytesIO();image.save(buffer,format='WEBP',quality=85,method=4)
        return 'data:image/webp;base64,'+base64.b64encode(buffer.getvalue()).decode()
    except (ImportError,OSError):
        return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()


@lru_cache(maxsize=128)
def class_portrait(name):
    """Resolve a logged class from known metadata, never from an input filename."""
    from pob_import import tree_data
    if not isinstance(name,str) or not name or len(name)>80:return None
    try:classes=tree_data('3_29').get('classes',[])
    except (OSError,ValueError):return None
    for entry in classes:
        base=entry.get('name','')
        if name==base:return local_art('center'+base.lower()+'.png')
        for ascendancy in entry.get('ascendancies',[]):
            if name in (ascendancy.get('name'),ascendancy.get('id')):
                return (local_art('Classes'+ascendancy['name']+'.png') or
                        local_art('Classes'+ascendancy.get('id',ascendancy['name'])+'.png') or
                        local_art('center'+base.lower()+'.png'))
    return None


def positions(tree):
    result={};angles={16:[0,30,45,60,90,120,135,150,180,210,225,240,270,300,315,330],40:sorted(set(range(0,360,10))|{45,135,225,315})}
    constants=tree['constants']
    for nid,node in tree['nodes'].items():
        group=tree['groups'].get(str(node.get('group')),{});orbit=node.get('orbit',0);idx=node.get('orbitIndex',0)
        if 'x' not in group or orbit>=len(constants['orbitRadii']):continue
        count=constants['skillsPerOrbit'][orbit]
        angle=math.radians((angles[count][idx%count] if count in angles else 360*idx/count))
        radius=constants['orbitRadii'][orbit]
        result[nid]=(group['x']+math.sin(angle)*radius,group['y']-math.cos(angle)*radius,angle,radius)
    return result


def path_between(a,b,nodes,coords):
    x,y,angle,radius=coords[a];ox,oy,other_angle,_=coords[b]
    if nodes[a].get('group')==nodes[b].get('group') and nodes[a].get('orbit')==nodes[b].get('orbit') and radius:
        sweep=1 if (other_angle-angle)%(2*math.pi)<math.pi else 0
        return f'M{x:.1f} {y:.1f} A{radius} {radius} 0 0 {sweep} {ox:.1f} {oy:.1f}'
    return f'M{x:.1f} {y:.1f} L{ox:.1f} {oy:.1f}'


def svg_view(tree,version,now,before,ascendancy='',diff=False,mini=False,class_name=''):
    nodes=tree['nodes'];coords=positions(tree)
    eligible={n for n in coords if (nodes[n].get('ascendancyName')==ascendancy if mini else not nodes[n].get('ascendancyName'))}
    class_index=next((i for i,c in enumerate(tree.get('classes',[])) if c.get('name')==class_name),None)
    starts={n for n in eligible if 'classStartIndex' in nodes[n] and (nodes[n]['classStartIndex']==class_index if class_index is not None else n in now)} if not mini else set()
    fresh=(now-before)&eligible;removed=(before-now)&eligible
    # Changes must retain the whole route back through the earlier allocation.
    focus=eligible if mini else (((now|before) if diff else now)&eligible)
    if not focus:focus={n for n in eligible if 'classStartIndex' in nodes[n]}
    if not focus:focus=set(list(eligible)[:1])
    focus=focus|starts
    points=[coords[n] for n in focus] or [(0,0,0,0)]
    pad=170 if mini else 380
    left=min(p[0] for p in points)-pad;top=min(p[1] for p in points)-pad
    width=max(max(p[0] for p in points)-left+pad,500);height=max(max(p[1] for p in points)-top+pad,500)
    scale=max(width/(900 if mini else 1200),height/(360 if mini else 1200))
    visible={n for n in eligible if left<=coords[n][0]<=left+width and top<=coords[n][1]<=top+height}
    defs=[];uses={};details={};paths=[];icons=[];labels=[];seen=set()
    def art(uri,x,y,size):
        if not uri:return ''
        if uri not in uses:
            key=('ascAsset' if mini else 'treeAsset')+str(len(uses));uses[uri]=key
            defs.append(f'<image id="{key}" href="{uri}" width="1" height="1" preserveAspectRatio="none"/>')
        return f'<use href="#{uses[uri]}" transform="translate({x-size/2:.1f} {y-size/2:.1f}) scale({size:.1f})"/>'
    for nid in sorted(visible,key=lambda n:int(n)):
        node=nodes[nid];x,y,_,_=coords[nid];active=nid in now;prior=nid in before
        state='new' if nid in fresh else 'removed' if nid in removed else 'kept' if active else 'unallocated'
        color='#86d5ff' if diff and state=='new' else '#ef8c80' if diff and state=='removed' else '#d7b679' if active else '#6a6254'
        stats=node.get('stats',[]);details[nid]={'name':node.get('name',nid),'stats':stats,'state':state,'ascendancy':bool(node.get('ascendancyName'))}
        for other in set(map(str,node.get('out',[])+node.get('in',[]))):
            edge=tuple(sorted((nid,other)))
            if other not in visible or edge in seen or node.get('isMastery') or nodes[other].get('isMastery'):continue
            seen.add(edge)
            kept=active and other in now;gone=prior and other in before and not kept
            edge_new=kept and (nid in fresh or other in fresh)
            stroke='#86d5ff' if diff and edge_new else '#ef8c80' if diff and gone else '#b99b66' if kept else '#38382f'
            dash=f' stroke-dasharray="{6*scale:.1f} {5*scale:.1f}"' if diff and gone else ''
            paths.append(f'<path d="{path_between(nid,other,nodes,coords)}" fill="none" stroke="{stroke}" stroke-width="{(2.4 if kept or gone else 1)*scale:.1f}"{dash}/>')
        notable=node.get('isNotable') or node.get('isKeystone');size=(36 if node.get('isAscendancyStart') else 26 if notable else 17)*scale
        kind='keystone' if node.get('isKeystone') else 'notable' if notable else 'normal'
        icon_kind='masteryActiveSelected' if active and node.get('isMastery') else 'masteryInactive' if node.get('isMastery') else kind+('Active' if active else 'Inactive')
        icon=sprite(version,icon_kind,node.get('icon',''))
        frame_key=('KeystoneFrame' if node.get('isKeystone') else 'NotableFrame' if notable else 'PSSkillFrame')+('Allocated' if active else 'Unallocated')
        if kind=='normal':frame_key='PSSkillFrameActive' if active else 'PSSkillFrame'
        if node.get('isJewelSocket'):frame_key='JewelFrameAllocated' if active else 'JewelFrameUnallocated'
        frame=sprite(version,'frame',frame_key)
        if node.get('ascendancyName'):
            frame=local_art('AscendancyFrame'+('Large' if notable else 'Small')+('Allocated' if active else 'Normal')+'.png') or frame
        if node.get('isAscendancyStart'):
            icon=local_art('Classes'+ascendancy+'.png') or icon
            frame=local_art('AscendancyMiddle.png') or frame
        title=html.escape(node.get('name',nid)+'\n'+'\n'.join(stats))
        glyph=art(icon,x,y,size) if icon else f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size*.35:.1f}" fill="#423d2c"/>'
        glyph+=art(frame,x,y,size*1.38)
        ring=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size*.77:.1f}" fill="none" stroke="{color}" stroke-width="{2.8*scale:.1f}"/>' if (diff and state in ('new','removed')) else ''
        opacity='1' if active or state=='removed' else '.65'
        icons.append(f'<g data-node="{nid}" role="button" tabindex="0" aria-label="{html.escape(node.get("name",nid),quote=True)}" opacity="{opacity}"><title>{title}</title>{glyph}{ring}</g>')
        if nid in starts:
            # Draw above the allocation so the origin stays recognisable in both modes.
            base=class_name or node.get('name','Class').title()
            portrait=local_art('center'+base.lower()+'.png')
            radius=45*scale
            marker=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius+6*scale:.1f}" fill="#101723" stroke="#f4d38f" stroke-width="{3*scale:.1f}"/>'
            marker+=art(portrait,x,y,radius*1.8) if portrait else f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius*.6:.1f}" fill="#e5bd79"/>'
            label=html.escape(base+' start')
            labels.append(f'<g data-tree-start="true" data-node="{nid}" role="button" tabindex="0" aria-label="{label}"><title>{label} · begin allocating here</title>{marker}</g>')
        if notable and active and not mini:
            labels.append(f'<text x="{x+20*scale:.1f}" y="{y-15*scale:.1f}" fill="{color}" font-size="{13*scale:.1f}" font-family="Georgia,serif" paint-order="stroke" stroke="#0c1015" stroke-width="{3*scale:.1f}">{html.escape(node.get("name",nid))}</text>')
    background=local_art('Classes'+ascendancy+'.png') if mini and ascendancy else None
    bg=f'<image href="{background}" x="{left:.1f}" y="{top:.1f}" width="{width:.1f}" height="{height:.1f}" opacity=".17" preserveAspectRatio="xMidYMid slice"/>' if background else ''
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{900 if mini else 1200}" height="{360 if mini else 1200}" viewBox="{left:.1f} {top:.1f} {width:.1f} {height:.1f}"><defs>{"".join(defs)}</defs><rect x="{left:.1f}" y="{top:.1f}" width="{width:.1f}" height="{height:.1f}" fill="#10151a"/>{bg}{"".join(paths+icons+labels)}</svg>'
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode(),details,{'added':len(fresh),'removed':len(removed),'kept':len((now&before)&eligible)}


def enrich(data):
    from pob_import import tree_data
    if data.get('treeViewVersion')==VIEW_VERSION:return data
    before_spec=None
    asc=data.get('build',{}).get('ascendClassName','')
    for setup in data['sets']:
        spec=setup.get('treeSpec')
        if not spec:
            before_spec=None;continue
        try:tree=tree_data(spec['version'])
        except (OSError,ValueError,IndexError):before_spec=None;continue
        now=selected(spec);compatible=before_spec and before_spec['version']==spec['version']
        before=selected(before_spec) if compatible else set()
        full,details,delta=svg_view(tree,spec['version'],now,before,asc,class_name=data.get('build',{}).get('className',''))
        changes,delta_details,delta=svg_view(tree,spec['version'],now,before,asc,True,class_name=data.get('build',{}).get('className',''))
        mini,asc_details,asc_delta=svg_view(tree,spec['version'],now,before,asc,True,True) if asc else ('',{}, {})
        combined=details|delta_details|asc_details
        for nid,eid in re.findall(r'\{(\d+),(\d+)\}',spec.get('masteries','')):
            if nid in combined:
                effect=next((e for e in tree['nodes'].get(nid,{}).get('masteryEffects',[]) if str(e.get('effect'))==eid),None)
                if effect:combined[nid]['stats']=effect.get('stats',[])
        setup.update(treeImage=full,treeDiffImage=changes,ascendancyImage=mini,nodeDetails=combined,treeDelta=delta,ascendancyDelta=asc_delta,
                     passivePoints=point_counts(spec,tree)[0],ascendancyPoints=point_counts(spec,tree)[1],
                     comparisonNote='Compared with the previous milestone' if compatible else 'First available allocation' if not before_spec else 'Tree versions differ; comparison starts fresh')
        before_spec=spec
    portrait=local_art('Classes'+asc+'.png') if asc else None
    portrait=portrait or local_art('center'+data.get('build',{}).get('className','Scion').lower()+'.png')
    data['uiAssets']={'portrait':portrait,'texture':local_art('Background1.png'),'points':local_art('PSPointsFrame.png')}
    data['treeViewVersion']=VIEW_VERSION
    return data
