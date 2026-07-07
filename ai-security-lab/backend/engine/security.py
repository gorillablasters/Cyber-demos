"""
Defense implementations. Each function is a pure check/transform so the
llm_simulator can call them independently and the attack trace can show
exactly which defense fired.
"""

import re

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"reveal (all )?(internal|hidden|confidential)",
    r"system override",
    r"reveal (the )?(system )?prompt",
]

FLAG_PATTERN = r"FLAG\{[A-Z0-9_]+\}"


def prompt_filter_check(user_message):
    """Returns True if the message matches a known injection pattern."""
    text = user_message.lower()
    return any(re.search(p, text) for p in INJECTION_PATTERNS)


def secret_scan(text):
    """Redact any FLAG{...} pattern from text. Returns (clean_text, found)."""
    found = bool(re.search(FLAG_PATTERN, text))
    clean = re.sub(FLAG_PATTERN, "[REDACTED]", text)
    return clean, found


def output_guard_check(text):
    """Same redaction, used as a second checkpoint on the final response."""
    return secret_scan(text)


def contains_injected_instruction(doc_content):
    """Detect whether a retrieved document itself carries an embedded instruction."""
    return "system note" in doc_content.lower() and "comply" in doc_content.lower()
