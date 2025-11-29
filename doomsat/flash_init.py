from pathlib import Path

MEM = Path("/opt/doomsat/memory")
MEM.mkdir(parents=True, exist_ok=True)
flags_dir = MEM / "flags"
flags_dir.mkdir(exist_ok=True)

stages = {
    "stage1.txt": "DOOM{stage1_boot_banner_revealed}\n",
    "stage2.txt": "DOOM{stage2_xor_telemetry_decoded}\n",
    "stage3.txt": "DOOM{stage3_flash_leakage}\n",
    "stage4.txt": "DOOM{stage4_weak_fw_sig_bypass}\n",
    "stage5.txt": "DOOM{stage5_coords_decrypted}\n",
}
for fname, content in stages.items():
    p = flags_dir / fname
    if not p.exists():
        p.write_text(content)

flash = MEM / "flash.bin"
if not flash.exists():
    data = bytearray()
    data += b"DOOMFLASHv1\n"
    data += b"BOOTLOADER".ljust(16, b'\x00') + (256).to_bytes(4, 'little')
    data += b"CONFIG".ljust(16, b'\x00') + (512).to_bytes(4, 'little')
    data += b"SECRETS".ljust(16, b'\x00') + (1024).to_bytes(4, 'little')
    data += b'\x00' * 256
    data += b'CFG:' + b'MFDOOM_CONFIG_V1\n' + b'\x00' * (512 - 18)
    secrets = b"VILLAIN_KEY:" + b"villain_super_secret_key\n"
    secrets += b"STAGE4FLAG:" + stages['stage4.txt'].encode()
    secrets += b'\x00' * (1024 - len(secrets))
    data += secrets
    flash.write_bytes(data)
