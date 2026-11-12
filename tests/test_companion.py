import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen, Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('companion', Path(__file__).resolve().parents[1] / 'slayer-companion.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class CompanionTests(unittest.TestCase):
    def test_progress_undo_reset_history_and_character_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'saved.json'
            path.write_text(json.dumps({'version':1,'characters':{'One':{'Cyclone':True},'Two':{'Leap Slam':True}}}))
            store=c.PurchaseStore(path)
            self.assertFalse(store.state('One')['canUndo'])
            store.set('One','Fortify',True)
            self.assertEqual(store.state('One')['undoLabel'],'Completed Fortify')
            reset=store.change('One','reset')
            self.assertEqual(reset['owned'],{})
            self.assertEqual(reset['undoLabel'],'Reset all gem progress')
            reopened=c.PurchaseStore(path)
            self.assertEqual(reopened.change('One','undo')['owned'],{'Cyclone':True,'Fortify':True})
            self.assertEqual(reopened.change('One','undo')['owned'],{'Cyclone':True})
            self.assertFalse(reopened.state('One')['canUndo'])
            self.assertEqual(reopened.get('Two'),{'Leap Slam':True})
            reopened.set('One','Cyclone',False)
            self.assertEqual(reopened.change('One','undo')['owned'],{'Cyclone':True})
            for i in range(40):reopened.set('One',f'Gem {i}',True)
            self.assertEqual(len(json.loads(path.read_text())['history']['One']),30)
            with self.assertRaises(ValueError):reopened.change('One','invalid')

    def test_purchases_persist_and_stay_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'saved.json'
            store = c.PurchaseStore(path)
            self.assertEqual(store.get('One'), {})
            store.set('One', 'Cyclone', True)
            store.set('Two', 'Leap Slam', True)
            self.assertEqual(c.PurchaseStore(path).get('One'), {'Cyclone': True})
            self.assertEqual(store.get('Two'), {'Leap Slam': True})
            store.set('One', 'Cyclone', False)
            self.assertEqual(store.get('One'), {})
            path.write_text('{broken')
            with self.assertRaises(ValueError):
                store.set('One', 'Cyclone', True)
            self.assertEqual(path.read_text(), '{broken')

    def test_log_events_partial_append_and_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'Client.txt'
            log = c.LogState(p)
            log.poll()
            self.assertEqual(log.snapshot()['status'], 'missing')
            p.write_bytes(b'2026/11/11 19:00:00 [INFO] : Test (Duelist) is now level 22\n'
                          b'2026/11/11 19:01:00 [DEBUG] Generating level 23 area "1_2_town" with seed 1\n'
                          b'2026/11/11 19:01:01 [INFO] : You have entered The Forest Encampment.\n'
                          b'2026/11/11 19:02:00 [INFO] : Test (Duelist) is now level 2')
            log.poll()
            s = log.snapshot()
            self.assertEqual((s['level'], s['act'], s['areaLevel']), (22, 2, 23))
            self.assertEqual(s['area'], 'The Forest Encampment')
            with p.open('ab') as f:
                f.write(b'3\n2026/11/11 19:03:00 [INFO] @From Private: secret chat\n')
            log.poll()
            self.assertEqual(log.snapshot()['level'], 23)
            self.assertNotIn('secret', json.dumps(log.snapshot()))
            p.write_text('2026/11/11 20:00:00 [INFO] : Other (Witch) is now level 4\n')
            log.poll()
            self.assertEqual(log.snapshot()['character'], 'Other')
            self.assertIsNone(log.snapshot()['area'])
            with p.open('a') as f:
                f.write('2026/11/11 20:01:00 [DEBUG] Generating level 60 area "2_4_town"\n')
            log.poll()
            self.assertEqual(log.snapshot()['act'], 9)

    def test_http_exposes_only_guide_and_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / 'slayer-leveling-guide.html').write_text('guide')
            log = c.LogState(directory / 'missing')
            server = ThreadingHTTPServer(('127.0.0.1', 0), c.make_handler(log, directory))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                self.assertEqual(urlopen(base + '/').read(), b'guide')
                version = json.load(urlopen(base + '/api/version'))['version']
                self.assertEqual(json.load(urlopen(base + '/api/version'))['version'], version)
                self.assertEqual(json.load(urlopen(base + '/api/state'))['status'], 'waiting')
                with urlopen(base + '/api/events', timeout=3) as stream:
                    self.assertEqual(stream.headers['Content-Type'], 'text/event-stream')
                    self.assertEqual(stream.readline(), b'event: game\n')
                    self.assertEqual(json.loads(stream.readline()[6:])['status'], 'waiting')
                    self.assertEqual(stream.readline(), b'\n')
                    with log.lock:
                        log.state.update(level=32, status='reading')
                    self.assertEqual(stream.readline(), b'event: game\n')
                    self.assertEqual(json.loads(stream.readline()[6:])['level'], 32)
                body = json.dumps({'character': 'Test', 'gem': 'Cyclone', 'owned': True}).encode()
                result = json.load(urlopen(Request(base + '/api/purchases', data=body, headers={'Content-Type': 'application/json'})))
                self.assertEqual(result['owned'], {'Cyclone': True})
                self.assertTrue(result['canUndo'])
                for action,expected in [('reset',{}),('undo',{'Cyclone':True})]:
                    payload=json.dumps({'character':'Test','action':action}).encode()
                    result=json.load(urlopen(Request(base+'/api/purchases',data=payload,headers={'Content-Type':'application/json'})))
                    self.assertEqual(result['owned'],expected)
                build_id='a'*32
                build_dir=directory/'builds';build_dir.mkdir()
                (build_dir/(build_id+'.json')).write_text(json.dumps({'id':build_id,'name':'Test build','createdAt':'2026-11-11'}))
                class NoRedirect(HTTPRedirectHandler):
                    def redirect_request(self,*args):return None
                with self.assertRaises(HTTPError) as redirect:
                    build_opener(NoRedirect()).open(base+'/')
                self.assertEqual(redirect.exception.code,302)
                self.assertEqual(redirect.exception.headers['Location'],'/guide?build='+build_id)
                self.assertEqual(urlopen(base+'/?library=1').read(),b'guide')
                for action in ['rename','remove','restore']:
                    payload=json.dumps({'id':build_id,'name':'Renamed guide'}).encode()
                    result=json.load(urlopen(Request(base+'/api/builds/'+action,data=payload,headers={'Content-Type':'application/json'})))
                    self.assertEqual(result['id'],build_id)
                    library=json.load(urlopen(base+'/api/builds'))
                    self.assertEqual(len(library['removed']),int(action=='remove'))
                    self.assertEqual(len(library['builds']),int(action!='remove'))
                    with self.assertRaises(HTTPError) as denied:
                        urlopen(Request(base+'/api/builds/'+action,data=payload,headers={'Origin':'https://example.com'}))
                    self.assertEqual(denied.exception.code,403)
                self.assertEqual(json.load(urlopen(base + '/api/version'))['version'], version)
                (directory / 'slayer-leveling-guide.html').write_text('updated guide')
                self.assertNotEqual(json.load(urlopen(base + '/api/version'))['version'], version)
                self.assertEqual(json.load(urlopen(base + '/api/purchases?character=Test'))['owned'], {'Cyclone': True})
                with self.assertRaises(HTTPError) as rejected:
                    urlopen(Request(base + '/api/purchases', data=body, headers={'Origin': 'https://example.com'}))
                self.assertEqual(rejected.exception.code, 403)
                for path in ['/Client.txt', '/slayer-companion.py', '/../work/guide-data.json']:
                    with self.assertRaises(HTTPError) as err:
                        urlopen(base + path)
                    self.assertEqual(err.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()

if __name__ == '__main__':
    unittest.main()

