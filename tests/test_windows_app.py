import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import os
import subprocess
import shutil
import desktop
import install_windows as setup

class WindowsAppTests(unittest.TestCase):
    def test_migration_copies_without_replacing_progress_or_builds(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'old';new=root/'new';old.mkdir();new.mkdir();(old/'builds').mkdir()
            progress={'version':1,'characters':{'Character':{'Momentum':True}}}
            (old/'slayer-purchases.json').write_text(json.dumps(progress))
            name='a'*32+'.json';(old/'builds'/name).write_text('{"name":"saved"}')
            self.assertEqual(desktop.import_saves(old,new),2)
            self.assertEqual(json.loads((new/'slayer-purchases.json').read_text()),progress)
            (new/'slayer-purchases.json').write_text('{"version":1,"characters":{}}')
            self.assertEqual(desktop.import_saves(old,new),0)
            self.assertEqual(json.loads((new/'slayer-purchases.json').read_text())['characters'],{})
            self.assertTrue((old/'slayer-purchases.json').exists())

    def test_installer_checks_archive_paths_and_keeps_untracked_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'app';payload=root/'app.zip'
            with self.assertRaises(ValueError):setup.checked_path(target,'../escape')
            with zipfile.ZipFile(payload,'w') as archive:
                archive.writestr('LeagueStartCompanion.exe','test app');archive.writestr('_internal/data.txt','data')
            with patch.object(setup,'register') as register:
                setup.install(target,payload,test=True);register.assert_called_once_with(target.resolve(),True)
            (target/'user-note.txt').write_text('keep me')
            import winreg
            with patch.object(winreg,'DeleteKey'):setup.uninstall(target,test=True)
            self.assertEqual((target/'user-note.txt').read_text(),'keep me')
            self.assertFalse((target/'LeagueStartCompanion.exe').exists())

    def test_shortcut_choices_survive_updates(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'custom location';payload=root/'app.zip'
            with zipfile.ZipFile(payload,'w') as archive:archive.writestr('LeagueStartCompanion.exe','test app')
            with patch.object(setup,'register'):
                setup.install(target,payload,test=True,desktop=True,start_menu=False)
                setup.install(target,payload,test=True)
            self.assertEqual(setup.installation_manifest(target)['shortcuts'],{'desktop':True,'startMenu':False})

    def test_rejects_nonempty_unrelated_folders_before_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'important.txt').write_text('keep')
            with self.assertRaises(ValueError):setup.validate_target(root)
            self.assertEqual((root/'important.txt').read_text(),'keep')

    def test_locked_uninstall_leaves_manifest_and_files_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder);marker=target/'.league-start-install.json'
            marker.write_text(json.dumps({'product':setup.PRODUCT,'test':True,'files':['LeagueStartCompanion.exe']}))
            (target/'LeagueStartCompanion.exe').write_text('app')
            with patch.object(setup,'require_unlocked',side_effect=PermissionError('close app')):
                with self.assertRaises(PermissionError):setup.uninstall(target,test=True)
            self.assertTrue(marker.exists());self.assertTrue((target/'LeagueStartCompanion.exe').exists())

    def test_shortcuts_created_and_removed_independently(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);paths={'desktop':root/'desktop.lnk','startMenu':root/'start.lnk'}
            paths['startMenu'].write_text('old shortcut')
            with patch.object(setup,'shortcut_paths',return_value=paths),patch.object(setup.subprocess,'run') as command,patch.object(setup,'shortcut_identity') as identity,patch.object(setup,'refresh_shell_icon'):
                setup.sync_shortcuts(root,{'desktop':True,'startMenu':False})
                identity.assert_called_once_with(paths['desktop'])
            self.assertFalse(paths['startMenu'].exists())
            self.assertEqual(command.call_count,1)
            self.assertEqual(command.call_args.kwargs['env']['LC_SHORTCUT'],str(paths['desktop']))

    def test_real_windows_shortcut_identity_and_icon_reference(self):
        from windows_identity import APP_ID,shortcut_identity
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'app';icons=target/'_internal/assets';icons.mkdir(parents=True)
            icon=icons/f'app-icon-{setup.VERSION}.ico'
            shutil.copy2(Path(__file__).resolve().parents[1]/'assets/app-icon.ico',icon)
            paths={'desktop':root/'Desktop.lnk','startMenu':root/'Programs.lnk'}
            with patch.object(setup,'shortcut_paths',return_value=paths):
                setup.sync_shortcuts(target,{'desktop':True,'startMenu':False})
            self.assertEqual(shortcut_identity(paths['desktop'],write=False),APP_ID)
            command="$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LC_SHORTCUT);$s.IconLocation"
            result=subprocess.run(['powershell.exe','-NoProfile','-Command',command],env=dict(os.environ,LC_SHORTCUT=str(paths['desktop'])),capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(result.stdout.strip(),str(icon)+',0')
            pin=root/'Pinned.lnk';shutil.copy2(paths['desktop'],pin)
            foreign=root/'Foreign.lnk';shutil.copy2(pin,foreign)
            command="$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LC_SHORTCUT);$s.TargetPath='C:\\Other\\Foreign.exe';$s.Save()"
            subprocess.run(['powershell.exe','-NoProfile','-Command',command],env=dict(os.environ,LC_SHORTCUT=str(foreign)),check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            with patch.object(setup,'pinned_shortcut_paths',return_value=[pin,foreign]),patch.object(setup,'shortcut_identity',wraps=shortcut_identity) as identity:
                setup.refresh_pinned_shortcuts(target)
                identity.assert_called_once_with(pin)
            self.assertEqual(shortcut_identity(pin,write=False),APP_ID)

    def test_upgrade_keeps_old_owned_resources_in_uninstall_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'app';payload=root/'app.zip'
            with zipfile.ZipFile(payload,'w') as archive:
                archive.writestr('LeagueStartCompanion.exe','app');archive.writestr('_internal/assets/old-icon.ico','old')
            with patch.object(setup,'register'):
                setup.install(target,payload,test=True)
                with zipfile.ZipFile(payload,'w') as archive:archive.writestr('LeagueStartCompanion.exe','new app')
                setup.install(target,payload,test=True)
            self.assertIn('_internal/assets/old-icon.ico',setup.installation_manifest(target)['files'])
            import winreg
            with patch.object(winreg,'DeleteKey'):setup.uninstall(target,test=True)
            self.assertFalse(target.exists())

if __name__=='__main__':unittest.main()
