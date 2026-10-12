"""Self-test: proves the project works end to end WITHOUT Ollama (uses a mock model).
Run:  python selfcheck.py"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mdbrain.bm25 import BM25, tokenize                      # noqa: E402
from mdbrain.llm import MockLLM                              # noqa: E402
from mdbrain.parsers import LEVELS, ocr_available, parse_folder   # noqa: E402
from mdbrain.pipeline import Index, answer, make_chunks      # noqa: E402
from mdbrain.scoring import is_correct, matches, retrieval_hit  # noqa: E402

ok_count, fails = 0, []


def check(name, cond):
    global ok_count
    if cond:
        ok_count += 1
        print(f"  ok   {name}")
    else:
        fails.append(name)
        print(f"  FAIL {name}")


corpus = ROOT / "corpus"
if not (corpus / "questions.json").exists():
    subprocess.check_call([sys.executable, str(ROOT / "tools" / "make_corpus.py")])
qs = json.loads((corpus / "questions.json").read_text(encoding="utf-8"))

print("scoring")
check("plain number matches", matches("The price is $154.", ["154"]))
check("comma number matches", matches("Revenue was 205,750", ["205750"]))
check("no partial number (9 vs 19)", not matches("lead time is 19 days", ["9"]))
check("no partial number (9 vs 89.50)", not matches("it costs 89.50", ["9"]))
check("plural accepted", matches("Wednesdays and Fridays", ["wednesday", "friday"]))
check("alternatives work", matches("two years", ["2 years|two years"]))
check("all parts required", not matches("9:00 only", ["9:00", "17:30"]))
check("unanswerable: NOT FOUND is correct", is_correct("NOT FOUND", {"kind": "unanswerable", "gold": []}))
check("unanswerable: a guess is wrong", not is_correct("It is $90,000", {"kind": "unanswerable", "gold": []}))

print("bm25")
b = BM25(["red apple pie", "green apple tart", "blue car engine"])
check("bm25 ranks the matching doc first", b.top("car engine", 1)[0][0] == 2)
check("tokenizer drops stopwords", "the" not in tokenize("the price of the boots"))

print("parsers")
p0 = [u.text for u in parse_folder(corpus, "P0")]
p1 = [u.text for u in parse_folder(corpus, "P1")]
p3 = [u.text for u in parse_folder(corpus, "P3")]
check("P0 drops docx table rows", not any("Senior" in t and "22" in t for t in p0))
check("P1 keeps docx table rows with headers", any("Role: Senior" in t and "Annual leave days: 22" in t for t in p1))
check("P0 spreadsheet rows have no header names", not any("Price:" in t for t in p0))
check("P1 spreadsheet rows have header names", any("Product: Ridge Boots" in t and "Price: 154" in t for t in p1))
check("scanned PDF has no text layer without OCR", not any("Okoye" in t for t in p1))
if ocr_available():
    check("P3 OCR reads the scanned notice", any("Okoye" in t for t in p3))
else:
    print("  skip OCR test (Tesseract not installed)")

print("chunks")
c2 = make_chunks(parse_folder(corpus, "P2"), "P2")
check("P2 chunks carry a [source | location] label", all(c.text.startswith("[") for c in c2))
check("P1 chunks have no label", not any(c.text.startswith("[") for c in make_chunks(parse_folder(corpus, "P1"), "P1")))

print("questions")
check("34 questions, unique ids", len(qs) == 34 and len({q["id"] for q in qs}) == 34)
best = "P3" if ocr_available() else "P2"
idx = Index(corpus, best)
alltext = "\n".join(c.text for c in idx.chunks)
bad = [q["id"] for q in qs if q["kind"] != "unanswerable" and not (q["kind"] == "scanned" and best == "P2")
       and not matches(alltext, q["gold"])]
check("every answerable gold string exists in the best-level text", not bad)
check("unanswerable questions have no source file", all(q["file"] == "" for q in qs if q["kind"] == "unanswerable"))

print("pipeline (mock model)")
q_ans = next(q for q in qs if q["id"] == "q16")
reply, chunks = answer(Index(corpus, "P1"), q_ans["question"], MockLLM(fixed="22 days"), 4)
check("answer() returns the model reply and chunks", reply == "22 days" and len(chunks) > 0)
check("P1 retrieval hits the table question", retrieval_hit(chunks, q_ans) is True)
check("P0 retrieval misses the table question",
      retrieval_hit(Index(corpus, "P0").retrieve(q_ans["question"], 4), q_ans) is False)
check("unanswerable has no retrieval hit value", retrieval_hit([], {"kind": "unanswerable", "gold": []}) is None)

print("runner / report / dashboard")
tmp = Path(tempfile.mkdtemp())
try:
    subprocess.check_call([sys.executable, str(ROOT / "run_experiment.py"), "--out", str(tmp), "--levels", "P0", "P1"],
                          stdout=subprocess.DEVNULL)
    check("retrieval.csv written", (tmp / "retrieval.csv").exists())
    import make_report, make_dashboard   # noqa: E402
    make_report.RES = tmp
    make_dashboard.RES = tmp
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        make_report.main()
        make_dashboard.main()
    check("REPORT.md written", (tmp / "REPORT.md").exists())
    check("dashboard.html written", (tmp / "dashboard.html").stat().st_size > 1000)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("PROBLEMS:", fails)
    sys.exit(1)
print(f"ALL GOOD ({ok_count} checks)")
