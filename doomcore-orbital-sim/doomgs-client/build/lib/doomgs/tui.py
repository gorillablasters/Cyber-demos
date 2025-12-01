from __future__ import annotations

import curses
import time
from typing import Optional

from .client import DoomGSClient


MF_DOOM_MASK = [
    "   ____  ____   ___   ___  __  __ ",
    "  |  _ \\|  _ \\ / _ \\ / _ \\|  \\/  |",
    "  | | | | | | | | | | | | | |\\/| |",
    "  | |_| | |_| | |_| | |_| | |  | |",
    "  |____/|____/ \\___/ \\___/|_|  |_|",
]


def _draw_header(stdscr, width: int) -> None:
    for i, line in enumerate(MF_DOOM_MASK):
        stdscr.addstr(i, max(0, (width - len(line)) // 2), line, curses.A_BOLD)
    stdscr.addstr(
        len(MF_DOOM_MASK),
        0,
        " DOOMSTATION-PRIME :: Ground Ops Console (TUI)",
        curses.A_BOLD,
    )


def _draw_world(stdscr, y: int, world: dict) -> int:
    stdscr.addstr(y, 0, "Satellites:", curses.A_UNDERLINE)
    y += 1
    for sat in sorted(world.get("satellites", []), key=lambda s: s["sat_id"]):
        line = (
            f"  [{sat['sat_id']:02X}] {sat['name']:<12} "
            f"mode={sat['mode']:<10} "
            f"power={sat['power_level']:3d}% "
            f"temp={sat['temp_c']:5.1f}C"
        )
        if sat.get("compromised"):
            line += "  <COMPROMISED>"
        stdscr.addstr(y, 0, line[: curses.COLS - 1])
        y += 1
    return y


def _draw_events(stdscr, y: int, height: int, events: list[dict]) -> None:
    stdscr.addstr(y, 0, "Recent Events:", curses.A_UNDERLINE)
    y += 1
    max_lines = height - y - 2
    tail = events[-max_lines:] if max_lines > 0 else events
    for ev in tail:
        line = (
            f"{time.strftime('%H:%M:%S', time.localtime(ev['ts']))} "
            f"{ev['type'].upper():<9} "
            f"sat={ev['sat_id']} :: {ev['detail']}"
        )
        stdscr.addstr(y, 0, line[: curses.COLS - 1])
        y += 1


def run_tui(base_url: Optional[str] = None) -> None:
    client = DoomGSClient(base_url=base_url)

    def _main(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(500)

        events: list[dict] = []
        last_ts: Optional[float] = None

        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()

            # header
            _draw_header(stdscr, width)
            y = len(MF_DOOM_MASK) + 2

            # world
            try:
                w = client.world()["world"]
            except Exception as e:  # noqa: BLE001
                stdscr.addstr(y, 0, f"Error: {e}")
                stdscr.refresh()
                time.sleep(1)
                continue

            y = _draw_world(stdscr, y, w)

            # events poll
            try:
                ev_data = client.events(since=last_ts, limit=50)
                if ev_data.get("ok"):
                    new_evs = ev_data["events"]
                    events.extend(new_evs)
                    events[:] = events[-200:]
                    if new_evs:
                        last_ts = new_evs[-1]["ts"]
            except Exception:
                pass

            _draw_events(stdscr, y + 1, height, events)

            # footer / help
            footer = "[Q]uit  [1] D00M-01 SAFE  [2] D00M-01 NOMINAL  [3] D00M-02 ➜ K00KIES-02 ping"
            stdscr.addstr(
                height - 1,
                0,
                footer[: width - 1],
                curses.A_REVERSE,
            )

            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                break
            elif ch == ord("1"):
                try:
                    client.uplink_set_mode(1, "SAFE")
                except Exception:
                    pass
            elif ch == ord("2"):
                try:
                    client.uplink_set_mode(1, "NOMINAL")
                except Exception:
                    pass
            elif ch == ord("3"):
                try:
                    client.uplink_send_crosslink(
                        src_sat_id=2,
                        dst_sat_id=18,
                        blob=b"doom_ping",
                    )
                except Exception:
                    pass

    curses.wrapper(_main)
