from pathlib import Path
import os

# Run build-guide.py first to refresh the base document.
output = Path(os.environ.get('SLAYER_BUILD_OUTPUT','slayer-leveling-guide.html'))
p = output.read_text(encoding='utf8')
css = Path('source/designs.css').read_text(encoding='utf8')
css += '\n' + '''body[data-design=board]{--bg:#101723;--panel:#172231;--panel2:#203248;--line:#34465e;--ink:#e9eff7;--muted:#b0bfd1;--green:#92c8ed;--gold:#e6c68e}
body[data-design=board] .topbar{background:#101723}
body[data-design=board] .tab[aria-selected=true]{color:#142235}
body[data-design=board] .concepttreeimage{background:#070d14}
'''
js = Path('source/chrome.js').read_text(encoding='utf8')+'\n'+Path('source/designs.js').read_text(encoding='utf8')
js = js.replace("let design='route';", "let design='board';")
js = '\n'.join(line for line in js.splitlines() if not line.startswith('const designBar='))
p = p.replace('</style>', css + '\n'+Path('source/chrome.css').read_text(encoding='utf8')+'\n</style>', 1)
p = p.replace('const initial=D.sets.findIndex', js + '\nconst initial=D.sets.findIndex', 1)
p = p.replace('</style>', Path('source/live-guide.css').read_text(encoding='utf8') + '\n' + Path('source/planner.css').read_text(encoding='utf8') + '\n</style>', 1)
p = p.replace('</script></body>', Path('source/live-guide.js').read_text(encoding='utf8') + '\n' + Path('source/ownership.js').read_text(encoding='utf8') + '\n' + Path('source/planner.js').read_text(encoding='utf8') + '\n' + Path('source/live-reload.js').read_text(encoding='utf8') + '\n' + Path('source/importer.js').read_text(encoding='utf8') + '\n</script></body>', 1)
p = p.replace('</style>',Path('source/importer.css').read_text(encoding='utf8')+'\n'+Path('source/tree-ui.css').read_text(encoding='utf8')+'\n</style>',1)
p = p.replace('</script></body>',Path('source/tree-ui.js').read_text(encoding='utf8')+'\n'+Path('source/library-home.js').read_text(encoding='utf8')+'\n'+Path('source/desktop.js').read_text(encoding='utf8')+'\n</script></body>',1)
output.write_text(p.rstrip()+'\n', encoding='utf8')
print('Saved final Swap board with the Tree first navy and blue palette.')
