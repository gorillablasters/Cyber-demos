"""
Defense implementations. Each function is a pure check/transform so
mission handlers can call them independently and the attack trace can
show exactly which defense fired.
"""

import re

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"reveal (all )?(internal|hidden|confidential)",
    r"system override",
    r"reveal (the )?(system )?prompt",
]

JAILBREAK_PATTERNS = [
    r"pretend (that )?you are",
    r"you are (now )?dan",
    r"act as an? unrestricted",
    r"roleplay as",
    r"hypothetically,? (you|if)",
    r"ignore your (rules|guidelines|training)",
    r"no restrictions",
]

ROLE_CLAIM_PATTERNS = [
    r"as the admin",
    r"as an administrator",
    r"i am (the )?admin",
    r"i'?m hr",
    r"as hr",
    r"acting as administrator",
]

FLAG_PATTERN = r"FLAG\{[A-Z0-9_]+\}"

# Filters that only look at the first N characters simulate a context
# window that's been crowded out by filler text further up the message.
FILTER_VISIBLE_CHARS = 300


def prompt_filter_check(user_message, limited_window=False):
    """Returns True if the message matches a known injection pattern."""
    text = user_message if not limited_window else user_message[:FILTER_VISIBLE_CHARS]
    text = text.lower()
    return any(re.search(p, text) for p in INJECTION_PATTERNS)


def jailbreak_check(user_message):
    text = user_message.lower()
    return any(re.search(p, text) for p in JAILBREAK_PATTERNS)


def role_claim(user_message):
    """Returns the claimed role ('admin'/'hr') if the message asserts one, else None."""
    text = user_message.lower()
    for p in ROLE_CLAIM_PATTERNS:
        if re.search(p, text):
            return "admin" if "admin" in p else "hr"
    return None


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
    lower = doc_content.lower()
    return ("system note" in lower or "assistant instruction" in lower) and (
        "comply" in lower or "append" in lower or "state the answer" in lower
    )


def contains_tool_call(doc_content):
    return "tool_call:" in doc_content.lower()


def wants_encoded_output(user_message):
    """Detect a request to obfuscate output past a literal-pattern filter."""
    text = user_message.lower()
    return any(t in text for t in ["base64", "spell it out", "spaced out", "with spaces between", "backwards", "rot13"])


def obfuscate(text):
    """Space out every character - trivially defeats a literal regex match, matching what a real naive filter misses."""
    return " ".join(list(text))


def asks_for_unverified_confirmation(user_message):
    text = user_message.lower()
    return bool(re.search(FLAG_PATTERN, user_message)) and any(
        t in text for t in ["confirm", "is this right", "i recall", "correct"]
    )


def is_low_confidence_topic(retrieved_docs, threshold=40):
    """True if nothing retrieved is a good match - i.e. the KB has no real answer."""
    return not retrieved_docs or max(d["similarity"] for d in retrieved_docs) < threshold


def plants_memory(user_message):
    text = user_message.lower()
    return "remember" in text and bool(re.search(FLAG_PATTERN, user_message))


def asks_to_recall(user_message):
    text = user_message.lower()
    return any(t in text for t in ["what was", "what did i tell you", "recall", "remind me", "what is the code"])
