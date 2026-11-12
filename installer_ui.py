"""Local, offline setup screen; installer operations stay in install_windows."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

from app_version import VERSION

ROOT=Path(__file__).resolve().parent

def run_setup(target,payload,test=False,preview=False):
    if os.environ.get('LC_SETUP_DIAGNOSTICS'):
        import faulthandler
        import logging
        logging.basicConfig(filename=os.environ['LC_SETUP_DIAGNOSTICS'],level=logging.DEBUG,force=True)
        diagnostic=open(os.environ['LC_SETUP_DIAGNOSTICS']+'.threads','w')
        faulthandler.dump_traceback_later(15,file=diagnostic)
        logging.debug('Importing setup UI runtime')
    import webview
    import install_windows as setup
    state={'busy':False,'installed':False,'target':Path(target)}
    window=None
    class Api:
        def defaults(self):
            manifest=setup.installation_manifest(target) or {}
            return {'path':str(target),'version':VERSION,'preview':preview,'shortcuts':manifest.get('shortcuts',{'desktop':False,'startMenu':True})}
        def browse(self):
            if state['busy']:return None
            folders=window.create_file_dialog(webview.FileDialog.FOLDER,directory=str(Path(target).parent))
            if not folders:return None
            folder=Path(folders[0])
            if not setup.installation_manifest(folder) and folder.name!='League Start Companion':folder=folder/'League Start Companion'
            return str(folder)
        def install_to(self,path,desktop,start_menu):
            if preview:return {'ok':False,'message':'This is a visual preview; no files will be installed.'}
            if state['busy']:return {'ok':False,'message':'Setup is already running.'}
            state['busy']=True
            try:
                destination=setup.validate_target(path)
                existing=setup.default_target(test)
                if setup.installation_manifest(existing) and destination!=existing.resolve():
                    raise ValueError('To move the app, uninstall the current installation first. Your saved builds and progress will be kept.')
                def progress(message,percent):
                    window.evaluate_js('setupProgress('+json.dumps(message)+','+str(percent)+')')
                setup.install(destination,payload,test,desktop=desktop,start_menu=start_menu,progress=progress)
                state.update(installed=True,target=destination)
                return {'ok':True,'path':str(destination)}
            except Exception as error:return {'ok':False,'message':str(error)}
            finally:state['busy']=False
        def finish(self,launch=False):
            if state['busy']:return
            if launch and state['installed'] and not test:
                subprocess.Popen([str(state['target']/'LeagueStartCompanion.exe')],env=os.environ.copy()|{'PYINSTALLER_RESET_ENVIRONMENT':'1'})
            window.destroy()
    html=(ROOT/'source/installer.html').read_text(encoding='utf8')
    icon=base64.b64encode((ROOT/'assets/app-icon.svg').read_bytes()).decode('ascii')
    html=html.replace('__ICON__','data:image/svg+xml;base64,'+icon)
    window=webview.create_window('League Start Companion Setup',html=html,js_api=Api(),width=920,height=680,min_size=(800,620),background_color='#101923',text_select=False)
    window.events.closing+=lambda:False if state['busy'] else None
    webview.start(gui='edgechromium',private_mode=True,icon=str(ROOT/'assets/app-icon.ico'))

if __name__=='__main__':
    import install_windows
    run_setup(install_windows.default_target(),ROOT/'build/windows/app.zip',preview=True)
