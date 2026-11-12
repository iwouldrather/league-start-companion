"""Validate every catalog gem for all classes and export the resolved locations."""
import argparse,csv,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import gem_acquisition as acquisition
import pob_import

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.cache/gem-acquisition-audit.json')
    args=parser.parse_args();catalog=pob_import.gem_catalog();snapshot=acquisition.snapshot()
    failures=[];rows=[];types=Counter();special=set()
    for name,meta in catalog.items():
        for cls in acquisition.CLASSES:
            primary,options,note=acquisition.resolve(name,meta,cls)
            act,vendor,quest,kind,source=primary
            if kind=='unknown':failures.append(f'{cls}: {name}: unknown acquisition')
            if kind in ('vendor','starter'):
                choices=[r for r in options if r['kind'] in ('vendor','starter')]
                first=min(choices,key=acquisition.order)
                if (act,vendor,quest)!=(first['act'],first['vendor'],first['quest']):failures.append(f'{cls}: {name}: later route selected')
                if cls not in first['classes']:failures.append(f'{cls}: {name}: wrong class')
            elif kind=='special':special.add(name)
            types[kind]+=1
            rows.append(dict(gem=name,characterClass=cls,minimumUseLevel=meta.get('minLevel'),act=act,vendor=vendor,quest=quest,kind=kind,source=source,note=note))
    failed_pages=[name for name,record in snapshot['gems'].items() if record['status']=='fetch-failed']
    failures.extend('Fetch failed: '+name for name in failed_pages)
    report=dict(checkedAt=snapshot['checkedAt'],catalogGems=len(catalog),classes=list(acquisition.CLASSES),classGemChecks=len(rows),individualPages=len(snapshot['gems']),fetchFailures=failed_pages,failures=failures,routeTypes=dict(types),specialAcquisitionReview=sorted(special),scope='Ordinary gem vendors checked against fresh per-gem pages and every class column in the quest vendor matrix, with official patch corrections. Special variants checked for campaign-vendor exclusion; exact league/drop sources are not independently verified by this audit.',sources=['https://poedb.tw/us/Quest','https://www.pathofexile.com/forum/view-thread/3985332'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    with args.output.with_suffix('.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(report,indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
