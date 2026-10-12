"""Build results/dashboard.html: a single static page (no libraries) from the CSV results.
Open it in a browser and screenshot it for your README / LinkedIn."""
import csv
import html
from collections import defaultdict
from pathlib import Path

from mdbrain.parsers import LEVELS, LEVEL_NAMES

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
GROUPS = ["prose", "docx_table", "xlsx", "csv", "scanned"]
LABEL = {"prose": "Prose (pdf / docx / md)", "docx_table": "Table inside a docx", "xlsx": "Spreadsheet (xlsx)",
         "csv": "CSV file", "scanned": "Scanned PDF (image only)"}


def read(p):
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grid(rows, field):
    cell = defaultdict(lambda: [0, 0])
    for r in rows:
        if r[field] == "" or r["kind"] not in GROUPS:
            continue
        c = cell[(r["kind"], r["level"])]
        c[0] += int(r[field])
        c[1] += 1
    return cell


def color(frac):
    # red -> amber -> green, readable with dark text
    r = int(235 - 120 * frac) if frac > .5 else 235
    g = int(110 + 120 * frac)
    return f"rgb({r},{g},120)"


def table_html(cell, title, sub):
    h = [f"<h2>{html.escape(title)}</h2><p class='sub'>{html.escape(sub)}</p><table><tr><th></th>"]
    for lv in LEVELS:
        h.append(f"<th>{lv}<br><span>{html.escape(LEVEL_NAMES[lv])}</span></th>")
    h.append("</tr>")
    for g in GROUPS:
        h.append(f"<tr><td class='row'>{html.escape(LABEL[g])}</td>")
        for lv in LEVELS:
            a, n = cell[(g, lv)]
            if n:
                f = a / n
                h.append(f"<td style='background:{color(f)}'>{a}/{n}<br><span>{round(100 * f)}%</span></td>")
            else:
                h.append("<td>-</td>")
        h.append("</tr>")
    h.append("<tr><td class='row'><b>All answerable</b></td>")
    for lv in LEVELS:
        a = sum(cell[(g, lv)][0] for g in GROUPS)
        n = sum(cell[(g, lv)][1] for g in GROUPS)
        h.append(f"<td class='tot'><b>{a}/{n}</b><br><span>{round(100 * a / n) if n else 0}%</span></td>")
    h.append("</tr></table>")
    return "".join(h)


def main():
    ret, ans = read(RES / "retrieval.csv"), read(RES / "answers.csv")
    parts = []
    if ret:
        parts.append(table_html(grid(ret, "hit"), "Retrieval: did the answer reach the model?",
                                "hit@4 on 31 answerable questions, plain BM25, no LLM involved"))
    if ans:
        models = sorted({r["model"] for r in ans})
        for m in models:
            rows = [r for r in ans if r["model"] == m]
            parts.append(table_html(grid(rows, "correct"), f"Model answers: {m}",
                                    "answer correct = known answer present in the reply (1 run per cell)"))
            un = [r for r in rows if r["kind"] == "unanswerable"]
            if un:
                bits = []
                for lv in LEVELS:
                    x = [r for r in un if r["level"] == lv]
                    if x:
                        bits.append(f"{lv}: {sum(int(r['correct']) for r in x)}/{len(x)}")
                parts.append("<p class='sub'><b>Refused when the answer was not in the files (NOT FOUND):</b> "
                             + " &nbsp; ".join(bits) + "</p>")
    body = "\n".join(parts) or "<p>No results yet. Run python run_experiment.py</p>"
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>MultiDoc Brain</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#0f1115;color:#eceff4;margin:0;padding:32px}}
.wrap{{max-width:980px;margin:auto}} h1{{margin:0 0 4px;font-size:30px}} h1 b{{color:#ff8a3d}}
.tag{{color:#9aa3b2;margin:0 0 24px}} h2{{margin:32px 0 2px;font-size:20px}} .sub{{color:#9aa3b2;margin:0 0 10px;font-size:14px}}
table{{border-collapse:collapse;width:100%}} th,td{{padding:12px 10px;text-align:center;border:1px solid #232834}}
th{{background:#171a21;font-size:15px}} th span,td span{{font-size:11px;color:#c5cbd6;font-weight:400}}
td{{color:#101216;font-weight:700}} td.row{{text-align:left;background:#171a21;color:#eceff4;font-weight:500}}
td span{{color:#202530}} td.tot{{background:#171a21;color:#ff8a3d;font-size:17px}} td.tot span{{color:#c5cbd6}} .foot{{margin-top:28px;color:#6f7889;font-size:12px}}
</style></head><body><div class="wrap">
<h1>MultiDoc <b>Brain</b></h1>
<p class="tag">Same documents, same questions, four ways of reading messy files (P0 to P3).</p>
{body}
<p class="foot">Synthetic corpus (8 files, 34 questions). Small test: treat gaps of a question or two as noise. Code: github.com/SabaAutomation/multidoc-brain</p>
</div></body></html>"""
    (RES / "dashboard.html").write_text(page, encoding="utf-8")
    print(f"Written: {RES / 'dashboard.html'}")


if __name__ == "__main__":
    main()
