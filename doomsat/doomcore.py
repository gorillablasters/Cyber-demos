import socket
import time
import struct
import threading
import os
import zlib
from pathlib import Path

# Protocol constants from the shared protocol module
from protocol import HEADER, TYPE_POWER, TYPE_TEMP, TYPE_DANGER

# initialize flash and flags (creates flash.bin etc.)
import flash_init

MEM_DIR = Path("/opt/doomsat/memory")
FLASH = MEM_DIR / "flash.bin"
FLAGS_DIR = MEM_DIR / "flags"
RAM = MEM_DIR / "ram.bin"  # for Stage 5 / RAM leak later if desired

LISTEN_ADDR = ("0.0.0.0", 7000)

# Villain key for "secure" operations (Stage 3+)
VILLAIN_KEY = b"villain_super_secret_key"


# ---------------------------------------------------------------------------
# Helper: simple CRC-8 for DOOM-FRAME
#   frame = HEADER | LEN | TYPE | PAYLOAD | CRC
# ---------------------------------------------------------------------------
def crc8(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
    return c & 0xFF


def build_frame(t: int, payload: bytes) -> bytes:
    body = bytes([t]) + payload
    length = len(body).to_bytes(1, "little")
    c = crc8(body).to_bytes(1, "little")
    return HEADER + length + body + c


# ---------------------------------------------------------------------------
# Stage 2: Telemetry scrambler (LFSR-based)
#   - We scramble special telemetry payloads with an 8-bit LFSR
#   - Poly: x^8 + x^5 + x^4 + 1 => 0x31
#   - Seed derived from the "count" index in the telemetry loop
# ---------------------------------------------------------------------------
def lfsr_step(state: int) -> int:
    # Poly bits at taps 7, 4, 3, 0 (0-indexed)
    feedback = ((state >> 7) ^ (state >> 4) ^ (state >> 3) ^ state) & 1
    return ((state << 1) & 0xFF) | feedback


def lfsr_scramble(data: bytes, seed: int) -> bytes:
    s = seed & 0xFF
    out = []
    for b in data:
        out.append(b ^ s)
        s = lfsr_step(s)
    return bytes(out)


# ---------------------------------------------------------------------------
# Telemetry loop:
#   - Periodically sends power and temp
#   - Occasionally sends a "danger" frame whose payload is LFSR-scrambled
#     flag data (Stage 2).
# ---------------------------------------------------------------------------
def telemetry_loop(conn):
    count = 0
    while True:
        # send power
        p = struct.pack("<f", 99.5)  # fake power reading
        try:
            conn.send(build_frame(TYPE_POWER, p))
        except Exception:
            break
        time.sleep(0.4)

        # send temp
        t = struct.pack("<f", 12.3 + (count % 5))
        try:
            conn.send(build_frame(TYPE_TEMP, t))
        except Exception:
            break
        time.sleep(0.4)

        # Occasionally send a "danger" / masked telemetry packet.
        # This is where Stage 2 data hides.
        if count % 11 == 0:
            try:
                # Optional external file for raw Stage 2 text
                # e.g. FLAGS_DIR / "stage2_raw.txt" containing: DOOM{only}
                secret = (FLAGS_DIR / "stage2_raw.txt").read_bytes().strip()
            except Exception:
                secret = b"DOOM{only}"

            # LFSR seed derived from count (reverse-engineerable from stream)
            seed = (0xA5 ^ (count * 11)) & 0xFF
            masked = lfsr_scramble(secret, seed)

            try:
                conn.send(build_frame(TYPE_DANGER, masked))
            except Exception:
                break

        time.sleep(0.2)
        count += 1


# ---------------------------------------------------------------------------
# Client handler:
#   - Stage 1: prints boot banner with XOR-masked block
#   - Stage 2: telemetry thread
#   - Stage 3 foundation: "secure" vs. insecure flash dump behavior
# ---------------------------------------------------------------------------
def handle_client(conn, addr):
    print("[DOOMCORE] connected:", addr)

    # ----- Stage 1: Boot banner + masked block (not in flash) -----
    boot = (
        b"[DOOMCORE BOOT] Mask restored...\n"
        b"[DOOMCORE BOOT] Villain Bootloader v1.3 (codename: OPERATION_DOOMSDAY)\n"
        b"[WARN] Debug UART left enabled by intern (masked name: VIKTOR VAUGHN)\n"
    )

    # DOOM{There's} XOR 0x37 = 73 78 78 7A 4C 63 5F 52 45 52 10 44 4A
    # Masked hex block: "7378787a4c635f52455210444a"
    boot += (
        b"[BOOTINFO] MASKED_BLOCK=7378787a4c635f52455210444a\n"
        b"[BOOTINFO] NOTE: Boot mask appears non-random.\n"
    )

    try:
        conn.send(boot)
    except Exception:
        pass

    # ----- Telemetry sender thread -----
    th = threading.Thread(target=telemetry_loop, args=(conn,), daemon=True)
    th.start()

    # ----- Command loop -----
    # Commands (single-byte ID followed by payload):
    #  0x01 -> flash dump (Stage 3 foundation)
    #  0x02 -> reboot
    #  0x03 -> memory leak (currently RAM leak stub)
    #  0x04 -> firmware update (Stage 4 later)
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break

            cmd = data[0]
            payload = data[1:]

            # -------------------------------------------------------
            # 0x01 - Flash dump (Stage 3: secure vs. insecure path)
            # For now:
            #   - If payload >= 8: treat as offset+len and dump that region
            #   - If payload < 8: insecure debug fallback with default range
            # Later we can harden this and require a "MAC" to get official access.
            # -------------------------------------------------------
            if cmd == 0x01:
                # Secure flash dump:
                #   payload: offset(4) | length(4) | mac(4)  (mac = crc32(off|len|VILLAIN_KEY))
                # Insecure legacy path:
                #   payload: offset(4) | length(4)           (no MAC, debug only)
                payload_len = len(payload)

                try:
                    raw = FLASH.read_bytes()
                except Exception:
                    conn.send(b"[DOOMCORE] ERROR\n")
                    continue

                # Secure path: MAC present
                if payload_len >= 12:
                    off = int.from_bytes(payload[0:4], "little")
                    ln = int.from_bytes(payload[4:8], "little")
                    mac = int.from_bytes(payload[8:12], "little")

                    msg = payload[0:8] + VILLAIN_KEY
                    exp = zlib.crc32(msg) & 0xFFFFFFFF

                    if mac != exp:
                        conn.send(b"[DOOMCORE] AUTH_FAIL\n")
                    else:
                        segment = raw[off : off + ln]
                        conn.send(b"[DOOMCORE] FLASHDUMP\n" + segment)

                # Insecure fallback: legacy debug path (no MAC)
                elif payload_len >= 8:
                    off = int.from_bytes(payload[0:4], "little")
                    ln = int.from_bytes(payload[4:8], "little")
                    conn.send(b"[WARN] insecure debug flashdump\n")
                    segment = raw[off : off + ln]
                    conn.send(b"[DOOMCORE] FLASHDUMP\n" + segment)

                else:
                    conn.send(b"[DOOMCORE] INVALID_ARGS\n")

            # -------------------------------------------------------
            # 0x02 - Reboot
            # -------------------------------------------------------
            elif cmd == 0x02:
                conn.send(b"[DOOMCORE] REBOOTING...\n")

            # -------------------------------------------------------
            # 0x03 - Memory leak (RAM leak stub for later stages)
            # Right now leaks RAM region (if present) instead of full flash.
            # -------------------------------------------------------
            elif cmd == 0x03:
                # Intentionally vulnerable semantics later; for now we just leak RAM.
                try:
                    if RAM.exists():
                        ram = RAM.read_bytes()
                    else:
                        # Fallback: leak a tail of flash as "RAM-ish"
                        raw = FLASH.read_bytes()
                        ram = raw[-512:]
                    conn.send(b"[DOOMCORE] MEMORY_LEAK\n" + ram)
                except Exception:
                    conn.send(b"[DOOMCORE] MEMORY_ERROR\n")

            # -------------------------------------------------------
            # 0x04 - Firmware update (Stage 4: weak signature)
            #   - Expected "signature" is just first 4 bytes "MFDO"
            #   - Everything else in header is ignored (truncation bug)
            #   - Any blob starting with "MFDO" is accepted as villain firmware.
            #   - On success, DOOMSAT prints STAGE4FLAG.
            # -------------------------------------------------------
            elif cmd == 0x04:
                fw = payload

                # Require at least a tiny header
                if len(fw) < 4:
                    conn.send(b"[DOOMCORE] FW_TOO_SHORT\n")
                    continue

                if fw[0:4] != b"MFDO":
                    conn.send(b"[DOOMCORE] INVALID_SIGNATURE\n")
                    continue

                # At this point, villain firmware is "accepted" purely
                # because of the truncated signature check.
                try:
                    raw = FLASH.read_bytes()
                    new = raw + b"\nFIRM_PATCH:accepted\n"
                    FLASH.write_bytes(new)
                except Exception:
                    # Ignore write failure, still report OK
                    pass

                banner = (
                    b"[DOOMCORE] FW_UPDATE_OK\n"
                    b"[HINT] Signature truncated to first 4 bytes (MFDO...).\n"
                    b"STAGE4FLAG:DOOM{beer}\n"
                )
                conn.send(banner)

            # -------------------------------------------------------
            # Unknown command
            # -------------------------------------------------------
            else:
                conn.send(b"[DOOMCORE] UNKNOWN_CMD\n")

        except Exception as e:
            try:
                conn.send(b"[DOOMCORE] EXCEPTION\n")
            except Exception:
                pass
            break

    conn.close()


def main():
    print("[DOOMCORE] starting...")
    s = socket.socket()
    s.bind(LISTEN_ADDR)
    s.listen(1)
    while True:
        conn, addr = s.accept()
        handle_client(conn, addr)


if __name__ == "__main__":
    main()
