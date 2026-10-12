"""Run the MultiDoc Brain experiment.

Phase 1 (always, seconds, no LLM): for each reading level P0..P3, did retrieval put the answer in the top-k chunks?
Phase 2 (optional, --answer): ask the local model each question and score the reply. Resumable.

Examples:
  python run_experiment.py                                   # retrieval only
  python run_experiment.py --answer --model qwen2.5-coder:7b
  python run_experiment.py --answer --levels P0 P3 --limit 12
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

from mdbrain.llm import OllamaLLM
from mdbrain.parsers import LEVELS, LEVEL_NAMES, ocr_available
from mdbrain.pipeline import Index, answer
from mdbrain.scoring import is_correct, retrieval_hit

ROOT = Path(__file__).resolve().parent
RET_FIELDS = ["level", "qid", "kind", "hit", "top_sources"]
ANS_FIELDS = ["level", "qid", "kind", "retrieval_hit", "correct", "seconds", "model", "reply"]


def load_questions(corpus: Path):
    p = corpus / "questions.json"
    if not p.exists():
        print("Corpus missing, generating it...")
        subprocess.check_call([sys.executable, str(ROOT / "tools" / "make_corpus.py")])
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=str(ROOT / "corpus"))
    ap.add_argument("--levels", nargs="+", default=LEVELS, choices=LEVELS)
    ap.add_argument("--k", type=int, default=4, help="chunks passed to the model")
    ap.add_argument("--answer", action="store_true", help="also ask the local model (slow on CPU)")
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--limit", type=int, default=0, help="only the first N questions")
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()

    corpus, out = Path(a.docs), Path(a.out)
    out.mkdir(exist_ok=True)
    qs = load_questions(corpus)
    if a.limit:
        qs = qs[: a.limit]

    if not ocr_available() and "P3" in a.levels:
        print("NOTE: Tesseract OCR not found, so P3 cannot read scanned files and will equal P2. "
              "Install it (see README) to measure the OCR level.")

    # ---------- Phase 1: retrieval ----------
    indexes, rows = {}, []
    for lv in a.levels:
        indexes[lv] = Index(corpus, lv)
        for q in qs:
            chunks = indexes[lv].retrieve(q["question"], a.k)
            hit = retrieval_hit(chunks, q)
            rows.append({"level": lv, "qid": q["id"], "kind": q["kind"],
                         "hit": "" if hit is None else int(hit),
                         "top_sources": ";".join(dict.fromkeys(c.source for c in chunks))})
    with open(out / "retrieval.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RET_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nRetrieval hit@{a.k} (answer text present in the chunks given to the model):")
    for lv in a.levels:
        r = [x for x in rows if x["level"] == lv and x["hit"] != ""]
        print(f"  {lv} {LEVEL_NAMES[lv]:<22} {sum(int(x['hit']) for x in r)}/{len(r)}")

    if not a.answer:
        print("\nRetrieval-only run done. Add --answer to test the local model. Then: python make_report.py")
        return

    # ---------- Phase 2: model answers (resumable) ----------
    llm = OllamaLLM(a.model)
    llm.check()
    ans_path = out / "answers.csv"
    done = set()
    if ans_path.exists():
        with open(ans_path, newline="", encoding="utf-8") as f:
            done = {(r["level"], r["qid"], r["model"]) for r in csv.DictReader(f)}
    todo = [(lv, q) for lv in a.levels for q in qs if (lv, q["id"], a.model) not in done]
    total = len(todo)
    new_file = not ans_path.exists()
    with open(ans_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ANS_FIELDS)
        if new_file:
            w.writeheader()
        for n, (lv, q) in enumerate(todo, 1):
            t0 = time.time()
            try:
                reply, chunks = answer(indexes[lv], q["question"], llm, a.k)
            except Exception as e:
                print(f"[{n}/{total}] {lv} {q['id']} ERROR: {e}")
                continue
            ok = is_correct(reply, q)
            hit = retrieval_hit(chunks, q)
            dt = time.time() - t0
            w.writerow({"level": lv, "qid": q["id"], "kind": q["kind"],
                        "retrieval_hit": "" if hit is None else int(hit), "correct": int(ok),
                        "seconds": f"{dt:.1f}", "model": a.model,
                        "reply": reply.replace("\n", " ")[:300]})
            f.flush()
            print(f"[{n}/{total}] {lv} {q['id']} {'OK ' if ok else 'BAD'} {dt:5.1f}s  {reply.strip()[:70]!r}")
    print("\nDone. Next: python make_report.py && python make_dashboard.py")


if __name__ == "__main__":
    main()
