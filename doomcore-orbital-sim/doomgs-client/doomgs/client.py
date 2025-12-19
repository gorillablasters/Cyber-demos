from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
import requests

from .config import get_base_url
from . import radio


class DoomGSClient:
    def __init__(self, base_url: Optional[str] = None, sid: Optional[str] = None) -> None:
        self.base_url = base_url or get_base_url()
        self.session = requests.Session()
        self.sid = sid or os.getenv("DOOMGS_SID")
        if self.sid:
            # Allow multiple isolated player sessions against one backend.
            self.session.headers.update({"X-SESSION-ID": self.sid})
        self._seq: Dict[int, int] = {}

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        resp = self.session.get(self._url(path), params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(self._url(path), json=json_data, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def _next_seq(self, sat_id: int) -> int:
        v = self._seq.get(sat_id, 0) + 1
        self._seq[sat_id] = v & 0xFFFF
        return v

    def world(self) -> Dict[str, Any]:
        return self._get("/api/sim/world")

    def session_info(self) -> Dict[str, Any]:
        return self._get("/api/sim/session")

    def reset_world(self) -> Dict[str, Any]:
        return self._post("/api/sim/reset", {})

    def events(self, since: Optional[float] = None, limit: int = 200) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if since is not None:
            params["since"] = since
        return self._get("/api/sim/events", params=params)

    def uplink_frame(self, frame: bytes) -> Dict[str, Any]:
        return self._post("/api/sim/uplink", {"frame_hex": frame.hex()})

    def uplink_set_mode(self, sat_id: int, mode: radio.Mode) -> Dict[str, Any]:
        seq = self._next_seq(sat_id)
        payload = radio.build_set_mode_payload(mode)
        frame = radio.build_cmd_frame(sat_id, seq, payload)
        return self.uplink_frame(frame)

    def uplink_nudge_power(self, sat_id: int, delta: int) -> Dict[str, Any]:
        seq = self._next_seq(sat_id)
        payload = radio.build_nudge_power_payload(delta)
        frame = radio.build_cmd_frame(sat_id, seq, payload)
        return self.uplink_frame(frame)

    def uplink_temp_offset(self, sat_id: int, delta: int) -> Dict[str, Any]:
        seq = self._next_seq(sat_id)
        payload = radio.build_temp_offset_payload(delta)
        frame = radio.build_cmd_frame(sat_id, seq, payload)
        return self.uplink_frame(frame)

    def uplink_send_crosslink(
        self,
        src_sat_id: int,
        dst_sat_id: int,
        blob: bytes,
    ) -> Dict[str, Any]:
        seq = self._next_seq(src_sat_id)
        payload = radio.build_send_crosslink_payload(dst_sat_id, blob)
        frame = radio.build_cmd_frame(src_sat_id, seq, payload)
        return self.uplink_frame(frame)

    def downlink(
        self,
        sat_id: Optional[int] = None,
        max_frames: int = 10,
    ) -> Dict[str, Any]:
        return self._post(
            "/api/sim/downlink",
            {"sat_id": sat_id, "max_frames": max_frames},
        )

    def crosslink_send(
        self,
        src_sat_id: int,
        dst_sat_id: Optional[int],
        payload_hex: str,
    ) -> Dict[str, Any]:
        return self._post(
            "/api/sim/crosslink/send",
            {
                "src_sat_id": src_sat_id,
                "dst_sat_id": dst_sat_id,
                "payload_hex": payload_hex,
            },
        )

    def crosslink_dump(self, sat_id: int, max_frames: int = 20) -> Dict[str, Any]:
        return self._post(
            "/api/sim/crosslink/dump",
            {"sat_id": sat_id, "max_frames": max_frames},
        )

    def firmware_status(self, sat_id: int) -> Dict[str, Any]:
        return self._get(f"/api/sim/firmware/{sat_id}")

    def firmware_upload_chunk(self, sat_id: int, chunk: bytes) -> Dict[str, Any]:
        return self._post(
            "/api/sim/firmware/upload",
            {"sat_id": sat_id, "chunk_hex": chunk.hex()},
        )

    def firmware_apply(self, sat_id: int, claimed_hash: str) -> Dict[str, Any]:
        return self._post(
            "/api/sim/firmware/apply",
            {"sat_id": sat_id, "claimed_hash": claimed_hash},
        )

    def firmware_download(self, sat_id: int) -> Dict[str, Any]:
        return self._get(f"/api/sim/firmware/download/{sat_id}")
