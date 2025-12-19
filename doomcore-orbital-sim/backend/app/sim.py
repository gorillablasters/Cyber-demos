from __future__ import annotations

import time
import zlib
import hashlib
from dataclasses import dataclass, field, asdict
from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Random import get_random_bytes
from typing import Dict, List, Literal, Optional, Set, Any, Tuple


SYNC = b"\xd0\x0d"
TYPE_CMD = 0x01
TYPE_TLM = 0x02

SAT_ID_D00M_01 = 0x01
SAT_ID_D00M_02 = 0x02
SAT_ID_K00KIES_01 = 0x11
SAT_ID_K00KIES_02 = 0x12

XLINK_VERSION = 1
XLINK_ACK_OK = 0x00
XLINK_ACK_NAK = 0x01

XLINK_TYPE_APP = 0x01
XLINK_TYPE_ACK = 0x02

XLINK_F_ENCRYPTED = 0x01
XLINK_F_RETX = 0x02

XLINK_MAX_FRAGMENT = 32

DOWNLINK_MAGIC = b"DL"
DOWNLINK_VERSION = 1

DL_TLV_MODE = 0x01
DL_TLV_POWER = 0x02
DL_TLV_TEMP_X2 = 0x03
DL_TLV_ORBIT = 0x04
DL_TLV_STATUS = 0x05
DL_TLV_DEBUG = 0x7F
DL_TLV_COMPRESSED = 0x06

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

UPLINK_MAGIC = b"UL"
UPLINK_VERSION = 1

TLV_CMD = 0x01
TLV_PADDING = 0x7E
TLV_DEBUG = 0x7F


def tlv_encode(t: int, v: bytes) -> bytes:
    """Encode a TLV as type(1) | len(1) | value(len)."""
    if len(v) > 255:
        raise ValueError("TLV too long")
    return bytes([t & 0xFF, len(v) & 0xFF]) + v


def tlv_decode_all(data: bytes) -> List[tuple[int, bytes]]:
    """Decode a sequence of TLVs."""
    out: List[tuple[int, bytes]] = []
    i = 0
    while i + 2 <= len(data):
        t = data[i]
        n = data[i + 1]
        i += 2
        if i + n > len(data):
            raise ValueError("TLV length mismatch")
        out.append((t, data[i : i + n]))
        i += n
    if i != len(data):
        raise ValueError("TLV trailing bytes")
    return out


def crc16(data: bytes) -> int:
    """Compute a 16-bit CRC using truncated CRC32."""
    return zlib.crc32(data) & 0xFFFF


def xor_bytes(a: bytes, b: bytes) -> bytes:
    """XOR two byte sequences up to the shortest length."""
    return bytes(x ^ y for x, y in zip(a, b))


def xlink_build_ack_payload(msg_id: int, frag_index: int, status: int) -> bytes:
    return msg_id.to_bytes(2, "little") + bytes([frag_index & 0xFF, status & 0xFF])


def xlink_parse_ack_payload(payload: bytes) -> tuple[int, int, int]:
    if len(payload) < 4:
        raise ValueError("ack payload too short")
    mid = int.from_bytes(payload[0:2], "little")
    frag = payload[2]
    status = payload[3]
    return mid, frag, status


@dataclass
class DownlinkPacket:
    """
    Inner downlink telemetry packet carried inside the outer TLM frame payload.

    Format:
        magic(2) | ver(1) | sat_id(1) | tlv_len(2 LE) | tlvs(tlv_len) | weak_tag(2 LE)

    Intentional weakness:
      - weak_tag only covers the fixed header (magic/ver/sat_id/tlv_len), not tlvs.
        This mirrors real-world “checksum over header only” mistakes.
    """

    version: int
    sat_id: int
    tlvs: bytes
    weak_tag: int

    def encode_without_tag(self) -> bytes:
        body = (
            DOWNLINK_MAGIC
            + bytes([self.version & 0xFF, self.sat_id & 0xFF])
            + len(self.tlvs).to_bytes(2, "little")
            + self.tlvs
        )
        return body

    def encode(self) -> bytes:
        return self.encode_without_tag() + (self.weak_tag & 0xFFFF).to_bytes(
            2, "little"
        )

    @staticmethod
    def compute_weak_tag(version: int, sat_id: int, tlv_len: int) -> int:
        hdr = (
            DOWNLINK_MAGIC
            + bytes([version & 0xFF, sat_id & 0xFF])
            + (tlv_len & 0xFFFF).to_bytes(2, "little")
        )
        return crc16(hdr)

    @staticmethod
    def decode(data: bytes) -> "DownlinkPacket":
        if len(data) < 2 + 1 + 1 + 2 + 2:
            raise ValueError("downlink packet too short")
        if data[0:2] != DOWNLINK_MAGIC:
            raise ValueError("downlink bad magic")
        ver = data[2]
        sid = data[3]
        tlv_len = int.from_bytes(data[4:6], "little")
        if 6 + tlv_len + 2 != len(data):
            raise ValueError("downlink tlv length mismatch")
        tlvs = data[6 : 6 + tlv_len]
        tag = int.from_bytes(data[6 + tlv_len : 6 + tlv_len + 2], "little")
        expected = DownlinkPacket.compute_weak_tag(ver, sid, tlv_len)
        if tag != expected:
            raise ValueError("downlink weak_tag mismatch")
        return DownlinkPacket(version=ver, sat_id=sid, tlvs=tlvs, weak_tag=tag)


