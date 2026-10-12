"""Tiny pure-Python BM25 so the project needs no vector database and no extra model download."""
import math
import re
from collections import Counter

STOP = set("""a an the of is are was were be been what how many much does do did for to in on at and or who whom
which when where by it its get gets from with as that this there have has had can i you we they me my our your
their about into per""".split())

_num_comma = re.compile(r"(?<=\d),(?=\d{3})")
_tok = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def tokenize(text: str) -> list:
    text = _num_comma.sub("", text.lower())
    out = []
    for t in _tok.findall(text):
        if t in STOP:
            continue
        if len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        out.append(t)
    return out


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tokens = [tokenize(d) for d in docs]
        self.n = len(docs)
        self.avgdl = (sum(len(t) for t in self.tokens) / self.n) if self.n else 0.0
        self.tf = [Counter(t) for t in self.tokens]
        df = Counter()
        for t in self.tokens:
            df.update(set(t))
        self.idf = {w: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def score(self, query: str) -> list:
        q = tokenize(query)
        scores = []
        for i in range(self.n):
            dl = len(self.tokens[i]) or 1
            s = 0.0
            for w in q:
                f = self.tf[i].get(w, 0)
                if not f:
                    continue
                s += self.idf.get(w, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            scores.append(s)
        return scores

    def top(self, query: str, k: int = 4) -> list:
        sc = self.score(query)
        order = sorted(range(self.n), key=lambda i: sc[i], reverse=True)
        return [(i, sc[i]) for i in order[:k]]
