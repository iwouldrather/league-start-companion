"""Background public-release checks; installation always requires a user click."""
import hashlib
import json
import re
import threading
import os
from pathlib import Path
import subprocess
import sys

from app_version import RELEASES_URL, VERSION
from github_http import fetch

LATEST_URL='https://api.github.com/repos/iwouldrather/league-start-companion/releases/latest'
ASSET_NAME='LeagueStartCompanion-Setup.exe'


def version_tuple(value):
    if not re.fullmatch(r'v?\d+\.\d+\.\d+',value):raise ValueError('Release version is not supported.')
    return tuple(map(int,value.lstrip('v').split('.')))


def release_update(release,current=VERSION):
    if release.get('draft') or release.get('prerelease'):return None
    tag=release.get('tag_name','')
    if version_tuple(tag)<=version_tuple(current):return None
    assets=[a for a in release.get('assets',[]) if a.get('name')==ASSET_NAME and a.get('state')=='uploaded']
    if len(assets)!=1:raise ValueError('This release has no ready Windows installer.')
    asset=assets[0];digest=asset.get('digest') or ''
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',digest):raise ValueError('The release has no verified installer checksum yet.')
    expected=RELEASES_URL+'/download/'+tag+'/'+ASSET_NAME
    if asset.get('browser_download_url')!=expected:raise ValueError('Unexpected installer address.')
    size=asset.get('size',0)
    if not isinstance(size,int) or not 0<size<=150_000_000:raise ValueError('Unexpected installer size.')
    return {'version':tag.lstrip('v'),'url':expected,'sha256':digest[7:],'size':size}


def verify_installer(path,update):
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if path.stat().st_size!=update['size'] or digest!=update['sha256']:
        raise ValueError('Installer verification failed. Check for updates to download a fresh copy.')
    with path.open('rb') as stream:
        if stream.read(2)!=b'MZ':raise ValueError('The downloaded file is not a Windows installer.')


class Updater:
    def __init__(self,data_dir):
        self.folder=Path(data_dir)/'updates';self.lock=threading.RLock();self.busy=False;self.update=None;self.path=None
        self.state={'status':'idle','message':'Updates are checked automatically at startup and every four hours.'}
    def snapshot(self):
        with self.lock:return dict(self.state)
    def set_state(self,status,message,**extra):
        with self.lock:self.state={'status':status,'message':message,**extra}
    def start(self):
        with self.lock:
            if self.busy:return self.snapshot()
            self.busy=True
        threading.Thread(target=self.run,daemon=True).start()
        return self.snapshot()
    def run(self):
        partial=None
        try:
            self.set_state('checking','Checking for updates…')
            update=release_update(json.loads(fetch(LATEST_URL)))
            if not update:
                self.set_state('current','You’re up to date. Version '+VERSION+'.');return
            self.folder.mkdir(parents=True,exist_ok=True)
            path=self.folder/('setup-'+update['version']+'.exe');partial=path.with_suffix('.part')
            self.set_state('downloading','Downloading version '+update['version']+' in the background…',version=update['version'])
            try:verify_installer(path,update)
            except (OSError,ValueError):
                fetch(update['url'],limit=update['size'],destination=partial)
                verify_installer(partial,update);partial.replace(path)
            self.update=update;self.path=path
            self.set_state('ready','Version '+update['version']+' is ready. Restart when it suits you.',version=update['version'])
        except Exception:
            self.set_state('error','Could not check or verify the update. Check your connection and try again.')
        finally:
            if partial:
                try:partial.unlink(missing_ok=True)
                except OSError:pass
            with self.lock:self.busy=False
    def install(self):
        with self.lock:
            if self.busy or self.state['status']!='ready':raise ValueError('No verified update is ready yet.')
            verify_installer(self.path,self.update)
            launch_installer(self.path,automatic=True)



def launch_installer(path,automatic=False):
    if not getattr(sys, 'frozen', False):
        raise ValueError('Install updates from the installed Windows app. This is the development preview.')
    # The installer waits for this process to exit before replacing locked files.
    subprocess.Popen([str(path), '--wait-for', str(os.getpid()), '--target', str(Path(sys.executable).parent)]+(['--update'] if automatic else []))


def open_releases():
    os.startfile(RELEASES_URL)
