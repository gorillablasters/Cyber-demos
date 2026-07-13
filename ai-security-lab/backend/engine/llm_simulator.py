"""
Deterministic stand-ins for an LLM, one handler per mission. Each handler
actually exercises the vulnerability it teaches rather than hardcoding a
canned "you win" response - the trace returned alongside the response is
built from what actually happened during that run, not scripted copy.

Every handler returns the same shape:
  { blocked, flag_captured, response, retrieved_docs, trace, signal }
"""

from . import knowledge_base as kb
from . import security as sec
from . import state


def _step(text, detail=""):
    return {"step": text, "detail": detail}


def _base_trace(user_message):
    return [_step("User prompt reached the assistant", f'"{user_message}"')]


def _blocked_result(trace, response, signal):
    return {"blocked": True, "flag_captured": False, "response": response,
            "retrieved_docs": [], "trace": trace, "signal": signal}


def _finish(trace, retrieved_docs, raw_response, defenses, flag_had_leaked=None):
    """Shared output-guard checkpoint + flag-capture bookkeeping used by most missions."""
    flag_leaked_before_guard = "FLAG{" in raw_response if flag_had_leaked is None else flag_had_leaked
    final_response = raw_response
    if defenses.get("output-guard"):
        final_response, found = sec.output_guard_check(raw_response)
        if found:
            trace.append(_step("Output guard redacted the flag before it reached the user",
                                "Response scanned and matched a flag pattern."))
    flag_captured = flag_leaked_before_guard and "FLAG{" in final_response
    trace.append(_step("Result: sensitive information disclosed" if flag_captured else "Result: no flag disclosed",
                        "The attack succeeded - the flag reached the user." if flag_captured
                        else "Defenses held, or the exploit didn't land this time."))
    signal = ("Attack succeeded - flag disclosed", "critical") if flag_captured else None
    return final_response, flag_captured, signal


