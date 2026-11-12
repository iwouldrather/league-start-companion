import tempfile
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import app_updates


class UpdateTests(unittest.TestCase):
    def release(self,content=b'MZverified installer'):
        return {'tag_name':'v9.0.0','assets':[{'name':app_updates.ASSET_NAME,'state':'uploaded','size':len(content),'digest':'sha256:'+hashlib.sha256(content).hexdigest(),'browser_download_url':app_updates.RELEASES_URL+'/download/v9.0.0/'+app_updates.ASSET_NAME}]}

    def test_release_selection_and_version_comparison(self):
        self.assertEqual(app_updates.release_update(self.release())['version'],'9.0.0')
        self.assertIsNone(app_updates.release_update(self.release(),current='10.0.0'))
        for key in ('draft','prerelease'):
            release=self.release();release[key]=True
            self.assertIsNone(app_updates.release_update(release))

    def test_rejects_missing_checksum_and_foreign_installer(self):
        for key,value in [('digest',None),('browser_download_url','https://evil.example/setup.exe'),('size',200_000_000)]:
            release=self.release();release['assets'][0][key]=value
            with self.assertRaises(ValueError):app_updates.release_update(release)

    def test_background_download_cache_and_install_time_tamper_check(self):
        content=b'MZverified installer';release=self.release(content)
        def fetch(url,**kwargs):
            if url==app_updates.LATEST_URL:return json.dumps(release).encode()
            kwargs['destination'].write_bytes(content)
        with tempfile.TemporaryDirectory() as directory,patch.object(app_updates,'fetch',side_effect=fetch) as network:
            updater=app_updates.Updater(directory);updater.run()
            self.assertEqual(updater.snapshot()['status'],'ready')
            updater.run();self.assertEqual(network.call_count,3) # cached binary, metadata checked again
            updater.path.write_bytes(b'MZtampered installer')
            with patch.object(app_updates,'launch_installer') as launch:
                with self.assertRaises(ValueError):updater.install()
                launch.assert_not_called()

    def test_corrupt_download_is_removed_and_not_installable(self):
        def fetch(url,**kwargs):
            if url==app_updates.LATEST_URL:return json.dumps(self.release()).encode()
            kwargs['destination'].write_bytes(b'MZcorrupt')
        with tempfile.TemporaryDirectory() as directory,patch.object(app_updates,'fetch',side_effect=fetch):
            updater=app_updates.Updater(directory);updater.run()
            self.assertEqual(updater.snapshot()['status'],'error')
            self.assertEqual(list(updater.folder.glob('*.part')),[])
            with self.assertRaises(ValueError):updater.install()

    def test_network_failure_is_recoverable(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(app_updates,'fetch',side_effect=OSError('offline')):
            updater=app_updates.Updater(directory);updater.run()
            self.assertEqual(updater.snapshot()['status'],'error')
            self.assertFalse(updater.busy)

    def test_download_transport_rejects_untrusted_urls_before_network(self):
        from github_http import fetch
        for url in ['http://github.com/a','https://github.com.evil.example/a','https://user:pass@github.com/a','https://github.com:444/a','https://localhost/setup.exe']:
            with self.assertRaises(ValueError):fetch(url)

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
