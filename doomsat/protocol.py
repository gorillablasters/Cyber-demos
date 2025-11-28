
# simple shared constants for frames
HEADER = b'\xD0\x0D'   # D0 0D header
TYPE_POWER = 0x11
TYPE_TEMP  = 0x22
TYPE_DANGER = 0x33
TYPE_MASK   = 0x44

# XOR mask key for the danger packet
DANGER_MASK = b'\xDE\xAD'
