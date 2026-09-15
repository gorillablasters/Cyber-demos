"""Root launches services as separate users, then supervises their lifetimes."""
import os
import json
import ipaddress
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
    launch(['ollama', 'serve'], 10003, model_env)
    launch([sys.executable, 'warmup.py'], 10003, model_env)
launch([sys.executable, 'server.py'], 10003 if role == 'api' else 10001, service_env)
# Shell sessions cannot inherit gateway credentials or model metadata.
console_env = {'PATH': os.environ['PATH'], 'HOME': '/tmp', 'TERM': 'dumb',
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
if role == 'api':
    # Bind SSH only as labssh; the API and model remain a separate identity.
    key_dir = '/tmp/libssh-keys'
    os.makedirs(key_dir, mode=0o700, exist_ok=True)
    os.chown(key_dir, 10004, 10004)
    key = key_dir + '/host_rsa'
    subprocess.run(['ssh-keygen', '-q', '-t', 'rsa', '-b', '2048', '-m', 'PEM', '-N', '', '-f', key],
                   user=10004, group=10004, extra_groups=[], check=True)
    ssh_env = dict(console_env, LD_LIBRARY_PATH='/opt/libssh/lib')
    launch(['/opt/libssh/bin/ssh_server_fork', '-n', '-k', key, '-p', '2222', '0.0.0.0'], 10004, ssh_env)
else:
    # Lab-only aliases make the decoy sources real addresses on this isolated link.
    private_ip = os.environ['CHAT_PRIVATE_IP']
    interfaces = json.loads(subprocess.check_output(['ip', '-j', 'addr']))
    device = next(i['ifname'] for i in interfaces
                  if any(a.get('local') == private_ip for a in i.get('addr_info', [])))
    for address in os.environ['DECOY_IPS'].split(','):
        address = str(ipaddress.IPv4Address(address))
        subprocess.run(['ip', 'addr', 'replace', address + '/32', 'dev', device], check=True)
    console_env['NMAP_PRIVILEGED'] = '1'
    # Ambient NET_RAW permits real SYN/decoy packets without a root shell.
    children.append(subprocess.Popen(['setpriv', '--reuid=10001', '--regid=10001', '--clear-groups',
        '--inh-caps=+net_raw', '--ambient-caps=+net_raw', sys.executable, 'console.py'], env=console_env))
while True:
    for child in children:
        if child.poll() is not None:
            print('A supervised service exited; stopping container.', flush=True)
            stop()
    time.sleep(1)
