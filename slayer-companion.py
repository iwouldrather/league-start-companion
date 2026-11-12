"""Local, read-only Path of Exile log companion. Standard library only."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webbrowser
import uuid
from pob_import import BuildLibrary, ImportProblem, gem_catalog
from gem_acquisition import CLASSES as GEM_CLASSES, snapshot as gem_snapshot
from urllib.parse import parse_qs, urlsplit

SERVER_SESSION = uuid.uuid4().hex


class PurchaseStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def read(self):
        if not self.path.exists():
            return {'version': 1, 'characters': {}}
        data = json.loads(self.path.read_text(encoding='utf8'))
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('characters'), dict):
            raise ValueError('Saved purchases could not be read; file left unchanged.')
        return data

    @staticmethod
    def name(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError('Choose a character name first.')
        return value.strip()

    def get(self, character):
        character = self.name(character)
        with self.lock:
            return dict(self.read()['characters'].get(character, {}))

    @staticmethod
    def summary(data, character):
        history=data.get('history',{}).get(character,[])
        return {'owned':dict(data['characters'].get(character,{})),
                'canUndo':bool(history),'undoLabel':history[-1]['label'] if history else ''}

    def state(self, character):
        character=self.name(character)
        with self.lock:
            return self.summary(self.read(),character)

    def set(self, character, gem, owned):
        return self.change(character,'set',gem,owned)['owned']

    def change(self, character, action, gem=None, owned=None):
        character=self.name(character)
        if action not in ('set','reset','undo'):
            raise ValueError('Unknown progress action.')
        if action=='set':
            gem=self.name(gem)
            if not isinstance(owned,bool):raise ValueError('Owned must be true or false.')
        with self.lock:
            data=self.read()
            gems=dict(data['characters'].get(character,{}))
            history=data.setdefault('history',{}).setdefault(character,[])
            if not isinstance(history,list):raise ValueError('Saved progress history could not be read.')
            if action=='undo':
                if history:gems=dict(history.pop()['owned'])
            else:
                next_gems={} if action=='reset' else dict(gems)
                if action=='set':
                    if owned:next_gems[gem]=True
                    else:next_gems.pop(gem,None)
                if next_gems!=gems:
                    label='Reset all gem progress' if action=='reset' else ('Completed ' if owned else 'Unchecked ')+gem
                    history.append({'owned':gems,'label':label})
                    del history[:-30]
                    gems=next_gems
            data['characters'][character]=gems
            temporary=self.path.with_suffix('.tmp')
            try:
                temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
                os.replace(temporary,self.path)
            finally:
                if temporary.exists():temporary.unlink()
            return self.summary(data,character)

DEFAULT_LOG = Path('E:/SteamLibrary/steamapps/common/Path of Exile/logs/Client.txt')

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

LEVEL = re.compile(r': (.+?) \(([^()]+)\) is now level (\d+)\s*$')
AREA = re.compile(r': You have entered (.+)\.\s*$')
GENERATE = re.compile(r'Generating level (\d+) area "([^"]+)"')
STAMP = re.compile(r'^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})')


class LogState:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.position = 0
        self.pending = b''
        self.identity = None
        self.state = self.blank()

    @staticmethod
    def blank():
        return dict(character=None, characterClass=None, level=None, levelAt=None,
                    area=None, areaAt=None, areaLevel=None, act=None,
                    status='waiting', updatedAt=None)

    def parse(self, line):
        stamp = STAMP.match(line)
        at = stamp.group(1) if stamp else None
        level = LEVEL.search(line)
        if level:
            name, cls, number = level.groups()
            self.state.update(character=name, characterClass=cls, level=int(number), levelAt=at)
        generate = GENERATE.search(line)
        if generate:
            area_level, area_id = generate.groups()
            # Campaign area IDs encode part and act; endgame areas do not.
            campaign = re.match(r'([12])_([1-5])_', area_id)
            act = (int(campaign[2]) + (5 if campaign[1] == '2' else 0)) if campaign else None
            self.state.update(areaLevel=int(area_level), act=act)
        area = AREA.search(line)
        if area:
            self.state.update(area=area[1], areaAt=at)

    def poll(self):
        with self.lock:
            try:
                stat = self.path.stat()
                identity = (stat.st_dev, stat.st_ino)
                reset = self.identity != identity or stat.st_size < self.position
                if reset:
                    self.state = self.blank()
                    self.position = 0
                    self.pending = b''
                    self.identity = identity
                # Binary incremental reads preserve partial UTF-8 lines between polls.
                with self.path.open('rb') as handle:
                    handle.seek(self.position)
                    while chunk := handle.read(1024 * 1024):
                        self.position = handle.tell()
                        lines = (self.pending + chunk).split(b'\n')
                        self.pending = lines.pop()
                        for line in lines:
                            self.parse(line.decode('utf8', errors='replace').rstrip('\r'))
                self.state.update(status='reading', updatedAt=datetime.now(timezone.utc).isoformat())
            except FileNotFoundError:
                self.state.update(status='missing')
            except OSError:
                self.state.update(status='unavailable')

    def snapshot(self):
        with self.lock:
            return dict(self.state)


def make_handler(log, directory, purchases=None, resources=None):
    resources=Path(resources or directory)
    purchases = purchases or PurchaseStore(directory / 'slayer-purchases.json')
    library = BuildLibrary(directory)
    version_lock = threading.Lock()
    version_cache = [None, None]

    def guide_version():
        path = resources / 'slayer-leveling-guide.html'
        stat = path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
        with version_lock:
            if signature != version_cache[0]:
                version_cache[:] = [signature, hashlib.sha256(path.read_bytes()).hexdigest()]
            return SERVER_SESSION + ':' + version_cache[1]

    class Handler(BaseHTTPRequestHandler):
        def json_response(self, value, code=200):
            content = json.dumps(value).encode('utf8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(content)

        def local_request(self):
            expected = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == expected and self.headers.get('Origin', f'http://{expected}') == f'http://{expected}'

        def do_POST(self):
            if not self.local_request() or self.path not in ('/api/purchases','/api/import/preview','/api/import/generate','/api/builds/rename','/api/builds/remove','/api/builds/restore'):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                limit = 12_500_000 if self.path == '/api/import/preview' else 100_000
                if not 0 < size <= limit:
                    raise ValueError('Invalid request size.')
                data = json.loads(self.rfile.read(size))
                if self.path == '/api/import/preview':
                    self.json_response(library.preview(data.get('input')))
                    return
                if self.path == '/api/import/generate':
                    self.json_response(library.create(data.get('draftId'),data.get('milestones'),data.get('name')))
                    return
                if self.path.startswith('/api/builds/'):
                    action=self.path.rsplit('/',1)[1]
                    result=getattr(library,action)(data.get('id'),data.get('name')) if action=='rename' else getattr(library,action)(data.get('id'))
                    self.json_response(result)
                    return
                self.json_response(purchases.change(data.get('character'),data.get('action','set'),data.get('gem'),data.get('owned')))
            except ImportProblem as error:
                self.json_response({'error': str(error),'row':error.row,'field':error.field},400)
            except (ValueError, AttributeError, TypeError):
                message = ('This build could not be processed. Check the milestone levels and set selections.'
                           if self.path.startswith('/api/import/') else 'Could not save purchases. Check character name and saved file.')
                self.json_response({'error': message}, 400)
            except OSError:
                self.json_response({'error': 'Could not write the local save file. Check folder permissions.'}, 500)

        def do_GET(self):
            # No arbitrary file access, log contents, chat, or game credentials served.
            route = self.path.split('?', 1)[0]
            if route == '/api/gem-coverage':
                self.json_response({'classes':list(GEM_CLASSES),'gems':sum(not m.get('itemGranted') for m in gem_catalog().values()),
                                    'checkedAt':gem_snapshot().get('checkedAt')})
                return
            if route == '/api/builds':
                self.json_response({'builds':library.list(),'removed':library.list(removed=True)})
                return
            if route == '/api/events':
                if not self.local_request():
                    self.send_error(403)
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                previous = None
                heartbeat = time.monotonic()
                try:
                    while True:
                        state = log.snapshot()
                        meaningful = {k:v for k,v in state.items() if k != 'updatedAt'}
                        if meaningful != previous:
                            payload = json.dumps(state)
                            self.wfile.write(f'event: game\ndata: {payload}\n\n'.encode('utf8'))
                            self.wfile.flush()
                            previous = meaningful
                            heartbeat = time.monotonic()
                        elif time.monotonic() - heartbeat >= 15:
                            self.wfile.write(b': keepalive\n\n')
                            self.wfile.flush()
                            heartbeat = time.monotonic()
                        time.sleep(.5)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    pass
                return
            if route == '/api/version':
                self.json_response({'version': guide_version()})
                return
            if route == '/api/purchases':
                if not self.local_request():
                    self.send_error(403)
                    return
                try:
                    character = parse_qs(urlsplit(self.path).query).get('character', [''])[0]
                    self.json_response(purchases.state(character))
                except (ValueError, OSError):
                    self.json_response({'error': 'Could not read purchases. Saved file has been left unchanged.'}, 500)
                return
            if route == '/api/state':
                content = json.dumps(log.snapshot()).encode('utf8')
                kind = 'application/json; charset=utf-8'
            elif route in ('/', '/slayer-leveling-guide.html', '/guide'):
                template = (resources / 'slayer-leveling-guide.html').read_text(encoding='utf8')
                query=parse_qs(urlsplit(self.path).query)
                build_id = query.get('build',[''])[0]
                if not build_id and 'library' not in query and 'removedBuild' not in query:
                    saved=library.list()
                    if saved:
                        self.send_response(302)
                        self.send_header('Location','/guide?build='+saved[0]['id'])
                        self.send_header('Cache-Control','no-store')
                        self.end_headers()
                        return
                try:
                    content = (library.render(template,build_id) if build_id else template).encode('utf8')
                except ImportProblem as error:
                    self.json_response({'error':str(error)},404)
                    return
                kind = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, default=DEFAULT_LOG)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    log = LogState(args.log)
    log.poll()
    stop = threading.Event()
    def watch():
        while not stop.wait(1):
            log.poll()
    threading.Thread(target=watch, daemon=True).start()
    try:
        server = LocalServer(('127.0.0.1', args.port), make_handler(log, Path(__file__).parent))
    except OSError:
        print(f'Cannot open local port {args.port}. Another companion may already be running.')
        return
    url = f'http://127.0.0.1:{args.port}/'
    print('SLAYER LOCAL COMPANION\n')
    print(f'Guide: {url}\nReading: {args.log}')
    print('Reads level/area events only. No game inputs, client changes, or log uploads.')
    print('Close this window or press Ctrl+C to stop.\n')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
