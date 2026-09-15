"""Small unauthenticated classroom console with Telnet newline negotiation.

Not a full terminal emulator: no PTY, job control or interactive full-screen apps.
"""
import os
import selectors
import signal
import socketserver
import subprocess


class TelnetInput:
    def __init__(self):
        self.state = 'text'
        self.command = None
        self.after_cr = False

    def decode(self, chunk):
        data, replies = bytearray(), bytearray()
        for value in chunk:
            if self.state == 'option':
                # Decline options; retain simple character stream operation.
                if self.command in (251, 253):
                    replies.extend([255, 254 if self.command == 251 else 252, value])
                self.state = 'text'
                continue
            if self.state == 'sub':
                if value == 255:
                    self.state = 'sub-iac'
                continue
            if self.state == 'sub-iac':
                self.state = 'text' if value == 240 else 'sub'
                continue
            if self.state == 'iac':
                if value in (251, 252, 253, 254):
                    self.command, self.state = value, 'option'
                    continue
                if value == 250:
                    self.state = 'sub'
                    continue
                self.state = 'text'
                if value != 255:
                    continue
            elif value == 255:
                self.state = 'iac'
                continue
            if self.after_cr and value in (0, 10):
                self.after_cr = False
                continue
            self.after_cr = value == 13
            data.append(10 if value == 13 else value)
        return bytes(data), bytes(replies)


class Console(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b'Bridge demo console. Type exit to disconnect.\r\n')
        process = subprocess.Popen(['/bin/sh', '-i'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd='/tmp',
            start_new_session=True, bufsize=0)
        decoder = TelnetInput()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(self.request, selectors.EVENT_READ, 'client')
                selector.register(process.stdout, selectors.EVENT_READ, 'shell')
                while True:
                    ready = selector.select(timeout=3600)
                    if not ready:
                        break
                    for key, _ in ready:
                        if key.data == 'client':
                            chunk = self.request.recv(4096)
                            if not chunk:
                                return
                            data, replies = decoder.decode(chunk)
                            if replies:
                                self.request.sendall(replies)
                            if data:
                                process.stdin.write(data)
                        else:
                            data = os.read(process.stdout.fileno(), 4096)
                            if not data:
                                return
                            self.request.sendall(data.replace(b'\xff', b'\xff\xff').replace(b'\n', b'\r\n'))
        except (OSError, BrokenPipeError):
            pass
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            except ProcessLookupError:
                pass
            process.stdin.close()
            process.stdout.close()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    with Server(('0.0.0.0', 2323), Console) as server:
        server.serve_forever()
