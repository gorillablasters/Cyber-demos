"""Consume Suricata SYN telemetry and enforce the named teaching heuristic."""
import ipaddress
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from datetime import datetime
from policy import Policy

CHAIN = 'BRIDGE_LAB_SCAN'


def iptables(*args, check=True):
    return subprocess.run(['iptables', '-w', '5', *args], check=check, capture_output=True, text=True)


def rule(source):
    return ['-s', str(ipaddress.IPv4Address(source)), '-p', 'tcp', '-m', 'conntrack', '--ctstate', 'NEW', '-j', 'DROP']


def setup():
    if iptables('-n', '-L', CHAIN, check=False).returncode:
        iptables('-N', CHAIN)
    iptables('-F', CHAIN)
    if iptables('-C', 'INPUT', '-j', CHAIN, check=False).returncode:
        iptables('-I', 'INPUT', '1', '-j', CHAIN)


def cleanup(*args):
    iptables('-F', CHAIN, check=False)
    iptables('-D', 'INPUT', '-j', CHAIN, check=False)
    iptables('-X', CHAIN, check=False)
    raise SystemExit(0)


def run():
    target = str(ipaddress.IPv4Address(os.environ['API_PRIVATE_IP']))
    subnet = ipaddress.IPv4Network(os.environ['LAB_SUBNET'])
    policy = Policy()
    setup()
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    path = Path('/var/log/suricata/eve.json')
    reader, identity, buffer = None, None, ''
    print(json.dumps({'event': 'guard_ready', 'policy': 'teaching-multiple-sources-suppress-blocking',
                      'threshold_ports': 8, 'window_seconds': 3, 'ban_seconds': 20}), flush=True)
    try:
        while True:
            if path.exists():
                stat = path.stat()
                if reader is None or identity != stat.st_ino or stat.st_size < reader.tell():
                    if reader:
                        reader.close()
                    reader = path.open()
                    identity, buffer = stat.st_ino, ''
                buffer += reader.read(262144)
                lines = buffer.split('\n')
                buffer = lines.pop()
                if len(buffer) > 1048576:
                    raise RuntimeError('Oversized EVE line')
                for line in lines:
                    try:
                        event = json.loads(line)
                        if event.get('alert', {}).get('signature_id') != 1093301 or event.get('dest_ip') != target:
                            continue
                        # Do not replay old alerts after guard/container restarts.
                        stamp = datetime.fromisoformat(event['timestamp']).timestamp()
                        if abs(time.time() - stamp) > 5:
                            continue
                        source = ipaddress.IPv4Address(event['src_ip'])
                        port = int(event['dest_port'])
                        if source not in subnet or str(source) == target or not 1 <= port <= 65535:
                            continue
                        policy.observe(str(source), port, time.monotonic())
                    except (KeyError, ValueError, TypeError):
                        continue
            for action, source in policy.tick(time.monotonic()):
                if action == 'block':
                    iptables('-A', CHAIN, *rule(source))
                elif action == 'unblock':
                    iptables('-D', CHAIN, *rule(source))
                print(json.dumps({'event': action, 'source': source}), flush=True)
            time.sleep(0.05)
    finally:
        if reader:
            reader.close()


if __name__ == '__main__':
    run()
