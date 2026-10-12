"""File parsers. Four levels (P0..P3) of how much care goes into reading messy files.

P0  plain text only      docx paragraphs only (tables are dropped), spreadsheets dumped as bare cell values
P1  table-aware          tables / sheets / csv rows become "Header: value | Header: value" lines
P2  P1 + source labels   every chunk starts with [file | sheet / page / table caption]
P3  P2 + OCR             pages with no text layer are read with Tesseract OCR (optional install)

Each parser returns a list of Unit objects (a paragraph, a line or a table row).
"""
import csv
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

LEVELS = ["P0", "P1", "P2", "P3"]
LEVEL_NAMES = {
    "P0": "plain text only",
    "P1": "+ table-aware rows",
    "P2": "+ source labels",
    "P3": "+ OCR for scans",
}
SUPPORTED = {".pdf", ".docx", ".xlsx", ".csv", ".md", ".txt"}


@dataclass
class Unit:
    text: str
    source: str
    loc: str = ""


def level_num(level: str) -> int:
    return LEVELS.index(level)


# ---------- OCR (optional) ----------
def tesseract_cmd():
    found = shutil.which("tesseract")
    if found:
        return found
    for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(p):
            return p
    return None


def ocr_available() -> bool:
    return tesseract_cmd() is not None


def ocr_image_bytes(data: bytes, suffix: str = ".png") -> str:
    cmd = tesseract_cmd()
    if not cmd:
        return ""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "page" + suffix)
        with open(p, "wb") as f:
            f.write(data)
        try:
            r = subprocess.run([cmd, p, "stdout"], capture_output=True, text=True, timeout=90)
            return r.stdout or ""
        except Exception:
            return ""


# ---------- helpers ----------
def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else f"{v:.2f}"
    return str(v).strip()


def row_to_text(headers, row) -> str:
    parts = []
    for h, v in zip(headers, row):
        s = fmt(v)
        if s:
            parts.append(f"{fmt(h)}: {s}")
    return " | ".join(parts)


# ---------- per format ----------
def parse_pdf(path: Path, level: str) -> list:
    from pypdf import PdfReader
    units = []
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        loc = f"page {i}"
        if text:
            for line in text.splitlines():
                if line.strip():
                    units.append(Unit(line.strip(), path.name, loc))
        elif level_num(level) >= 3:
            try:
                for img in page.images:
                    suffix = os.path.splitext(img.name)[1] or ".png"
                    ocr = ocr_image_bytes(img.data, suffix)
                    for line in ocr.splitlines():
                        if line.strip():
                            units.append(Unit(line.strip(), path.name, loc + " (OCR)"))
            except Exception:
                pass
    return units


def _docx_body(doc):
    """Yield ('p', text) and ('t', table) in document order."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield "p", Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield "t", Table(child, doc)


def parse_docx(path: Path, level: str) -> list:
    from docx import Document
    doc = Document(str(path))
    units, last_par, n_table = [], "", 0
    for kind, obj in _docx_body(doc):
        if kind == "p":
            t = obj.text.strip()
            if t:
                units.append(Unit(t, path.name, ""))
                last_par = t
        elif level_num(level) >= 1:
            n_table += 1
            rows = [[c.text.strip() for c in r.cells] for r in obj.rows]
            if len(rows) < 2:
                continue
            caption = last_par[:60]
            loc = f"table {n_table}" + (f": {caption}" if caption else "")
            for r in rows[1:]:
                units.append(Unit(row_to_text(rows[0], r), path.name, loc))
    return units


def parse_xlsx(path: Path, level: str) -> list:
    from openpyxl import load_workbook
    wb = load_workbook(str(path), data_only=True, read_only=True)
    units = []
    for ws in wb.worksheets:
        rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
        if not rows:
            continue
        if level_num(level) == 0:
            for r in rows:
                t = " ".join(fmt(c) for c in r if fmt(c))
                if t:
                    units.append(Unit(t, path.name, ""))
        else:
            for r in rows[1:]:
                t = row_to_text(rows[0], r)
                if t:
                    units.append(Unit(t, path.name, f"sheet {ws.title}"))
    return units


def parse_csv(path: Path, level: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    units = []
    if level_num(level) == 0:
        for r in rows:
            units.append(Unit(" ".join(c for c in r if c), path.name, ""))
    else:
        for r in rows[1:]:
            t = row_to_text(rows[0], r)
            if t:
                units.append(Unit(t, path.name, "csv"))
    return units


def parse_text(path: Path, level: str) -> list:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Unit(line.strip(), path.name, ""))
    return out


PARSERS = {".pdf": parse_pdf, ".docx": parse_docx, ".xlsx": parse_xlsx,
           ".csv": parse_csv, ".md": parse_text, ".txt": parse_text}


def parse_file(path: Path, level: str) -> list:
    return PARSERS[path.suffix.lower()](path, level)


def parse_folder(folder, level: str) -> list:
    units = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() in SUPPORTED:
            units.extend(parse_file(p, level))
    return units
