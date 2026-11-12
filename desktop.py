"""Installed Windows entry point; resources and user saves are kept separate."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
from app_version import VERSION, RELEASES_URL
import app_updates
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parent

def default_data_dir():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'LeagueStartCompanion'

def find_log():
    candidates=[Path('E:/SteamLibrary/steamapps/common/Path of Exile/logs/Client.txt')]
    for key in ('ProgramFiles(x86)','ProgramFiles'):
        base=Path(os.environ.get(key,'C:/Program Files'))
        candidates.extend([base/'Grinding Gear Games/Path of Exile/logs/Client.txt',base/'Steam/steamapps/common/Path of Exile/logs/Client.txt'])
        manifest=base/'Steam/steamapps/libraryfolders.vdf'
        if manifest.exists():
            for value in re.findall(r'"path"\s+"([^"]+)"',manifest.read_text(errors='replace')):
                candidates.append(Path(value.replace('\\\\','\\'))/'steamapps/common/Path of Exile/logs/Client.txt')
    return next((p for p in candidates if p.is_file()),None)

def import_saves(source,destination):
    """Copy selected legacy saves; never replace existing progress or builds."""
    source,destination=Path(source),Path(destination)
    copied=0
    progress=source/'slayer-purchases.json'
    target=destination/progress.name
    if progress.is_file() and not target.exists():
        data=json.loads(progress.read_text(encoding='utf8'))
        if data.get('version')!=1 or not isinstance(data.get('characters'),dict):raise ValueError('This folder has an invalid progress file.')
        shutil.copy2(progress,target);copied+=1
    for path in (source/'builds').glob('*.json'):
        if path.is_symlink() or not re.fullmatch(r'(?:draft-)?[0-9a-f]{32}\.json',path.name):continue
        target=destination/'builds'/path.name
        if target.exists():continue
        json.loads(path.read_text(encoding='utf8'))
        target.parent.mkdir(exist_ok=True);shutil.copy2(path,target);copied+=1
    return copied

class LogSource:
    def __init__(self,module,path):self.module=module;self.lock=threading.RLock();self.use(path)
    def use(self,path):
        with self.lock:self.current=self.module.LogState(Path(path));self.current.poll()
    def poll(self):
        with self.lock:self.current.poll()
    def snapshot(self):
        with self.lock:return self.current.snapshot()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',type=Path,default=default_data_dir());parser.add_argument('--smoke-test',type=Path)
    args=parser.parse_args();args.data_dir.mkdir(parents=True,exist_ok=True)
    if not args.smoke_test:
        import ctypes
        from ctypes import wintypes
        create_mutex=ctypes.windll.kernel32.CreateMutexW;create_mutex.restype=wintypes.HANDLE
        create_mutex.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        mutex=create_mutex(None,False,'Local\\LeagueStartCompanion')
        if ctypes.windll.kernel32.GetLastError()==183:
            ctypes.windll.user32.MessageBoxW(None,'League Start Companion is already open.','League Start Companion',64);return
    settings_path=args.data_dir/'settings.json'
    settings=json.loads(settings_path.read_text(encoding='utf8')) if settings_path.exists() else {}
    spec=importlib.util.spec_from_file_location('companion',ROOT/'slayer-companion.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    log=LogSource(module,settings.get('logPath') or find_log() or args.data_dir/'Client.txt-not-selected')
    handler=module.make_handler(log,args.data_dir,resources=ROOT)
    try:server=module.LocalServer(('127.0.0.1',int(settings.get('port',8768))),handler)
    except OSError:server=module.LocalServer(('127.0.0.1',0),handler)
    server.daemon_threads=True
    settings['port']=server.server_port;settings_path.write_text(json.dumps(settings),encoding='utf8')
    stop=threading.Event()
    threading.Thread(target=server.serve_forever,daemon=True).start()
    def watch():
        while not stop.wait(1):log.poll()
    threading.Thread(target=watch,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/'
    if args.smoke_test:
        from http.client import HTTPConnection
        import pob_import
        import poe_tree
        connection=HTTPConnection('127.0.0.1',server.server_port);connection.request('GET','/');response=connection.getresponse();response.read();connection.close()
        result={'http':response.status,'catalog':len(pob_import.gem_catalog()),'treeNodes':len(pob_import.tree_data('3_29')['nodes']),'nativeSprite':bool(poe_tree.sprite_data('3_29')),'dataDir':str(args.data_dir)}
        args.smoke_test.write_text(json.dumps(result),encoding='utf8');server.shutdown();return
    import webview
    window=None
    class Api:
        def settings(self):return {'logPath':str(log.current.path),'dataDir':str(args.data_dir),'version':VERSION,'releasesUrl':RELEASES_URL,'installed':bool(getattr(sys,'frozen',False))}
        def check_updates(self):
            app_updates.open_releases()
            return {'message':'The releases page is open in your browser. Sign in to GitHub if asked, and compare the latest release with version '+VERSION+'.'}
        def install_update(self):
            if not getattr(sys,'frozen',False):raise ValueError('Install updates from the installed Windows app.')
            files=window.create_file_dialog(webview.FileDialog.OPEN,file_types=('Companion installer (*.exe)',))
            if not files:return {'cancelled':True}
            installer=app_updates.stage_installer(files[0],args.data_dir)
            import ctypes
            if ctypes.windll.user32.MessageBoxW(None,'Close the companion and run this installer?\n\n'+str(files[0])+'\n\nOnly continue if you downloaded it from our GitHub releases. Your builds and progress will be kept.','Install companion update',0x24)!=6:return {'cancelled':True}
            app_updates.launch_installer(installer)
            window.destroy()
            return {'message':'Closing the app to install the update…'}
        def choose_game_log(self):
            files=window.create_file_dialog(webview.FileDialog.OPEN,file_types=('PoE game log (*.txt)',))
            if files:
                path=Path(files[0])
                if not path.is_file():raise ValueError('Choose an existing Client.txt file.')
                log.use(path);settings['logPath']=str(path);settings_path.write_text(json.dumps(settings),encoding='utf8')
            return self.settings()
        def import_existing_saves(self):
            folders=window.create_file_dialog(webview.FileDialog.FOLDER)
            return {'copied':import_saves(folders[0],args.data_dir) if folders else 0}
        def open_data_folder(self):os.startfile(args.data_dir)
    window=webview.create_window('League Start Companion',url,js_api=Api(),width=1600,height=950,min_size=(1100,720),text_select=True)
    try:webview.start(gui='edgechromium',private_mode=False,storage_path=str(args.data_dir/'webview'))
    finally:stop.set();server.shutdown();server.server_close()

if __name__=='__main__':
    try:main()
    except Exception as failure:
        import traceback
        error=traceback.format_exc();folder=default_data_dir();folder.mkdir(parents=True,exist_ok=True);(folder/'startup-error.log').write_text(error,encoding='utf8')
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,'The app could not start: '+str(failure)+'\nDetails: '+str(folder/'startup-error.log'),'League Start Companion',16)
        raise
