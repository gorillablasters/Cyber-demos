# IDS basics with Suricata

## Detection, prevention and response

An **intrusion detection system (IDS)** observes activity and reports patterns of
interest. A network IDS works from traffic it can see; a host-based detector works
from endpoint evidence such as processes or files. An **intrusion prevention system
(IPS)** can enforce decisions while traffic traverses its blocking path.

In this lab, Suricata is a passive network detector. A separate Python service,
`scan-guard`, reacts to its events by changing the API namespace's firewall.
Therefore, “Suricata alerted” and “the firewall blocked” are two observations to
verify separately. The demo version has neither component.

## What the sensor can see

Suricata shares the API network namespace and captures on `eth0`. It sees traffic
at that API interface, including student probes arriving from chat. It is not a
sensor for every packet on the host or every Docker network. In particular, the
API's local model calls use loopback, not the captured interface.

Encrypted SSH still exposes network metadata needed to observe a TCP scan:
addresses, ports, timing and TCP flags. That does not give the IDS plaintext SSH
commands. Also, a network connection from chat is not labelled with the student's
browser identity; several students can share that apparent source address.

## The two lab rules

The rules in [lab.rules](../lab-ver/ids/lab.rules) are intentionally small:

```text
alert tcp any any -> $HOME_NET any (msg:"LAB inbound SYN telemetry"; flags:S; flow:stateless; sid:1093301; rev:1;)
alert tcp any any -> $HOME_NET any (msg:"LAB possible port scan - SYN burst"; flags:S; flow:stateless; detection_filter:track by_src,count 12,seconds 3; sid:1093302; rev:1;)
```

| Part | Meaning |
| --- | --- |
| `alert tcp` | Generate an alert for matching TCP traffic |
| `any any -> $HOME_NET any` | Any source address/port toward the configured API address, on any port |
| `flags:S` | Match the rule's SYN-flag condition |
| `flow:stateless` | Do not require an established session for the match |
| `sid` | Stable rule identifier used to distinguish the two event types |
| `rev` | Revision of that rule |

SID **1093301** is telemetry for the guard; ordinary new connections can match it.
SID **1093302** is a possible-scan alert using a per-source 12-matches/3-seconds
filter. A detection filter produces alerts after its configured threshold is
reached; it does not count distinct destination ports by itself.
[Suricata thresholding reference](https://docs.suricata.io/en/suricata-8.0.0/rules/thresholding.html).

Neither rule proves that Nmap generated a packet. Neither detects an SSH
authentication bypass or Markdown prompt injection specifically. Those lessons
need application and endpoint evidence as well.

## EVE JSON: the observation record

Suricata's EVE output supports structured records such as alerts and protocol
events. This lab enables **only alert records**, writing one JSON event per line
to `/var/log/suricata/eve.json` on the shared `ids-logs` volume. It is not configured
as a full packet recording or complete traffic-history system.
[Suricata EVE reference](https://docs.suricata.io/en/suricata-8.0.0/output/eve/eve-json-output.html).

An abbreviated illustrative record, not a newly captured event:

```json
{
  "timestamp": "2026-09-17T10:00:00.000000-0500",
  "event_type": "alert",
  "src_ip": "172.30.109.10",
  "src_port": 41000,
  "dest_ip": "172.30.109.20",
  "dest_port": 2222,
  "proto": "TCP",
  "alert": {
    "signature_id": 1093301,
    "signature": "LAB inbound SYN telemetry"
  }
}
```

Use the timestamp to align events, `src_ip` to identify the apparent sender,
`dest_port` to see the probe target and `signature_id` to distinguish telemetry
from the burst alert. A source port is commonly the client's temporary port; it
is not the server port being scanned.

## The deliberately weak attribution policy

The guard consumes SID **1093301**, not the burst-alert SID. It accepts recent
IPv4 telemetry destined for the configured API and originating within the lab
subnet. That narrow scope is implemented in [guard.py](../lab-ver/ids/guard.py).

The separate [policy.py](../lab-ver/ids/policy.py) implements:

1. Count distinct destination ports seen from each source in a rolling 3-second
   window. Repeated connections to just port 8000 do not reach eight distinct ports.
2. At eight ports from a source, start a 0.5-second attribution grace period.
3. At decision time, if only one source meets the threshold, block its new TCP
   connections for 20 seconds.
4. If two or more apparent sources meet the threshold, emit `suppress` and withhold
   blocking for those scan bursts.
5. Remove a ban when it expires. Adding decoys after a ban starts does not cancel it.

The guard writes rules into `BRIDGE_LAB_SCAN`, reached from API's INPUT chain.
Rules match source IP and TCP connections in conntrack state `NEW`. Existing
established sessions are not deliberately targeted. The rule applies to new TCP
connections generally, so it can also interrupt chat-to-API HTTP.

| Traffic pattern | Suricata evidence | Intended guard response |
| --- | --- | --- |
| Normal connections to one destination port | SYN telemetry; a sufficiently intense burst may also alert | No distinct-port threshold, so no scan block |
| One source probes at least eight ports quickly | SYN telemetry and, for a sufficient burst, SID 1093302 | `block`, then `unblock` after expiry |
| Multiple sources each exceed the threshold together | Matching traffic from all apparent sources remains logged | `suppress`; no new ban for that burst |
| Decoys added during an existing ban | Matching decoy traffic can still be logged | Existing ban continues until expiry |

This teaches a flawed policy: uncertainty about who scanned is treated as a reason
to withhold a response. It is not a property of Suricata or a sound production
attribution method. Legitimate concurrent scanners could produce the same
suppression; many students behind one gateway can look like one source.

“Logs in both cases” means the policy does not intentionally silence Suricata
when decoys appear. It is not a guarantee of complete capture if the sensor is
down, overloaded, unable to write or observing the wrong interface.

## Instructor observation workflow

From `lab-ver`, inspect readiness before running the
[paired Nmap trials](04-nmap-port-discovery.md):

```sh
docker compose ps -a
docker compose logs --tail 30 suricata scan-guard
docker compose run --rm --no-deps suricata -T -c /rules/suricata.yaml
```

The current Compose entrypoint tries to change ownership of a file on the
read-only rules mount. If this fails, even the configuration-test command can stop
before Suricata runs. Check the actual error; do not interpret missing events as
successful evasion. The [current-source notes](02-architecture.md) distinguish
this configuration from the earlier successful test report.

During each scan, collect the sensor, policy and enforcement views:

```sh
docker compose exec suricata tail -n 30 /var/log/suricata/eve.json
docker compose logs --tail 30 scan-guard
docker compose exec scan-guard iptables -n -v -L BRIDGE_LAB_SCAN
```

`block` in a guard log records its action; packet counters and a failed new
connection provide stronger evidence that the rule affected traffic. `suppress`
plus EVE events demonstrates detection without that automatic response. For a
prepared stack, `python3 tests/verify_live.py` exercises these checks through the
real chat Telnet shell.

## Limits and review

Fast scans may discover a service before reactive enforcement. Slow scans can stay
below the thresholds. Packet loss, clock differences, stale events and log failures
can affect the response. A burst of normal connections can produce a scan-like
alert, while an unrecognized attack can produce no relevant alert. These are why
analysts correlate multiple evidence sources.

Review: What distinguishes IDS visibility from IPS enforcement? Why can a normal
SYN produce telemetry? Why are the sensor's 12-match filter and the guard's
eight-port threshold different? Why is an empty firewall chain insufficient
evidence that the network was quiet?
