try:
    from .retrieval import score_documents
    from .security import is_suspicious_prompt, redact_secrets
except ImportError:
    from retrieval import score_documents
    from security import is_suspicious_prompt, redact_secrets


def _sources(hits):
    return [
        f"{hit.document.path.name} ({hit.document.classification}, score {hit.score})"
        for hit in hits
    ]


def _trace(hits, blocked=None):
    blocked = blocked or []
    return {
        "retrieved": [
            {
                "title": hit.document.title,
                "file": hit.document.path.name,
                "classification": hit.document.classification,
                "score": hit.score,
                "matched_terms": hit.matched_terms[:8],
            }
            for hit in hits
        ],
        "blocked": [
            {
                "title": hit.document.title,
                "file": hit.document.path.name,
                "classification": hit.document.classification,
                "score": hit.score,
                "reason": hit.reason,
            }
            for hit in blocked
        ],
    }


def vulnerable_answer(question: str) -> dict:
    hits, blocked = score_documents(question, safe_mode=False)
    docs = [hit.document for hit in hits]
    context = "\n\n".join(doc.text for doc in docs)

    # This intentionally simulates a dangerously obedient chatbot.
    lower = question.lower()
    if any(word in lower for word in ["secret", "password", "token", "api key", "internal notes", "full context"]):
        answer = "Here is the retrieved context:\n\n" + context
    elif "vpn" in lower:
        # Poisoned docs can override the public answer because retrieved context is blindly trusted.
        if "VPN access does not require MFA" in context:
            answer = "VPN access does not require MFA."
        else:
            answer = "VPN access requires multi-factor authentication."
    elif any(word in lower for word in ["phishing", "malware", "incident", "suspicious email"]):
        answer = (
            "Report suspected phishing, malware, lost devices, or unusual login prompts to "
            "security@example.local. Include the affected system, time observed, and screenshots "
            "if you have them."
        )
    elif "password" in lower:
        answer = "Passwords must be at least 14 characters long. Use multi-factor authentication for protected services."
    elif "access" in lower or "admin" in lower:
        answer = (
            "Administrative access requires manager approval, security review, and ticket-based "
            "tracking. Shared accounts are prohibited."
        )
    elif "chatbot" in lower or "assistant" in lower or "knowledge" in lower:
        answer = (
            "The chatbot should answer from approved policy documents, cite source titles when "
            "possible, and refuse requests for hidden context or credentials."
        )
    else:
        answer = "Based on the retrieved context:\n\n" + context[:800]

    return {
        "mode": "vulnerable",
        "answer": answer,
        "sources": _sources(hits),
        "trace": _trace(hits, blocked),
        "warning": "This response came from intentionally vulnerable logic.",
    }


def safe_answer(question: str) -> dict:
    suspicious = is_suspicious_prompt(question)
    hits, blocked = score_documents(question, safe_mode=True)
    docs = [hit.document for hit in hits]
    context = "\n\n".join(doc.text for doc in docs)

    lower = question.lower()
    if suspicious:
        answer = "I can answer policy questions, but I cannot reveal secrets, credentials, internal notes, or raw hidden context."
    elif "vpn" in lower:
        answer = "VPN access requires multi-factor authentication."
    elif any(word in lower for word in ["phishing", "malware", "incident", "suspicious email"]):
        answer = (
            "Report suspected phishing, malware, lost devices, or unusual login prompts to "
            "security@example.local. Include the affected system, time observed, and screenshots "
            "if available."
        )
    elif "password" in lower:
        answer = "Passwords must be at least 14 characters long. Use multi-factor authentication for protected services."
    elif "access" in lower or "admin" in lower:
        answer = (
            "Administrative access requires manager approval, security review, and ticket-based "
            "tracking. Shared accounts are prohibited."
        )
    elif "chatbot" in lower or "assistant" in lower or "knowledge" in lower:
        answer = (
            "The chatbot should answer from approved public policy documents, cite source titles "
            "when possible, and refuse requests for hidden context or credentials."
        )
    else:
        answer = "Based on approved public documents: " + context[:500]

    return {
        "mode": "safe",
        "answer": redact_secrets(answer),
        "sources": _sources(hits),
        "trace": _trace(hits, blocked),
        "warning": "Safe mode filters confidential documents and redacts secret-like strings.",
    }
