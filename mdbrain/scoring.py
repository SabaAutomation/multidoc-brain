"""Deterministic scoring. No LLM judge: a plain string match against the known answer."""
import re

_comma = re.compile(r"(?<=\d),(?=\d{3})")


def norm(s: str) -> str:
    s = s.lower().replace("$", "")
    s = _comma.sub("", s)
    return s


def _find(text: str, alt: str) -> bool:
    alt = norm(alt).strip()
    return re.search(r"(?<![\w.])" + re.escape(alt) + r"s?(?![\w])", text) is not None


def matches(text: str, gold_all: list) -> bool:
    """Every gold item must be present; an item may list alternatives separated by '|'."""
    t = norm(text)
    return all(any(_find(t, a) for a in item.split("|")) for item in gold_all)


def is_correct(reply: str, question: dict) -> bool:
    if question["kind"] == "unanswerable":
        return "not found" in reply.lower()
    return matches(reply, question["gold"])


def retrieval_hit(chunks, question: dict):
    """None for unanswerable questions (nothing to retrieve)."""
    if question["kind"] == "unanswerable":
        return None
    return matches("\n".join(c.text for c in chunks), question["gold"])
