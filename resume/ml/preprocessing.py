import re
from collections import Counter


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
    "with", "or", "this", "these", "those", "you", "your", "i", "we", "our", "their",
}


def simple_stem(token: str) -> str:
    for suffix in ("ingly", "edly", "ing", "ed", "ly", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9+#\s]", " ", lowered)
    raw_tokens = cleaned.split()
    tokens: list[str] = []
    for token in raw_tokens:
        if token in STOP_WORDS:
            continue
        stemmed = simple_stem(token)
        if len(stemmed) < 2:
            continue
        tokens.append(stemmed)
    return tokens


def vectorize_tokens(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def combine_feature_text(resume_text: str, skills: str = "", education: str = "", experience: str = "") -> str:
    parts: list[str] = []
    if skills:
        parts.append((skills + " ") * 3)
    if experience:
        parts.append((experience + " ") * 2)
    if education:
        parts.append(education + " ")
    if resume_text:
        parts.append(resume_text)
    return "".join(parts).strip()
