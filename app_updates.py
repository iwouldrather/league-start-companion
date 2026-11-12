"""User-initiated updates through the private repository's signed-in browser."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from app_version import RELEASES_URL


def stage_installer(source, data_dir):
    source = Path(source).resolve()
    if source.suffix.lower() != '.exe' or not source.name.lower().startswith('leaguestartcompanion-setup'):
        raise ValueError('Choose LeagueStartCompanion-Setup.exe from the GitHub release.')
    with source.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('This file is not a Windows installer. Download the release installer again.')
    folder = Path(data_dir) / 'updates'
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / 'LeagueStartCompanion-Setup.exe'
    if source != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def launch_installer(path):
    if not getattr(sys, 'frozen', False):
        raise ValueError('Install updates from the installed Windows app. This is the development preview.')
    # The installer waits for this process to exit before replacing locked files.
    subprocess.Popen([str(path), '--wait-for', str(os.getpid()), '--target', str(Path(sys.executable).parent)])


def open_releases():
    os.startfile(RELEASES_URL)
