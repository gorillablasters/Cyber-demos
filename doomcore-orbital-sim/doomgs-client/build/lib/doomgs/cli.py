from __future__ import annotations

import argparse
import json
from typing import Optional

from .client import DoomGSClient
from . import radio
from . import secure


def cmd_world(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    data = c.world()
    print(json.dumps(data, indent=2))


def cmd_events(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    data = c.events(limit=args.limit)
    print(json.dumps(data, indent=2))


def cmd_uplink_set_mode(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.uplink_set_mode(args.sat_id, args.mode.upper())
    print(json.dumps(res, indent=2))


def cmd_uplink_nudge_power(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.uplink_nudge_power(args.sat_id, args.delta)
    print(json.dumps(res, indent=2))


def cmd_uplink_temp_offset(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.uplink_temp_offset(args.sat_id, args.delta)
    print(json.dumps(res, indent=2))


def cmd_downlink(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    sat_id: Optional[int] = args.sat_id
    res = c.downlink(sat_id=sat_id, max_frames=args.max_frames)
    print(json.dumps(res, indent=2))


def cmd_xlink_send(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    dst = None if args.broadcast else args.dst_sat_id
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
    res = c.firmware_status(args.sat_id)
    print(json.dumps(res, indent=2))


def cmd_firmware_download(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.firmware_download(args.sat_id)
    print(json.dumps(res, indent=2))


def cmd_firmware_upload_hex(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    chunk = bytes.fromhex(args.chunk_hex.strip())
    res = c.firmware_upload_chunk(args.sat_id, chunk)
    print(json.dumps(res, indent=2))


def cmd_firmware_apply(args: argparse.Namespace) -> None:
    c = DoomGSClient(base_url=args.base_url)
    res = c.firmware_apply(args.sat_id, args.claimed_hash)
    print(json.dumps(res, indent=2))


def cmd_secure_xlink_build(args: argparse.Namespace) -> None:
    key = args.key.encode()
    nonce = args.nonce
    plain = bytes.fromhex(args.plain_hex.strip())
    cipher = secure.build_secure_crosslink(key, nonce, plain)
    print(cipher.hex())


def cmd_tui(args: argparse.Namespace) -> None:
    from . import tui

    tui.run_tui(base_url=args.base_url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="doomgs")
    p.add_argument(
        "--base-url",
        default=None,
        help="Backend base URL (default: env DOOMGS_BASE_URL or http://localhost:8000)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # world
    sp = sub.add_parser("world", help="Show satellite + GS status")
    sp.set_defaults(func=cmd_world)

    # events
    sp = sub.add_parser("events", help="Show recent RF/events")
    sp.add_argument("--limit", type=int, default=50)
    sp.set_defaults(func=cmd_events)

    # uplink set-mode
    sp = sub.add_parser("uplink-set-mode", help="Send SET_MODE uplink")
    sp.add_argument("sat_id", type=int)
    sp.add_argument("mode", choices=["SAFE", "NOMINAL", "SCIENCE", "DIAGNOSTIC"])
    sp.set_defaults(func=cmd_uplink_set_mode)

    # uplink nudge power
    sp = sub.add_parser("uplink-nudge-power", help="Adjust power level")
    sp.add_argument("sat_id", type=int)
    sp.add_argument("delta", type=int)
    sp.set_defaults(func=cmd_uplink_nudge_power)

    # uplink temp offset
    sp = sub.add_parser("uplink-temp-offset", help="Adjust temp offset")
    sp.add_argument("sat_id", type=int)
    sp.add_argument("delta", type=int)
    sp.set_defaults(func=cmd_uplink_temp_offset)

    # downlink
    sp = sub.add_parser("downlink", help="Pop telemetry frames")
    sp.add_argument("--sat-id", type=int, default=None)
    sp.add_argument("--max-frames", type=int, default=10)
    sp.set_defaults(func=cmd_downlink)

    # crosslink send
    sp = sub.add_parser("xlink-send", help="Send crosslink frame (raw payload hex)")
    sp.add_argument("src_sat_id", type=int)
    sp.add_argument("--dst-sat-id", type=int)
    sp.add_argument("--broadcast", action="store_true")
    sp.add_argument("payload_hex", help="hex payload, e.g. 646f6f6d")
    sp.set_defaults(func=cmd_xlink_send)

    # crosslink dump
    sp = sub.add_parser("xlink-dump", help="Dump crosslink inbox")
    sp.add_argument("sat_id", type=int)
    sp.add_argument("--max-frames", type=int, default=20)
    sp.set_defaults(func=cmd_xlink_dump)

    # firmware status
    sp = sub.add_parser("firmware-status", help="Show firmware status")
    sp.add_argument("sat_id", type=int)
    sp.set_defaults(func=cmd_firmware_status)

    # firmware download
    sp = sub.add_parser("firmware-download", help="Download staged firmware")
    sp.add_argument("sat_id", type=int)
    sp.set_defaults(func=cmd_firmware_download)

    # firmware upload hex
    sp = sub.add_parser("firmware-upload-hex", help="Upload firmware chunk as hex")
    sp.add_argument("sat_id", type=int)
    sp.add_argument("chunk_hex", help="hex bytes of firmware chunk")
    sp.set_defaults(func=cmd_firmware_upload_hex)

    # firmware apply
    sp = sub.add_parser(
        "firmware-apply", help="Apply staged firmware with claimed hash"
    )
    sp.add_argument("sat_id", type=int)
    sp.add_argument("claimed_hash", help="claimed hex hash (can be truncated)")
    sp.set_defaults(func=cmd_firmware_apply)

    # secure crosslink builder
    sp = sub.add_parser(
        "secure-xlink-build", help="Build secure ciphertext from key/nonce/plain_hex"
    )
    sp.add_argument("key", help="ASCII key (e.g. D00M02_KEY)")
    sp.add_argument("nonce", type=int, help="nonce integer as seen in events")
    sp.add_argument("plain_hex", help="plaintext bytes (hex)")
    sp.set_defaults(func=cmd_secure_xlink_build)

    # TUI
    sp = sub.add_parser("tui", help="Launch curses TUI")
    sp.set_defaults(func=cmd_tui)

    return p


def main() -> None:
    p = build_parser()
    args = p.parse_args()
    args.func(args)
