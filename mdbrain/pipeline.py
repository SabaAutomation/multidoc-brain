"""Chunk, index, retrieve, prompt, answer."""
from dataclasses import dataclass

from .bm25 import BM25
from .parsers import level_num, parse_folder

MAX_CHARS = 700

SYSTEM = (
    "You answer questions using ONLY the context excerpts provided. "
    "If the context does not contain the answer, reply with exactly: NOT FOUND. "
    "Otherwise answer in one short sentence with the exact value. Do not guess."
)


@dataclass
class Chunk:
    text: str
    source: str
    loc: str


def make_chunks(units, level: str) -> list:
    """Group consecutive units from the same source and location up to MAX_CHARS."""
    chunks, buf, key, size = [], [], None, 0

    def flush():
        nonlocal buf, key, size
        if buf:
            body = "\n".join(buf)
            if level_num(level) >= 2:
                label = key[0] + (f" | {key[1]}" if key[1] else "")
                body = f"[{label}]\n{body}"
            chunks.append(Chunk(body, key[0], key[1]))
        buf, key, size = [], None, 0

    for u in units:
        k = (u.source, u.loc)
        if key is not None and (k != key or size + len(u.text) > MAX_CHARS):
            flush()
        if key is None:
            key = k
        buf.append(u.text)
        size += len(u.text) + 1
    flush()
    return chunks


class Index:
    def __init__(self, folder, level: str):
        self.level = level
        self.chunks = make_chunks(parse_folder(folder, level), level)
        self.bm25 = BM25([c.text for c in self.chunks])

    def retrieve(self, question: str, k: int = 4) -> list:
        return [self.chunks[i] for i, s in self.bm25.top(question, k) if s > 0]


def build_prompt(question: str, chunks) -> str:
    if not chunks:
        ctx = "(no relevant excerpts found)"
    else:
        ctx = "\n\n".join(f"--- excerpt {i} ---\n{c.text}" for i, c in enumerate(chunks, 1))
    return f"Context:\n{ctx}\n\nQuestion: {question}\nAnswer:"


def answer(index: Index, question: str, llm, k: int = 4):
    chunks = index.retrieve(question, k)
    reply = llm.chat(SYSTEM, build_prompt(question, chunks))
    return reply.strip(), chunks
