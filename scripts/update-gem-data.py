"""Refresh the offline all-class gem registry and PoEDB acquisition snapshot."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pob_import as pob

CLASSES = ['Marauder','Witch','Scion','Ranger','Duelist','Shadow','Templar']
QUEST_VENDOR={
 'Enemy at the Gate':(1,'Nessa'),'Mercy Mission':(1,'Nessa'),'Breaking Some Eggs':(1,'Nessa'),
 'The Caged Brute':(1,'Nessa'),"The Siren's Cadence":(1,'Nessa'),
 'Intruders in Black':(2,'Yeena'),'Sharp and Cruel':(2,'Yeena'),'The Root of the Problem':(2,'Yeena'),
 'Lost in Love':(3,'Clarissa'),"Victario's Secrets":(3,'Clarissa'),'Sever the Right Hand':(3,'Clarissa'),
 'A Fixture of Fate':(3,'Clarissa'),'Breaking the Seal':(4,'Petarus and Vanja'),'The Eternal Nightmare':(4,'Petarus and Vanja')}


def plain(text):
    return html.unescape(re.sub(r'<[^>]*>','',text)).strip()


def extract_routes(page):
    routes=[]
    for table in re.findall(r'<table\b.*?</table>',page,re.S|re.I):
        headers=[plain(x) for x in re.findall(r'<th\b[^>]*>(.*?)</th>',table,re.S|re.I)]
        if headers != ['Act','Quest','NPC','Character']:
            continue
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S|re.I):
            cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S|re.I)
            if len(cells)!=4 or not plain(cells[0]).isdigit():
                continue
            classes=[c for c in CLASSES if re.search(r'\b'+c+r'\b',plain(cells[3]))]
            if 'All Classes' in plain(cells[3]):
                classes=list(CLASSES)
            if not classes:
                continue
            kind='vendor' if 'Quest Vendor' in cells[2] else 'reward' if 'Quest Reward' in cells[2] else 'starter' if 'title="Box"' in cells[2] else None
            if not kind:
                continue
            vendor=plain(cells[2]) or ('Supply chest' if kind=='starter' else 'Quest reward')
            routes.append({'act':int(plain(cells[0])),'quest':plain(cells[1]),'vendor':vendor,'classes':classes,'kind':kind})
    return routes


def matrix_routes(page,catalog):
    section=page.split('<div id="QuestVendorRewards"',1)[1].split('</table>',1)[0]
    result={}
    aliases={n.casefold():n for n in catalog}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',section,re.S):
        cells=re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.S)
        if len(cells)!=8:
            continue
        quest=plain(cells[0])
        if quest not in QUEST_VENDOR:
            continue
        act,vendor=QUEST_VENDOR[quest]
        for cls,cell in zip(CLASSES,cells[1:]):
            for attrs,text in re.findall(r'<a\b([^>]*)>(.*?)</a>',cell,re.S):
                if 'gem_' not in attrs:
                    continue
                label=plain(text)
                name=aliases.get(label.casefold()) or aliases.get(label.removesuffix(' Support').casefold())
                if name:
                    result.setdefault(name,[]).append({'act':act,'quest':quest,'vendor':vendor,'classes':[cls],'kind':'vendor','source':'https://poedb.tw/us/Quest'})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/gem-quests')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    args.cache.mkdir(parents=True,exist_ok=True)
    catalog=pob.gem_catalog()
    ordinary={n:m for n,m in catalog.items() if not any(m.get(k) for k in ('itemGranted','transfigured','trarthus','vaal','awakened','exceptional'))}
    checked=datetime.now(timezone.utc).isoformat()
    matrix_cache=args.cache/'quest-matrix.html'
    if not matrix_cache.exists() or args.refresh:
        request=Request('https://poedb.tw/us/Quest',headers={'User-Agent':'LocalPoBGuide/1.0'})
        matrix_cache.write_text(urlopen(request,timeout=20).read().decode('utf8'),encoding='utf8')
    matrix=matrix_routes(matrix_cache.read_text(encoding='utf8'),catalog)

    def get(entry):
        name,meta=entry
        cache=args.cache/(hashlib.sha256(name.encode()).hexdigest()+'.json')
        slug=(name+(' Support' if meta.get('isSupport') and not name.endswith(' Support') else '')).replace("'",'').replace('’','').replace(' ','_')
        source='https://poedb.tw/us/'+quote(slug)
        if cache.exists() and not args.refresh:
            cached=json.loads(cache.read_text(encoding='utf8'))
            if cached['source']==source:
                return name,cached
        result=None
        for attempt in range(3):
            try:
                request=Request(source,headers={'User-Agent':'LocalPoBGuide/1.0 (offline gem acquisition snapshot)'})
                with urlopen(request,timeout=20) as response:
                    raw=response.read(4_000_001)
                if len(raw)>4_000_000:
                    raise ValueError('Response too large')
                page=raw.decode('utf8',errors='replace')
                routes=extract_routes(page)
                result={'source':source,'checkedAt':checked,'routes':routes,'status':'verified' if routes else 'no-quest-route'}
                break
            except Exception as error:
                result={'source':source,'checkedAt':checked,'routes':[],'status':'fetch-failed','error':str(error)}
                time.sleep(.5*(attempt+1))
        if result['status']!='fetch-failed':
            cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')
        return name,result

    records={}
    with ThreadPoolExecutor(max_workers=max(1,min(args.workers,4))) as pool:
        futures=[pool.submit(get,item) for item in ordinary.items()]
        for i,future in enumerate(as_completed(futures),1):
            name,record=future.result();records[name]=record
            if i%25==0 or i==len(futures):
                print(f'Checked {i}/{len(futures)} gem pages; {sum(r["status"]=="fetch-failed" for r in records.values())} fetch failures',flush=True)
    for name,record in records.items():
        eligible=bool(record['routes']) or name in ('Arctic Armour','Phase Run')
        if eligible and record['status']!='fetch-failed' and not any(r['kind']=='vendor' for r in record['routes']) and name in matrix:
            record['routes'].extend(matrix[name])
            record['status']='verified'
            record['matrixSource']='https://poedb.tw/us/Quest'
    snapshot={'source':'https://poedb.tw/us/Quest','checkedAt':checked,'classes':CLASSES,'gems':dict(sorted(records.items()))}
    (ROOT/'source/gem-acquisition.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (ROOT/'source/gem-registry.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Saved {len(catalog)} gem/effect records and {len(records)} acquisition records.',flush=True)


if __name__=='__main__':
    main()
