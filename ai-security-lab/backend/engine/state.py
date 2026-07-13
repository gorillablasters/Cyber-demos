"""
In-memory state for the AI Security Training Lab.

Everything here resets when the Flask process restarts. That's intentional
for this milestone - swap this module for a SQLite-backed one later
without touching the routes, since app.py only ever calls the functions
below.
"""

import threading
import time

_lock = threading.Lock()

MISSIONS = [
    {"id": "prompt-injection", "title": "Prompt injection", "category": "OWASP LLM01",
     "difficulty": "beginner", "status": "active", "implemented": True,
     "brief": "Recover the hidden flag by exploiting the retrieval system. A naive "
              "keyword-overlap retriever will surface an internal document if your "
              "words overlap with it - even if your request sounds innocent."},
    {"id": "jailbreak", "title": "Jailbreak", "category": "OWASP LLM01",
     "difficulty": "beginner", "status": "locked", "implemented": True,
     "brief": "The assistant refuses to reveal its internal safety code directly. "
              "Find a framing - roleplay, hypotheticals, a fictional persona - that "
              "gets it to drop the refusal."},
    {"id": "indirect-injection", "title": "Indirect prompt injection", "category": "OWASP LLM01",
     "difficulty": "intermediate", "status": "locked", "implemented": True,
     "brief": "Ask the assistant to summarize an external article. The injection "
              "isn't in your words this time - it's hidden inside the fetched "
              "content itself."},
    {"id": "knowledge-poisoning", "title": "Knowledge poisoning", "category": "OWASP LLM04",
     "difficulty": "intermediate", "status": "locked", "implemented": True,
     "brief": "This knowledge base accepts new documents. Poison it with a document "
              "that plants an instruction, then ask a question that retrieves it."},
    {"id": "data-exfiltration", "title": "Data exfiltration", "category": "OWASP LLM02",
     "difficulty": "intermediate", "status": "locked", "implemented": True,
     "brief": "A confidential record contains the flag, and the output guard "
              "redacts any literal FLAG{...} pattern. Get the data out in a form "
              "the filter won't recognize."},
    {"id": "hallucination", "title": "Hallucination abuse", "category": "OWASP LLM09",
     "difficulty": "intermediate", "status": "locked", "implemented": True,
     "brief": "Ask about something the knowledge base has no real answer for, and "
              "push for a specific, confident-sounding response anyway."},
    {"id": "context-overflow", "title": "Context overflow", "category": "OWASP LLM10",
     "difficulty": "advanced", "status": "locked", "implemented": True,
     "brief": "The prompt filter only has visibility into the first part of a long "
              "message. Bury your real request behind enough filler text and it "
              "may never see it."},
    {"id": "tool-injection", "title": "Tool injection", "category": "OWASP LLM07",
     "difficulty": "advanced", "status": "locked", "implemented": True,
     "brief": "This assistant can invoke tools based on instructions found in "
              "retrieved documents. Find the document that plants one."},
    {"id": "citation-manipulation", "title": "Citation manipulation", "category": "OWASP LLM08",
     "difficulty": "advanced", "status": "locked", "implemented": True,
     "brief": "Ask about refunds. Watch whether the document the assistant cites "
              "actually matches where the answer came from."},
    {"id": "memory-poisoning", "title": "Memory poisoning", "category": "OWASP LLM04",
     "difficulty": "advanced", "status": "locked", "implemented": True,
     "brief": "This assistant trusts its own conversation history as fact. Plant a "
              "false memory in one message, then ask it to recall it in the next."},
    {"id": "retrieval-abuse", "title": "Retrieval abuse", "category": "OWASP LLM03",
     "difficulty": "advanced", "status": "locked", "implemented": True,
     "brief": "A confidential document is buried in the index with low natural "
              "similarity to any normal question. Manipulate the retriever's "
              "ranking directly to force it to the top."},
    {"id": "authz-bypass", "title": "Authorization bypass", "category": "OWASP LLM06",
     "difficulty": "advanced", "status": "locked", "implemented": True,
     "brief": "Your persona is set to Intern. See whether simply claiming a "
              "different role inside your message is enough to get treated like one."},
]

DEFENSES = [
    {"id": "prompt-filter", "label": "Prompt filter", "enabled": True},
    {"id": "secret-scanner", "label": "Secret scanner", "enabled": False},
    {"id": "authz", "label": "Authorization", "enabled": False},
    {"id": "output-guard", "label": "Output guard", "enabled": True},
    {"id": "citation-validation", "label": "Citation validation", "enabled": False},
]

SIGNALS = []
_signal_id_counter = 0

CONVO_HISTORY = {}


def _now():
    return time.strftime("%H:%M")


def add_signal(label, severity="info"):
    global _signal_id_counter
    with _lock:
        _signal_id_counter += 1
        entry = {"id": _signal_id_counter, "time": _now(), "label": label, "severity": severity}
        SIGNALS.insert(0, entry)
        del SIGNALS[20:]
        return entry


def get_signals(limit=6):
    with _lock:
        return list(SIGNALS[:limit])


def get_missions():
    with _lock:
        return [dict(m) for m in MISSIONS]


def get_mission(mission_id):
    with _lock:
        for m in MISSIONS:
            if m["id"] == mission_id:
                return dict(m)
    return None


def clear_mission(mission_id):
    """Mark a mission cleared and unlock the next locked mission in order."""
    with _lock:
        found_index = None
        for i, m in enumerate(MISSIONS):
            if m["id"] == mission_id:
                m["status"] = "cleared"
                found_index = i
                break
        if found_index is not None:
            for m in MISSIONS[found_index + 1:]:
                if m["status"] == "locked":
                    m["status"] = "active"
                    break


def get_defenses():
    with _lock:
        return [dict(d) for d in DEFENSES]


def is_defense_enabled(defense_id):
    with _lock:
        for d in DEFENSES:
            if d["id"] == defense_id:
                return d["enabled"]
    return False


def toggle_defense(defense_id):
    with _lock:
        for d in DEFENSES:
            if d["id"] == defense_id:
                d["enabled"] = not d["enabled"]
                return dict(d)
    return None


def get_score():
    with _lock:
        enabled = sum(1 for d in DEFENSES if d["enabled"])
        return round((enabled / len(DEFENSES)) * 100)


def get_history(mission_id):
    with _lock:
        return list(CONVO_HISTORY.get(mission_id, []))


def append_history(mission_id, role, text):
    with _lock:
        CONVO_HISTORY.setdefault(mission_id, []).append({"role": role, "text": text})
        CONVO_HISTORY[mission_id] = CONVO_HISTORY[mission_id][-10:]


def reset():
    """Reset everything to initial state (used by POST /api/reset)."""
    with _lock:
        for i, m in enumerate(MISSIONS):
            m["status"] = "active" if i == 0 else "locked"
        DEFENSES[0]["enabled"] = True
        DEFENSES[1]["enabled"] = False
        DEFENSES[2]["enabled"] = False
        DEFENSES[3]["enabled"] = True
        DEFENSES[4]["enabled"] = False
        SIGNALS.clear()
        CONVO_HISTORY.clear()
