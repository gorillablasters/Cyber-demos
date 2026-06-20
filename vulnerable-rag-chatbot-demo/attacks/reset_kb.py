from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POISON_FILE = ROOT / "data" / "poisoned_policy.txt"

if POISON_FILE.exists():
    POISON_FILE.unlink()
    print("Removed poisoned_policy.txt")
else:
    print("No poisoned document found")