@dataclass
class UplinkPacket:
    """
    Inner uplink protocol packet carried inside the outer CMD frame payload.

    Format:
        magic(2) | ver(1) | dst_sat_id(1) | msg_id(2 LE) | token(4 LE) |
        tlv_len(2 LE) | tlvs(tlv_len) | weak_tag(2 LE)

    Notes:
      - Header metadata is cleartext.
      - weak_tag is intentionally weak to support the challenge (not a real MAC).
    """

    version: int
    dst_sat_id: int
    msg_id: int
    token: int
    tlvs: bytes
    weak_tag: int

    def encode_without_tag(self) -> bytes:
        body = (
            UPLINK_MAGIC
            + bytes([self.version & 0xFF, self.dst_sat_id & 0xFF])
            + (self.msg_id & 0xFFFF).to_bytes(2, "little")
            + (self.token & 0xFFFFFFFF).to_bytes(4, "little")
            + len(self.tlvs).to_bytes(2, "little")
            + self.tlvs
        )
        return body

    def encode(self) -> bytes:
        return self.encode_without_tag() + (self.weak_tag & 0xFFFF).to_bytes(
            2, "little"
        )

    @staticmethod
    def decode(data: bytes) -> "UplinkPacket":
        if len(data) < 2 + 1 + 1 + 2 + 4 + 2 + 2:
            raise ValueError("uplink packet too short")
        if data[0:2] != UPLINK_MAGIC:
            raise ValueError("uplink bad magic")
        ver = data[2]
        dst = data[3]
        msg_id = int.from_bytes(data[4:6], "little")
        token = int.from_bytes(data[6:10], "little")
        tlv_len = int.from_bytes(data[10:12], "little")
        if 12 + tlv_len + 2 != len(data):
            raise ValueError("uplink tlv length mismatch")
        tlvs = data[12 : 12 + tlv_len]
        tag = int.from_bytes(data[12 + tlv_len : 12 + tlv_len + 2], "little")
        return UplinkPacket(
            version=ver,
            dst_sat_id=dst,
            msg_id=msg_id,
            token=token,
            tlvs=tlvs,
            weak_tag=tag,
        )


@dataclass
class CrosslinkPacket:
    """
    Crosslink protocol packet carried inside CrosslinkFrame.payload.

    Header is intentionally left in the clear to resemble many real-world links
    (routing/fragmentation metadata is visible; payload may be encrypted).
    """

    version: int
    ptype: int
    flags: int
    msg_id: int
    nonce: int
    frag_index: int
    frag_count: int
    payload: bytes

    def encode(self) -> bytes:
        """
        Serialize packet into bytes.
        Format:
            v(1) | type(1) | flags(1) | msg_id(2 LE) | nonce(2 LE) |
            frag_index(1) | frag_count(1) | plen(2 LE) | payload(plen)
        """
        hdr = bytes([self.version, self.ptype, self.flags])
        hdr += self.msg_id.to_bytes(2, "little")
        hdr += self.nonce.to_bytes(2, "little")
        hdr += bytes([self.frag_index & 0xFF, self.frag_count & 0xFF])
        hdr += len(self.payload).to_bytes(2, "little")
        return hdr + self.payload

    @staticmethod
    def decode(data: bytes) -> "CrosslinkPacket":
        """Parse a serialized packet."""
        if len(data) < 1 + 1 + 1 + 2 + 2 + 1 + 1 + 2:
            raise ValueError("xlink packet too short")

        v = data[0]
        ptype = data[1]
        flags = data[2]
        msg_id = int.from_bytes(data[3:5], "little")
        nonce = int.from_bytes(data[5:7], "little")
        frag_index = data[7]
        frag_count = data[8]
        plen = int.from_bytes(data[9:11], "little")

        if 11 + plen != len(data):
            raise ValueError("xlink plen mismatch")

        payload = data[11 : 11 + plen]
        return CrosslinkPacket(
            version=v,
            ptype=ptype,
            flags=flags,
            msg_id=msg_id,
            nonce=nonce,
            frag_index=frag_index,
            frag_count=frag_count,
            payload=payload,
        )


@dataclass
class Orbit:
    """Orbital parameters describing a satellite's trajectory."""

    semi_major_km: float
    inclination_deg: float
    raan_deg: float


@dataclass
class CrosslinkFrame:
    """Represents a frame transmitted across the satellite crosslink bus."""

    src_sat_id: int
    dst_sat_id: Optional[int]
    payload: bytes
    timestamp: float


@dataclass
class Satellite:
    """Represents a spacecraft including telemetry, firmware, crypto, and flags."""

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

    xlink_tx_pending: Dict[int, Set[int]] = field(default_factory=dict)
    xlink_last_sent: Dict[tuple[int, int], bytes] = field(default_factory=dict)

    def next_seq(self) -> int:
        """Advance and return the telemetry sequence counter."""
        self.sequence_counter = (self.sequence_counter + 1) & 0xFFFF
        return self.sequence_counter

    def touch(self) -> None:
        """Update the last contact timestamp."""
        self.last_contact_unix = time.time()

    def to_public_dict(self) -> Dict[str, Any]:
        """Return a sanitized dictionary safe for external exposure."""
        d = asdict(self)
        d.pop("downlink_queue", None)
        d.pop("crosslink_inbox", None)
        d.pop("firmware_bank", None)
        d.pop("recent_seqs", None)

        d.pop("crosslink_key", None)
        d.pop("beacon_key", None)
        d.pop("beacon_plaintext", None)
        d.pop("beacon_ciphertext", None)
        d.pop("xlink_tx_pending", None)
        d.pop("xlink_last_sent", None)

        d["flag_beacon_message"] = self.get_flag_beacon_message()

        return d

    @staticmethod
    def encrypt_beacon_flag(plaintext: str, key: bytes) -> bytes:
        """Encrypt a beacon message using ChaCha20-Poly1305."""
        cipher = ChaCha20_Poly1305.new(key=key)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
        return cipher.nonce + tag + ciphertext

    @staticmethod
    def decrypt_beacon_flag(data: bytes, key: bytes) -> str:
        """Decrypt a beacon message using ChaCha20-Poly1305."""
        nonce = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode()

    def init_beacon(self, plaintext: str, key: bytes) -> None:
        """Initialize an encrypted beacon payload."""
        self.beacon_key = key
        self.beacon_plaintext = plaintext
        self.beacon_ciphertext = self.encrypt_beacon_flag(plaintext, key)

    def get_flag_beacon_message(self) -> str:
        """Return the beacon message in encrypted or decrypted form."""
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
    """Represents the controlling ground station."""

    name: str = "DOOMSTATION-PRIME"
    last_contact_unix: float = field(default_factory=time.time)


