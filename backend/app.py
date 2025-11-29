# groundstation/backend/app.py
import os
import socket
import base64
import time
import zlib
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DOOMSAT_HOST = os.getenv("DOOMSAT_HOST", "doomsat")
DOOMSAT_PORT = int(os.getenv("DOOMSAT_PORT", "7000"))

# This must match the villain key in flash_init.py / doomcore.py
VILLAIN_KEY = b"villain_super_secret_key"

app = FastAPI(title="Operation Doomsday Groundstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def talk_to_sat(payload: bytes, recv_timeout: float = 1.0) -> bytes:
    """
    Open a TCP connection to DOOMSAT, read the boot banner,
    send payload, then read only the immediate response.
    """
    s = socket.socket()
    s.settimeout(recv_timeout)
    s.connect((DOOMSAT_HOST, DOOMSAT_PORT))

    chunks = []

    # 1) Read initial boot banner (non-fatal if it times out)
    try:
        banner = s.recv(2048)
        if banner:
            chunks.append(banner)
    except socket.timeout:
        pass

    # 2) Send the command
    s.sendall(payload)

    # 3) Short timeout so we only read the immediate response,
    #    not continuous telemetry spam.
    s.settimeout(0.4)

    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    except socket.timeout:
        pass
    finally:
        s.close()

    return b"".join(chunks)


def bytes_to_safe_text(b: bytes, limit: int = 4096) -> str:
    """
    Convert binary data into a readable text view:

    - Keep printable ASCII (32–126)
    - Convert NUL (0x00) to newline so flash strings appear on new lines
    - Drop other control characters
    """
    view = b[:limit]
    out = []
    for x in view:
        if 32 <= x < 127:
            out.append(chr(x))
        elif x == 0:
            out.append("\n")
        # else: drop
    s = "".join(out)
    if len(b) > limit:
        s += f"\n[+ {len(b) - limit} more bytes truncated]"
    return s


def bytes_to_hex_preview(b: bytes, limit: int = 1024) -> str:
    view = b[:limit]
    h = view.hex()
    if len(b) > limit:
        h += "...(truncated)"
    return h


class CommandRequest(BaseModel):
    line: str


class DumpRequest(BaseModel):
    offset: int
    length: int


@app.post("/api/cmd")
def api_cmd(req: CommandRequest):
    line = req.line.strip()
    parts = line.split()
    if not parts:
        return {"ok": False, "error": "empty command"}

    cmd = parts[0].lower()

    # --------------------------------------------------
    # Local meta-commands (handled by GS only)
    # --------------------------------------------------
    if cmd == "help":
        text = (
            "DOOMSAT GS HELP\n"
            "  dump <off> <len>  - request flash segment (secured)\n"
            "  leak              - trigger memory leak (cmd 0x03)\n"
            "  reboot            - request reboot (cmd 0x02)\n"
            "  fw_info           - firmware update hints\n"
            "  raw <hex bytes>   - send raw bytes to DOOMSAT (dangerous)\n"
        )
        return {"ok": True, "text": text, "raw_hex": "", "raw_b64": ""}

    if cmd == "fw_info":
        text = (
            "Firmware Update Info:\n"
            "  - Underlying protocol uses command ID 0x04\n"
            "  - Only first 4 bytes of signature are checked (MFDO...)\n"
            "  - Upload villain firmware via the firmware panel in the UI.\n"
        )
        return {"ok": True, "text": text, "raw_hex": "", "raw_b64": ""}

    # --------------------------------------------------
    # RAW command: send arbitrary bytes to DOOMSAT
    #   Usage: raw <hexbytes>
    #   Example: raw 010000000001000000
    # --------------------------------------------------
    if cmd == "raw":
        if len(parts) < 2:
            return {"ok": False, "error": "usage: raw <hexbytes>"}
        hex_str = "".join(parts[1:])
        try:
            raw_payload = bytes.fromhex(hex_str)
        except ValueError:
            return {"ok": False, "error": "invalid hex"}
        try:
            raw = talk_to_sat(raw_payload, recv_timeout=1.5)
        except Exception as e:
            return {"ok": False, "error": f"backend error talking to DOOMSAT: {e}"}
        safe_text = bytes_to_safe_text(raw)
        hex_preview = bytes_to_hex_preview(raw)
        b64_all = base64.b64encode(raw).decode("ascii")
        return {
            "ok": True,
            "text": safe_text,
            "raw_hex": hex_preview,
            "raw_b64": b64_all,
        }

    # --------------------------------------------------
    # Commands that talk to DOOMSAT with structured payloads
    # --------------------------------------------------
    try:
        # ----------------------------------------------
        # DUMP: now uses the "secure" path by default
        #   payload: offset(4) | length(4) | mac(4)
        #   mac = crc32(off|len|VILLAIN_KEY)  (but we DELIBERATELY
        #         miscompute here, so AUTH_FAIL from the sat)
        # ----------------------------------------------
        if cmd == "dump":
            if len(parts) != 3:
                return {"ok": False, "error": "usage: dump <offset> <length>"}
            try:
                off = int(parts[1], 0)
                ln = int(parts[2], 0)
            except ValueError:
                return {"ok": False, "error": "offset/length must be integers"}

            # Construct the "official" message (offset|len)
            msg = off.to_bytes(4, "little") + ln.to_bytes(4, "little")

            # Intentionally WRONG MAC for gameplay:
            #   we use only msg (no VILLAIN_KEY), so DOOMSAT
            #   will treat it as AUTH_FAIL.
            bad_mac = zlib.crc32(msg) & 0xFFFFFFFF
            payload = msg + bad_mac.to_bytes(4, "little")

            raw = talk_to_sat(b"\x01" + payload, recv_timeout=1.5)

        elif cmd == "leak":
            payload = b"A" * 200
            raw = talk_to_sat(b"\x03" + payload, recv_timeout=2.0)

        elif cmd == "reboot":
            raw = talk_to_sat(b"\x02", recv_timeout=1.0)

        else:
            return {"ok": False, "error": f"unknown command: {cmd}"}

    except Exception as e:
        return {"ok": False, "error": f"backend error talking to DOOMSAT: {e}"}

    safe_text = bytes_to_safe_text(raw)
    hex_preview = bytes_to_hex_preview(raw)
    b64_all = base64.b64encode(raw).decode("ascii")
    return {"ok": True, "text": safe_text, "raw_hex": hex_preview, "raw_b64": b64_all}


@app.post("/api/dump_raw")
def api_dump_raw(req: DumpRequest):
    """
    Raw API endpoint: still uses the "secure" dump format
    with the same intentionally wrong MAC. This keeps the
    HTTP API consistent with the CLI behavior.
    """
    off = req.offset
    ln = req.length
    msg = off.to_bytes(4, "little") + ln.to_bytes(4, "little")
    bad_mac = zlib.crc32(msg) & 0xFFFFFFFF
    payload = msg + bad_mac.to_bytes(4, "little")
    try:
        raw = talk_to_sat(b"\x01" + payload, recv_timeout=1.5)
    except Exception as e:
        return {"ok": False, "error": f"backend error talking to DOOMSAT: {e}"}
    return {
        "ok": True,
        "raw_b64": base64.b64encode(raw).decode("ascii"),
        "size": len(raw),
    }


@app.post("/api/upload_firmware")
async def api_upload_firmware(file: UploadFile = File(...)):
    data = await file.read()
    try:
        raw = talk_to_sat(b"\x04" + data, recv_timeout=2.0)
    except Exception as e:
        return {"ok": False, "error": f"backend error talking to DOOMSAT: {e}"}
    safe_text = bytes_to_safe_text(raw)
    hex_preview = bytes_to_hex_preview(raw)
    b64_all = base64.b64encode(raw).decode("ascii")
    return {"ok": True, "text": safe_text, "raw_hex": hex_preview, "raw_b64": b64_all}
