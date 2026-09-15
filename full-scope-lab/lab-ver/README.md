# Bridge — lab version (libssh + Suricata)

This variant preserves the demo chatbot, Markdown-upload injection exercise and
chat-server Telnet foothold. Only the lab variant is modified.

| Service | Access | Process identity |
| --- | --- | --- |
| chat | Host loopback HTTP 8081 and Telnet 2324; container ports 8000 and 2323 | student, UID 10001 |
| api | Private TCP 8000 HTTP and TCP 2222 vulnerable libssh; **no Telnet listener** | API/model: labapi, UID 10003; SSH/shell: labssh, UID 10004 |
| suricata | Shares API network namespace to observe inbound traffic | IDS sidecar |
| scan-guard | Shares API network namespace to apply temporary INPUT rules | Blocking-policy sidecar |

The private network defaults to `172.30.109.0/24`: chat `.10`, API `.20`, and
chat-owned decoy aliases `.11` and `.12`. The API has no host-published ports or
runtime Internet route. Suricata and scan-guard are observer/enforcement helpers,
not additional student targets. Sharing the API namespace gives the sensor the
correct view; merely placing it elsewhere on the bridge does not mirror traffic.

The Compose project is `full-scope-lab-training`, with distinct host ports so it
can coexist with demo-ver. Host Docker administrators remain outside the student
threat model, including direct Docker-bridge access on native Linux.

## Build and start

```bash
cd full-scope-lab/lab-ver
# First setup only: copy .env.example to .env and set SERVICE_TOKEN.
docker compose up -d --build
```

Open http://localhost:8081. Model weights are packaged during the image build;
subsequent starts warm the same Qwen 2.5 0.5B model locally inside API.

```bash
docker compose logs -f api          # wait for Conversation model ready.
docker compose logs -f suricata scan-guard
```

Start all services before the scan lesson. If recreating API, recreate its
namespace-sharing sidecars too:

```bash
docker compose up -d --force-recreate api suricata scan-guard
```

`LAB_SUBNET`, `CHAT_PRIVATE_IP`, `API_PRIVATE_IP`, and `DECOY_IPS` may be set in
`.env` together if the default subnet conflicts with a local network.

## Which libssh is used

The root Dockerfile builds the **cloned** `cve-2018-10933/libssh-0.8.3.tar.xz`
with both `cve-2018-10933.patch` and `server.patch`, matching the important build
steps in the cloned Dockerfile. The original clone remains unchanged. The server
is its `ssh_server_fork` example, not OpenSSH and not a simulated SSH endpoint.

The build uses Debian Bullseye/OpenSSL 1.1 instead of the historical rolling
`base/archlinux` environment. The resulting old libssh and its matching libcrypto
are bundled privately under `/opt/libssh`. This is a local-source build of the
Hacker House target, not a pull of `hackerhouse/cve-2018-10933` from Docker Hub.
Licenses are copied into that bundle.

Fresh RSA host keys are generated in disposable `/tmp` on API recreation, so
SSH clients can report a changed host key after resets. The example retains its
upstream `myuser` / `mypassword` application credentials. Its shell runs under
`labssh` regardless of a claimed SSH username; it does not grant root.

The supplied server patch removes the example's extra authentication gate, making
CVE-2018-10933 observable. That vulnerability confuses an incoming authentication
success message with completed authentication. It is not a generic SSH bypass.

## Student progression

1. Converse with the bot. Upload `instructor/blocked.md` to see the obvious
   override rejected; put the override in a fenced code block to pass the intended
   Markdown inspection blind spot. `instructor/code-block.md` is a starting example.
2. Obtain the chat server's ports and connect from the host:

   ```bash
   telnet 127.0.0.1 2324
   ```

3. From that shell, use `netstat -at`, `ip route` and `ip neigh` to discover the
   private API target. Netstat defaults to numeric addresses, and shows API TCP
   connections while the bot is responding or briefly afterward.
4. Scan the discovered private target. Compare plain SYN scanning with decoys as
   described below, then investigate the libssh banner on TCP 2222.
