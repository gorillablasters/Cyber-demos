
import os
import socket
import base64
from typing import Optional

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DOOMSAT_HOST = os.getenv("DOOMSAT_HOST", "doomsat")
DOOMSAT_PORT = int(os.getenv("DOOMSAT_PORT", "7000"))

app = FastAPI(title="Operation Doomsday Groundstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def talk_to_sat(payload: bytes, recv_timeout: float = 1.0) -> bytes:
    """Open TCP connection to DOOMSAT, read banner, send payload, read until timeout."""
    s = socket.socket()
    s.settimeout(recv_timeout)
    s.connect((DOOMSAT_HOST, DOOMSAT_PORT))

    chunks = []
    # Attempt to read initial banner (non-fatal)
    try:
        banner = s.recv(1024)
        if banner:
            chunks.append(banner)
    except socket.timeout:
        pass

    # Send command payload
    s.sendall(payload)

    # Read until timeout
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

class CommandRequest(BaseModel):
    line: str  # e.g. "leak", "dump 0 512"

@app.post("/api/cmd")
def api_cmd(req: CommandRequest):
    line = req.line.strip()
    parts = line.split()
    if not parts:
        return {"ok": False, "error": "empty command"}

    cmd = parts[0].lower()

    if cmd == "dump":
        if len(parts) != 3:
            return {"ok": False, "error": "usage: dump <offset> <length>"}
        try:
            off = int(parts[1], 0)
            ln = int(parts[2], 0)
        except ValueError:
            return {"ok": False, "error": "offset/length must be integers"}
        payload = off.to_bytes(4, "little") + ln.to_bytes(4, "little")
        raw = talk_to_sat(b"\x01" + payload, recv_timeout=1.5)

    elif cmd == "leak":
        payload = b"A" * 200
        raw = talk_to_sat(b"\x03" + payload, recv_timeout=2.0)

    elif cmd == "reboot":
        raw = talk_to_sat(b"\x02", recv_timeout=1.0)

    elif cmd == "help":
        text = (
            "DOOMSAT GS HELP\n"
            "  dump <off> <len>  - request flash segment (cmd 0x01)\n"
            "  leak              - trigger memory leak (cmd 0x03)\n"
            "  reboot            - request reboot (cmd 0x02)\n"
            "  fw_info           - firmware update hints\n"
        )
        return {"ok": True, "text": text, "raw_hex": ""}

    elif cmd == "fw_info":
        text = (
            "Firmware Update Info:\n"
            "  - Underlying protocol uses command ID 0x04\n"
            "  - Only first 4 bytes of signature are checked (MFDO...)\n"
            "  - Upload via the firmware page in the UI.\n"
        )
        return {"ok": True, "text": text, "raw_hex": ""}

    else:
        return {"ok": False, "error": f"unknown command: {cmd}"}

    raw_hex = raw.hex()
    try:
        decoded = raw.decode("latin1", errors="ignore")
    except Exception:
        decoded = ""

    return {
        "ok": True,
        "text": decoded,
        "raw_hex": raw_hex,
        "raw_b64": base64.b64encode(raw).decode("ascii"),
    }

class DumpRequest(BaseModel):
    offset: int
    length: int

@app.post("/api/dump_raw")
def api_dump_raw(req: DumpRequest):
    payload = req.offset.to_bytes(4, "little") + req.length.to_bytes(4, "little")
    raw = talk_to_sat(b"\x01" + payload, recv_timeout=1.5)
    return {
        "ok": True,
        "raw_b64": base64.b64encode(raw).decode("ascii"),
        "size": len(raw),
    }

@app.post("/api/upload_firmware")
async def api_upload_firmware(file: UploadFile = File(...)):
    data = await file.read()
    raw = talk_to_sat(b"\x04" + data, recv_timeout=2.0)
    raw_hex = raw.hex()
    try:
        decoded = raw.decode("latin1", errors="ignore")
    except Exception:
        decoded = ""
    return {
        "ok": True,
        "text": decoded,
        "raw_hex": raw_hex,
        "raw_b64": base64.b64encode(raw).decode("ascii"),
    }
