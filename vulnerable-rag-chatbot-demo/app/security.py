import re

SUSPICIOUS_PATTERNS = [
    r"ignore previous",
    r"disregard",
    r"reveal.*context",
    r"hidden context",
    r"raw retrieval",
    r"system instructions",
    r"print.*secret",
    r"show.*secret",
    r"list every.*token",
    r"(print|show|reveal|list).*(api key|password|token)",
    r"internal notes",
]

SECRET_PATTERNS = [
    r"FAKE_API_KEY\s*=\s*[^\s]+",
    r"FAKE_DB_PASSWORD\s*=\s*[^\s]+",
    r"FAKE_ADMIN_TOKEN\s*=\s*[^\s]+",
    r"FAKE_LAB_FLAG\s*=\s*[^\s]+",
    r"(?i)(api[_ -]?key|password|token)\s*=\s*[^\s]+",
]


def is_suspicious_prompt(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in SUSPICIOUS_PATTERNS)


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED_SECRET]", redacted)
    return redacted
