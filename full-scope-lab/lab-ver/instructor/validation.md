# Lab-ver validation status

This variant replaces the copied demo topology. The old demo's live-test results
must not be applied to this SSH/IDS setup.

Verified September 15, 2026 (America/Chicago; September 16 UTC), on Docker Desktop.

## Fixes verified

- Built all three lab images successfully. The libssh stage uses signed Debian
  snapshot packages because live Bullseye security package URLs returned 404.
- Suricata repairs ownership of its log volume and bundled configuration before
  starting. Both startup and `suricata -T` pass without permission errors.
- Removed the attempted guard-image chmod: that directory does not exist during
  its build, and the guard only mounts the runtime log volume read-only.

## Observed live results

- All four services running; all 14 unit/HTTP tests pass; Compose config validates.
- Through host Telnet port 2324, the shell reports `uid=10001(student)`.
- From that shell, API `2222/tcp open` and `2323/tcp closed`.
- The cloned historical libssh teaching endpoint returns `labssh`, UID 10004,
  through the supplied teaching client. API `server.py` and Ollama run as
  `labapi`, UID 10003.
- API has no published ports, attaches only to the internal private network,
  and has no default route. Model listeners bind to loopback. Docker host
  administrators remain outside the student segmentation model.
- A paced single-source SYN scan produces `block` for `172.30.109.10`.
  A subsequent SSH connection probe times out; the DROP rule recorded 32 packets
  in this trial. `unblock` follows after the 20-second ban.
- With decoys `.11` and `.12`, the same scan reports SSH open, logs `suppress`
  for all three sources, and leaves no DROP rule. EVE contains telemetry SID
  1093301 and scan-alert SID 1093302 for each apparent source.
- Live HTTP upload: `blocked.md` rejected with HTTP 400; `code-block.md`
  accepted. Asking for chat-server ports using that reference returned
  `8000, 2323`. The parser and model policy were unchanged. Future model outputs
  remain probabilistic.

Repeat the network trials with `python3 tests/verify_live.py` from `lab-ver`.
It requires a ready stack and no concurrent scans, and temporarily blocks new
chat-to-API connections. The parser/session tests run with
`python3 -m unittest discover -s tests -v`.

Process injection remains outside this task.
