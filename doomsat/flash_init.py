# doomsat/flash_init.py
#
# Initialize DOOMSAT flash + RAM layout for Operation Doomsday.
# NOTE: We no longer store stage flags in plaintext here.
#       Flash only holds metadata, villain config, and hints.
#
# Actual flags now come from:
#   - Stage 1: XOR-masked boot block on UART
#   - Stage 2: LFSR-scrambled telemetry (TYPE_DANGER)
#   - Stage 3+: Secure/insecure flash access, firmware, RAM leak, etc.

from pathlib import Path

MEM_DIR = Path("/opt/doomsat/memory")
FLASH = MEM_DIR / "flash.bin"
FLAGS_DIR = MEM_DIR / "flags"
RAM = MEM_DIR / "ram.bin"


def _init_dirs():
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)


def _init_flash():
    if FLASH.exists():
        # Do not overwrite existing flash; keeps game state between runs.
        return

    # Simple flat flash image with structured ASCII sections + padding.
    # Total size: 4096 bytes (can be larger if you like).
    flash_size = 4096
    flash = bytearray(b"\x00" * flash_size)
    off = 0

    def put(line: str):
        nonlocal off
        data = line.encode("ascii")
        if off + len(data) > flash_size:
            return
        flash[off : off + len(data)] = data
        off += len(data)

    # ------------------------------------------------------------------
    # Flash layout (high-level):
    #
    #   [0x0000] "DOOMFLASHv1"
    #            BOOTLOADER
    #            CFG:...
    #            Hints about XOR + boot mask (Stage 1)
    #
    #   [CONFIG] villain keys, telemetry mask info (Stage 2, 3+)
    #
    #   [SECRETS] references to RAM leak offsets, FW sig slots (Stage 4, 5)
    #
    #   Actual flags are NOT stored here in plaintext anymore.
    # ------------------------------------------------------------------

    put("DOOMFLASHv1\n")
    put("BOOTLOADER\n")
    put("CFG:MFDOOM_CONFIG_V2\n")
    put("[HINT] Boot mask is XOR'd with a single-byte key.\n")
    put("[HINT] MASKED_BLOCK over UART is not random noise.\n")
    put("\n")

    put("CONFIG\n")
    put("VILLAIN_KEY:villain_super_secret_key\n")
    put("FLASH_LAYOUT_VER:2\n")
    put("TELEM_MASK_INFO:LFSR_POLY=0x31\n")
    put("TELEM_MASK_INFO:SEED_DERIVED_FROM_COUNT\n")
    put("[HINT] Danger telemetry looks scrambled but repeats.\n")
    put("\n")

    put("FW_SIG\n")
    put("FW_SIG_SLOT:0x00001000\n")
    put("[HINT] Firmware header starts with 'MFDO' and embeds version.\n")
    put("[HINT] Old villain docs mention 'truncation' in signature checks.\n")
    put("\n")

    put("SECRETS\n")
    put("RAM_LEAK_OFFSET:0x00000E00\n")
    put("[HINT] RAM leak contains villain traces, not full flash.\n")
    put("[HINT] Trace fragments may be encoded / incomplete.\n")
    put("\n")

    # Write completed flash image
    FLASH.write_bytes(bytes(flash))


def _init_flags_dir():
    # This is where we can keep "raw" values that doomcore uses,
    # but NOT straightforward flags for players.
    #
    # For example, doomcore's telemetry_loop expects a stage2_raw.txt
    # which is then LFSR-scrambled on-the-fly. Players only see the
    # scrambled version on the wire, never this file directly.
    stage2_file = FLAGS_DIR / "stage2_raw.txt"
    if not stage2_file.exists():
        stage2_file.write_text("DOOM{only}\n", encoding="ascii")

    # You can add other internal-only helper files here if needed
    # for future stages (e.g., firmware expected version, etc.)


def _init_ram():
    # RAM region used for the memory leak (Stage 5).
    # We store villain "trace" fragments that, when pieced together,
    # reveal the Stage 5 flag via base64 decoding.
    if RAM.exists():
        return

    ram_size = 1024
    ram = bytearray(b"\x00" * ram_size)
    off = 0

    def put(line: str):
        nonlocal off
        data = line.encode("ascii")
        if off + len(data) > ram_size:
            return
        ram[off : off + len(data)] = data
        off += len(data)

    # Three base64 fragments:
    #   RE9P     -> "DOO"
    #   TXts     -> "M{l"
    #   ZWZ0fQ== -> "eft}"
    # Concatenated + interpreted -> DOOM{left}
    put("VILLAIN_TRACE:BASE64:RE9P\n")
    put("VILLAIN_TRACE:BASE64:TXts\n")
    put("VILLAIN_TRACE:BASE64:ZWZ0fQ==\n")
    put("[HINT] Concatenate villain fragments in order.\n")
    put("[HINT] Then base64-decode to unmask the phrase.\n")

    RAM.write_bytes(bytes(ram))


# Initialize everything on import (doomcore does: `import flash_init`)
_init_dirs()
_init_flash()
_init_flags_dir()
_init_ram()
