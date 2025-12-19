from __future__ import annotations

import argparse
import json
import time
from typing import Optional

from .client import DoomGSClient
from . import radio
from . import secure
from . import tui as tui_mod


def cmd_world(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    data = c.world()
    print(json.dumps(data, indent=2))


def cmd_session(args: argparse.Namespace) -> None:
    """Print the active session id (SID) used by this client."""
    c = DoomGSClient(base_url=args.base_url)
    data = c.session_info()
    print(json.dumps(data, indent=2))


def cmd_reset(args: argparse.Namespace) -> None:
    """Reset the simulation for the current session."""
    c = DoomGSClient(base_url=args.base_url)
    data = c.reset_world()
    print(json.dumps(data, indent=2))


def cmd_events(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.events(since=args.since, limit=args.limit)
    print(json.dumps(res, indent=2))


def cmd_downlink(args: argparse.Namespace) -> None:
    """Fetch and decode downlink frames."""

    c = DoomGSClient(base_url=args.base_url)

    def once() -> None:
        res = c.downlink(sat_id=args.sat_id, max_frames=args.max_frames)
        frames = res.get("frames", []) if isinstance(res, dict) else []
        decoded = []
        for fh in frames:
            try:
                decoded.append(radio.decode_downlink_frame_hex(fh))
            except Exception:
                decoded.append({"frame_hex": fh, "error": "decode_failed"})
        out = {"ok": True, "count": len(decoded), "decoded": decoded}
        print(json.dumps(out, indent=2))

    if not args.watch:
        once()
        return

    interval = max(0.1, float(args.interval))
    try:
        while True:
            once()
            time.sleep(interval)
    except KeyboardInterrupt:
        return


def cmd_uplink_set_mode(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    mode = args.mode.upper()
    if args.seq is None:
        res = c.uplink_set_mode(args.sat_id, mode)  # type: ignore[arg-type]
    else:
        payload = radio.build_set_mode_payload(mode)  # type: ignore[arg-type]
        frame = radio.build_cmd_frame(args.sat_id, args.seq, payload)
        res = c.uplink_frame(frame)
    print(json.dumps(res, indent=2))


def cmd_uplink_nudge_power(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    if args.seq is None:
        res = c.uplink_nudge_power(args.sat_id, args.delta)
    else:
        payload = radio.build_nudge_power_payload(args.delta)
        frame = radio.build_cmd_frame(args.sat_id, args.seq, payload)
        res = c.uplink_frame(frame)
    print(json.dumps(res, indent=2))


def cmd_uplink_temp_offset(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    if args.seq is None:
        res = c.uplink_temp_offset(args.sat_id, args.delta)
    else:
        payload = radio.build_temp_offset_payload(args.delta)
        frame = radio.build_cmd_frame(args.sat_id, args.seq, payload)
        res = c.uplink_frame(frame)
    print(json.dumps(res, indent=2))


def cmd_uplink_drift_raan(args: argparse.Namespace) -> None:
    """
    Stage 9 helper: orbit drift manipulation.
    Sends CMD_ID 0x04 with a single unsigned delta byte.
    """
    c = DoomGSClient(base_url=args.base_url)
    sat_id = args.sat_id
    delta = args.delta & 0xFF
    if args.seq is None:
        seq = c._next_seq(sat_id)  # type: ignore[attr-defined]
    else:
        seq = args.seq
    payload = bytes([0x04, delta])
    frame = radio.build_cmd_frame(sat_id, seq, payload)
    res = c.uplink_frame(frame)
    print(json.dumps(res, indent=2))


def cmd_uplink_raw(args: argparse.Namespace) -> None:
    """
    Send a raw DOOMLINK frame (full header+payload+CRC) in hex.
    Great for replay and fuzzing. You are responsible for CRC/length.
    """
    c = DoomGSClient(base_url=args.base_url)
    try:
        frame = bytes.fromhex(args.frame_hex)
    except ValueError as e:
        raise SystemExit(f"Invalid hex: {e}")
    res = c.uplink_frame(frame)
    print(json.dumps(res, indent=2))


def cmd_xlink_send(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    dst: Optional[int]
    if args.dst.lower() in ("b", "broadcast", "*"):
        dst = None
    else:
        dst = int(args.dst, 0)
    res = c.crosslink_send(
        src_sat_id=args.src_sat_id,
        dst_sat_id=dst,
        payload_hex=args.payload_hex,
    )
    print(json.dumps(res, indent=2))


def cmd_xlink_dump(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.crosslink_dump(sat_id=args.sat_id, max_frames=args.max_frames)
    print(json.dumps(res, indent=2))


def cmd_firmware_status(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.firmware_status(sat_id=args.sat_id)
    print(json.dumps(res, indent=2))


def cmd_firmware_upload_chunk(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    try:
        chunk = bytes.fromhex(args.chunk_hex)
    except ValueError as e:
        raise SystemExit(f"Invalid hex: {e}")
    res = c.firmware_upload_chunk(sat_id=args.sat_id, chunk=chunk)
    print(json.dumps(res, indent=2))


def cmd_firmware_apply(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.firmware_apply(sat_id=args.sat_id, claimed_hash=args.claimed_hash)
    print(json.dumps(res, indent=2))


def cmd_firmware_download(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.firmware_download(sat_id=args.sat_id)
    print(json.dumps(res, indent=2))


def cmd_secure_xlink_build(args: argparse.Namespace) -> None:
    key = bytes.fromhex(args.key_hex)
    nonce = args.nonce
    plain = bytes.fromhex(args.plain_hex)
    cipher = secure.build_secure_crosslink(key, nonce, plain)
    out = {
        "key_hex": args.key_hex,
        "nonce": nonce,
        "plain_hex": args.plain_hex,
        "cipher_hex": cipher.hex(),
    }
    print(json.dumps(out, indent=2))


def cmd_secure_xlink_forge(args: argparse.Namespace) -> None:
    known_plain = bytes.fromhex(args.known_plain_hex)
    known_cipher = bytes.fromhex(args.known_cipher_hex)
    desired_plain = bytes.fromhex(args.desired_plain_hex)
    forged = secure.forge_secure_crosslink(known_plain, known_cipher, desired_plain)
    out = {
        "known_plain_hex": args.known_plain_hex,
        "known_cipher_hex": args.known_cipher_hex,
        "desired_plain_hex": args.desired_plain_hex,
        "forged_cipher_hex": forged.hex(),
    }
    print(json.dumps(out, indent=2))


def cmd_tui(args: argparse.Namespace) -> None:
    tui_mod.run_tui(base_url=args.base_url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="doomgs",
        description="MF DOOM-themed groundstation client for Doomcore Orbital Sim",
    )
    p.add_argument(
        "--base-url",
        help="Override DOOMGS_BASE_URL (default http://localhost:8000 or env DOOMGS_BASE_URL)",
        default=None,
    )

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("session", help="Show the active session id (SID)")
    sp.set_defaults(func=cmd_session)

    sp = sub.add_parser("reset", help="Reset the simulation for this SID")
    sp.set_defaults(func=cmd_reset)

    sp = sub.add_parser("world", help="Show world / constellation status")
    sp.set_defaults(func=cmd_world)

    sp = sub.add_parser("events", help="Show recent events log")
    sp.add_argument(
        "--since",
        type=float,
        default=None,
        help="Only events after this UNIX timestamp",
    )
    sp.add_argument("--limit", type=int, default=200, help="Max events to return")
    sp.set_defaults(func=cmd_events)

    sp = sub.add_parser("downlink", help="Pop and decode downlink telemetry frames")
    sp.add_argument(
        "--sat-id",
        type=int,
        default=None,
        help="Optional satellite ID to pop from (default: all)",
    )
    sp.add_argument(
        "--max-frames",
        type=int,
        default=10,
        help="Maximum frames to pop per request",
    )
    sp.add_argument(
        "--watch",
        action="store_true",
        help="Continuously poll downlink until Ctrl-C",
    )
    sp.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval seconds (with --watch)",
    )
    sp.set_defaults(func=cmd_downlink)

    sp = sub.add_parser("uplink-set-mode", help="Send SET_MODE command to a satellite")
    sp.add_argument("sat_id", type=int, help="Satellite ID (e.g. 1, 2, 17, 18)")
    sp.add_argument(
        "mode",
        choices=[
            "SAFE",
            "NOMINAL",
            "SCIENCE",
            "DIAGNOSTIC",
            "safe",
            "nominal",
            "science",
            "diagnostic",
        ],
        help="Mode name",
    )
    sp.add_argument(
        "--seq",
        type=int,
        default=None,
        help="Optional explicit sequence number (for replay experiments)",
    )
    sp.set_defaults(func=cmd_uplink_set_mode)

    sp = sub.add_parser(
        "uplink-nudge-power", help="Adjust satellite power level by a delta"
    )
    sp.add_argument("sat_id", type=int)
    sp.add_argument("delta", type=int, help="Delta in percent (e.g. -10, +5)")
    sp.add_argument(
        "--seq",
        type=int,
        default=None,
        help="Optional explicit sequence number (for replay experiments)",
    )
    sp.set_defaults(func=cmd_uplink_nudge_power)

    sp = sub.add_parser(
        "uplink-temp-offset", help="Apply temp calibration offset to satellite"
    )
    sp.add_argument("sat_id", type=int)
    sp.add_argument("delta", type=int, help="Delta in degrees C (approx)")
    sp.add_argument(
        "--seq",
        type=int,
        default=None,
        help="Optional explicit sequence number (for replay experiments)",
    )
    sp.set_defaults(func=cmd_uplink_temp_offset)

    sp = sub.add_parser(
        "uplink-drift-raan", help="Adjust orbit RAAN via DRIFT_RAAN command (Stage 9)"
    )
    sp.add_argument("sat_id", type=int)
    sp.add_argument(
        "delta",
        type=int,
        help="Delta degrees (0-255). Interpreted unsigned by the satellite (bug).",
    )
    sp.add_argument(
        "--seq",
        type=int,
        default=None,
        help="Optional explicit sequence number (for replay experiments)",
    )
    sp.set_defaults(func=cmd_uplink_drift_raan)

    sp = sub.add_parser("uplink-raw", help="Send a raw DOOMLINK frame (hex)")
    sp.add_argument("frame_hex", help="Full DOOMLINK frame in hex")
    sp.set_defaults(func=cmd_uplink_raw)

    sp = sub.add_parser(
        "xlink-send", help="Send a crosslink frame from one sat to another"
    )
    sp.add_argument("src_sat_id", type=int, help="Source satellite ID")
    sp.add_argument(
        "dst",
        help="Destination satellite ID (e.g. 1, 0x11) or 'broadcast'",
    )
    sp.add_argument(
        "payload_hex", help="Crosslink payload hex (plain; sim encrypts if needed)"
    )
    sp.set_defaults(func=cmd_xlink_send)

    sp = sub.add_parser("xlink-dump", help="Dump crosslink inbox for a satellite")
    sp.add_argument("sat_id", type=int)
    sp.add_argument("--max-frames", type=int, default=20)
    sp.set_defaults(func=cmd_xlink_dump)

    sp = sub.add_parser("firmware-status", help="Show firmware status for a satellite")
    sp.add_argument("sat_id", type=int)
    sp.set_defaults(func=cmd_firmware_status)

    sp = sub.add_parser(
        "firmware-upload-chunk", help="Upload a firmware chunk (hex) to a satellite"
    )
    sp.add_argument("sat_id", type=int)
    sp.add_argument("chunk_hex", help="Firmware bytes in hex")
    sp.set_defaults(func=cmd_firmware_upload_chunk)

    sp = sub.add_parser(
        "firmware-apply", help="Apply staged firmware with a claimed hash"
    )
    sp.add_argument("sat_id", type=int)
    sp.add_argument("claimed_hash", help="Claimed firmware hash (hex string)")
    sp.set_defaults(func=cmd_firmware_apply)

    sp = sub.add_parser(
        "firmware-download", help="Download active firmware image for a satellite"
    )
    sp.add_argument("sat_id", type=int)
    sp.set_defaults(func=cmd_firmware_download)

    sp = sub.add_parser(
        "secure-xlink-build",
        help="Build ciphertext matching the sim's secure crosslink scheme",
    )
    sp.add_argument("key_hex", help="Key bytes (hex) for keystream")
    sp.add_argument("nonce", type=int, help="Nonce value (int)")
    sp.add_argument("plain_hex", help="Plaintext bytes (hex)")
    sp.set_defaults(func=cmd_secure_xlink_build)

    sp = sub.add_parser("tui", help="Launch curses TUI")
    sp.set_defaults(func=cmd_tui)

    sp = sub.add_parser(
        "secure-xlink-forge",
        help="Forge ciphertext from (plain,cipher) leak without knowing the key",
    )
    sp.add_argument("known_plain_hex", help="Known plaintext (hex) from ENC log")
    sp.add_argument("known_cipher_hex", help="Known ciphertext (hex) from ENC log")
    sp.add_argument("desired_plain_hex", help="Desired plaintext to inject (hex)")
    sp.set_defaults(func=cmd_secure_xlink_forge)

    return p


def main() -> None:
    p = build_parser()
    args = p.parse_args()
    args.func(args)
