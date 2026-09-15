"""Root launches services as separate users, then supervises their lifetimes."""
import os
import signal
import subprocess
import sys
import time

role = os.environ['SERVICE_ROLE']
children = []


def launch(command, uid, env):
    child = subprocess.Popen(command, user=uid, group=uid, extra_groups=[], env=env)
    children.append(child)
    return child


def stop(*args):
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
    sys.exit(0)


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
service_env = dict(os.environ)
if role == 'api':
    # Model weights are built into the image. No runtime download or Internet needed.
    model_env = {key: value for key, value in service_env.items() if key != 'SERVICE_TOKEN'}
    model_env['HOME'] = '/tmp/ollama-home'
    launch(['ollama', 'serve'], 10002, model_env)
    launch([sys.executable, 'warmup.py'], 10002, model_env)
launch([sys.executable, 'server.py'], 10002 if role == 'api' else 10001, service_env)
# Shell sessions cannot inherit gateway credentials or model metadata.
console_env = {'PATH': os.environ['PATH'], 'HOME': '/tmp', 'TERM': 'dumb',
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
launch([sys.executable, 'console.py'], 10001, console_env)
while True:
    for child in children:
        if child.poll() is not None:
            print('A supervised service exited; stopping container.', flush=True)
            stop()
    time.sleep(1)
