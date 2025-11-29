import os, socket, base64
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DOOMSAT_HOST = os.getenv("DOOMSAT_HOST", "doomsat")
DOOMSAT_PORT = int(os.getenv("DOOMSAT_PORT", "7000"))

app = FastAPI(title="Operation Doomsday Groundstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def talk_to_sat(payload: bytes, recv_timeout: float = 1.0) -> bytes:
    s = socket.socket()
    s.settimeout(0.2)
    s.connect((DOOMSAT_HOST, DOOMSAT_PORT))

    # Step 1: Read and discard boot + telemetry noise for 200ms
    try:
        while True:
            junk = s.recv(4096)
            if not junk:
                break
            # stop flushing once we see the boot_COMPLETE marker OR too much noise
            if b"BOOT" in junk or b"DOOMCORE" in junk:
                break
    except socket.timeout:
        pass

    # Step 2: Send the command
    s.sendall(payload)

    # Step 3: Capture ONLY the command response
    # Look for [DOOMCORE] prefix that marks command replies.
    s.settimeout(recv_timeout)
    chunks = []
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            # Break if we detect a command response header
            if b"DOOMCORE" in chunk:
                # Allow a bit more for the rest of the response
                s.settimeout(0.1)
                continue
    except socket.timeout:
        pass
    finally:
        s.close()

    return b"".join(chunks)


def bytes_to_safe_text(b: bytes, limit: int = 2048) -> str:
    """
    Convert binary data to text, but REMOVE non-printable chars instead of replacing them with dots.
    """
    view = b[:limit]
    s = "".join(chr(x) for x in view if 32 <= x < 127)  # REMOVE non-printables
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
    if cmd == "help":
        text = (
            "DOOMSAT GS HELP\n"
            "  dump <off> <len>  - request flash segment (cmd 0x01)\n"
            "  leak              - trigger memory leak (cmd 0x03)\n"
            "  reboot            - request reboot (cmd 0x02)\n"
            "  fw_info           - firmware update hints\n"
        )
        return {"ok": True, "text": text, "raw_hex": "", "raw_b64": ""}
    if cmd == "fw_info":
        text = (
            "Firmware Update Info:\n"
            "  - Underlying protocol uses command ID 0x04\n"
            "  - Only first 4 bytes of signature are checked (MFDO...)\n"
            "  - Upload via the firmware page in the UI.\n"
        )
        return {"ok": True, "text": text, "raw_hex": "", "raw_b64": ""}
    try:
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
    payload = req.offset.to_bytes(4, "little") + req.length.to_bytes(4, "little")
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