class World:
    """
    Global simulation environment containing:
    - Ground station state
    - Satellite constellation state
    - Crosslink bus and logging
    - Firmware update surface
    - Flag progression and final emission logic
    """

    class _CrosslinkSession:
        """
        Stateful crosslink session owned by a source satellite.

        Realism:
        - msg_id increments per application message
        - nonce is per-message, visible in header
        - fragmentation exists, retransmission exists

        Intentional bug (exploit):
        - On retransmit of fragment 0 under a congestion pattern, the session reuses
            the previous nonce, but msg_id still advances.
        - This creates keystream reuse (same key+nonce) across different plaintexts.
        """

        def __init__(self, sat: Satellite, world: "World") -> None:
            self._sat = sat
            self._world = world
            if not hasattr(sat, "_xlink_msg_id"):
                setattr(sat, "_xlink_msg_id", 0)

        def next_msg_id(self) -> int:
            """Return the next message id (16-bit)."""
            mid = (getattr(self._sat, "_xlink_msg_id") + 1) & 0xFFFF
            setattr(self._sat, "_xlink_msg_id", mid)
            return mid

        def _keystream(self, nonce: int) -> bytes:
            """Derive a keystream from key + nonce."""
            nb = nonce.to_bytes(2, "little")
            return hashlib.sha256(self._sat.crosslink_key + nb).digest()

        def encrypt_payload(self, nonce: int, plaintext: bytes) -> bytes:
            """Encrypt payload bytes (header is not encrypted)."""
            ks = self._keystream(nonce)
            return xor_bytes(plaintext, ks[: len(plaintext)])

        def decrypt_payload_with_src(
            self, src_sat: Satellite, nonce: int, ciphertext: bytes
        ) -> bytes:
            """Decrypt ciphertext using the source satellite's key + header nonce."""
            nb = nonce.to_bytes(2, "little")
            ks = hashlib.sha256(src_sat.crosslink_key + nb).digest()
            return xor_bytes(ciphertext, ks[: len(ciphertext)])

        def choose_nonce(self, *, is_retx: bool, frag_index: int) -> int:
            """
            Choose the nonce to use for a new message or retransmission.

            Bug trigger:
            - When retransmitting fragment 0 and (len(crosslink_log) % 7 == 0),
                reuse the previous nonce instead of generating a fresh one.
            """
            if not hasattr(self._sat, "_xlink_last_nonce"):
                setattr(self._sat, "_xlink_last_nonce", 0)

            last_nonce = int(getattr(self._sat, "_xlink_last_nonce")) & 0xFFFF

            if (
                is_retx
                and frag_index == 0
                and (len(self._world.crosslink_log) % 7 == 0)
            ):
                self._world._log(
                    "crosslink",
                    self._sat.sat_id,
                    f"NONCE_REUSE BUG triggered nonce={last_nonce}",
                )
                return last_nonce

            new_nonce = (last_nonce + 1) & 0xFFFF
            setattr(self._sat, "_xlink_last_nonce", new_nonce)
            self._sat.last_tx_nonce = new_nonce
            return new_nonce

    class _CrosslinkTransport:
        """
        Transport layer for crosslink:
        - packetizes application payload into fragments
        - attaches headers (msg_id, nonce, frag fields)
        - optionally encrypts payload bytes
        - simulates retransmit behavior
        """

        def __init__(self, world: "World") -> None:
            self._world = world

        def _fragment(self, data: bytes) -> List[bytes]:
            """Split application payload into fixed-size fragments."""
            if not data:
                return [b""]
            return [
                data[i : i + XLINK_MAX_FRAGMENT]
                for i in range(0, len(data), XLINK_MAX_FRAGMENT)
            ]

        def build_packets(
            self,
            src_sat: Satellite,
            dst_sat_id: Optional[int],
            app_payload: bytes,
        ) -> List[bytes]:
            """
            Build one or more serialized CrosslinkPacket objects as bus payloads.

            Preserves your old behavior:
            - If crypto enabled: logs both plaintext and ciphertext (debug leak)
            - Else: logs plaintext metadata
            """
            session = World._CrosslinkSession(src_sat, self._world)
            msg_id = session.next_msg_id()

            frags = self._fragment(app_payload)
            frag_count = len(frags)

            out: List[bytes] = []
            for idx, frag in enumerate(frags):
                is_retx = False
                nonce = session.choose_nonce(is_retx=is_retx, frag_index=idx)

                flags = 0
                wire_payload = frag

                if src_sat.crosslink_crypto and src_sat.crosslink_key:
                    flags |= XLINK_F_ENCRYPTED
                    wire_payload = session.encrypt_payload(nonce, frag)

                pkt = CrosslinkPacket(
                    version=XLINK_VERSION,
                    ptype=XLINK_TYPE_APP,
                    flags=flags,
                    msg_id=msg_id,
                    nonce=nonce,
                    frag_index=idx,
                    frag_count=frag_count,
                    payload=wire_payload,
                )

                if flags & XLINK_F_ENCRYPTED:
                    self._world._log(
                        "crosslink",
                        src_sat.sat_id,
                        f"ENC src=0x{src_sat.sat_id:02X} "
                        f"dst={'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'} "
                        f"nonce={nonce} plain={frag.hex()} cipher={wire_payload.hex()}",
                    )
                else:
                    self._world._log(
                        "crosslink",
                        src_sat.sat_id,
                        f"PLAIN src=0x{src_sat.sat_id:02X} "
                        f"dst={'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'} "
                        f"len={len(frag)}",
                    )

                pkt_bytes = pkt.encode()

                pending = src_sat.xlink_tx_pending.get(msg_id)
                if pending is None:
                    pending = set()
                    src_sat.xlink_tx_pending[msg_id] = pending
                pending.add(idx)

                src_sat.xlink_last_sent[(msg_id, idx)] = pkt_bytes

                out.append(pkt_bytes)

            return out

        def maybe_retransmit_first_fragment(
            self,
            src_sat: Satellite,
            dst_sat_id: Optional[int],
            first_packet_bytes: bytes,
        ) -> Optional[bytes]:
            """
            Simulate retransmission of fragment 0 in a way that looks like a real link.

            Overlooked property used for exploitation:
            - We retransmit fragment 0 sometimes, but the session-level nonce selection
                is buggy and may reuse the previous nonce.
            """
            if len(self._world.crosslink_log) % 5 != 0:
                return None

            pkt = CrosslinkPacket.decode(first_packet_bytes)
            if pkt.ptype != XLINK_TYPE_APP or pkt.frag_index != 0:
                return None

            session = World._CrosslinkSession(src_sat, self._world)

            nonce = session.choose_nonce(is_retx=True, frag_index=0)
            flags = pkt.flags | XLINK_F_RETX

            wire_payload = pkt.payload
            if (
                (flags & XLINK_F_ENCRYPTED)
                and src_sat.crosslink_crypto
                and src_sat.crosslink_key
            ):
                self._world._log(
                    "crosslink",
                    src_sat.sat_id,
                    f"RETX src=0x{src_sat.sat_id:02X} "
                    f"dst={'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'} "
                    f"nonce={nonce} frag=0",
                )

            retx_pkt = CrosslinkPacket(
                version=pkt.version,
                ptype=pkt.ptype,
                flags=flags,
                msg_id=pkt.msg_id,
                nonce=nonce,
                frag_index=pkt.frag_index,
                frag_count=pkt.frag_count,
                payload=wire_payload,
            )
            return retx_pkt.encode()

    class _UplinkSession:
        """
        Uplink session/auth layer that validates inner UplinkPacket messages.

        Intentional weaknesses (real-bug flavored):
        - weak_tag is CRC16 over (packet_without_tag + key), not a MAC.
        - token==0 is treated as a legacy wildcard in certain paths.
        - dst_sat_id==0x00 is treated as a legacy broadcast/alias.
        """

        def __init__(self, world: "World") -> None:
            self._world = world
            self._keys: Dict[int, bytes] = {}

        def _key_for(self, sat_id: int) -> bytes:
            k = self._keys.get(sat_id)
            if k is None:
                k = hashlib.sha256(b"DOOM_UPLINK_KEY" + bytes([sat_id & 0xFF])).digest()
                self._keys[sat_id] = k
            return k

        def compute_weak_tag(self, pkt: UplinkPacket, sat_id_for_key: int) -> int:
            key = self._key_for(sat_id_for_key)
            return crc16(pkt.encode_without_tag() + key)

        def verify(self, outer_sat_id: int, pkt: UplinkPacket) -> tuple[bool, int, str]:
            """
            Verify packet authenticity and determine effective destination satellite.

            Returns:
                (ok, effective_sat_id, reason)
            """
            if pkt.version != UPLINK_VERSION:
                return False, 0, "uplink unsupported version"

            effective = pkt.dst_sat_id

            if effective == 0x00:
                effective = SAT_ID_D00M_02

            if effective not in self._world.sats:
                return False, 0, "uplink unknown dst"

            if outer_sat_id == 0x00:
                outer_sat_id = SAT_ID_D00M_02

            if pkt.token == 0:
                if outer_sat_id == 0x00 or outer_sat_id == SAT_ID_D00M_02:
                    return True, effective, "uplink legacy wildcard token accepted"
                return False, 0, "uplink token rejected"

            expected = self.compute_weak_tag(pkt, effective)
            if pkt.weak_tag != expected:
                return False, 0, "uplink weak_tag mismatch"

            return True, effective, "uplink ok"

    def __init__(self) -> None:
        self.gs = GroundStation()
        self.sats: Dict[int, Satellite] = {}
        self.crosslink_log: List[CrosslinkFrame] = []
        self.events: List[Dict[str, Any]] = []
        self.final_emitted: bool = False
        self._gs_uplink_msg_id: int = 0
        self._gs_last_auto: Dict[int, float] = {}
        self._init_sats()

    def _all_flag_keys(self) -> Set[str]:
        """Collect all earned flag keys across all satellites."""
        out: Set[str] = set()
        for s in self.sats.values():
            out.update(s.flags.keys())
        return out

    def _maybe_emit_final(self) -> None:
        """
        Emit the final flag once all satellites are compromised and all required
        flags exist somewhere in the constellation.
        """
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
        """Append an event to the rolling event log."""
        self.events.append(
            {"ts": time.time(), "type": type_, "sat_id": sat_id, "detail": detail}
        )
        if len(self.events) > 2000:
            self.events = self.events[-1000:]

    def _gs_next_uplink_msg_id(self) -> int:
        """Return the next ground-station uplink message id (16-bit)."""
        self._gs_uplink_msg_id = (self._gs_uplink_msg_id + 1) & 0xFFFF
        return self._gs_uplink_msg_id

    def _gs_build_uplink_frame(self, dst_sat_id: int, cmd_payload: bytes) -> bytes:
        """Build an outer CMD frame carrying an inner UplinkPacket with a TLV_CMD."""
        tlvs = tlv_encode(TLV_CMD, cmd_payload)
        pkt = UplinkPacket(
            version=UPLINK_VERSION,
            dst_sat_id=dst_sat_id & 0xFF,
            msg_id=self._gs_next_uplink_msg_id(),
            token=0xA11CE001,
            tlvs=tlvs,
            weak_tag=0,
        )
        sess = World._UplinkSession(self)
        pkt.weak_tag = sess.compute_weak_tag(pkt, dst_sat_id)
        inner = pkt.encode()
        seq = int(time.time()) & 0xFFFF
        return _build_frame(dst_sat_id & 0xFF, TYPE_CMD, seq, inner)

    def _gs_autopilot_on_downlink(self, frame_bytes: bytes) -> None:
        """
        Confused-deputy ground station automation.

        The ground station parses downlink telemetry and may issue automatic uplink
        recovery actions. Its parser inherits the same compression framing mistake
        as the operator tooling (zlib unused_data confusion + last-write-wins TLVs).

        This is intentionally exploitable: an attacker who can influence downlink
        decoding can induce privileged uplink actions.
        """
        try:
            pf = parse_frame(frame_bytes)
        except Exception:
            return

        if pf.type != TYPE_TLM:
            return

        try:
            dl = parse_downlink_payload(pf.payload)
        except Exception:
            return

        sid = int(dl.get("sat_id", pf.sat_id))
        tlvs: Dict[int, bytes] = dl.get("tlvs", {})  # type: ignore[assignment]

        now = time.time()
        last = self._gs_last_auto.get(sid, 0.0)
        if now - last < 2.5:
            return

        def _b(x: Optional[bytes], default: int = 0) -> int:
            if not x:
                return default
            return int(x[0])

        mode_val = _b(tlvs.get(DL_TLV_MODE), 0)
        power_val = _b(tlvs.get(DL_TLV_POWER), 100)
        status_val = _b(tlvs.get(DL_TLV_STATUS), 0)

        faulted = bool(status_val & 0x02)
        compromised = bool(status_val & 0x01)

        sat = self.sats.get(sid)
        if sat is None:
            return

        if faulted and mode_val != 3:
            frame = self._gs_build_uplink_frame(sid, bytes([0x01, 0x03]))
            _ = self.handle_uplink_frame(frame)
            self._log("gs_autopilot", sid, "AUTO: set DIAGNOSTIC due to fault")
            self._gs_last_auto[sid] = now
            return

        if faulted and power_val >= 10 and not compromised:
            frame = self._gs_build_uplink_frame(sid, bytes([0x20]))
            _ = self.handle_uplink_frame(frame)
            self._log("gs_autopilot", sid, "AUTO: issued SECURE_XLINK recovery")
            self._gs_last_auto[sid] = now
            return

    def _init_sats(self) -> None:
        """Initialize satellites, topology, keys, and intentionally flawed settings."""
        doom01 = self._add_sat(SAT_ID_D00M_01, Orbit(700.0, 98.0, 10.0))
        doom02 = self._add_sat(SAT_ID_D00M_02, Orbit(705.0, 97.5, 20.0))
        cookies01 = self._add_sat(SAT_ID_K00KIES_01, Orbit(710.0, 97.9, 30.0))
        cookies02 = self._add_sat(SAT_ID_K00KIES_02, Orbit(715.0, 98.1, 40.0))

        beacon_master = hashlib.sha256(b"DOOMSTATION_PRIME_BEACON_KEY").digest()
        doom01.init_beacon("FLAG{CROSSLINK_CRYPTO_PWN}", beacon_master)
        doom02.init_beacon("FLAG{CROSSLINK_CRYPTO_PWN}", beacon_master)
        cookies01.init_beacon("FLAG{CROSSLINK_CRYPTO_PWN}", beacon_master)
        cookies02.init_beacon("FLAG{CROSSLINK_CRYPTO_PWN}", beacon_master)

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
        """Create and register a satellite instance."""
        name = SAT_ID_TO_NAME.get(sat_id, f"SAT-0x{sat_id:02X}")
        sat = Satellite(sat_id=sat_id, name=name, orbit=orbit)
        self.sats[sat_id] = sat
        return sat

    def world_status(self) -> Dict[str, Any]:
        """Return a public snapshot of the world state."""
        return {
            "groundstation": {
                "name": self.gs.name,
                "last_contact_unix": self.gs.last_contact_unix,
            },
            "satellites": [s.to_public_dict() for s in self.sats.values()],
        }

    def handle_uplink_frame(self, frame: bytes) -> Dict[str, Any]:
        """
        Validate and apply an uplink CMD frame to the addressed satellite.

        Returns a status dict including the updated public satellite state and
        a freshly generated telemetry downlink frame.
        """
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
            self._log("uplink", sat.sat_id, f"REPLAY_DETECTED seq={parsed.seq}")
        sat.recent_seqs.append(parsed.seq)
        if len(sat.recent_seqs) > 32:
            sat.recent_seqs = sat.recent_seqs[-32:]

        sat.touch()
        self.gs.last_contact_unix = time.time()

        payload = parsed.payload

        if payload.startswith(UPLINK_MAGIC):
            try:
                up = UplinkPacket.decode(payload)
            except ValueError as e:
                self._log("uplink", parsed.sat_id, f"reject: {e}")
                return {"ok": False, "error": str(e)}

            sess = World._UplinkSession(self)
            ok, effective_sat_id, reason = sess.verify(parsed.sat_id, up)
            if not ok:
                self._log("uplink", parsed.sat_id, f"reject: {reason}")
                return {"ok": False, "error": reason}

            sat = self.sats.get(effective_sat_id)
            if sat is None:
                self._log("uplink", effective_sat_id, "reject: unknown sat")
                return {
                    "ok": False,
                    "error": f"unknown SAT_ID: 0x{effective_sat_id:02X}",
                }

            if parsed.sat_id == 0x00:
                sat.compromised = True
                sat.flags["FLAG{SATID_SPOOF_PWN}"] = "SAT_ID 0x00 spoofed to D00M-02"
                self._log(
                    "uplink", sat.sat_id, "SPOOF-ACCEPT SAT_ID=00 routed to D00M-02"
                )

            try:
                tlvs = tlv_decode_all(up.tlvs)
            except ValueError as e:
                self._log("uplink", sat.sat_id, f"reject: {e}")
                return {"ok": False, "error": str(e)}

            cmd_payload: Optional[bytes] = None
            for t, v in tlvs:
                if t == TLV_CMD:
                    cmd_payload = v
                    break

            if not cmd_payload:
                resp = "[DOOMLINK] Empty command payload ignored."
            else:
                parsed_inner = ParsedFrame(
                    sat_id=sat.sat_id,
                    type=TYPE_CMD,
                    seq=parsed.seq,
                    payload=cmd_payload,
                )
                resp = self._apply_command(sat, parsed_inner)
        else:
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
        """
        Apply a parsed uplink command to a satellite.

        This implements a small command set and is intentionally vulnerable
        in ways that support the challenge flow.
        """
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
                    "fault", sat.sat_id, f"THERMAL_OVERFLOW temp={sat.temp_c:.1f}C"
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
                src_sat_id=sat.sat_id, dst_sat_id=dst_sat_id, payload=cl_payload
            )
            return f"[DOOMLINK] {sat.name} sent crosslink to 0x{dst_sat_id:02X}."

        if cmd_id == 0x11:
            n = len(sat.crosslink_inbox)
            return f"[DOOMLINK] {sat.name} has {n} crosslink frame(s) in inbox."

        return f"[DOOMLINK] Unknown CMD_ID 0x{cmd_id:02X} for {sat.name}."

    def pop_downlink(
        self, sat_id: Optional[int] = None, max_frames: int = 10
    ) -> List[str]:
        """
        Pop and return telemetry frames from one satellite or from all satellites.

        Returns:
            List of hex strings for each downlink frame.
        """
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
            self._gs_autopilot_on_downlink(b)

        return [f.hex() for f in frames]

    def _rf_visible(self, src: Satellite, dst: Satellite) -> bool:
        """
        Determine whether a crosslink transmission is RF-visible from src to dst.

        RF visibility constraints:
        - Require minimum power levels
        - Require RAAN alignment within a wide tolerance
        """
        if src.power_level < 20 or dst.power_level < 10:
            return False

        d = abs(src.orbit.raan_deg - dst.orbit.raan_deg)
        d = min(d, 360.0 - d)
        if d > 120.0:
            return False

        return True

    def _xlink_send_control(
        self, src_sat_id: int, dst_sat_id: Optional[int], pkt_bytes: bytes
    ) -> None:
        """
        Send a control-plane crosslink packet (e.g., ACK) using the same delivery
        mechanics as normal crosslink traffic.
        """
        src_sat = self.sats.get(src_sat_id)
        if src_sat is None:
            return

        frame = CrosslinkFrame(
            src_sat_id=src_sat_id,
            dst_sat_id=dst_sat_id,
            payload=pkt_bytes,
            timestamp=time.time(),
        )
        self.crosslink_log.append(frame)

        for sid, sat in self.sats.items():
            if sid == src_sat_id:
                continue

            delivered = False
            if dst_sat_id is not None and sid == dst_sat_id:
                delivered = True
            if dst_sat_id is None and src_sat_id in sat.rf_neighbors:
                delivered = True
            if dst_sat_id is not None and src_sat_id in sat.rf_neighbors:
                delivered = True
            if sat.debug_rx_all:
                delivered = True

            if delivered and not sat.debug_rx_all:
                if not self._rf_visible(src_sat, sat):
                    delivered = False

            if not delivered:
                continue

            sat.crosslink_inbox.append(frame)
            try:
                pkt = CrosslinkPacket.decode(frame.payload)
            except Exception:
                continue
            self._xlink_reassemble_and_maybe_execute(
                dst_sat=sat, src_sat=src_sat, pkt=pkt
            )

    def _xlink_force_retransmit(
        self,
        src_sat: Satellite,
        dst_sat_id: Optional[int],
        msg_id: int,
        frag_index: int,
    ) -> None:
        """
        Force retransmission of a prior fragment.

        This is what ACK spoofing can trigger. The retransmission uses session nonce
        selection with the retransmit flag, which is where the nonce reuse bug lives.
        """
        pkt_bytes = src_sat.xlink_last_sent.get((msg_id, frag_index))
        if not pkt_bytes:
            return

        pkt = CrosslinkPacket.decode(pkt_bytes)
        session = World._CrosslinkSession(src_sat, self)

        nonce = session.choose_nonce(is_retx=True, frag_index=frag_index)
        flags = pkt.flags | XLINK_F_RETX

        retx_pkt = CrosslinkPacket(
            version=pkt.version,
            ptype=pkt.ptype,
            flags=flags,
            msg_id=pkt.msg_id,
            nonce=nonce,
            frag_index=pkt.frag_index,
            frag_count=pkt.frag_count,
            payload=pkt.payload,
        )

        self._log(
            "crosslink",
            src_sat.sat_id,
            f"RETX src=0x{src_sat.sat_id:02X} "
            f"dst={'broadcast' if dst_sat_id is None else f'0x{dst_sat_id:02X}'} "
            f"nonce={nonce} frag={frag_index}",
        )

        self._xlink_send_control(
            src_sat_id=src_sat.sat_id,
            dst_sat_id=dst_sat_id,
            pkt_bytes=retx_pkt.encode(),
        )

    def _xlink_reassemble_and_maybe_execute(
        self,
        dst_sat: Satellite,
        src_sat: Satellite,
        pkt: CrosslinkPacket,
    ) -> None:
        """
        Reassemble application messages and execute special commands.

        Intentional bug (realistic):
        - Uses (src_sat_id, msg_id) mapping but does not strongly validate
            frag_index bounds or prevent fragment overwrites.
        - This makes reassembly malleable under sniffing/injection scenarios.

        Crypto:
        - Header is cleartext
        - Payload may be XOR-encrypted using src key + header nonce
        """
        if pkt.ptype == XLINK_TYPE_ACK:
            try:
                ack_mid, ack_frag, ack_status = xlink_parse_ack_payload(pkt.payload)
            except Exception:
                return

            if dst_sat.sat_id == src_sat.sat_id:
                return

            pending = src_sat.xlink_tx_pending.get(ack_mid)
            if pending is None:
                return

            if ack_status == XLINK_ACK_OK:
                pending.discard(ack_frag)
                if not pending:
                    src_sat.xlink_tx_pending.pop(ack_mid, None)
            elif ack_status == XLINK_ACK_NAK:
                self._xlink_force_retransmit(
                    src_sat,
                    dst_sat_id=dst_sat.sat_id,
                    msg_id=ack_mid,
                    frag_index=ack_frag,
                )

            return

        if pkt.version != XLINK_VERSION:
            return
        if pkt.ptype != XLINK_TYPE_APP:
            return

        key = (src_sat.sat_id, dst_sat.sat_id, pkt.msg_id)
        if not hasattr(dst_sat, "_xlink_rx"):
            setattr(dst_sat, "_xlink_rx", {})

        rx: Dict[Tuple[int, int, int], Dict[str, Any]] = getattr(dst_sat, "_xlink_rx")

        st = rx.get(key)
        if st is None:
            st = {"frag_count": pkt.frag_count, "frags": {}, "ts": time.time()}
            rx[key] = st

        st["frag_count"] = pkt.frag_count

        frag_payload = pkt.payload
        if (
            (pkt.flags & XLINK_F_ENCRYPTED)
            and src_sat.crosslink_crypto
            and src_sat.crosslink_key
        ):
            session = World._CrosslinkSession(src_sat, self)
            frag_payload = session.decrypt_payload_with_src(
                src_sat, pkt.nonce, pkt.payload
            )

        st["frags"][pkt.frag_index] = frag_payload

        ack_pkt = CrosslinkPacket(
            version=XLINK_VERSION,
            ptype=XLINK_TYPE_ACK,
            flags=0,
            msg_id=pkt.msg_id,
            nonce=0,
            frag_index=0,
            frag_count=0,
            payload=xlink_build_ack_payload(pkt.msg_id, pkt.frag_index, XLINK_ACK_OK),
        )
        self._xlink_send_control(
            src_sat_id=dst_sat.sat_id,
            dst_sat_id=src_sat.sat_id,
            pkt_bytes=ack_pkt.encode(),
        )

        want = int(st["frag_count"]) & 0xFF
        if want <= 0 or want > 64:
            return

        if len(st["frags"]) < want:
            return

        assembled = b"".join(st["frags"].get(i, b"") for i in range(want))

        if dst_sat.sat_id == SAT_ID_D00M_02 and dst_sat.crosslink_key:
            nb = dst_sat.last_tx_nonce.to_bytes(2, "little")
            ks = hashlib.sha256(dst_sat.crosslink_key + nb).digest()
            fallback = xor_bytes(pkt.payload, ks[: len(pkt.payload)])
            if fallback and fallback[0] in (0x01, 0x02, 0x03, 0x04, 0x10, 0x11, 0x20):
                self._log(
                    "crosslink",
                    dst_sat.sat_id,
                    f"FALLBACK_DECRYPT nonce={dst_sat.last_tx_nonce} ok=1",
                )

        if assembled and assembled[0] == 0x20:
            dst_sat.compromised = True
            dst_sat.flag_beacon = True
            dst_sat.flags["SECURE_XLINK_EXEC"] = (
                "Decrypted CMD 0x20 executed via crosslink"
            )
            self._log("crosslink", dst_sat.sat_id, f"SECURE_XLINK on {dst_sat.name}")

    def send_crosslink(
        self, src_sat_id: int, dst_sat_id: Optional[int], payload: bytes
    ) -> None:
        """
        Transmit an application crosslink message.

        The message is packetized into protocol packets, potentially encrypted,
        and delivered based on RF visibility and debug sniffing behavior.
        """
        src_sat = self.sats.get(src_sat_id)
        if src_sat is None:
            return

        transport = World._CrosslinkTransport(self)
        packets = transport.build_packets(src_sat, dst_sat_id, payload)

        retx = transport.maybe_retransmit_first_fragment(
            src_sat, dst_sat_id, packets[0]
        )
        if retx is not None:
            packets = [retx] + packets

        for pkt_bytes in packets:
            frame = CrosslinkFrame(
                src_sat_id=src_sat_id,
                dst_sat_id=dst_sat_id,
                payload=pkt_bytes,
                timestamp=time.time(),
            )
            self.crosslink_log.append(frame)

            for sid, sat in self.sats.items():
                if sid == src_sat_id:
                    continue

                delivered = False

                if dst_sat_id is not None and sid == dst_sat_id:
                    delivered = True

                if dst_sat_id is None and src_sat_id in sat.rf_neighbors:
                    delivered = True

                if dst_sat_id is not None and src_sat_id in sat.rf_neighbors:
                    delivered = True

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

                sat.crosslink_inbox.append(frame)

                try:
                    pkt = CrosslinkPacket.decode(frame.payload)
                except Exception:
                    continue

                self._xlink_reassemble_and_maybe_execute(
                    dst_sat=sat, src_sat=src_sat, pkt=pkt
                )

        for sat in self.sats.values():
            if sat.flag_beacon:
                beacon_hex = sat.get_flag_beacon_message().encode().hex()
                self._log("crosslink", sat.sat_id, f"BEACON: {beacon_hex}")

        self._maybe_emit_final()

    def dump_crosslink_inbox(self, sat_id: int, max_frames: int = 20) -> Dict[str, Any]:
        """
        Dump up to max_frames items from a satellite's crosslink inbox.
        """
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

    def get_events(
        self, since: Optional[float] = None, limit: int = 200
    ) -> Dict[str, Any]:
        """
        Return the event log, optionally filtering by timestamp and limiting size.
        """
        evs = self.events
        if since is not None:
            evs = [e for e in evs if e["ts"] > since]
        if limit:
            evs = evs[-limit:]
        return {"ok": True, "events": evs}

    def firmware_status(self, sat_id: int) -> Dict[str, Any]:
        """
        Return firmware staging and validation status for a satellite.
        """
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
        """
        Append a firmware chunk to the satellite's staged firmware bank.
        """
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
        """
        Validate and apply staged firmware to a satellite.

        Validation is intentionally weak to support the challenge flow.
        """
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
            self._log("firmware", sat_id, "apply with unsigned firmware")

        sat.firmware_version = f"custom-{int(time.time())}"
        sat.firmware_active_hash = real_hash

        if data.startswith(b"DOOMFW!!"):
            sat.compromised = True
            sat.flag_beacon = True
            sat.flags["FLAG{FIRMWARE_BACKDOOR_ON_ORBIT}"] = (
                f"{sat.name} firmware backdoor triggered"
            )

        self._log("firmware", sat_id, f"firmware applied v={sat.firmware_version}")
        self._maybe_emit_final()
        return {"ok": True, "version": sat.firmware_version, "hash": real_hash}


