# The Core Philosophy

Every stage follows the same loop (Erickson):

> **Observe → Infer → Hypothesize → Test → Exploit → Generalize**

The goal of the progression is not “get flag X”
The goal is: *“Ah — this is how systems really break.”*

---

# 🧠 Stage 0 — Orientation: “Everything Is a System”

### Player learns

**Skill:** *Reading systems, not instructions*

### What they see

* UI dashboard (world state)
* Events log
* Raw hex tools
* GS client

### Hidden lesson

* There is no “solve button”
* Logs are narrative, not hints
* Hex is first-class, not an afterthought

### Transferable skill

> *Comfort living inside an unfamiliar system without guidance.*

This is foundational for everything else.

---

# 🧩 Stage 1 — Addressing & Trust Boundaries

**FLAG{SATID_SPOOF_PWN}**

### Skill taught

**“Trust is often encoded in identifiers.”**

### Player behavior

* Notices SAT_ID in uplink frames
* Wonders what happens if it’s changed
* Tests `SAT_ID=0x00`

### System response

* Compatibility routing
* Logs reveal “SPOOF-ACCEPT”

### What they learn

* IDs are often *policy*
* “Legacy” == “attack surface”
* Special values matter

### Transferability

* Network addressing
* Device IDs
* User IDs
* Session IDs
* Routing tables

This prepares them for **all identity-based attacks later**.

---

# 🔁 Stage 2 — Time, State & Replay

**FLAG{REPLAY_THAT_SLAPS}**

### Skill taught

**“Detection ≠ enforcement.”**

### Player behavior

* Sees sequence numbers
* Replays a command
* Notices it still executes

### System response

* Logs replay
* Allows execution anyway

### What they learn

* State machines are brittle
* Security features are often cosmetic
* Logs are not guards

### Transferability

* API replay attacks
* Token reuse
* CSRF nonces
* Message queues

This primes them to **never assume “detected” means “blocked.”**

---

# 📡 Stage 3 — Observation as Power

**FLAG{SNIFFED_THROUGH_THE_MASK}**

### Skill taught

**“Visibility is an exploit primitive.”**

### Player behavior

* Notices debug-enabled satellite
* Sees traffic it shouldn’t receive

### System response

* Logs “DEBUG_SNIFF”
* Reveals crosslink traffic

### What they learn

* Debug paths bypass controls
* Observability is often privileged
* Passive access can be decisive

### Transferability

* Packet captures
* Logs-as-leaks
* Metrics endpoints
* Debug interfaces

This skill is **required** for the crypto exploit later.

---

# 🔐 Stage 4 — Cryptography as a State Machine

**FLAG{CROSSLINK_CRYPTO_PWN}**

### Skill taught

**“Crypto fails at the boundaries, not the math.”**

### Player behavior

* Observes encrypted crosslink packets
* Notices nonce reuse on retransmit
* Triggers retransmit via ACK/NAK spoofing
* XORs ciphertexts

### System response

* Nonce reuse logged
* Secure command accepted

### What they learn

* Stream cipher invariants
* Why nonces exist
* How retransmission breaks assumptions

### Transferability

* TLS nonce reuse
* WEP-style attacks
* CTR/GCM misuse
* Rolling keys

This is a **core Erickson chapter brought to life**.

---

# 🌍 Stage 5 — Physical Constraints as Attack Surface

**FLAG{ATTENUATION_AND_ELATION}**

### Skill taught

**“The environment is part of the system.”**

### Player behavior

* Adjusts RAAN and power
* Sees RF links break
* Observes fallback behaviors

### System response

* RF_BLOCK logs
* Alternate paths and leaks

### What they learn

* Systems react to physics
* Failures cause mode switches
* Topology changes behavior

### Transferability

* Wireless attacks
* Fault injection
* Power analysis
* Network partitioning

This teaches **systems thinking beyond software**.

---

# 🌡️ Stage 6 — Fault Paths Are Different Code

**FLAG{TOO_HOT_TO_HANDLE}**

### Skill taught

**“Error paths are attack paths.”**

### Player behavior

* Pushes temp out of bounds
* Observes fault mode
* Notices behavior changes

### System response

* Mode forced SAFE
* Telemetry changes
* Debug leakage increases

### What they learn

* Safety systems override normal rules
* Fault handling is rarely hardened
* Failures expose internals

### Transferability

* Crash handling
* Exception paths
* Watchdogs
* Fail-open logic

This prepares them for **confused deputy attacks**.

---

# 📥 Stage 7 — Parsing & Ambiguity

**Downlink Compression Bug**

### Skill taught

**“Boundaries are everything.”**

### Player behavior

* Sees compressed telemetry
* Notices zlib framing
* Observes strange TLVs after decompression

### System response

* GS parses `unused_data`
* Last-write-wins TLVs

### What they learn

* Compression formats leak structure
* Parsers make assumptions
* Ambiguity is exploitable

### Transferability

* File format exploits
* ZIP bombs
* Protocol smuggling
* Request smuggling

This is a **pure parser exploitation lesson**.

---

# 🤖 Stage 8 — Confused Deputy

**Chain exploit → FINAL_FLAG**

### Skill taught

**“Make the system attack itself.”**

### Player behavior

* Lies via downlink
* GS believes fault state
* GS auto-sends privileged commands

### System response

* Autopilot uplinks
* Crosslink compromise spreads
* Final beacon unlocks

### What they learn

* Authority ≠ origin
* Automation magnifies mistakes
* Control planes are dangerous

### Transferability

* Cloud IAM confusion
* CI/CD pipeline abuse
* Monitoring-driven automation
* SOC tooling exploits

This is the **capstone skill**.

---

# 🎓 What the Player Walks Away With

After finishing your sim, a player has *implicitly learned*:

* Protocol analysis
* Wire-level reasoning
* Crypto invariants
* State machine attacks
* Parser exploitation
* Physical + logical interaction
* Confused deputy exploitation

And most importantly:

> **Hacking is not about bugs.
> It’s about understanding systems well enough to misuse them creatively.**