from __future__ import annotations

from typing import Dict, Literal
import zlib

SYNC = b"\xd0\x0d"
TYPE_CMD = 0x01
TYPE_TLM = 0x02

SAT_ID_D00M_01 = 0x01
SAT_ID_D00M_02 = 0x02
SAT_ID_K00KIES_01 = 0x11
SAT_ID_K00KIES_02 = 0x12

Mode = Literal["SAFE", "NOMINAL", "SCIENCE", "DIAGNOSTIC"]


def crc16(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFF


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
    # signed int8
    return bytes([0x02, (delta & 0xFF)])


def build_temp_offset_payload(delta: int) -> bytes:
    # signed int8
    return bytes([0x03, (delta & 0xFF)])


def build_send_crosslink_payload(dst_sat_id: int, blob: bytes) -> bytes:
    length = len(blob)
    if length > 255:
        raise ValueError("crosslink payload too large for 1-byte length")
    return bytes([0x10, dst_sat_id & 0xFF, length]) + blob


def build_read_crosslink_summary_payload() -> bytes:
    return bytes([0x11])


def parse_tlm_payload(payload: bytes) -> dict:
    """
    Decode TLM payload:
      [ mode(1) | power(1) | temp_c*2 (int16 LE) ]
    """
    if len(payload) != 4:
        return {"raw_hex": payload.hex()}
    mode_val = payload[0]
    power = payload[1]
    temp_raw = int.from_bytes(payload[2:4], "little", signed=True)
    temp_c = temp_raw / 2.0

    inv_mode_map = {0: "SAFE", 1: "NOMINAL", 2: "SCIENCE", 3: "DIAGNOSTIC"}
    mode_name = inv_mode_map.get(mode_val, f"UNKNOWN({mode_val})")
    return {
        "mode": mode_name,
        "power": power,
        "temp_c": temp_c,
    }