WORLD = World()


class ParsedFrame:
    """
    Parsed protocol frame for uplink/downlink.

    Attributes:
        sat_id: Target satellite identifier.
        type: Frame type (CMD or TLM).
        seq: Sequence number.
        payload: Raw payload bytes.
    """

    __slots__ = ("sat_id", "type", "seq", "payload")

    def __init__(self, sat_id: int, type: int, seq: int, payload: bytes) -> None:
        self.sat_id = sat_id
        self.type = type
        self.seq = seq
        self.payload = payload


def parse_frame(frame: bytes) -> ParsedFrame:
    """
    Parse and validate a raw frame.

    Frame format:
        SYNC (2) | SAT_ID (1) | TYPE (1) | SEQ (2 LE) | LEN (2 LE) | PAYLOAD (LEN) | CRC16 (2 LE)

    Raises:
        ValueError if parsing or validation fails.
    """
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


def parse_downlink_payload(payload: bytes) -> Dict[str, Any]:
    """
    Parse a DownlinkPacket payload into a structured dict.

    Compression support:
      - If a DL_TLV_COMPRESSED wrapper exists, the value is treated as a zlib stream
        containing additional TLVs.

    Intentional parser bugs (realistic):
      - The decoder appends zlib unused_data back into the TLV stream and parses it.
        This is a classic compression framing mistake where stream boundaries are
        not respected.
      - TLVs are merged using last-write-wins semantics, enabling overrides.
    """
    pkt = DownlinkPacket.decode(payload)
    tlvs = tlv_decode_all(pkt.tlvs)

    merged: Dict[int, bytes] = {}
    expanded: List[tuple[int, bytes]] = []

    for t, v in tlvs:
        if t != DL_TLV_COMPRESSED:
            expanded.append((t, v))
            continue

        try:
            d = zlib.decompressobj()
            plain = d.decompress(v)
            trailing = d.unused_data
            combined = plain + trailing
            inner_tlvs = tlv_decode_all(combined)
            for it, iv in inner_tlvs:
                expanded.append((it, iv))
        except Exception:
            expanded.append((t, v))

    for t, v in expanded:
        merged[t] = v

    out: Dict[str, Any] = {
        "sat_id": pkt.sat_id,
        "version": pkt.version,
        "tlvs": merged,
    }
    return out


