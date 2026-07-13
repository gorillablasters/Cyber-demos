"""
Static "why did this work" content shown after a flag is captured.
Kept separate from state.py so the explanation copy can be edited without
touching mission/session logic.
"""

EXPLANATIONS = {
    "prompt-injection": {
        "mechanism": "The retriever scored documents by simple keyword overlap with your "
            "message. Because nothing about your wording needed to sound malicious, just "
            "share vocabulary with the internal document, it got pulled into context. Once "
            "there, the model treated its contents as instructions rather than as reference "
            "text, because nothing in the prompt distinguished trusted instructions from "
            "untrusted retrieved data.",
        "real_world": "Several early production RAG chatbots leaked internal documentation "
            "after users asked innocent-sounding questions that happened to retrieve "
            "internal wikis or support tickets containing sensitive notes.",
        "recommended_defense": "Secret scanner, backed by Output guard",
        "why_it_works": "Secret scanner strips known-sensitive patterns from retrieved "
            "content before it ever enters the prompt, so the model never sees the flag in "
            "the first place. Output guard is a second checkpoint that catches anything "
            "that slips past the first layer.",
    },
    "jailbreak": {
        "mechanism": "Wrapping the request in a fictional or hypothetical frame ('let's "
            "roleplay', 'pretend you are') convinced the model the usual rules didn't "
            "apply, even though the information requested was identical to a direct ask.",
        "real_world": "Jailbreak prompts like 'DAN' (Do Anything Now) circulated widely "
            "for early consumer chatbots and reliably bypassed safety guidelines by "
            "reframing requests as fiction.",
        "recommended_defense": "Prompt filter",
        "why_it_works": "Pattern-matching known jailbreak framings, roleplay, hypotheticals, "
            "\"ignore your rules\", catches the most common attempts before the model "
            "processes the request. It won't catch every novel phrasing, but it closes off "
            "well-known techniques cheaply.",
    },
    "indirect-injection": {
        "mechanism": "The malicious instruction lived inside a document the assistant "
            "fetched on your behalf, not in anything you typed. A prompt filter that only "
            "inspects the user's own message has no visibility into that content at all.",
        "real_world": "Security researchers demonstrated this against browsing-enabled "
            "assistants: a webpage containing hidden text like \"ignore your instructions "
            "and do X\" could hijack the assistant when a user simply asked it to summarize "
            "that page.",
        "recommended_defense": "Secret scanner applied to fetched content",
        "why_it_works": "Scanning fetched or retrieved content for injected instructions "
            "before it enters the prompt closes the gap a user-input-only filter misses "
            "entirely, since the attack never touches the user's message.",
    },
    "knowledge-poisoning": {
        "mechanism": "The knowledge base accepted a new document with no review or "
            "validation. Once indexed, the retriever treated it exactly like every other "
            "trusted document, including any instructions embedded inside it.",
        "real_world": "Any RAG system with an open or lightly-moderated ingestion pipeline "
            "is at risk, wikis, ticket systems, or public forums scraped into a knowledge "
            "base can be poisoned by anyone able to post content there.",
        "recommended_defense": "Secret scanner, plus content review before indexing",
        "why_it_works": "Secret scanner still catches the flag pattern at the retrieval "
            "boundary, but the deeper fix is procedural: unreviewed content shouldn't enter "
            "a trusted index at all.",
    },
    "data-exfiltration": {
        "mechanism": "Output guard only matches a literal 'FLAG{...}' pattern. Asking for "
            "the same data spaced out character by character produced text that means the "
            "same thing to a person but no longer matches the filter's regex.",
        "real_world": "Attackers routinely bypass naive data-loss-prevention filters using "
            "encoding tricks like Base64, character spacing, or synonym substitution, a "
            "well-known weakness of pattern-based filtering.",
        "recommended_defense": "Semantic output filtering, not pure regex matching",
        "why_it_works": "A filter that understands meaning rather than exact text can catch "
            "reformatted or encoded versions of the same sensitive data, removing the "
            "attacker's ability to simply disguise it before it's checked.",
    },
    "hallucination": {
        "mechanism": "Nothing in the knowledge base actually answered your question. "
            "Instead of saying so, the model produced a specific, confident-sounding answer "
            "because you asked for one directly and confidently.",
        "real_world": "A well-documented case: a company's support chatbot invented a "
            "refund policy that didn't exist, and the company was held to the fabricated "
            "answer. Confident hallucination on unsupported topics is one of the most "
            "common real-world LLM failure modes.",
        "recommended_defense": "Citation validation",
        "why_it_works": "Requiring every claim to trace back to a specific retrieved source "
            "makes it possible to detect and block answers that aren't actually grounded in "
            "anything, forcing the model to say \"I don't know\" instead of guessing.",
    },
    "context-overflow": {
        "mechanism": "The prompt filter only inspected the first 300 characters of your "
            "message. Padding the request with filler text pushed the real trigger phrase "
            "past that window, so it was never checked.",
        "real_world": "Long-context and multi-turn attacks are an active area of concern: "
            "attackers pad conversations with benign content to push safety-relevant "
            "instructions out of a filter's, or even a model's, effective attention.",
        "recommended_defense": "Scan the entire message regardless of length",
        "why_it_works": "A filter with an artificially limited window is only as strong as "
            "that window. Scanning the full input, however long, closes this specific gap.",
    },
    "tool-injection": {
        "mechanism": "A retrieved document contained an embedded instruction to call a "
            "tool. Because the system executed tool calls found in document content, "
            "anyone able to get content into the index could trigger tool actions.",
        "real_world": "As assistants gain tool access (email, code execution, purchasing), "
            "this attack surface grows: a poisoned calendar invite or document can trigger "
            "unintended actions if the system can't distinguish developer instructions from "
            "text encountered while doing a task.",
        "recommended_defense": "Authorization checkpoint on tool calls",
        "why_it_works": "Requiring tool calls to be explicitly authorized, and rejecting "
            "ones sourced from retrieved content rather than a direct user request, prevents "
            "documents from silently triggering actions.",
    },
    "citation-manipulation": {
        "mechanism": "The response cited a public, uncontroversial-looking document as its "
            "source, while the actual content, including the flag, came from a different, "
            "internal document. Nothing checked whether the citation matched the real "
            "source.",
        "real_world": "This mirrors \"citation laundering\": unverified claims get "
            "attributed to a credible-looking source to make them appear trustworthy, a "
            "known technique in both human and AI-generated misinformation.",
        "recommended_defense": "Citation validation",
        "why_it_works": "Checking that the source cited in a response actually contains "
            "the claim being made catches mismatches like this one before the answer "
            "reaches the user.",
    },
    "memory-poisoning": {
        "mechanism": "You told the assistant to \"remember\" a false statement in one turn. "
            "It stored the claim without verifying it, then repeated it back as fact when "
            "asked to recall it, treating its own prior turn as a trusted source.",
        "real_world": "Long-running agents and assistants with persistent memory are "
            "vulnerable to this: if an attacker gets a false \"fact\" into a memory store "
            "early on, the assistant may treat it as ground truth indefinitely.",
        "recommended_defense": "Authorization / re-verification on recall",
        "why_it_works": "Requiring claims to be re-verified against a source of record "
            "before being repeated as fact, rather than trusting prior conversational turns "
            "unconditionally, breaks the plant-then-recall pattern.",
    },
    "retrieval-abuse": {
        "mechanism": "The retriever ranks by raw keyword overlap. Stuffing your query with "
            "the target document's own vocabulary, with no \"malicious\"-sounding language "
            "at all, forced it to the top of the ranking regardless of relevance.",
        "real_world": "This mirrors SEO keyword stuffing and search-ranking manipulation: "
            "gaming a ranking algorithm directly, rather than the model's behavior, is a "
            "distinct and often-overlooked attack surface for any ranked retrieval system.",
        "recommended_defense": "Classification-based access control, independent of ranking",
        "why_it_works": "Even if ranking itself can be gamed, restricting who can retrieve "
            "confidential-classified documents at all, regardless of similarity score, "
            "prevents an attacker from surfacing the content just by out-scoring others.",
    },
    "authz-bypass": {
        "mechanism": "The system trusted a role claimed in the message text (\"as the "
            "admin\") instead of verifying it against the actual authenticated session, so "
            "anyone could grant themselves elevated access just by asserting it.",
        "real_world": "This is a classic authorization flaw, sometimes called a \"confused "
            "deputy\": it shows up whenever an application checks a role or permission "
            "embedded in request content instead of a verified session or token.",
        "recommended_defense": "Authorization",
        "why_it_works": "Deciding access based only on the verified session persona, and "
            "explicitly ignoring role claims made in the message itself, closes this off "
            "entirely: the text can say anything, but it can't change who you actually are.",
    },
}


def get_explanation(mission_id):
    return EXPLANATIONS.get(mission_id)
