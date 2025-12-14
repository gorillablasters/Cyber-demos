from __future__ import annotations

import time
import zlib
import hashlib
from dataclasses import dataclass, field, asdict
from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Random import get_random_bytes
from typing import Dict, List, Literal, Optional, Set, Any


SYNC = b"\xd0\x0d"
TYPE_CMD = 0x01
TYPE_TLM = 0x02

SAT_ID_D00M_01 = 0x01
SAT_ID_D00M_02 = 0x02
SAT_ID_K00KIES_01 = 0x11
SAT_ID_K00KIES_02 = 0x12

SAT_ID_TO_NAME: Dict[int, str] = {
    SAT_ID_D00M_01: "D00M-01",
    SAT_ID_D00M_02: "D00M-02",
    SAT_ID_K00KIES_01: "K00KIES-01",
    SAT_ID_K00KIES_02: "K00KIES-02",
}

FINAL_FLAG = "FLAG{MF_DOOM_CONTROLS_ORBIT}"

REQUIRED_FLAGS: Set[str] = {
    "FLAG{SATID_SPOOF_PWN}",
    "FLAG{CROSSLINK_CRYPTO_PWN}",
    "FLAG{SNIFFED_THROUGH_THE_MASK}",
    "FLAG{FIRMWARE_BACKDOOR_ON_ORBIT}",
    "FLAG{ATTENUATION_AND_ELATION}",
    "FLAG{TOO_HOT_TO_HANDLE}",
    "FLAG{REPLAY_THAT_SLAPS}",
    "FLAG{RAAN_TILTED_THE_SCALE}",
}

Mode = Literal["SAFE", "NOMINAL", "SCIENCE", "DIAGNOSTIC"]


def crc16(data: bytes) -> int:
    """CRC-16 using zlib CRC32 truncated to 16 bits."""
    return zlib.crc32(data) & 0xFFFF


def xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


@dataclass
class Orbit:
    semi_major_km: float
    inclination_deg: float
    raan_deg: float


@dataclass
class CrosslinkFrame:
    src_sat_id: int
    dst_sat_id: Optional[int]
    payload: bytes
    timestamp: float


@dataclass
class Satellite:
    sat_id: int
    name: str

    mode: Mode = "SAFE"
    power_level: int = 100  # %
    temp_c: float = 10.0
    orbit: Orbit = field(default_factory=lambda: Orbit(700.0, 98.0, 0.0))
    sequence_counter: int = 0
    last_contact_unix: float = field(default_factory=time.time)
    last_tx_nonce: int = 0

    compromised: bool = False
    flags: Dict[str, str] = field(default_factory=dict)

    faulted: bool = False

    downlink_queue: List[bytes] = field(default_factory=list)
    rf_neighbors: Set[int] = field(default_factory=set)
    debug_rx_all: bool = False
    crosslink_inbox: List[CrosslinkFrame] = field(default_factory=list)
    crosslink_key: bytes = b""
    crosslink_crypto: bool = False
    crosslink_nonce: int = 0

    firmware_version: str = "1.0.0"
    firmware_bank: bytes = b""
    firmware_active_hash: str = ""
    allow_unsigned_fw: bool = False
    fw_sig_prefix_len: int = 64

    beacon_ciphertext: bytes = b""
    beacon_key: bytes = b""
    beacon_plaintext: str = ""
    flag_beacon: bool = False

    recent_seqs: List[int] = field(default_factory=list)

    def next_seq(self) -> int:
        self.sequence_counter = (self.sequence_counter + 1) & 0xFFFF
        return self.sequence_counter

    def touch(self) -> None:
        self.last_contact_unix = time.time()

    def to_public_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("downlink_queue", None)
        d.pop("crosslink_inbox", None)
        d.pop("firmware_bank", None)
        d.pop("recent_seqs", None)

        d.pop("crosslink_key", None)
        d.pop("beacon_key", None)
        d.pop("beacon_plaintext", None)
        d.pop("beacon_ciphertext", None)

        d["flag_beacon_message"] = self.get_flag_beacon_message()

        return d

    @staticmethod
    def encrypt_beacon_flag(plaintext: str, key: bytes) -> bytes:
        cipher = ChaCha20_Poly1305.new(key=key)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
        return cipher.nonce + tag + ciphertext

    @staticmethod
    def decrypt_beacon_flag(data: bytes, key: bytes) -> str:
        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext.decode("utf-8")

    def init_beacon(self, plaintext: str, key: bytes) -> None:
        self.beacon_key = key
        self.beacon_plaintext = plaintext
        self.beacon_ciphertext = self.encrypt_beacon_flag(plaintext, key)

    def get_flag_beacon_message(self) -> str:
        if not self.beacon_ciphertext:
            return "[BEACON] (no beacon configured)"
        if self.flag_beacon:
            try:
                return "[BEACON] " + self.decrypt_beacon_flag(
                    self.beacon_ciphertext, self.beacon_key
                )
            except Exception:
                return "[BEACON] (decrypt error)"
        return "[BEACON] " + self.beacon_ciphertext.hex()


