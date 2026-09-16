"""Instructor-only live checks. Requires the running Compose lab; performs two scans.

Run separately from unit tests: python3 tests/verify_live.py
The single-source trial temporarily blocks chat-to-API traffic for 20 seconds.
"""
import json
from pathlib import Path
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def compose(*args):
    return subprocess.check_output(['docker', 'compose', *args], cwd=ROOT, text=True)


def main():
    config = json.loads(compose('config', '--format', 'json'))
    services = config['services']
    target = services['scan-guard']['environment']['API_PRIVATE_IP']
    source = services['chat']['environment']['CHAT_PRIVATE_IP']
    decoys = services['chat']['environment']['DECOY_IPS'].split(',')
    port = next(int(p['published']) for p in services['chat']['ports'] if p['target'] == 2323)

    def console(command):
        with socket.create_connection(('127.0.0.1', port), timeout=5) as sock:
            sock.settimeout(45)
            sock.sendall((command + '\nexit\n').encode())
            chunks = []
            while chunk := sock.recv(65536):
                chunks.append(chunk)
        output = b''.join(chunks).decode(errors='replace')
        print(output, flush=True)
        return output

    def events():
        return [json.loads(line) for line in compose(
            'exec', '-T', 'scan-guard', 'cat', '/var/log/suricata/eve.json').splitlines() if line]

    def firewall():
        return compose('exec', '-T', 'scan-guard', 'iptables', '-n', '-v', '-L', 'BRIDGE_LAB_SCAN')

    def await_condition(predicate, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.5)
        raise AssertionError('Timed out waiting for live lab condition')

    assert not services['api'].get('ports'), 'API must have no published ports'
    assert config['networks']['private']['internal']
    assert set(services['api']['networks']) == {'private'}
    processes = compose('exec', '-T', 'api', 'ps', '-eo', 'user:15,args')
    assert any(line.startswith('labapi ') and 'server.py' in line for line in processes.splitlines())
    listeners = compose('exec', '-T', 'api', 'ss', '-lnt')
    assert ':2222 ' in listeners and ':2323 ' not in listeners, listeners
    output = console('id; nmap -sT -n -Pn -p 2222,2323 ' + target)
    assert 'uid=10001(student)' in output
    assert '2222/tcp open' in output and '2323/tcp closed' in output
    output = console('/usr/bin/python3 /app/ssh_bypass.py')
    assert 'labssh' in output, 'Historical libssh teaching client failed'

    await_condition(lambda: 'DROP' not in firewall(), 25)
    # Let previous probes age out before each attribution trial.
    time.sleep(4)
    start = len(events())
    scan = 'nmap -sS -n -Pn -r --scan-delay 100ms --max-retries 0 -p 1-40,2222 '
    output = console(scan + target)
    await_condition(lambda: source in firewall() and 'DROP' in firewall(), 5)
    output = console('nc -z -w 2 ' + target + ' 2222; echo SSH_PROBE=$?')
    assert 'SSH_PROBE=1' in output, 'Single-source block did not affect SSH probe'
    print(firewall(), flush=True)
    await_condition(lambda: any(e.get('alert', {}).get('signature_id') == 1093302
                               for e in events()[start:]), 5)
    await_condition(lambda: 'DROP' not in firewall(), 25)
    time.sleep(4)
    start = len(events())
    since = str(int(time.time()))
    output = console(scan + '-D ' + ','.join(decoys + ['ME']) + ' ' + target)
    assert '2222/tcp open' in output, 'Decoy trial did not reach SSH'
    time.sleep(2)
    assert 'DROP' not in firewall(), 'Decoy trial unexpectedly blocked'
    logs = compose('logs', '--since', since, 'scan-guard')
    assert '"event": "suppress"' in logs and '"event": "block"' not in logs, logs
    alerts = events()[start:]
    for address in [source, *decoys]:
        assert any(e.get('src_ip') == address and e.get('alert', {}).get('signature_id') == 1093301
                   for e in alerts), f'Missing SYN telemetry from {address}'
        assert any(e.get('src_ip') == address and e.get('alert', {}).get('signature_id') == 1093302
                   for e in alerts), f'Missing scan alert from {address}'
    print(logs, flush=True)
    print('PASS: segmentation configuration, identities, Telnet, SSH, closed API Telnet, '
          'single-source enforcement/expiry, decoy suppression and Suricata alerts.', flush=True)


if __name__ == '__main__':
    main()
