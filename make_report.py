"""Turn results/*.csv into results/REPORT.md (tables you can paste into the README)."""
import csv
from collections import defaultdict
from pathlib import Path

from mdbrain.parsers import LEVELS, LEVEL_NAMES

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
GROUPS = ["prose", "docx_table", "xlsx", "csv", "scanned"]
GROUP_LABEL = {"prose": "Prose (pdf/docx/md)", "docx_table": "Table in a docx", "xlsx": "Spreadsheet (xlsx)",
               "csv": "CSV", "scanned": "Scanned PDF", "unanswerable": "Not in the docs"}


def read(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def table(rows, field, groups, model=None):
    cell = defaultdict(lambda: [0, 0])
    tot = defaultdict(lambda: [0, 0])
    for r in rows:
        if model and r.get("model") != model:
            continue
        v = r[field]
        if v == "" or r["kind"] not in groups:
            continue
        cell[(r["level"], r["kind"])][0] += int(v)
        cell[(r["level"], r["kind"])][1] += 1
        if r["kind"] in GROUPS:
            tot[r["level"]][0] += int(v)
            tot[r["level"]][1] += 1
    head = "| File type | " + " | ".join(f"{lv} {LEVEL_NAMES[lv]}" for lv in LEVELS) + " |"
    sep = "|---|" + "---|" * len(LEVELS)
    lines = [head, sep]
    for g in groups:
        cells = []
        for lv in LEVELS:
            a, n = cell[(lv, g)]
            cells.append(f"{a}/{n}" if n else "-")
        lines.append(f"| {GROUP_LABEL[g]} | " + " | ".join(cells) + " |")
    if groups == GROUPS:
        cells = []
        for lv in LEVELS:
            a, n = tot[lv]
            cells.append(f"**{a}/{n}**" if n else "-")
        lines.append("| **All answerable** | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    ret = read(RES / "retrieval.csv")
    ans = read(RES / "answers.csv")
    out = ["# MultiDoc Brain results", ""]
    if ret:
        out += ["## 1. Retrieval: was the answer inside the chunks the model received?",
                "", "Deterministic (no LLM). Higher is better.", "", table(ret, "hit", GROUPS), ""]
    if ans:
        models = sorted({r["model"] for r in ans})
        for m in models:
            out += [f"## 2. Model answers ({m})", "",
                    "Answer correct = known answer string present in the reply.", "",
                    table(ans, "correct", GROUPS, m), ""]
            un = defaultdict(lambda: [0, 0])
            for r in ans:
                if r["model"] == m and r["kind"] == "unanswerable":
                    un[r["level"]][0] += int(r["correct"])
                    un[r["level"]][1] += 1
            if un:
                out += ["**Questions whose answer is NOT in the documents** "
                        "(correct = the model said NOT FOUND instead of guessing):", ""]
                out += ["| Level | Correctly refused |", "|---|---|"]
                for lv in LEVELS:
                    if un[lv][1]:
                        out.append(f"| {lv} {LEVEL_NAMES[lv]} | {un[lv][0]}/{un[lv][1]} |")
                out.append("")
    out += ["## What this does and does not show", "",
            "- It compares ways of *reading* messy files, on a small synthetic corpus (8 files, 34 questions) "
            "with known answers.",
            "- Retrieval is plain BM25 keyword search. Results may differ with embeddings or other retrievers.",
            "- Model answers come from a small local model on a CPU, usually 1 run per cell. "
            "Small differences can be noise; repeat before you trust them.",
            "- The corpus is invented and clean compared with real client files.", ""]
    (RES / "REPORT.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print(f"\nWritten: {RES / 'REPORT.md'}")


if __name__ == "__main__":
    main()
