from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import re

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

@dataclass
class Document:
    path: Path
    title: str
    classification: str
    text: str


@dataclass
class RetrievalHit:
    document: Document
    score: int
    matched_terms: list[str]
    blocked: bool = False
    reason: str = ""


def load_documents():
    docs = []
    for path in sorted(DATA_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        title = "Untitled"
        classification = "public"
        for line in text.splitlines():
            if line.startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
            if line.startswith("CLASSIFICATION:"):
                classification = line.split(":", 1)[1].strip().lower()
        docs.append(Document(path=path, title=title, classification=classification, text=text))
    return docs


def tokenize(text: str):
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def score_documents(query: str, safe_mode: bool = False, limit: int = 3):
    docs = load_documents()

    q_tokens = tokenize(query)
    scored: list[RetrievalHit] = []

    for doc in docs:
        matched_terms = sorted(q_tokens & tokenize(doc.text))
        score = len(matched_terms)
        # Deliberately unsafe behavior: secret-seeking queries retrieve more docs.
        if not safe_mode and any(word in query.lower() for word in ["secret", "password", "token", "api key", "internal"]):
            score += 5
        blocked = safe_mode and doc.classification != "public"
        reason = "blocked by classification filter" if blocked else ""
        scored.append(RetrievalHit(doc, score, matched_terms, blocked, reason))

    scored.sort(key=lambda hit: hit.score, reverse=True)
    visible_hits = [hit for hit in scored if not hit.blocked]
    selected = [hit for hit in visible_hits[:limit] if hit.score > 0 or not safe_mode]
    blocked = [hit for hit in scored if hit.blocked]
    return selected, blocked


def retrieve(query: str, safe_mode: bool = False, limit: int = 3):
    selected, _blocked = score_documents(query, safe_mode=safe_mode, limit=limit)
    return [hit.document for hit in selected]
