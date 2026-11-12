import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
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

if __name__=='__main__':unittest.main()
