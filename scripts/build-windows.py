"""Create a self-contained x64 app and per-user Windows installer."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');parser.add_argument('--skip-guide-build',action='store_true');args=parser.parse_args()
    os.chdir(ROOT)
    if not args.skip_guide_build:subprocess.run([sys.executable,'scripts/build.py'],check=True)
    staging=ROOT/'build/windows';staging.mkdir(parents=True,exist_ok=True);args.output.mkdir(parents=True,exist_ok=True)
    work=staging/'pyinstaller';spec=staging/'spec';spec.mkdir(exist_ok=True)
    def freeze(entry,name,onefile=False,data=(),extra=()):
        command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--name',name,'--distpath',str(args.output),'--workpath',str(work/name),'--specpath',str(spec)]
        if onefile:command.append('--onefile')
        for source,destination in data:command.extend(['--add-data',str(source)+';'+destination])
        subprocess.run(command+list(extra)+[str(ROOT/entry)],check=True)
    pob=Path(os.environ.get('POB_DATA_DIR',str(Path(os.environ['APPDATA'])/'Path of Building Community')))
    if not (pob/'TreeData/3_29/tree.lua').exists():raise SystemExit('Install PoB Community or set POB_DATA_DIR before building the Windows app.')
    data=[(ROOT/'slayer-leveling-guide.html','.'),(ROOT/'slayer-companion.py','.'),(ROOT/'THIRD_PARTY.md','.'),(pob/'TreeData/3_29','pob-data/TreeData/3_29'),(pob/'Data/Gems.lua','pob-data/Data'),(pob/'Data/Skills','pob-data/Data/Skills')]
    data.extend((p,'source') for p in (ROOT/'source').glob('*.json'))
    data.extend((p,'pob-data/TreeData') for p in (pob/'TreeData').glob('*.png'))
    license_path=pob/'LICENSE.md'
    if license_path.exists():data.append((license_path,'pob-data'))
    freeze('desktop.py','LeagueStartCompanion',data=data,extra=['--collect-all','webview','--collect-all','pythonnet','--collect-all','clr_loader'])
    freeze('install_windows.py','Uninstall',onefile=True)
    app=args.output/'LeagueStartCompanion'
    shutil.copy2(args.output/'Uninstall.exe',app/'Uninstall.exe')
    payload=staging/'app.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in app.rglob('*'):
            if path.is_file():archive.write(path,path.relative_to(app).as_posix())
    freeze('install_windows.py','LeagueStartCompanion-Setup',onefile=True,data=[(payload,'.')])
    print('Installer:',args.output/'LeagueStartCompanion-Setup.exe')

if __name__=='__main__':main()
