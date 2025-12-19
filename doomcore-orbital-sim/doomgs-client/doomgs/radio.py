from __future__ import annotations

import time
import zlib
from dataclasses import dataclass
from typing import Dict, Literal, Optional, List, Tuple, Any

SYNC = b"\xd0\x0d"
TYPE_CMD = 0x01
TYPE_TLM = 0x02

SAT_ID_D00M_01 = 0x01
SAT_ID_D00M_02 = 0x02
SAT_ID_K00KIES_01 = 0x11
SAT_ID_K00KIES_02 = 0x12

Mode = Literal["SAFE", "NOMINAL", "SCIENCE", "DIAGNOSTIC"]


DOWNLINK_MAGIC = b"DL"
DOWNLINK_VERSION = 1

DL_TLV_MODE = 0x01
DL_TLV_POWER = 0x02
DL_TLV_TEMP_X2 = 0x03
DL_TLV_ORBIT = 0x04
DL_TLV_STATUS = 0x05
DL_TLV_COMPRESSED = 0x06
DL_TLV_DEBUG = 0x7F


def crc16(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFF


def tlv_decode_all(data: bytes) -> List[Tuple[int, bytes]]:
    out: List[Tuple[int, bytes]] = []
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


@dataclass
class ParsedFrame:
    """Parsed outer DOOMLINK frame."""

    sat_id: int
    ftype: int
    seq: int
    payload: bytes


def parse_frame(frame: bytes) -> ParsedFrame:
    """Parse and validate an outer DOOMLINK frame."""

    if len(frame) < 2 + 1 + 1 + 2 + 2 + 2:
        raise ValueError("frame too short")
    if frame[0:2] != SYNC:
        raise ValueError("bad SYNC")

    sat_id = frame[2]
    ftype = frame[3]
    seq = int.from_bytes(frame[4:6], "little")
    length = int.from_bytes(frame[6:8], "little")

    if 8 + length + 2 != len(frame):
        raise ValueError("length mismatch")

    payload = frame[8 : 8 + length]
    recv_crc = int.from_bytes(frame[8 + length : 8 + length + 2], "little")
    calc_crc = crc16(frame[0 : 8 + length])
    if recv_crc != calc_crc:
        raise ValueError("CRC mismatch")

    return ParsedFrame(sat_id=sat_id, ftype=ftype, seq=seq, payload=payload)


@dataclass
class DownlinkPacket:
    """Inner downlink telemetry packet carried inside the TLM payload."""

    version: int
    sat_id: int
    tlvs: bytes
    weak_tag: int

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


def build_cmd_frame(
    sat_id: int,
    seq: int,
    payload: bytes,
) -> bytes:
    header = (
        SYNC
        + bytes([sat_id, TYPE_CMD])
        + seq.to_bytes(2, "little")
        + len(payload).to_bytes(2, "little")
    )
    c = crc16(header + payload)
    return header + payload + c.to_bytes(2, "little")


def build_set_mode_payload(mode: Mode) -> bytes:
    mode_map: Dict[Mode, int] = {
        "SAFE": 0,
        "NOMINAL": 1,
        "SCIENCE": 2,
        "DIAGNOSTIC": 3,
    }
    return bytes([0x01, mode_map[mode]])


def build_nudge_power_payload(delta: int) -> bytes:
    return bytes([0x02, (delta & 0xFF)])


def build_temp_offset_payload(delta: int) -> bytes:
    return bytes([0x03, (delta & 0xFF)])


def build_send_crosslink_payload(dst_sat_id: int, blob: bytes) -> bytes:
    length = len(blob)
    if length > 255:
        raise ValueError("crosslink payload too large for 1-byte length")
    return bytes([0x10, dst_sat_id & 0xFF, length]) + blob


def build_read_crosslink_summary_payload() -> bytes:
    return bytes([0x11])


def parse_tlm_payload(payload: bytes) -> dict:
    """Decode a telemetry payload.

    Supports both legacy 4-byte payloads and the newer TLV-based DownlinkPacket.
    """

    if payload.startswith(DOWNLINK_MAGIC):
        try:
            pkt = DownlinkPacket.decode(payload)
        except Exception:
            return {"raw_hex": payload.hex()}

        try:
            tlvs = tlv_decode_all(pkt.tlvs)
        except Exception:
            return {"raw_hex": payload.hex()}

        expanded: List[Tuple[int, bytes]] = []
        for t, v in tlvs:
            if t != DL_TLV_COMPRESSED:
                expanded.append((t, v))
                continue

            try:
                d = zlib.decompressobj()
                plain = d.decompress(v)
                trailing = d.unused_data
                combined = plain + trailing
                inner = tlv_decode_all(combined)
                expanded.extend(inner)
            except Exception:
                expanded.append((t, v))

        merged: Dict[int, bytes] = {}
        for t, v in expanded:
            merged[t] = v

        inv_mode_map = {0: "SAFE", 1: "NOMINAL", 2: "SCIENCE", 3: "DIAGNOSTIC"}
        out: Dict[str, Any] = {
            "sat_id": pkt.sat_id,
            "version": pkt.version,
            "tlvs_raw": {str(k): merged[k].hex() for k in merged.keys()},
        }

        if DL_TLV_MODE in merged and len(merged[DL_TLV_MODE]) >= 1:
            mv = merged[DL_TLV_MODE][0]
            out["mode"] = inv_mode_map.get(mv, f"UNKNOWN({mv})")

        if DL_TLV_POWER in merged and len(merged[DL_TLV_POWER]) >= 1:
            out["power"] = merged[DL_TLV_POWER][0]

        if DL_TLV_TEMP_X2 in merged and len(merged[DL_TLV_TEMP_X2]) >= 2:
            tr = int.from_bytes(merged[DL_TLV_TEMP_X2][:2], "little", signed=True)
            out["temp_c"] = tr / 2.0

        if DL_TLV_ORBIT in merged and len(merged[DL_TLV_ORBIT]) >= 6:
            sm = (
                int.from_bytes(merged[DL_TLV_ORBIT][0:2], "little", signed=False) / 10.0
            )
            inc = (
                int.from_bytes(merged[DL_TLV_ORBIT][2:4], "little", signed=False) / 10.0
            )
            raan = (
                int.from_bytes(merged[DL_TLV_ORBIT][4:6], "little", signed=False) / 10.0
            )
            out["orbit"] = {
                "semi_major_km": sm,
                "inclination_deg": inc,
                "raan_deg": raan,
            }

        if DL_TLV_STATUS in merged and len(merged[DL_TLV_STATUS]) >= 1:
            sb = merged[DL_TLV_STATUS][0]
            out["status_bits"] = sb
            out["compromised"] = bool(sb & 0x01)
            out["faulted"] = bool(sb & 0x02)

        if DL_TLV_DEBUG in merged:
            out["debug_hex"] = merged[DL_TLV_DEBUG].hex()

        return out

    if len(payload) != 4:
        return {"raw_hex": payload.hex()}

    mode_val = payload[0]
    power = payload[1]
    temp_raw = int.from_bytes(payload[2:4], "little", signed=True)
    temp_c = temp_raw / 2.0

    inv_mode_map = {0: "SAFE", 1: "NOMINAL", 2: "SCIENCE", 3: "DIAGNOSTIC"}
    mode_name = inv_mode_map.get(mode_val, f"UNKNOWN({mode_val})")
    return {"mode": mode_name, "power": power, "temp_c": temp_c}


def decode_downlink_frame_hex(frame_hex: str) -> Dict[str, Any]:
    """Decode a full outer frame hex string into structured telemetry."""
    frame = bytes.fromhex(frame_hex)
    pf = parse_frame(frame)
    out: Dict[str, Any] = {
        "sat_id": pf.sat_id,
        "type": pf.ftype,
        "seq": pf.seq,
        "payload_hex": pf.payload.hex(),
        "frame_hex": frame_hex,
    }
    if pf.ftype == TYPE_TLM:
        out["telemetry"] = parse_tlm_payload(pf.payload)
    else:
        out["telemetry"] = None
    return out
