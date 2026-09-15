"""Small classroom HTTP service, used as either gateway or private API."""
import hmac
import json
import os
import secrets
import threading
import time
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from engine import respond, upload, UploadError, ModelUnavailable

ROLE = os.getenv('SERVICE_ROLE', 'api')
TOKEN = os.environ['SERVICE_TOKEN']
CLUE = os.getenv('DEPLOYMENT_CLUE', 'Chat server: TCP 8000 HTTP and TCP 2323 Telnet.')
STATES = {}
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = 'Bridge'
    sys_version = ''

    def send(self, status, body, content_type='application/json', cookie=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/health':
            return self.send(200, {'status': 'ok'})
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/chat.js': ('chat.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
        if ROLE == 'gateway' and self.path in files:
            filename, mime = files[self.path]
            return self.send(200, Path(__file__).with_name(filename).read_bytes(), mime)
        self.send(404, {'error': 'Not found'})

    def do_POST(self):
        if self.path not in ('/chat', '/reset', '/upload'):
            return self.send(404, {'error': 'Not found'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 100000:
                return self.send(413, {'error': 'Request too large or empty'})
            if self.headers.get_content_type() != 'application/json':
                return self.send(415, {'error': 'Use JSON'})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError()
            if ROLE == 'gateway':
                return self.gateway(body)
            if not hmac.compare_digest(self.headers.get('X-Service-Token', ''), TOKEN):
                return self.send(403, {'error': 'Forbidden'})
            sid = body.get('session', '')
            if not isinstance(sid, str) or len(sid) != 64:
                raise ValueError()
            message = body.get('message', '')
            if not isinstance(message, str) or len(message) > 4000:
                raise ValueError()
            # Serial generation keeps a session's notes/history consistent and
            # bounds concurrent model work for a small classroom deployment.
            with LOCK:
                now = time.monotonic()
                for key in list(STATES):
                    if now - STATES[key]['seen'] > 7200:
                        del STATES[key]
                if self.path == '/reset':
                    STATES.pop(sid, None)
                    return self.send(200, {'reply': 'Conversation and notes cleared.'})
                if self.path == '/chat' and not message.strip():
                    raise ValueError()
                if sid not in STATES and len(STATES) >= 100:
                    return self.send(503, {'error': 'Class capacity reached; try again later.'})
                state = STATES.setdefault(sid, {'notes': [], 'history': [], 'seen': now})
                state['seen'] = now
                answer = (upload(state, body.get('filename'), body.get('content')) if self.path == '/upload'
                          else respond(state, message.strip(), CLUE))
            self.send(200, {'reply': answer})
        except UploadError as error:
            self.send(400, {'error': str(error)})
        except ModelUnavailable:
            self.send(503, {'error': 'Assistant is warming up. Please try again shortly.'})
        except (ValueError, TypeError):
            self.send(400, {'error': 'Invalid request'})
        except Exception:
            # Never return upstream errors, URLs, or prompts to the student.
            self.send(503, {'error': 'Assistant unavailable. Ask your instructor to check model readiness.'})

    def gateway(self, body):
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return self.send(403, {'error': 'Forbidden'})
        cookies = SimpleCookie()
        cookies.load(self.headers.get('Cookie', ''))
        sid = cookies['bridge'].value if 'bridge' in cookies else ''
        if len(sid) != 64 or any(c not in '0123456789abcdef' for c in sid):
            sid = secrets.token_hex(32)
        payload = json.dumps({'session': sid, 'message': body.get('message', ''),
                              'filename': body.get('filename'), 'content': body.get('content')}).encode()
        request = urllib.request.Request(os.environ['API_URL'] + self.path, data=payload,
            headers={'Content-Type': 'application/json', 'X-Service-Token': TOKEN})
        try:
            with urllib.request.urlopen(request, timeout=200) as response:
                result, status = json.load(response), 200
        except urllib.error.HTTPError as error:
            with error:
                result, status = json.load(error), error.code
        self.send(status, result, cookie=f'bridge={sid}; HttpOnly; SameSite=Strict; Path=/')


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT', '8000'))), Handler)
    server.serve_forever()
