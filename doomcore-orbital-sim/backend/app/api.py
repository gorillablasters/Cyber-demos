import os
import uuid
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .world_manager import WorldManager


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


SID_COOKIE = "doom_sid"
SID_HEADER = "X-SESSION-ID"


def _extract_sid(request: Request) -> Optional[str]:
    sid = request.headers.get(SID_HEADER)
    if sid:
        return sid.strip()
    sid = request.cookies.get(SID_COOKIE)
    if sid:
        return sid.strip()
    return None


manager = WorldManager(
    ttl_seconds=int(os.getenv("WORLD_TTL_SECONDS", str(6 * 60 * 60)))
)


@app.middleware("http")
async def sid_middleware(request: Request, call_next):
    """Ensure every request has an SID.

    Browser UI uses a cookie; CLI can supply an explicit SID via header.
    """
    sid = _extract_sid(request)
    generated = False
    if not sid:
        sid = str(uuid.uuid4())
        generated = True

    request.state.sid = sid

    response: Response = await call_next(request)
    if generated:
        response.set_cookie(
            key=SID_COOKIE,
            value=sid,
            httponly=False,
            samesite="lax",
        )
    return response


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


@app.get("/api/sim/world")
def api_sim_world(request: Request):
    world = manager.get(request.state.sid)
    return {"ok": True, "world": world.world_status()}


@app.get("/api/sim/session")
def api_sim_session(request: Request):
    """Return the session id associated with this caller."""
    return {"ok": True, "sid": request.state.sid}


@app.post("/api/sim/reset")
def api_sim_reset(request: Request):
    """Reset the simulation for the current session."""
    world = manager.reset(request.state.sid)
    return {"ok": True, "world": world.world_status()}


@app.post("/api/sim/uplink")
def api_sim_uplink(request: Request, req: UplinkRequest):
    world = manager.get(request.state.sid)
    try:
        frame = bytes.fromhex(req.frame_hex)
    except ValueError:
        return {"ok": False, "error": "invalid frame_hex"}
    return world.handle_uplink_frame(frame)


@app.post("/api/sim/downlink")
def api_sim_downlink(request: Request, req: DownlinkRequest):
    world = manager.get(request.state.sid)
    frames = world.pop_downlink(req.sat_id, req.max_frames)
    return {"ok": True, "frames": frames}


@app.post("/api/sim/crosslink/send")
def api_sim_crosslink_send(request: Request, req: CrosslinkSend):
    world = manager.get(request.state.sid)
    try:
        payload = bytes.fromhex(req.payload_hex)
    except ValueError:
        return {"ok": False, "error": "invalid payload_hex"}
    world.send_crosslink(
        src_sat_id=req.src_sat_id,
        dst_sat_id=req.dst_sat_id,
        payload=payload,
    )
    return {"ok": True}


@app.post("/api/sim/crosslink/dump")
def api_sim_crosslink_dump(request: Request, req: CrosslinkDump):
    world = manager.get(request.state.sid)
    return world.dump_crosslink_inbox(req.sat_id, req.max_frames)


@app.get("/api/sim/events")
def api_sim_events(request: Request, since: Optional[float] = None, limit: int = 200):
    world = manager.get(request.state.sid)
    return world.get_events(since=since, limit=limit)


@app.get("/api/sim/firmware/{sat_id}")
def api_sim_firmware_status(request: Request, sat_id: int):
    world = manager.get(request.state.sid)
    return world.firmware_status(sat_id)


@app.post("/api/sim/firmware/upload")
def api_sim_firmware_upload(request: Request, req: FirmwareUpload):
    world = manager.get(request.state.sid)
    try:
        chunk = bytes.fromhex(req.chunk_hex)
    except ValueError:
        return {"ok": False, "error": "invalid chunk_hex"}
    return world.firmware_upload_chunk(req.sat_id, chunk)


@app.post("/api/sim/firmware/apply")
def api_sim_firmware_apply(request: Request, req: FirmwareApply):
    world = manager.get(request.state.sid)
    return world.firmware_apply(req.sat_id, req.claimed_hash)


@app.get("/api/sim/firmware/download/{sat_id}")
def api_sim_firmware_download(request: Request, sat_id: int):
    world = manager.get(request.state.sid)
    sat = world.sats.get(sat_id)
    if sat is None:
        return {"ok": False, "error": "unknown sat"}
    return {
        "ok": True,
        "sat_id": sat_id,
        "firmware_hex": sat.firmware_bank.hex(),
    }
