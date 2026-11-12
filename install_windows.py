"""Per-user Windows installer/uninstaller. Saves live outside the install folder."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from app_version import VERSION

PRODUCT='LeagueStartCompanion'

def wait_for_app(pid):
    """Wait for the requesting app to release its executable before installation."""
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x100000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return
        raise OSError('Could not wait for the companion to close. Close it and run setup again.')
    try:
        if kernel.WaitForSingleObject(handle,30000)!=0:raise TimeoutError('The companion is still closing. Close it and run setup again.')
    finally:kernel.CloseHandle(handle)
def registry_key(test=False):return 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'+PRODUCT+('-Test' if test else '')
def checked_path(base,name):
    target=(base/name).resolve()
    if not target.is_relative_to(base.resolve()):raise ValueError('Invalid installer archive path.')
    return target

def register(target,test=False):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,registry_key(test)) as key:
        values={'DisplayName':'League Start Companion'+(' (test)' if test else ''),'DisplayVersion':VERSION,'Publisher':'League Start Companion',
                'InstallLocation':str(target),'DisplayIcon':str(target/'LeagueStartCompanion.exe'),
                'UninstallString':subprocess.list2cmdline([str(target/'Uninstall.exe'),'--uninstall','--target',str(target)]+(['--test'] if test else []))}
        for name,value in values.items():winreg.SetValueEx(key,name,0,winreg.REG_SZ,value)
        winreg.SetValueEx(key,'NoModify',0,winreg.REG_DWORD,1);winreg.SetValueEx(key,'NoRepair',0,winreg.REG_DWORD,1)
    if not test:
        script="$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'League Start Companion.lnk'));$s.TargetPath=(Join-Path $env:LC_INSTALL_DIR 'LeagueStartCompanion.exe');$s.WorkingDirectory=$env:LC_INSTALL_DIR;$s.Save()"
        subprocess.run(['powershell.exe','-NoProfile','-Command',script],env=dict(os.environ,LC_INSTALL_DIR=str(target)),creationflags=subprocess.CREATE_NO_WINDOW,check=True)

def install(target,payload,test=False):
    target=Path(target).resolve()
    with tempfile.TemporaryDirectory(prefix='league-start-setup-') as staging:
        staging=Path(staging)
        with zipfile.ZipFile(payload) as archive:
            names=archive.namelist()
            for name in names:checked_path(staging,name)
            archive.extractall(staging)
        if not (staging/'LeagueStartCompanion.exe').is_file():raise ValueError('The app payload is incomplete.')
        target.mkdir(parents=True,exist_ok=True)
        shutil.copytree(staging,target,dirs_exist_ok=True)
        (target/'.league-start-install.json').write_text(json.dumps({'product':PRODUCT,'files':names,'test':test}),encoding='utf8')
    register(target,test)

def uninstall(target,test=False):
    import winreg
    target=Path(target).resolve()
    marker=target/'.league-start-install.json'
    manifest=json.loads(marker.read_text(encoding='utf8'))
    if manifest.get('product')!=PRODUCT or bool(manifest.get('test'))!=test:raise ValueError('This is not a matching companion installation.')
    directories=set()
    for name in manifest['files']:
        path=checked_path(target,name)
        if path.is_file():path.unlink()
        directories.update(p for p in path.parents if p.is_relative_to(target) and p!=target)
    marker.unlink()
    for path in sorted(directories,key=lambda p:len(p.parts),reverse=True):
        try:path.rmdir()
        except OSError:pass
    try:target.rmdir()
    except OSError:pass
    try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,registry_key(test))
    except FileNotFoundError:pass
    if not test:
        shortcut=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/League Start Companion.lnk'
        shortcut.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--silent',action='store_true');parser.add_argument('--test',action='store_true');parser.add_argument('--uninstall',action='store_true');parser.add_argument('--worker',action='store_true');parser.add_argument('--target',type=Path,default=Path(os.environ['LOCALAPPDATA'])/'Programs/League Start Companion')
    parser.add_argument('--wait-for',type=int)
    args=parser.parse_args()
    if args.wait_for:
        try:wait_for_app(args.wait_for)
        except (OSError,TimeoutError) as error:
            if args.silent:raise
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(error),'Setup could not finish',16);return
    if args.uninstall:
        if not args.silent:
            import ctypes
            if ctypes.windll.user32.MessageBoxW(None,'Remove League Start Companion? Your saved builds and character progress will be kept.','Uninstall League Start Companion',0x24)!=6:return
        if getattr(sys,'frozen',False) and not args.worker:
            worker=Path(tempfile.mkdtemp(prefix='league-start-uninstall-'))/'remove.exe';shutil.copy2(sys.executable,worker)
            subprocess.Popen([str(worker),'--uninstall','--worker','--silent','--target',str(args.target)]+(['--test'] if args.test else []));return
        uninstall(args.target,args.test);return
    payload=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'app.zip'
    if args.silent:install(args.target,payload,args.test);return
    import ctypes
    message=ctypes.windll.user32.MessageBoxW
    answer=message(None,'Install League Start Companion for your Windows account?\n\nLocation: '+str(args.target)+'\n\nWindows 10/11 (64-bit) with Microsoft Edge WebView2 is required. Python and Codex are not needed.\n\nSaved builds and progress stay local and are retained during upgrades and uninstall.','League Start Companion Setup',0x21)
    if answer!=1:return
    try:
        install(args.target,payload,args.test)
        if message(None,'League Start Companion is installed and available in the Start menu.\n\nOpen the app now?','Setup complete',0x24)==6:
            subprocess.Popen([str(args.target/'LeagueStartCompanion.exe')])
    except Exception as error:message(None,str(error)+'\nClose the companion before updating it.','Setup could not finish',16)

if __name__=='__main__':main()