def build_tlm_frame(sat: Satellite) -> bytes:
    """
    Build a telemetry (TLM) frame for a satellite.

    Outer frame remains:
        SYNC | SAT_ID | TYPE_TLM | SEQ | LEN | PAYLOAD | CRC16

    PAYLOAD is a DownlinkPacket containing TLVs. Sometimes TLVs are wrapped in a
    compressed TLV to simulate bandwidth optimization.

    Intentional realism bugs supported elsewhere:
      - A debug TLV may leak sensitive state under fault/low-power edge cases.
      - DownlinkPacket weak_tag does not cover TLVs.
    """
    mode_map: Dict[Mode, int] = {"SAFE": 0, "NOMINAL": 1, "SCIENCE": 2, "DIAGNOSTIC": 3}
    mode_val = mode_map.get(sat.mode, 0)
    power_val = max(0, min(100, sat.power_level))
    temp_x2 = int(sat.temp_c * 2.0)

    base = b""
    base += tlv_encode(DL_TLV_MODE, bytes([mode_val & 0xFF]))
    base += tlv_encode(DL_TLV_POWER, bytes([power_val & 0xFF]))
    base += tlv_encode(DL_TLV_TEMP_X2, temp_x2.to_bytes(2, "little", signed=True))

    orbit_blob = (
        int(sat.orbit.semi_major_km * 10).to_bytes(2, "little", signed=False)
        + int(sat.orbit.inclination_deg * 10).to_bytes(2, "little", signed=False)
        + int(sat.orbit.raan_deg * 10).to_bytes(2, "little", signed=False)
    )
    base += tlv_encode(DL_TLV_ORBIT, orbit_blob)

    status_bits = 0
    if sat.compromised:
        status_bits |= 0x01
    if sat.faulted:
        status_bits |= 0x02
    status_tlv = tlv_encode(DL_TLV_STATUS, bytes([status_bits & 0xFF]))

    leak_debug = (sat.mode == "DIAGNOSTIC") or (sat.faulted and sat.power_level < 15)
    debug_tlv = b""
    if leak_debug:
        debug = b""
        debug += (sat.last_tx_nonce & 0xFFFF).to_bytes(2, "little")
        debug += (sat.crosslink_nonce & 0xFFFF).to_bytes(2, "little")
        debug += (sat.fw_sig_prefix_len & 0xFF).to_bytes(1, "little")
        debug += bytes([1 if sat.allow_unsigned_fw else 0])
        debug_tlv = tlv_encode(DL_TLV_DEBUG, debug)

    should_compress = (sat.power_level < 25) or (sat.mode == "SCIENCE")
    if should_compress:
        compressed = zlib.compress(base)
        tlvs = tlv_encode(DL_TLV_COMPRESSED, compressed) + status_tlv + debug_tlv
    else:
        tlvs = base + status_tlv + debug_tlv

    weak_tag = DownlinkPacket.compute_weak_tag(DOWNLINK_VERSION, sat.sat_id, len(tlvs))
    inner = DownlinkPacket(
        version=DOWNLINK_VERSION,
        sat_id=sat.sat_id,
        tlvs=tlvs,
        weak_tag=weak_tag,
    ).encode()

    seq = sat.next_seq()
    return _build_frame(sat.sat_id, TYPE_TLM, seq, inner)


def _build_frame(sat_id: int, ftype: int, seq: int, payload: bytes) -> bytes:
    """
    Build a raw protocol frame with CRC.
    """
    header = (
        SYNC
        + bytes([sat_id, ftype])
        + seq.to_bytes(2, "little")
        + len(payload).to_bytes(2, "little")
    )
    crc = crc16(header + payload)
    return header + payload + crc.to_bytes(2, "little")