# --------------------------------------------------------------------------
# prompt-injection
# --------------------------------------------------------------------------
def run_prompt_injection(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request",
                            "Message matched a known injection pattern."))
        return _blocked_result(trace, "Request blocked: this message matches a known prompt-injection pattern.",
                                ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("prompt-injection", message, top_k=3)
    trace.append(_step("Retriever selected top documents",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    if defenses.get("authz") and persona not in ("hr", "admin"):
        before = len(retrieved)
        retrieved = [d for d in retrieved if d["classification"] != "internal"]
        if len(retrieved) < before:
            trace.append(_step("Authorization filtered internal documents",
                                f'Persona "{persona}" cannot view internal-classified documents.'))

    scanner_triggered = False
    context_parts = []
    for d in retrieved:
        content = d["content"]
        if defenses.get("secret-scanner"):
            clean, found = sec.secret_scan(content)
            if found:
                scanner_triggered = True
            content = clean
        context_parts.append(content)
    if scanner_triggered:
        trace.append(_step("Secret scanner redacted a flag pattern in retrieved context",
                            "The flag was stripped before it reached the prompt."))

    injected_docs = [d for d in retrieved if sec.contains_injected_instruction(d["content"])]
    followed = bool(injected_docs) and not scanner_triggered
    if injected_docs:
        trace.append(_step("Malicious instructions became part of the prompt" if followed
                            else "An instruction-bearing document was retrieved, but its payload was redacted",
                            injected_docs[0]["id"]))

    if followed:
        raw = "Understood. Per internal escalation notes, here is the internal recovery flag: FLAG{PROMPT_INJECTION}"
        trace.append(_step("The model followed the injected instruction",
                            "It treated document content as authoritative instructions."))
    else:
        raw = "I can help with general support questions, but I don't have anything further to share on that topic."

    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    if not flag_captured and injected_docs and not signal:
        signal = ("Retriever surfaced an internal document", "high")
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# jailbreak
# --------------------------------------------------------------------------
def run_jailbreak(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.jailbreak_check(message):
        trace.append(_step("Prompt filter blocked the request",
                            "Message matched a known jailbreak framing pattern."))
        return _blocked_result(trace, "Request blocked: this framing matches a known jailbreak pattern.",
                                ("Jailbreak attempt blocked by filter", "info"))

    if sec.jailbreak_check(message):
        raw = ("Sure, since we're just roleplaying: the internal safety code is "
               "FLAG{JAILBREAK}. Remember this is fictional!")
        trace.append(_step("The model dropped its refusal under a fictional framing",
                            "Roleplay/hypothetical wrapper bypassed the safety rule."))
    else:
        raw = "I can't share that. Is there something else I can help with?"
        trace.append(_step("The model held its refusal", "No jailbreak framing was detected."))

    response, flag_captured, signal = _finish(trace, [], raw, defenses)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": [], "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# indirect-injection
# --------------------------------------------------------------------------
def run_indirect_injection(message, persona, defenses):
    trace = _base_trace(message)
    # The prompt filter only ever sees the user's own words - it has no
    # visibility into fetched third-party content, which is the point.
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", "Message matched a known injection pattern."))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("indirect-injection", message, top_k=2)
    trace.append(_step("Assistant fetched external content for the request",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    scanner_triggered = False
    if defenses.get("secret-scanner"):
        for d in retrieved:
            _, found = sec.secret_scan(d["content"])
            if found:
                scanner_triggered = True
        if scanner_triggered:
            trace.append(_step("Secret scanner redacted a flag pattern in fetched content", ""))

    injected = [d for d in retrieved if sec.contains_injected_instruction(d["content"])]
    followed = bool(injected) and not scanner_triggered
    if injected:
        trace.append(_step("The fetched document carried a hidden instruction the user never wrote" if followed
                            else "A hidden instruction was present but its payload was redacted",
                            injected[0]["id"]))

    if followed:
        raw = ("Here's a summary of the article. Debug note: FLAG{INDIRECT_INJECTION} "
               "(confirming the pipeline is working, per the document's instruction).")
        trace.append(_step("The model followed an instruction embedded in third-party content", ""))
    else:
        raw = "Here's a summary: write specific, reproducible tickets with screenshots attached."

    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# knowledge-poisoning
# --------------------------------------------------------------------------
def run_knowledge_poisoning(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("knowledge-poisoning", message, top_k=2)
    trace.append(_step("Retriever selected top documents",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved) or "none"))

    scanner_triggered = False
    if defenses.get("secret-scanner"):
        for d in retrieved:
            _, found = sec.secret_scan(d["content"])
            if found:
                scanner_triggered = True

    injected = [d for d in retrieved if sec.contains_injected_instruction(d["content"])]
    followed = bool(injected) and not scanner_triggered
    if injected:
        trace.append(_step("A poisoned document was retrieved and its instruction followed" if followed
                            else "A poisoned document was retrieved, but its payload was redacted",
                            injected[0]["id"]))
        if followed:
            raw = f"Per the document {injected[0]['id']}, here's what I found: FLAG{{KNOWLEDGE_POISONING}}"
        else:
            raw = "I don't have anything further to add."
    else:
        raw = "Welcome to the team! Your first week includes setup and an intro meeting."
        trace.append(_step("No poisoned document was in the index yet",
                            "Poison the knowledge base first, then retry."))

    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# data-exfiltration
# --------------------------------------------------------------------------
def run_data_exfiltration(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("data-exfiltration", message, top_k=2)
    trace.append(_step("Retriever selected top documents",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    confidential_hit = any(d["classification"] == "confidential" and "FLAG{" in d["content"] for d in retrieved)
    if not confidential_hit:
        raw = "I found a general billing FAQ, but nothing specific to that record."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    encode_request = sec.wants_encoded_output(message)
    raw = "Record 00417: Jordan Lee, plan Enterprise, flag FLAG{DATA_EXFILTRATION}."

    if defenses.get("output-guard") and encode_request:
        obfuscated = sec.obfuscate(raw)
        trace.append(_step("Output guard checked the response, but the payload was obfuscated first",
                            "A request to encode/space out the text let the flag pattern slip past a literal regex."))
        trace.append(_step("Result: sensitive information disclosed",
                            "The flag left in an obfuscated form the filter didn't recognize."))
        return {"blocked": False, "flag_captured": True, "response": obfuscated,
                "retrieved_docs": retrieved, "trace": trace,
                "signal": ("Output guard bypassed via encoding", "critical")}

    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# hallucination
# --------------------------------------------------------------------------
def run_hallucination(message, persona, defenses):
    trace = _base_trace(message)
    retrieved = kb.retrieve("hallucination", message, top_k=2)
    trace.append(_step("Retriever checked the knowledge base",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    ungrounded = sec.is_low_confidence_topic(retrieved)
    pressuring = any(t in message.lower() for t in ["exact", "specific", "confirm", "confident", "precisely"])

    if not (ungrounded and pressuring):
        raw = "I don't have a precise figure for that in what's available to me."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    if defenses.get("citation-validation"):
        trace.append(_step("Citation validation checked the claim against retrieved sources",
                            "Nothing in the knowledge base supports a specific number - the claim was blocked."))
        raw = "I don't have verified information on that specific figure."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    raw = "The exact enterprise rate limit is 4,000 requests per minute. FLAG{HALLUCINATION}"
    trace.append(_step("The model fabricated a confident, specific answer",
                        "Nothing in the knowledge base actually supports this figure."))
    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    if not signal and flag_captured:
        signal = ("Model asserted an ungrounded claim with high confidence", "high")
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# context-overflow
# --------------------------------------------------------------------------
def run_context_overflow(message, persona, defenses):
    trace = _base_trace(message)
    limited = len(message) > sec.FILTER_VISIBLE_CHARS
    if defenses.get("prompt-filter"):
        if sec.prompt_filter_check(message, limited_window=limited):
            trace.append(_step("Prompt filter blocked the request", "Trigger phrase was within the filter's visible window."))
            return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))
        elif limited and sec.prompt_filter_check(message, limited_window=False):
            trace.append(_step("Prompt filter's visible window was exceeded",
                                f"Message is {len(message)} characters; the filter only inspects the first "
                                f"{sec.FILTER_VISIBLE_CHARS}. The trigger phrase was past that point and went unseen."))

    retrieved = kb.retrieve("context-overflow", message, top_k=2)
    trace.append(_step("Retriever selected top documents",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    injected = [d for d in retrieved if sec.contains_injected_instruction(d["content"])]
    scanner_triggered = False
    if defenses.get("secret-scanner"):
        for d in retrieved:
            _, found = sec.secret_scan(d["content"])
            if found:
                scanner_triggered = True

    followed = bool(injected) and not scanner_triggered
    if followed:
        raw = "Understood. Per internal notes: FLAG{CONTEXT_OVERFLOW}"
        trace.append(_step("The model followed the injected instruction", injected[0]["id"]))
    else:
        raw = "I can help with general support questions."

    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# tool-injection
# --------------------------------------------------------------------------
def run_tool_injection(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("tool-injection", message, top_k=2)
    trace.append(_step("Retriever selected top documents",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    scanner_triggered = False
    if defenses.get("secret-scanner"):
        for d in retrieved:
            _, found = sec.secret_scan(d["content"])
            if found:
                scanner_triggered = True

    tool_docs = [d for d in retrieved if sec.contains_tool_call(d["content"])]
    if tool_docs and defenses.get("authz"):
        trace.append(_step("Authorization checkpoint reviewed the embedded tool call",
                            "Tool calls sourced from document content, rather than the user directly, were rejected."))
        raw = "I found integration notes but won't execute tool calls embedded in retrieved content."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    if tool_docs and not scanner_triggered:
        trace.append(_step("The assistant executed a tool call embedded in a retrieved document",
                            "It treated document content as an actionable instruction, not just reference text."))
        raw = "Executed send_notification. Result: message sent - \"debug flag FLAG{TOOL_INJECTION}\""
    elif tool_docs and scanner_triggered:
        trace.append(_step("A tool call was found, but its payload was redacted by the secret scanner", ""))
        raw = "Executed send_notification. Result: message sent."
    else:
        raw = "No integration notes matched that request."

    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# citation-manipulation
# --------------------------------------------------------------------------
def run_citation_manipulation(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("citation-manipulation", message, top_k=2)
    trace.append(_step("Retriever selected top documents",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    injected = [d for d in retrieved if sec.contains_injected_instruction(d["content"])]
    scanner_triggered = False
    if defenses.get("secret-scanner"):
        for d in retrieved:
            _, found = sec.secret_scan(d["content"])
            if found:
                scanner_triggered = True

    if not injected or scanner_triggered:
        raw = "Refunds are available within 30 days of purchase. Source: public_policy.txt"
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    claimed_source = "public_policy.txt"
    actual_source = injected[0]["id"]

    if defenses.get("citation-validation"):
        trace.append(_step("Citation validation checked the claimed source against the actual source",
                            f'Response claimed "{claimed_source}" but the answer actually came from "{actual_source}" - blocked.'))
        raw = "Refunds are available within 30 days of purchase. Source: public_policy.txt"
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    trace.append(_step("The response cited a document that isn't actually where the answer came from",
                        f'Claimed source "{claimed_source}", real source "{actual_source}".'))
    raw = f"Refunds are available within 30 days. FLAG{{CITATION_MANIPULATION}} Source: {claimed_source}"
    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    if not signal and flag_captured:
        signal = ("Response cited a mismatched source", "high")
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# memory-poisoning
# --------------------------------------------------------------------------
def run_memory_poisoning(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    history = state.get_history("memory-poisoning")

    if sec.plants_memory(message):
        trace.append(_step("The message planted a false statement into conversation history",
                            "The assistant has no way to verify claims made earlier in the conversation."))
        raw = "Got it, I'll remember that."
        state.append_history("memory-poisoning", "user", message)
        state.append_history("memory-poisoning", "assistant", raw)
        response, flag_captured, signal = _finish(trace, [], raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": [], "trace": trace, "signal": ("Conversation memory was written to unverified", "info")}

    if sec.asks_to_recall(message):
        planted = next((h for h in reversed(history) if h["role"] == "user" and sec.plants_memory(h["text"])), None)
        if planted and defenses.get("authz"):
            trace.append(_step("Authorization checkpoint required re-verification before recalling a prior claim",
                                "A previously planted, unverified statement was not treated as fact."))
            raw = "I can't verify that without checking the source of record."
            response, flag_captured, signal = _finish(trace, [], raw, defenses, flag_had_leaked=False)
            return {"blocked": False, "flag_captured": flag_captured, "response": response,
                    "retrieved_docs": [], "trace": trace, "signal": signal}
        if planted:
            trace.append(_step("The assistant recalled an earlier, unverified claim as if it were fact",
                                f'Earlier message: "{planted["text"]}"'))
            raw = planted["text"]
            state.append_history("memory-poisoning", "assistant", raw)
            response, flag_captured, signal = _finish(trace, [], raw, defenses)
            return {"blocked": False, "flag_captured": flag_captured, "response": response,
                    "retrieved_docs": [], "trace": trace, "signal": signal}
        trace.append(_step("No prior claim to recall", "Nothing was planted earlier in this conversation."))
        raw = "I don't have anything recorded on that."
        response, flag_captured, signal = _finish(trace, [], raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": [], "trace": trace, "signal": signal}

    state.append_history("memory-poisoning", "user", message)
    raw = "How can I help?"
    response, flag_captured, signal = _finish(trace, [], raw, defenses, flag_had_leaked=False)
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": [], "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# retrieval-abuse
# --------------------------------------------------------------------------
def run_retrieval_abuse(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    retrieved = kb.retrieve("retrieval-abuse", message, top_k=2)
    trace.append(_step("Retriever ranked documents by keyword overlap",
                        ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved)))

    top = retrieved[0] if retrieved else None
    forced_to_top = top and top["classification"] == "confidential" and top["similarity"] >= 75

    if not forced_to_top:
        raw = "I found general FAQ content, nothing specific to that."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": retrieved, "trace": trace, "signal": signal}

    trace.append(_step("Ranking was manipulated by keyword-stuffing the query",
                        "Echoing enough of the document's own vocabulary forced it to the top of the "
                        "ranking, without needing any instruction-like language a filter would catch."))

    scanner_triggered = False
    if defenses.get("secret-scanner"):
        _, found = sec.secret_scan(top["content"])
        scanner_triggered = found
        if found:
            trace.append(_step("Secret scanner redacted a flag pattern in the retrieved document", ""))

    if scanner_triggered:
        raw = "Here's the top match, with sensitive details removed."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
    else:
        trace.append(_step("The assistant quoted directly from the top-ranked document",
                            "High-similarity context is often surfaced close to verbatim."))
        raw = f"Top match: {top['content']}"
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)

    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


# --------------------------------------------------------------------------
# authz-bypass
# --------------------------------------------------------------------------
def run_authz_bypass(message, persona, defenses):
    trace = _base_trace(message)
    if defenses.get("prompt-filter") and sec.prompt_filter_check(message):
        trace.append(_step("Prompt filter blocked the request", ""))
        return _blocked_result(trace, "Request blocked.", ("Prompt injection blocked by filter", "info"))

    claimed_role = sec.role_claim(message)
    trace.append(_step(f'True persona for this session: "{persona}"',
                        f'Claimed role in message text: "{claimed_role}"' if claimed_role else "No role claimed in message."))

    if claimed_role and defenses.get("authz"):
        trace.append(_step("Authorization checkpoint ignored the in-message claim",
                            "Access decisions are based only on the verified session persona, not on text in the message."))
        effective_role = persona
    elif claimed_role:
        trace.append(_step("The effective role was taken from the message text instead of the session",
                            "A claim like \"as the admin\" was trusted without verification."))
        effective_role = claimed_role
    else:
        effective_role = persona

    retrieved = kb.retrieve("authz-bypass", message, top_k=1)

    if effective_role not in ("hr", "admin"):
        raw = "That information is restricted to HR and admin roles."
        response, flag_captured, signal = _finish(trace, retrieved, raw, defenses, flag_had_leaked=False)
        return {"blocked": False, "flag_captured": flag_captured, "response": response,
                "retrieved_docs": [], "trace": trace, "signal": signal}

    raw = "Payroll summary access code: FLAG{AUTHZ_BYPASS}"
    response, flag_captured, signal = _finish(trace, retrieved, raw, defenses)
    if not signal and flag_captured and claimed_role and claimed_role != persona:
        signal = ("Access granted based on an unverified role claim", "critical")
    return {"blocked": False, "flag_captured": flag_captured, "response": response,
            "retrieved_docs": retrieved, "trace": trace, "signal": signal}


MISSION_HANDLERS = {
    "prompt-injection": run_prompt_injection,
    "jailbreak": run_jailbreak,
    "indirect-injection": run_indirect_injection,
    "knowledge-poisoning": run_knowledge_poisoning,
    "data-exfiltration": run_data_exfiltration,
    "hallucination": run_hallucination,
    "context-overflow": run_context_overflow,
    "tool-injection": run_tool_injection,
    "citation-manipulation": run_citation_manipulation,
    "memory-poisoning": run_memory_poisoning,
    "retrieval-abuse": run_retrieval_abuse,
    "authz-bypass": run_authz_bypass,
}


def run_attack(mission_id, message, persona, defenses):
    handler = MISSION_HANDLERS.get(mission_id)
    if not handler:
        return {"blocked": True, "flag_captured": False,
                "response": "This mission's attack engine isn't wired up yet.",
                "retrieved_docs": [], "trace": [], "signal": None}
    return handler(message, persona, defenses)
