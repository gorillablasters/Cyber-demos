from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict

from .sim import World


@dataclass
class _Entry:
    world: World
    last_access_unix: float


class WorldManager:
    """Manage per-session simulation worlds.

    Each session (SID) gets an isolated :class:`~app.sim.World` instance so
    multiple players can solve the CTF without interfering with each other's
    progress.

    Entries are evicted after a configurable TTL to keep memory bounded.
    """

    def __init__(self, ttl_seconds: int = 6 * 60 * 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._worlds: Dict[str, _Entry] = {}

    def get(self, sid: str) -> World:
        """Return the world for *sid*, creating it if needed."""
        now = time.time()
        self._gc(now)
        entry = self._worlds.get(sid)
        if entry is None:
            entry = _Entry(world=World(), last_access_unix=now)
            self._worlds[sid] = entry
        else:
            entry.last_access_unix = now
        return entry.world

    def reset(self, sid: str) -> World:
        """Reset *sid* to a brand new world and return it."""
        now = time.time()
        self._worlds[sid] = _Entry(world=World(), last_access_unix=now)
        return self._worlds[sid].world

    def _gc(self, now: float) -> None:
        if not self._worlds:
            return
        dead = [
            sid
            for sid, entry in self._worlds.items()
            if now - entry.last_access_unix > self.ttl_seconds
        ]
        for sid in dead:
            self._worlds.pop(sid, None)
