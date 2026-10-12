"""Ask questions about your own folder of documents, using a local model.

  python ask.py                         # chat over ./corpus (the demo files)
  python ask.py --docs C:\\path\\to\\your\\files --level P3
  python ask.py "How many annual leave days does a Senior get?"
"""
import argparse
import sys
from pathlib import Path

from mdbrain.llm import OllamaLLM
from mdbrain.parsers import LEVELS, LEVEL_NAMES
from mdbrain.pipeline import Index, answer


def show(reply, chunks):
    print(f"\nAnswer: {reply}\n")
    print("Sources:")
    for c in chunks:
        print(f"  - {c.source}" + (f" ({c.loc})" if c.loc else ""))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="*")
    ap.add_argument("--docs", default=str(Path(__file__).resolve().parent / "corpus"))
    ap.add_argument("--level", default="P3", choices=LEVELS)
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--k", type=int, default=4)
    a = ap.parse_args()

    llm = OllamaLLM(a.model)
    llm.check()
    idx = Index(a.docs, a.level)
    print(f"Indexed {len(idx.chunks)} chunks from {a.docs} at level {a.level} ({LEVEL_NAMES[a.level]}).")
    if a.question:
        show(*answer(idx, " ".join(a.question), llm, a.k))
        return
    print("Type a question (empty line to quit).")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        show(*answer(idx, q, llm, a.k))


if __name__ == "__main__":
    sys.exit(main())
