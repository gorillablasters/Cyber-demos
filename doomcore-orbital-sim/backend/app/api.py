import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .sim import WORLD


DOOMSAT_HOST = os.getenv("DOOMSAT_HOST", "doomsat")
DOOMSAT_PORT = int(os.getenv("DOOMSAT_PORT", "7000"))

VILLAIN_KEY = b"villain_super_secret_key"

app = FastAPI(title="Operation Doomsday")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- request models ---------------------------------------------------------


class UplinkRequest(BaseModel):
    frame_hex: str


class DownlinkRequest(BaseModel):
    sat_id: Optional[int] = None
    max_frames: int = 10


class CrosslinkSend(BaseModel):
    src_sat_id: int
    dst_sat_id: Optional[int] = None
    payload_hex: str


class CrosslinkDump(BaseModel):
    sat_id: int
    max_frames: int = 20


class FirmwareUpload(BaseModel):
    sat_id: int
    chunk_hex: str


class FirmwareApply(BaseModel):
    sat_id: int
    claimed_hash: str


# --- endpoints --------------------------------------------------------------


@app.get("/api/sim/world")
def api_sim_world():
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    return {"ok": True, "world": WORLD.world_status()}


@app.post("/api/sim/uplink")
def api_sim_uplink(req: UplinkRequest):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    try:
        frame = bytes.fromhex(req.frame_hex)
    except ValueError:
        return {"ok": False, "error": "invalid frame_hex"}
    return WORLD.handle_uplink_frame(frame)


@app.post("/api/sim/downlink")
def api_sim_downlink(req: DownlinkRequest):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    frames = WORLD.pop_downlink(req.sat_id, req.max_frames)
    return {"ok": True, "frames": frames}


@app.post("/api/sim/crosslink/send")
def api_sim_crosslink_send(req: CrosslinkSend):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    try:
        payload = bytes.fromhex(req.payload_hex)
    except ValueError:
        return {"ok": False, "error": "invalid payload_hex"}
    WORLD.send_crosslink(
        src_sat_id=req.src_sat_id,
        dst_sat_id=req.dst_sat_id,
        payload=payload,
    )
    return {"ok": True}


@app.post("/api/sim/crosslink/dump")
def api_sim_crosslink_dump(req: CrosslinkDump):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    return WORLD.dump_crosslink_inbox(req.sat_id, req.max_frames)


@app.get("/api/sim/events")
def api_sim_events(since: Optional[float] = None, limit: int = 200):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    return WORLD.get_events(since=since, limit=limit)


@app.get("/api/sim/firmware/{sat_id}")
def api_sim_firmware_status(sat_id: int):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    return WORLD.firmware_status(sat_id)


@app.post("/api/sim/firmware/upload")
def api_sim_firmware_upload(req: FirmwareUpload):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    try:
        chunk = bytes.fromhex(req.chunk_hex)
    except ValueError:
        return {"ok": False, "error": "invalid chunk_hex"}
    return WORLD.firmware_upload_chunk(req.sat_id, chunk)


@app.post("/api/sim/firmware/apply")
def api_sim_firmware_apply(req: FirmwareApply):
    if WORLD is None:
        return {"ok": False, "error": "sim world not initialized"}
    return WORLD.firmware_apply(req.sat_id, req.claimed_hash)


@app.get("/api/sim/firmware/download/{sat_id}")
def api_sim_firmware_download(sat_id: int):
    if WORLD is None:
        return {"ok": False, "error": "sim world uninitialized"}
    sat = WORLD.sats.get(sat_id)
    if sat is None:
        return {"ok": False, "error": "unknown sat"}
    return {
        "ok": True,
        "sat_id": sat_id,
        "firmware_hex": sat.firmware_bank.hex(),
    }