@dataclass
class GroundStation:
    name: str = "DOOMSTATION-PRIME"
    last_contact_unix: float = field(default_factory=time.time)


class World:
    """
    Multi-satellite constellation + crosslink bus + firmware surface.
    Exposed to FastAPI as WORLD.
    """

    def __init__(self) -> None:
        self.gs = GroundStation()
        self.sats: Dict[int, Satellite] = {}
        self.crosslink_log: List[CrosslinkFrame] = []
        self.events: List[Dict[str, Any]] = []
        self._init_sats()
        self.final_emitted: bool = False

    def _all_flag_keys(self) -> Set[str]:
        out: Set[str] = set()
        for s in self.sats.values():
            out.update(s.flags.keys())
        return out

    def _maybe_emit_final(self) -> None:
        if self.final_emitted:
            return

        all_flags = self._all_flag_keys()
        all_compromised = all(s.compromised for s in self.sats.values())

        if all_compromised and REQUIRED_FLAGS.issubset(all_flags):
            self.final_emitted = True
            self._log("world", None, f"FINAL: {FINAL_FLAG}")

            for s in self.sats.values():
                s.flag_beacon = True

    def _log(self, type_: str, sat_id: Optional[int], detail: str) -> None:
        self.events.append(
            {"ts": time.time(), "type": type_, "sat_id": sat_id, "detail": detail}
        )
        if len(self.events) > 2000:
            self.events = self.events[-1000:]

    def _init_sats(self) -> None:
        doom01 = self._add_sat(SAT_ID_D00M_01, Orbit(700.0, 98.0, 10.0))
        doom02 = self._add_sat(SAT_ID_D00M_02, Orbit(705.0, 97.5, 20.0))
        cookies01 = self._add_sat(SAT_ID_K00KIES_01, Orbit(710.0, 97.9, 30.0))
        cookies02 = self._add_sat(SAT_ID_K00KIES_02, Orbit(715.0, 98.1, 40.0))

        beacon_master = hashlib.sha256(b"DOOMSTATION_PRIME_BEACON_KEY").digest()
        doom01.init_beacon(
            plaintext="FLAG{CROSSLINK_CRYPTO_PWN}",
            key=beacon_master,
        )
        doom02.init_beacon(
            plaintext="FLAG{CROSSLINK_CRYPTO_PWN}",
            key=beacon_master,
        )
        cookies01.init_beacon(
            plaintext="FLAG{CROSSLINK_CRYPTO_PWN}",
            key=beacon_master,
        )
        cookies02.init_beacon(
            plaintext="FLAG{CROSSLINK_CRYPTO_PWN}",
            key=beacon_master,
        )

        doom01.rf_neighbors.update({SAT_ID_D00M_02})
        doom02.rf_neighbors.update({SAT_ID_D00M_01, SAT_ID_K00KIES_01})
        cookies01.rf_neighbors.update({SAT_ID_D00M_02, SAT_ID_K00KIES_02})
        cookies02.rf_neighbors.update({SAT_ID_K00KIES_01})

        cookies01.debug_rx_all = True

        doom01.crosslink_key = b"D00M01_KEY"
        doom02.crosslink_key = b"D00M02_KEY"
        cookies01.crosslink_key = b"K00KIES01_KEY"
        cookies02.crosslink_key = b"K00KIES02_KEY"

        doom02.crosslink_crypto = True

        cookies02.fw_sig_prefix_len = 8

    def _add_sat(self, sat_id: int, orbit: Orbit) -> Satellite:
        name = SAT_ID_TO_NAME.get(sat_id, f"SAT-0x{sat_id:02X}")
        sat = Satellite(sat_id=sat_id, name=name, orbit=orbit)
        self.sats[sat_id] = sat
        return sat

    def world_status(self) -> Dict[str, Any]:
        return {
            "groundstation": {
                "name": self.gs.name,
                "last_contact_unix": self.gs.last_contact_unix,
            },
            "satellites": [s.to_public_dict() for s in self.sats.values()],
        }

    def handle_uplink_frame(self, frame: bytes) -> Dict[str, Any]:
        try:
            parsed = parse_frame(frame)
        except ValueError as e:
            self._log("uplink", None, f"reject: {e}")
            return {"ok": False, "error": str(e)}

        if parsed.type != TYPE_CMD:
            self._log("uplink", parsed.sat_id, "reject: non-CMD frame")
            return {"ok": False, "error": "uplink frame is not a CMD frame"}

        sat = self.sats.get(parsed.sat_id)
        if sat is None:
            if parsed.sat_id == 0x00:
                sat = self.sats.get(SAT_ID_D00M_02)
                if sat is not None:
                    sat.compromised = True
                    sat.flags["FLAG{SATID_SPOOF_PWN}"] = (
                        "SAT_ID 0x00 spoofed to D00M-02"
                    )
                    self._log(
                        "uplink",
                        sat.sat_id,
                        "SPOOF-ACCEPT SAT_ID=00 routed to D00M-02",
                    )
            if sat is None:
                self._log("uplink", parsed.sat_id, "reject: unknown sat")
                return {"ok": False, "error": f"unknown SAT_ID: 0x{parsed.sat_id:02X}"}

        if parsed.seq in sat.recent_seqs:
            sat.flags["FLAG{REPLAY_THAT_SLAPS}"] = "Replay accepted despite detection"
            self._log(
                "uplink",
                sat.sat_id,
                f"REPLAY_DETECTED seq={parsed.seq}",
            )
        sat.recent_seqs.append(parsed.seq)
        if len(sat.recent_seqs) > 32:
            sat.recent_seqs = sat.recent_seqs[-32:]

        sat.touch()
        self.gs.last_contact_unix = time.time()

        resp = self._apply_command(sat, parsed)

        tlm = build_tlm_frame(sat)
        sat.downlink_queue.append(tlm)

        self._log("uplink", sat.sat_id, resp)
        self._maybe_emit_final()
        return {
            "ok": True,
            "satellite": sat.to_public_dict(),
            "response_text": resp,
            "tlm_frame_hex": tlm.hex(),
        }

    def _apply_command(self, sat: Satellite, parsed: "ParsedFrame") -> str:
        if sat.sat_id != parsed.sat_id and parsed.sat_id != 0x00:
            return f"[DOOMLINK] Invalid SAT_ID for {sat.name}."

        payload = parsed.payload
        if not payload:
            return "[DOOMLINK] Empty command payload ignored."

        cmd_id = payload[0]
        args = payload[1:]

        if cmd_id == 0x20:
            sat.compromised = True
            sat.flag_beacon = True
            sat.flags["FLAG{CROSSLINK_CRYPTO_PWN}"] = (
                "Secure crosslink command executed via crypto weakness"
            )
            return (
                f"[DOOMLINK] {sat.name} secure crosslink operation accepted (uplink)."
            )

        if cmd_id == 0x01:
            if not args:
                return "[DOOMLINK] SET_MODE missing argument."
            mode_map: Dict[int, Mode] = {
                0: "SAFE",
                1: "NOMINAL",
                2: "SCIENCE",
                3: "DIAGNOSTIC",
            }
            mode = mode_map.get(args[0])
            if mode is None:
                return f"[DOOMLINK] Invalid mode value: {args[0]}"
            sat.mode = mode
            return f"[DOOMLINK] {sat.name} mode set to {sat.mode}."

        if cmd_id == 0x02:
            if not args:
                return "[DOOMLINK] NUDGE_POWER missing argument."
            delta = int.from_bytes(args[:1], "big", signed=True)
            sat.power_level = max(0, min(100, sat.power_level + delta))
            return f"[DOOMLINK] {sat.name} power level adjusted to {sat.power_level}%."

        if cmd_id == 0x03:
            if not args:
                return "[DOOMLINK] TEMP_CAL_OFFSET missing argument."
            delta = int.from_bytes(args[:1], "big", signed=True)
            sat.temp_c += float(delta)
            if abs(sat.temp_c) > 150.0:
                sat.faulted = True
                sat.mode = "SAFE"
                sat.flags["FLAG{TOO_HOT_TO_HANDLE}"] = (
                    f"{sat.name} telemetry temp overflow triggered"
                )

                self._log(
                    "fault",
                    sat.sat_id,
                    f"THERMAL_OVERFLOW temp={sat.temp_c:.1f}C",
                )
            return f"[DOOMLINK] {sat.name} temp offset applied, now {sat.temp_c:.1f} C."

        if cmd_id == 0x04:
            if not args:
                return "[DOOMLINK] DRIFT_RAAN missing argument."
            delta = int(args[0])
            sat.orbit.raan_deg = (sat.orbit.raan_deg + float(delta)) % 360.0
            self._log(
                "orbit",
                sat.sat_id,
                f"DRIFT_RAAN delta={delta} new={sat.orbit.raan_deg:.1f}",
            )
            sat.flags["FLAG{RAAN_TILTED_THE_SCALE}"] = (
                f"RAAN drift applied delta={delta}"
            )
            return f"[DOOMLINK] {sat.name} orbit RAAN adjusted."

        if cmd_id == 0x10:
            if len(args) < 2:
                return "[DOOMLINK] SEND_CROSSLINK requires dst_sat_id and length."
            dst_sat_id = args[0]
            plen = args[1]
            if len(args) < 2 + plen:
                return "[DOOMLINK] SEND_CROSSLINK payload length mismatch."
            cl_payload = bytes(args[2 : 2 + plen])
            self.send_crosslink(
                src_sat_id=sat.sat_id,
                dst_sat_id=dst_sat_id,
                payload=cl_payload,
            )
            return f"[DOOMLINK] {sat.name} sent crosslink to 0x{dst_sat_id:02X}."

        if cmd_id == 0x11:
            n = len(sat.crosslink_inbox)
            return f"[DOOMLINK] {sat.name} has {n} crosslink frame(s) in inbox."

        return f"[DOOMLINK] Unknown CMD_ID 0x{cmd_id:02X} for {sat.name}."

    def pop_downlink(
        self,
        sat_id: Optional[int] = None,
        max_frames: int = 10,
    ) -> List[str]:
        frames: List[bytes] = []
        if sat_id is None:
            for s in self.sats.values():
                while s.downlink_queue and len(frames) < max_frames:
                    frames.append(s.downlink_queue.pop(0))
        else:
            sat = self.sats.get(sat_id)
            if sat is None:
                return []
            while sat.downlink_queue and len(frames) < max_frames:
                frames.append(sat.downlink_queue.pop(0))

        for b in frames:
            self._log("downlink", sat_id, f"TLM {b.hex()}")

        return [f.hex() for f in frames]

    def _rf_visible(self, src: Satellite, dst: Satellite) -> bool:
        """
        Super simplified RF model:
        - require some minimum power on src/dst
        - require RAAN alignment within ~120 degrees
        """
        if src.power_level < 20 or dst.power_level < 10:
            return False

        d = abs(src.orbit.raan_deg - dst.orbit.raan_deg)
        d = min(d, 360.0 - d)
        if d > 120.0:
            return False

        return True

    def send_crosslink(
        self,
        src_sat_id: int,
        dst_sat_id: Optional[int],
        payload: bytes,
    ) -> None:
        src_sat = self.sats.get(src_sat_id)
        if src_sat is None:
            return

        plain = payload
        bus_payload = plain

        # "Secure" crosslink for D00M-02: XOR stream cipher with debug leak.
        if src_sat.crosslink_crypto and src_sat.crosslink_key:
            # BUG: nonce reuse under crosslink congestion
            if len(self.crosslink_log) % 7 != 0:
                src_sat.crosslink_nonce = (src_sat.crosslink_nonce + 1) & 0xFFFF
            else:
                self._log(
                    "crosslink",
                    src_sat_id,
                    f"NONCE_REUSE BUG triggered nonce={src_sat.crosslink_nonce}",
                )

            src_sat.last_tx_nonce = src_sat.crosslink_nonce
            nonce_bytes = src_sat.crosslink_nonce.to_bytes(2, "little")
            keystream = hashlib.sha256(src_sat.crosslink_key + nonce_bytes).digest()
            bus_payload = xor_bytes(plain, keystream[: len(plain)])

            # VULN: log both plaintext and ciphertext for debugging
            self._log(
                "crosslink",
                src_sat_id,
                f"ENC src=0x{src_sat_id:02X} "
                f"dst={'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'} "
                f"nonce={src_sat.crosslink_nonce} plain={plain.hex()} cipher={bus_payload.hex()}",
            )
        else:
            self._log(
                "crosslink",
                src_sat_id,
                f"PLAIN src=0x{src_sat_id:02X} "
                f"dst={'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'} "
                f"len={len(plain)}",
            )

        frame = CrosslinkFrame(
            src_sat_id=src_sat_id,
            dst_sat_id=dst_sat_id,
            payload=bus_payload,
            timestamp=time.time(),
        )
        self.crosslink_log.append(frame)

        # Deliver over RF to neighbors / dest / debug listeners
        for sid, sat in self.sats.items():
            if sid == src_sat_id:
                continue

            delivered = False

            # direct dest
            if dst_sat_id is not None and sid == dst_sat_id:
                delivered = True

            # broadcast to RF neighbors
            if dst_sat_id is None and src_sat_id in sat.rf_neighbors:
                delivered = True

            # unicast but also leaked to RF neighbors (bus leakage)
            if dst_sat_id is not None and src_sat_id in sat.rf_neighbors:
                delivered = True

            # debug sniffer hears all regardless of RF attenuation
            if sat.debug_rx_all:
                is_direct = dst_sat_id is not None and sat.sat_id == dst_sat_id
                is_bcast = dst_sat_id is None and src_sat_id in sat.rf_neighbors
                if not is_direct and not is_bcast:
                    self._log(
                        "crosslink",
                        sat.sat_id,
                        f"DEBUG_SNIFF src=0x{src_sat_id:02X} dst="
                        f"{'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'}",
                    )
                    sat.flags["FLAG{SNIFFED_THROUGH_THE_MASK}"] = (
                        "debug_rx_all captured crosslink leakage"
                    )
                delivered = True

            # apply RF visibility only for "normal" deliveries
            if delivered and not sat.debug_rx_all:
                if not self._rf_visible(src_sat, sat):
                    sat.flags["FLAG{ATTENUATION_AND_ELATION}"] = (
                        "RF blockage due to power/orbit"
                    )
                    self._log(
                        "crosslink",
                        sat.sat_id,
                        f"RF_BLOCK src=0x{src_sat_id:02X} dst=0x{sid:02X}",
                    )
                    delivered = False

            if not delivered:
                continue

            # Deliver frame
            sat.crosslink_inbox.append(frame)

            # If SRC uses crypto, RECEIVER can try to decrypt using SRC key.
            if src_sat.crosslink_crypto and src_sat.crosslink_key:
                nonce_bytes = src_sat.crosslink_nonce.to_bytes(2, "little")
                keystream = hashlib.sha256(src_sat.crosslink_key + nonce_bytes).digest()
                decrypted = xor_bytes(frame.payload, keystream[: len(frame.payload)])
            else:
                decrypted = frame.payload

            if sat.sat_id == SAT_ID_D00M_02 and sat.crosslink_key:
                nb = sat.last_tx_nonce.to_bytes(2, "little")
                ks = hashlib.sha256(sat.crosslink_key + nb).digest()
                fallback = xor_bytes(frame.payload, ks[: len(frame.payload)])

                if fallback and fallback[0] in (
                    0x01,
                    0x02,
                    0x03,
                    0x04,
                    0x10,
                    0x11,
                    0x20,
                ):
                    decrypted = fallback
                    self._log(
                        "crosslink",
                        sat.sat_id,
                        f"FALLBACK_DECRYPT nonce={sat.last_tx_nonce} ok=1",
                    )
            # SECURE_XLINK command: decrypted payload starting with 0x20
            if decrypted and decrypted[0] == 0x20:
                sat.compromised = True
                sat.flag_beacon = True
                sat.flags["SECURE_XLINK_EXEC"] = (
                    "Decrypted CMD 0x20 executed via crosslink"
                )
                self._log("crosslink", sid, f"SECURE_XLINK on {sat.name}")

        # --- Hidden flag beacon emission -------------------------------------
        for sat in self.sats.values():
            if sat.flag_beacon:
                beacon_hex = sat.get_flag_beacon_message().encode().hex()
                self._log("crosslink", sat.sat_id, f"BEACON: {beacon_hex}")
        self._maybe_emit_final()

    def dump_crosslink_inbox(
        self,
        sat_id: int,
        max_frames: int = 20,
    ) -> Dict[str, Any]:
        sat = self.sats.get(sat_id)
        if sat is None:
            return {"ok": False, "error": f"unknown SAT_ID: 0x{sat_id:02X}"}
        frames = sat.crosslink_inbox[:max_frames]
        out = []
        for f in frames:
            out.append(
                {
                    "src_sat_id": f.src_sat_id,
                    "dst_sat_id": f.dst_sat_id,
                    "payload_hex": f.payload.hex(),
                    "timestamp": f.timestamp,
                }
            )
        return {"ok": True, "count": len(frames), "frames": out}

    # --- events API helper --------------------------------------------------

    def get_events(
        self,
        since: Optional[float] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        evs = self.events
        if since is not None:
            evs = [e for e in evs if e["ts"] > since]
        if limit:
            evs = evs[-limit:]
        return {"ok": True, "events": evs}

    # --- firmware surface ---------------------------------------------------

    def firmware_status(self, sat_id: int) -> Dict[str, Any]:
        sat = self.sats.get(sat_id)
        if sat is None:
            return {"ok": False, "error": "unknown sat"}
        return {
            "ok": True,
            "sat_id": sat_id,
            "version": sat.firmware_version,
            "bank_len": len(sat.firmware_bank),
            "active_hash": sat.firmware_active_hash,
            "allow_unsigned": sat.allow_unsigned_fw,
            "sig_prefix_len": sat.fw_sig_prefix_len,
            "compromised": sat.compromised,
            "faulted": sat.faulted,
            "flags": sat.flags,
        }

    def firmware_upload_chunk(self, sat_id: int, chunk: bytes) -> Dict[str, Any]:
        sat = self.sats.get(sat_id)
        if sat is None:
            return {"ok": False, "error": "unknown sat"}
        sat.firmware_bank += chunk
        self._log(
            "firmware",
            sat_id,
            f"upload_chunk len={len(chunk)} total={len(sat.firmware_bank)}",
        )
        return {"ok": True, "total_len": len(sat.firmware_bank)}

    def firmware_apply(self, sat_id: int, claimed_hash: str) -> Dict[str, Any]:
        sat = self.sats.get(sat_id)
        if sat is None:
            return {"ok": False, "error": "unknown sat"}

        data = sat.firmware_bank
        if not data:
            return {"ok": False, "error": "no firmware staged"}

        real_hash = hashlib.sha256(data).hexdigest()

        if not sat.allow_unsigned_fw:
            need_prefix = real_hash[: sat.fw_sig_prefix_len]
            if not claimed_hash.startswith(need_prefix):
                self._log("firmware", sat_id, "apply rejected: bad signature")
                return {"ok": False, "error": "invalid firmware signature"}
        else:
            # misconfig: accepts anything
            self._log("firmware", sat_id, "apply with unsigned firmware")

        # Apply firmware
        sat.firmware_version = f"custom-{int(time.time())}"
        sat.firmware_active_hash = real_hash

        # Backdoor: if firmware begins with magic, mark compromised and set a flag.
        if data.startswith(b"DOOMFW!!"):
            sat.compromised = True
            sat.flag_beacon = True
            sat.flags["FLAG{FIRMWARE_BACKDOOR_ON_ORBIT}"] = (
                f"{sat.name} firmware backdoor triggered"
            )

        self._log(
            "firmware",
            sat_id,
            f"firmware applied v={sat.firmware_version}",
        )
        self._maybe_emit_final()
        return {"ok": True, "version": sat.firmware_version, "hash": real_hash}


# global world singleton
WORLD = World()


# --- frame parsing / building -----------------------------------------------


class ParsedFrame:
    __slots__ = ("sat_id", "type", "seq", "payload")

    def __init__(self, sat_id: int, type: int, seq: int, payload: bytes) -> None:
        self.sat_id = sat_id
        self.type = type
        self.seq = seq
        self.payload = payload


def parse_frame(frame: bytes) -> ParsedFrame:
    if len(frame) < 2 + 1 + 1 + 2 + 2 + 2:
        raise ValueError("frame too short")

    if frame[0:2] != SYNC:
        raise ValueError("bad SYNC word")

    sat_id = frame[2]
    ftype = frame[3]
    seq = int.from_bytes(frame[4:6], "little")
    length = int.from_bytes(frame[6:8], "little")

    if 8 + length + 2 != len(frame):
        raise ValueError("length field mismatch")

    payload = frame[8 : 8 + length]
    recv_crc = int.from_bytes(frame[8 + length : 8 + length + 2], "little")
    calc_crc = crc16(frame[0 : 8 + length])

    if recv_crc != calc_crc:
        raise ValueError("CRC mismatch")

    return ParsedFrame(sat_id=sat_id, type=ftype, seq=seq, payload=payload)


def build_tlm_frame(sat: Satellite) -> bytes:
    mode_map: Dict[Mode, int] = {
        "SAFE": 0,
        "NOMINAL": 1,
        "SCIENCE": 2,
        "DIAGNOSTIC": 3,
    }
    mode_val = mode_map.get(sat.mode, 0)
    power_val = max(0, min(100, sat.power_level))
    temp_val = int(sat.temp_c * 2.0)
    payload = bytes([mode_val, power_val]) + temp_val.to_bytes(2, "little", signed=True)
    seq = sat.next_seq()
    return _build_frame(sat.sat_id, TYPE_TLM, seq, payload)


def _build_frame(sat_id: int, ftype: int, seq: int, payload: bytes) -> bytes:
    header = (
        SYNC
        + bytes([sat_id, ftype])
        + seq.to_bytes(2, "little")
        + len(payload).to_bytes(2, "little")
    )
    crc = crc16(header + payload)
    return header + payload + crc.to_bytes(2, "little")
