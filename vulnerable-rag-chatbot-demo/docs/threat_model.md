# Threat Model

## System

A local RAG-style chatbot that retrieves documents from a knowledge base and uses the retrieved content to answer user questions.

## Assets

- Public policy documents
- Confidential internal notes
- Synthetic fake credentials
- User trust in chatbot output

## Threats

### Spoofing

An attacker pretends to be an authorized auditor or admin in a prompt.

### Tampering

An attacker adds or modifies a knowledge-base document to poison retrieval results.

### Repudiation

Without logging, the team cannot prove who added poisoned content or who requested secrets.

### Information Disclosure

The bot reveals confidential retrieved context, fake tokens, or internal notes.

### Denial of Service

Attackers can flood the bot with long prompts or many poisoned documents.

### Elevation of Privilege

A normal user accesses internal-only data because retrieval lacks authorization checks.

## Mitigations

- Require document classification and ownership metadata.
- Enforce retrieval-time authorization.
- Keep secrets out of RAG indexes.
- Add ingestion review and signing for trusted documents.
- Redact credentials before output.
- Log suspicious prompts and retrieval sources.
- Test with red-team prompt suites.
