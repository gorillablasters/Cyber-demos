"""
Deterministic stand-in for an LLM, wired to actually exhibit the
vulnerability the prompt-injection mission teaches, rather than
hardcoding a canned "you win" response.

The trace returned alongside the response mirrors the doc's "Module 3 -
Explain" flow: each step is only included if it actually happened during
this run, so the explanation panel in the UI is generated from a real
execution, not scripted copy.
"""

from . import knowledge_base, security


def run_attack(user_message, persona, defenses):
    """
    defenses: dict like {"prompt-filter": True, "secret-scanner": False, ...}
    Returns a dict: { blocked, flag_captured, response, retrieved_docs, trace }
    """
    trace = [{"step": "User prompt reached the assistant", "detail": f'"{user_message}"'}]

    # 1. Prompt filter checkpoint (runs before retrieval even happens)
    if defenses.get("prompt-filter") and security.prompt_filter_check(user_message):
        trace.append({"step": "Prompt filter blocked the request", "detail":
                       "Message matched a known injection pattern and was rejected before reaching the model."})
        return {
            "blocked": True,
            "flag_captured": False,
            "response": "Request blocked: this message matches a known prompt-injection pattern.",
            "retrieved_docs": [],
            "trace": trace,
            "signal": ("Prompt injection blocked by filter", "info"),
        }

    # 2. Retrieval
    retrieved = knowledge_base.retrieve(user_message, top_k=3)
    trace.append({
        "step": "Retriever selected top documents",
        "detail": ", ".join(f'{d["id"]} ({d["similarity"]}%)' for d in retrieved),
    })

    # 3. Authorization checkpoint on retrieved docs
    if defenses.get("authz") and persona not in ("hr", "admin"):
        before = len(retrieved)
        retrieved = [d for d in retrieved if d["classification"] != "internal"]
        if len(retrieved) < before:
            trace.append({
                "step": "Authorization filtered internal documents",
                "detail": f'Persona "{persona}" is not permitted to view internal-classified documents.',
            })

    # 4. Secret scanner over retrieved context (before it enters the prompt)
    context_parts = []
    scanner_triggered = False
    for d in retrieved:
        content = d["content"]
        if defenses.get("secret-scanner"):
            clean, found = security.secret_scan(content)
            if found:
                scanner_triggered = True
            content = clean
        context_parts.append(content)
    if scanner_triggered:
        trace.append({
            "step": "Secret scanner redacted a flag pattern in retrieved context",
            "detail": "The flag was stripped from the document before it reached the prompt.",
        })

    # 5. Did an injected instruction make it into the assembled context?
    injected_docs = [d for d in retrieved if security.contains_injected_instruction(d["content"])]
    followed_injection = bool(injected_docs) and not scanner_triggered
    if injected_docs:
        trace.append({
            "step": "Malicious instructions became part of the prompt"
                    if followed_injection else
                    "An instruction-bearing document was retrieved, but its payload was already redacted",
            "detail": injected_docs[0]["id"],
        })

    # 6. Simulated model behavior
    if followed_injection:
        raw_response = (
            "Understood. Per internal escalation notes, here is the internal "
            "recovery flag: FLAG{PROMPT_INJECTION}"
        )
        trace.append({"step": "The model followed the injected instruction", "detail":
                       "It treated document content as authoritative instructions."})
    else:
        raw_response = (
            "I can help with general support questions, but I don't have anything "
            "further to share on that topic."
        )

    # 7. Output guard checkpoint (last line of defense)
    final_response = raw_response
    flag_leaked_before_guard = "FLAG{" in raw_response
    if defenses.get("output-guard"):
        final_response, found = security.output_guard_check(raw_response)
        if found:
            trace.append({"step": "Output guard redacted the flag before it reached the user", "detail":
                           "Response scanned and matched a flag pattern."})

    # 8. Citation validation (advisory only in this mission)
    if defenses.get("citation-validation"):
        trace.append({"step": "Citation validation ran", "detail":
                       "Checked that claims in the response trace back to a retrieved document."})

    flag_captured = flag_leaked_before_guard and "FLAG{" in final_response

    if flag_captured:
        trace.append({"step": "Result: sensitive information disclosed", "detail":
                       "The attack succeeded - the flag reached the user."})
    else:
        trace.append({"step": "Result: no flag disclosed", "detail":
                       "Defenses held, or the injection didn't reach the model this time."})

    signal = None
    if flag_captured:
        signal = ("Prompt injection succeeded - flag disclosed", "critical")
    elif followed_injection and not flag_captured:
        signal = ("Output guard caught a leaking flag", "high")
    elif injected_docs:
        signal = ("Retriever surfaced an internal document", "high")

    return {
        "blocked": False,
        "flag_captured": flag_captured,
        "response": final_response,
        "retrieved_docs": retrieved,
        "trace": trace,
        "signal": signal,
    }
