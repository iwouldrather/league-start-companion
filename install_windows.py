"""Per-user Windows installer/uninstaller. Saves live outside the install folder."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from app_version import VERSION

PRODUCT='LeagueStartCompanion'

def default_target(test=False):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,registry_key(test)) as key:
            return Path(winreg.QueryValueEx(key,'InstallLocation')[0])
    except OSError:return Path(os.environ['LOCALAPPDATA'])/'Programs/League Start Companion'

def shortcut_paths():
    """Resolve redirected Desktop/Programs folders, including OneDrive desktops."""
    import ctypes
    from ctypes import wintypes
    shell=ctypes.WinDLL('shell32');ole=ctypes.WinDLL('ole32')
    shell.SHGetKnownFolderPath.argtypes=[ctypes.c_void_p,wintypes.DWORD,wintypes.HANDLE,ctypes.POINTER(wintypes.LPWSTR)]
    ole.CoTaskMemFree.argtypes=[ctypes.c_void_p]
    def known(identifier):
        guid=ctypes.create_string_buffer(uuid.UUID(identifier).bytes_le)
        value=wintypes.LPWSTR()
        if shell.SHGetKnownFolderPath(guid,0,None,ctypes.byref(value))!=0:raise OSError('Could not find your Windows shortcut folder.')
        try:return Path(value.value)/'League Start Companion.lnk'
        finally:ole.CoTaskMemFree(value)
    return {'desktop':known('B4BFCC3A-DB2C-424C-B029-7FE99A87C641'),'startMenu':known('A77F5D77-2E2B-44C3-A6A2-ABA601054A51')}

def sync_shortcuts(target,choices,test=False):
    if test:return
    for kind,path in shortcut_paths().items():
        if choices[kind]:
            path.parent.mkdir(parents=True,exist_ok=True)
            script="$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LC_SHORTCUT);$s.TargetPath=(Join-Path $env:LC_INSTALL_DIR 'LeagueStartCompanion.exe');$s.WorkingDirectory=$env:LC_INSTALL_DIR;$s.IconLocation=$s.TargetPath+',0';$s.Save()"
            subprocess.run(['powershell.exe','-NoProfile','-Command',script],env=dict(os.environ,LC_INSTALL_DIR=str(target),LC_SHORTCUT=str(path)),creationflags=subprocess.CREATE_NO_WINDOW,check=True)
        else:path.unlink(missing_ok=True)

def installation_manifest(target):
    marker=Path(target)/'.league-start-install.json'
    return json.loads(marker.read_text(encoding='utf8')) if marker.is_file() else None

def validate_target(target):
    target=Path(target).expanduser().resolve()
    data=(Path(os.environ['LOCALAPPDATA'])/'LeagueStartCompanion').resolve()
    if target==Path(target.anchor) or target.is_relative_to(data):raise ValueError('Choose a dedicated app folder outside the saved-data folder.')
    manifest=installation_manifest(target)
    if manifest and manifest.get('product')!=PRODUCT:raise ValueError('This folder belongs to another application.')
    if target.exists() and not manifest and any(target.iterdir()):raise ValueError('Choose an empty folder, or the existing League Start Companion installation.')
    return target

def require_unlocked(path):
    """Preflight executable deletion without changing or stopping any process."""
    if not Path(path).exists():return
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(path),0x10000,7,None,3,0,None)
    if handle==wintypes.HANDLE(-1).value:raise PermissionError('Close League Start Companion and any open setup windows, then try again. Windows is still using '+Path(path).name+'.')
    kernel.CloseHandle(handle)

def remove_file(path):
    for attempt in range(20):
        try:path.unlink(missing_ok=True);return
        except PermissionError:
            if attempt==19:raise PermissionError('Windows is still using '+path.name+'. Close the companion and try uninstalling again.')
            time.sleep(.1)

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

def install(target,payload,test=False,desktop=None,start_menu=None,progress=None):
    target=validate_target(target)
    previous=installation_manifest(target) or {}
    if previous and bool(previous.get('test'))!=test:raise ValueError('Choose a folder matching this installation mode.')
    choices=previous.get('shortcuts',{'desktop':False,'startMenu':True}).copy()
    if desktop is not None:choices['desktop']=bool(desktop)
    if start_menu is not None:choices['startMenu']=bool(start_menu)
    for name in ('LeagueStartCompanion.exe','Uninstall.exe'):require_unlocked(target/name)
    progress=progress or (lambda *_:None)
    progress('Preparing your companion',10)
    with tempfile.TemporaryDirectory(prefix='league-start-setup-') as staging:
        staging=Path(staging)
        with zipfile.ZipFile(payload) as archive:
            names=archive.namelist()
            for name in names:checked_path(staging,name)
            archive.extractall(staging)
        if not (staging/'LeagueStartCompanion.exe').is_file():raise ValueError('The app payload is incomplete.')
        progress('Installing app files',45)
        target.mkdir(parents=True,exist_ok=True)
        shutil.copytree(staging,target,dirs_exist_ok=True)
        (target/'.league-start-install.json').write_text(json.dumps({'product':PRODUCT,'files':names,'test':test,'shortcuts':choices}),encoding='utf8')
    progress('Creating your shortcuts',85)
    sync_shortcuts(target,choices,test)
    register(target,test)
    progress('Ready for your next league',100)

def uninstall(target,test=False):
    import winreg
    target=Path(target).resolve()
    marker=target/'.league-start-install.json'
    manifest=json.loads(marker.read_text(encoding='utf8'))
    if manifest.get('product')!=PRODUCT or bool(manifest.get('test'))!=test:raise ValueError('This is not a matching companion installation.')
    for name in ('LeagueStartCompanion.exe','Uninstall.exe'):require_unlocked(target/name)
    # Check every manifest path before removing anything.
    for name in manifest['files']:checked_path(target,name)
    directories=set()
    for name in manifest['files']:
        path=checked_path(target,name)
        if path.is_file():remove_file(path)
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
        choices=manifest.get('shortcuts',{'desktop':False,'startMenu':True})
        for kind,path in shortcut_paths().items():
            if choices.get(kind):path.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--silent',action='store_true');parser.add_argument('--test',action='store_true');parser.add_argument('--uninstall',action='store_true');parser.add_argument('--worker',action='store_true');parser.add_argument('--target',type=Path)
    parser.add_argument('--wait-for',type=int)
    parser.add_argument('--update',action='store_true')
    args=parser.parse_args()
    args.target=args.target or default_target(args.test)
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
            # The one-file bootloader also holds Uninstall.exe open. Wait for
            # that parent, not just the Python child, and start a fresh runtime.
            subprocess.Popen([str(worker),'--uninstall','--worker','--silent','--wait-for',str(os.getppid()),'--target',str(args.target)]+(['--test'] if args.test else []),env=dict(os.environ,PYINSTALLER_RESET_ENVIRONMENT='1'),cwd=str(worker.parent),close_fds=True);return
        uninstall(args.target,args.test);return
    payload=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'app.zip'
    if args.update:
        try:
            install(args.target,payload,args.test)
            if not args.test:subprocess.Popen([str(args.target/'LeagueStartCompanion.exe')])
        except Exception as error:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(error)+'\nRun the downloaded installer again to retry. Your saved builds and progress are retained.','Update could not finish',16)
        return
    if args.silent:install(args.target,payload,args.test);return
    from installer_ui import run_setup
    run_setup(args.target,payload,args.test)

if __name__=='__main__':
    try:main()
    except Exception as error:
        if '--test' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(error)+'\nYour saved builds and progress have been kept.','League Start Companion',16)
        else:
            (Path(tempfile.gettempdir())/'league-start-test-error.log').write_text(str(error),encoding='utf8')
        sys.exit(1)
