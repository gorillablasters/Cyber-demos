
import socket, time, struct, threading
from pathlib import Path
from protocol import HEADER, TYPE_POWER, TYPE_TEMP, TYPE_DANGER, TYPE_MASK, DANGER_MASK
import flash_init

MEM_DIR = Path("/opt/doomsat/memory")
FLASH = MEM_DIR / "flash.bin"
FLAGS_DIR = MEM_DIR / "flags"

LISTEN_ADDR = ("0.0.0.0", 7000)

def crc8(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
    return c & 0xFF

def build_frame(t: int, payload: bytes) -> bytes:
    body = bytes([t]) + payload
    length = len(body).to_bytes(1, 'little')
    c = crc8(body).to_bytes(1, 'little')
    return HEADER + length + body + c

def telemetry_loop(conn):
    count = 0
    while True:
        p = struct.pack("<f", 99.5)
        try:
            conn.send(build_frame(TYPE_POWER, p))
        except:
            break
        time.sleep(0.4)

        t = struct.pack("<f", 12.3 + (count % 5))
        try:
            conn.send(build_frame(TYPE_TEMP, t))
        except:
            break
        time.sleep(0.4)

        if count % 11 == 0:
            try:
                secret = (FLAGS_DIR / "stage2.txt").read_bytes().strip()
            except Exception:
                secret = b"DOOM{hidden}"
            masked = bytes([secret[i] ^ DANGER_MASK[i % len(DANGER_MASK)] for i in range(len(secret))])
            try:
                conn.send(build_frame(TYPE_DANGER, masked))
            except:
                break
        time.sleep(0.2)
        count += 1

def handle_client(conn, addr):
    print("[DOOMCORE] connected:", addr)
    boot = b"[DOOMCORE BOOT] Mask restored...\n[DOOMCORE BOOT] Villain Bootloader v1.3 (codename: OPERATION_DOOMSDAY)\n[WARN] Debug UART left enabled by intern (masked name: VIKTOR VAUGHN)\n"
    try:
        conn.send(boot)
    except:
        pass
    th = threading.Thread(target=telemetry_loop, args=(conn,), daemon=True)
    th.start()

    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            cmd = data[0]
            payload = data[1:]
            if cmd == 0x01:
                if len(payload) >= 8:
                    off = int.from_bytes(payload[0:4], 'little')
                    ln  = int.from_bytes(payload[4:8], 'little')
                else:
                    off, ln = 0, 256
                try:
                    b = FLASH.read_bytes()[off:off+ln]
                    conn.send(b"[DOOMCORE] FLASHDUMP\n" + b)
                except Exception:
                    conn.send(b"[DOOMCORE] ERROR\n")
            elif cmd == 0x02:
                conn.send(b"[DOOMCORE] REBOOTING...\n")
            elif cmd == 0x03:
                if len(payload) > 64:
                    try:
                        b = FLASH.read_bytes()
                        conn.send(b"[DOOMCORE] MEMORY_LEAK\n" + b)
                    except:
                        conn.send(b"[DOOMCORE] MEMORY_ERROR\n")
                else:
                    conn.send(b"[DOOMCORE] ACCESS_DENIED\n")
            elif cmd == 0x04:
                if len(payload) >= 4 and payload[0:4] == b"MFDO":
                    try:
                        raw = FLASH.read_bytes()
                        new = raw + b"\nFIRM_PATCH:accepted\n"
                        FLASH.write_bytes(new)
                        conn.send(b"[DOOMCORE] FW_UPDATE_OK\n")
                    except Exception:
                        conn.send(b"[DOOMCORE] FW_WRITE_FAIL\n")
                else:
                    conn.send(b"[DOOMCORE] INVALID_SIGNATURE\n")
            else:
                conn.send(b"[DOOMCORE] UNKNOWN_CMD\n")
        except Exception:
            try:
                conn.send(b"[DOOMCORE] EXCEPTION\n")
            except:
                pass
            break
    conn.close()

def main():
    print("[DOOMCORE] starting...")
    s = socket.socket()
    s.bind(LISTEN_ADDR)
    s.listen(5)
    while True:
        conn, addr = s.accept()
        handle_client(conn, addr)

if __name__ == "__main__":
    main()
