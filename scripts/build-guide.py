"""Build the generic companion shell; saved guides are injected by the server."""
import json,os
from pathlib import Path

d={'name':'League Start Companion','build':{},'sets':[],'names':[],'meta':{},
   'acquisition':{},'acquisitionOptions':{},'acquisitionNotes':{},'warnings':[]}
payload=json.dumps(d,separators=(',',':'))
template=Path('source/guide-template.html').read_text(encoding='utf8')
template=template.replace('</style>',Path('source/dashboard.css').read_text(encoding='utf8')+'\n</style>',1)
template=template.replace('<noscript>','<dialog class="dialog" id="recordDialog" aria-labelledby="recordTitle"><div class="dialoghead"><h2 id="recordTitle">Details</h2><button data-close="recordDialog">Close</button></div><div class="recordbody" id="recordBody"></div></dialog><noscript>',1)
template=template.replace('const initial=D.sets.findIndex',Path('source/dashboard.js').read_text(encoding='utf8')+'\nconst initial=D.sets.findIndex',1)
out=Path(os.environ.get('SLAYER_BUILD_OUTPUT','slayer-leveling-guide.html'));out.write_text(template.replace('__GUIDE_DATA__',payload),encoding='utf8')
print(f'Created build-library app: {out.stat().st_size:,} bytes')
