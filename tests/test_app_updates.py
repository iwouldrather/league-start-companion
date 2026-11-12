import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import app_updates


class UpdateTests(unittest.TestCase):
    def test_stages_installer_without_touching_saves(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);data=root/'data';data.mkdir()
            save=data/'slayer-purchases.json';save.write_text('preserve me')
            source=root/'LeagueStartCompanion-Setup (1).exe';source.write_bytes(b'MZinstaller')
            staged=app_updates.stage_installer(source,data)
            self.assertEqual(staged.read_bytes(),source.read_bytes())
            self.assertEqual(save.read_text(),'preserve me')
            self.assertEqual(app_updates.stage_installer(staged,data),staged)

    def test_rejects_wrong_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,content in [('other.exe',b'MZ'),('LeagueStartCompanion-Setup.exe',b'not an executable')]:
                source=root/name;source.write_bytes(content)
                with self.assertRaises(ValueError):app_updates.stage_installer(source,root/'data')

    def test_launch_waits_for_current_process_and_keeps_install_location(self):
        with patch.object(app_updates.sys,'frozen',True,create=True),patch.object(app_updates.sys,'executable',r'C:\Apps\Companion\LeagueStartCompanion.exe'),patch.object(app_updates.subprocess,'Popen') as launch:
            app_updates.launch_installer(Path('setup.exe'))
            arguments=launch.call_args.args[0]
            self.assertEqual(arguments[1:3],['--wait-for',str(app_updates.os.getpid())])
            self.assertEqual(arguments[3:],['--target',str(Path(app_updates.sys.executable).parent)])