5. The cloned target provides a patched client at `/opt/libssh/bin/ssh-client`.
   The user-supplied `app/ssh_bypass.py` is also retained. Its Paramiko dependency
   is installed for `/usr/bin/python3`, so run it from the chat shell with:

   ```sh
   /usr/bin/python3 /app/ssh_bypass.py
   ```

   It targets `api:2222` and requests `whoami; id; uname -a`. Check that the resulting
   identity is `labssh`, not the demo's `student`. For the patched interactive
   client, scope its library path to that invocation:

   ```sh
   LD_LIBRARY_PATH=/opt/libssh/lib /opt/libssh/bin/ssh-client -l myuser -p 2222 api
   ```

6. After obtaining a shell, inspect `ps -eo pid,user:15,args`. The API runs as
   `labapi`; the SSH shell runs as `labssh`. Process enumeration is implemented;
   cross-user process injection remains a separate future exercise.

The chatbot still uses the same real model and single refusal policy. Uploads
are .md-only and server-validated; the intentional omission is checking fenced
blocks. Model injection outcomes remain probabilistic.

## Suricata and the explicitly weak blocking heuristic

Suricata is passive IDS here, not inline IPS. The companion `scan-guard` reads
Suricata EVE JSON and inserts actual iptables rules in the API namespace.

- SID **1093301** records inbound IPv4 TCP SYNs for the guard.
- SID **1093302** alerts on a SYN burst. An alert is evidence of a pattern, not proof
  that the originating program is Nmap.
- Eight distinct destination ports from one source in three seconds starts a
  half-second attribution grace period.
- If only one source reaches that threshold, new TCP traffic from it is dropped
  for 20 seconds. Existing established sessions are not intentionally dropped.
- If at least two apparent sources reach that threshold together, the guard logs
  `suppress` and deliberately withholds blocking for that scan burst. **Suricata
  still sees and records the scan.** This is an intentionally bad attribution policy.
- An existing ban is not removed by subsequently adding decoys. Wait for expiry
  or restart scan-guard before comparing trials.

A fast scan can reveal ports before reactive blocking starts; slow scans may stay
below the threshold. This cannot guarantee that every `nmap <ip>` invocation is
blocked. Use a paced, ordered scan for a repeatable classroom comparison:

```sh
# From the chat shell; replace this address if the lab subnet was customized.
nmap -sS -n -Pn -r --scan-delay 100ms --max-retries 0 -p 1-40,2222 172.30.109.20
```

Inspect `docker compose logs scan-guard` from the instructor terminal for `block`.
Some early ports may already have been reported before enforcement. Blocking chat's
source IP can also temporarily interrupt new chat-to-API HTTP requests. Wait for
`unblock`, or reset the guard from the instructor terminal:

```bash
docker compose restart scan-guard
```

Then compare from the chat shell:

```sh
nmap -sS -n -Pn -r --scan-delay 100ms --max-retries 0 -D 172.30.109.11,172.30.109.12,ME -p 1-40,2222 172.30.109.20
```

The aliases are real addresses assigned to the chat container's private interface;
use these isolated lab addresses rather than `RND` or unrelated hosts. The console
has ambient `NET_RAW` and `NMAP_PRIVILEGED=1` so an unprivileged student process can
send real SYN/decoy probes. This capability does not make the shell root.

`-D` adds spoofed source packets; it does not automatically evade IDS. It also does
not work for TCP connect scanning (`-sT`) or version detection. The exercise works
by exploiting the named attribution mistake, not by hiding the scan from Suricata.
[Nmap documentation](https://nmap.org/book/man-bypass-firewalls-ids.html)

## Validation

```bash
python3 -m unittest discover -s tests -v
docker compose config --quiet
docker compose run --rm --no-deps suricata -T -c /rules/suricata.yaml
```

With the stack running, check API listeners and identities:

```bash
docker compose exec api ss -lnt
docker compose exec api ps -eo pid,user:15,args
docker compose exec scan-guard iptables -n -L BRIDGE_LAB_SCAN
docker compose exec suricata tail -n 20 /var/log/suricata/eve.json
```

Expect API TCP 8000 and 2222; no TCP 2323. Ollama and its runner should be loopback
only. Verify SSH bypass and the paired scan trials on the actual Docker host before
classroom use. Unit tests verify policy decisions, not packet capture or firewall
behavior. The copied demo validation report is not evidence for this new variant.

No service uses host networking, `privileged: true`, host PID sharing, or the Docker
socket. The API is isolated; NET_ADMIN is granted to the chat startup process for
lab aliases and to the IDS/guard for their namespace-local duties. Stopping the
stack with `docker compose down` removes these namespaces and temporary rules.
