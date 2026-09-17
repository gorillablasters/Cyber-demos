# Port discovery with Nmap

## Learning objective

Use Nmap to determine which **assigned lab** TCP ports appear reachable, interpret
the results and explain how viewpoint and filtering change them. Discovery is
evidence gathering; it is not proof that a service is vulnerable or that access
has been obtained.

A default Nmap invocation usually checks 1,000 common TCP ports, not every port.
Explicit `-p` selections make this lesson reproducible.
[Nmap tutorial](https://nmap.org/book/port-scanning-tutorial.html).

## Start with the network viewpoint

From the host, you see chat's published loopback ports. From the chat shell, you
can reach the private API. `localhost` always means the current network namespace,
so scanning it inside chat will not scan API.

In a host terminal, choose the version you are using:

```sh
# demo-ver: provided environment settings
nmap -sT -n -Pn -p 8080,2323 127.0.0.1

# lab-ver: provided environment settings
nmap -sT -n -Pn -p 8081,2324 127.0.0.1
```

Check custom mappings with `docker compose port chat 2323` from that version's
directory. The current lab Compose fallback differs from its environment example;
the [architecture notes](02-architecture.md) explain this.

After connecting to chat Telnet, investigate from that shell:

```sh
ip route
ip neigh
netstat -at
```

Routes reveal connected networks; neighbor entries reveal recently resolved local
peers; connection listings may reveal API traffic during or after a chat request.
An empty neighbor table does not prove there are no other hosts. The demo API
address is dynamic. The lab's default API address is `172.30.109.20`.

## Read the command before running it

| Option | Meaning in this lesson |
| --- | --- |
| `-sT` | TCP connect scan: uses the operating system's connection calls |
| `-sS` | TCP SYN scan: sends raw SYN probes without completing a normal application connection |
| `-n` | Avoid reverse-DNS lookups |
| `-Pn` | Skip host discovery and try the requested port scan; it does not prove the host is up |
| `-p 2222,2323` | Scan exactly those TCP ports |
| `-sV` | Send additional probes to identify services and versions |
| `-r` | Visit selected ports in numerical order |
| `--scan-delay 100ms` | Pace probes to the host for this comparison |
| `--max-retries 0` | Do not retry unanswered probes; loss can therefore affect results |

SYN scans need raw-packet privileges. The lab chat console supplies `NET_RAW` and
sets `NMAP_PRIVILEGED=1`; this does not make the shell root. The demo does not grant
the same capability, so use `-sT` there. A SYN scan is visible to suitable sensors;
the word “stealth” is not an invisibility guarantee.
[Nmap scan techniques](https://nmap.org/book/man-port-scanning-techniques.html).

## Discover the private API services

Run these from the **chat Telnet shell**, using the version you are studying:

```sh
# Demo: the service name resolves on its private Docker network.
nmap -sT -n -Pn -p 8000,2323 api

# Lab: substitute your assigned API address if customized.
nmap -sT -n -Pn -p 8000,2222,2323 172.30.109.20
```

With the intended services running and no active ban, expect demo ports 8000 and
2323 open. Expect lab ports 8000 and 2222 open, with 2323 closed. These are
expectations to verify, not results newly measured by this guide.

| Nmap state | Interpretation from your scan location |
| --- | --- |
| `open` | A service accepts connections or produces the scan's open-port response |
| `closed` | The host responds but no service accepts that port |
| `filtered` | Filtering or another obstacle prevents determining whether a listener exists |
| `unfiltered` | The port responds to the chosen probe, but open/closed is unresolved |
| `open\|filtered` | The probe results cannot distinguish those two states |
| `closed\|filtered` | The probe results cannot distinguish those two states |

The state describes an observation, not an unchanging property of a port.
[Nmap port states](https://nmap.org/book/man-port-scanning-basics.html).

Without service detection, the `SERVICE` column can be a port-number lookup.
For example, this lab's SSH on 2222 may be labelled `EtherNetIP-1`. Investigate
with a narrow follow-up such as:

```sh
nmap -sT -sV -n -Pn -p 2222 172.30.109.20
```

Version detection supplies more evidence, but banners can be misleading and a
reported version alone does not prove exploitability.
[Nmap service/version detection](https://nmap.org/book/man-version-detection.html).

## Controlled single-source and decoy comparison

This exercise applies only to **lab-ver**, with Suricata and scan-guard running.
Perform it without concurrent student scans, which would change the apparent
source count. The [IDS guide](05-ids-and-suricata.md) explains the policy.

From chat Telnet, run:

```sh
nmap -sS -n -Pn -r --scan-delay 100ms --max-retries 0 -p 1-40,2222 172.30.109.20
```

In the instructor's `lab-ver` terminal, inspect the independent evidence:

```sh
docker compose logs --tail 30 scan-guard
docker compose exec scan-guard iptables -n -v -L BRIDGE_LAB_SCAN
docker compose exec suricata tail -n 20 /var/log/suricata/eve.json
```

Expect a temporary source block after the threshold and grace period. Early ports
may be discovered before the response. Nmap may group filtered ports in its summary
instead of listing port 2222 individually. The same ban can temporarily interrupt
new chatbot requests to API.

Wait for `unblock` and allow a few seconds for old scan observations to age out.
Then, from chat Telnet, use only the configured lab decoys:

```sh
nmap -sS -n -Pn -r --scan-delay 100ms --max-retries 0 -D 172.30.109.11,172.30.109.12,ME -p 1-40,2222 172.30.109.20
```

`ME` positions the real source among the decoy probes. Decoys add apparent sources;
they do not make packets disappear. Nmap's decoys do not apply to TCP connect
scanning or version detection. Here they exploit the lab's deliberately weak
response policy, which should log `suppress` and leave SSH reachable.
[Nmap decoy documentation](https://nmap.org/book/man-bypass-firewalls-ids.html).

## Record and interpret results

For each trial, record time, scan location, target, options, port states, Suricata
SID/source fields and the guard action. If a result differs, check service startup,
the assigned address, current bans, capability availability and sensor logs before
concluding that detection was bypassed. Fast scans can finish before a reactive
block; slow probes can stay below this policy's threshold.

Review: Why can the same port appear open and later filtered? Why does a service
label not identify a vulnerability? Why do decoys change the guard's decision
without preventing Suricata from recording the scan?
