"""Extract the text of every shared document so the review can quote and cite it.

    python extract_docs.py <file or folder> [more ...] --out corpus

Reads .pdf, .docx, .pptx, .xlsx, .csv, .txt and .md. Writes:
  corpus/<file>.txt   the text, with a marker before each page, slide or sheet: === [rfp.pdf | page 3] ===
  corpus/index.json   one entry per page/slide/sheet: file, location, number of characters
and prints a summary. Pages with no text (scanned PDFs) are listed: the review must say they were not read.

Word, PowerPoint and Excel files are read with the Python standard library (python-pptx and openpyxl are used
when installed), so this works in locked-down sandboxes. PDFs need pypdf, pdfplumber or the pdftotext program.
"""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TYPES = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".md"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def clean(text):
    text = text.replace(" ", " ").replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------- readers: each returns [(location, text)]
def read_pdf(path):
    try:
        from pypdf import PdfReader
        return [(f"page {i}", p.extract_text() or "") for i, p in enumerate(PdfReader(str(path)).pages, 1)]
    except ImportError:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return [(f"page {i}", p.extract_text() or "") for i, p in enumerate(pdf.pages, 1)]
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
        return [(f"page {i}", t) for i, t in enumerate(out.split("\f"), 1) if t.strip() or i == 1]
    raise RuntimeError("no PDF reader available (install pypdf, or ask for the document as Word or text)")


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    lines, section, out = [], "start", []

    def para_text(p):
        return "".join(t.text or "" for t in p.iter(f"{W}t"))

    for el in body:
        if el.tag == f"{W}p":
            style = el.find(f"{W}pPr/{W}pStyle")
            t = para_text(el)
            if style is not None and style.get(f"{W}val", "").lower().startswith(("heading", "title")) and t.strip():
                if lines:
                    out.append((f"section '{section}'", "\n".join(lines))); lines = []
                section = t.strip()[:60]
            lines.append(t)
        elif el.tag == f"{W}tbl":
            for row in el.iter(f"{W}tr"):
                cells = [" ".join(para_text(p) for p in c.iter(f"{W}p")).strip() for c in row.iter(f"{W}tc")]
                lines.append(" | ".join(cells))
    if lines:
        out.append((f"section '{section}'", "\n".join(lines)))
    return out


def read_pptx(path):
    try:
        from pptx import Presentation
    except ImportError:
        Presentation = None
    out = []
    if Presentation:
        prs = Presentation(str(path))
        for i, slide in enumerate(prs.slides, 1):
            parts = []

            def walk(shapes):
                for sh in shapes:
                    if sh.shape_type == 6:                      # group
                        walk(sh.shapes)
                    if sh.has_text_frame and sh.text_frame.text.strip():
                        parts.append(sh.text_frame.text)
                    if getattr(sh, "has_table", False) and sh.has_table:
                        for r in sh.table.rows:
                            parts.append(" | ".join(c.text for c in r.cells))
                    if getattr(sh, "has_chart", False) and sh.has_chart:
                        try:
                            ch = sh.chart
                            cats = list(ch.plots[0].categories)
                            for s in ch.plots[0].series:
                                parts.append(f"chart {s.name}: " + ", ".join(f"{c}={v}" for c, v in zip(cats, s.values)))
                        except Exception:
                            pass
            walk(slide.shapes)
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                parts.append("[speaker notes] " + slide.notes_slide.notes_text_frame.text)
            out.append((f"slide {i}", "\n".join(parts)))
        return out
    with zipfile.ZipFile(path) as z:
        names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                       key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for n in names:
            root = ET.fromstring(z.read(n))
            paras = ["".join(t.text or "" for t in p.iter(f"{A}t")) for p in root.iter(f"{A}p")]
            num = int(re.findall(r"\d+", n)[-1])
            out.append((f"slide {num}", "\n".join(p for p in paras if p.strip())))
    return out


def read_xlsx(path):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        out = []
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows(values_only=True):
                vals = ["" if v is None else str(v) for v in row]
                if any(v.strip() for v in vals):
                    rows.append("\t".join(vals).rstrip())
            out.append((f"sheet '{ws.title}'", "\n".join(rows)))
        return out
    except ImportError:
        pass
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{S}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{S}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        titles = [s.get("name") for s in wb.iter(f"{S}sheet")]
        sheets = sorted((n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                        key=lambda n: int(re.findall(r"\d+", n)[-1]))
        out = []
        for k, n in enumerate(sheets):
            rows = []
            for r in ET.fromstring(z.read(n)).iter(f"{S}row"):
                vals = []
                for c in r.iter(f"{S}c"):
                    v = c.find(f"{S}v")
                    t = c.get("t")
                    if t == "s" and v is not None:
                        vals.append(shared[int(v.text)])
                    elif t == "inlineStr":
                        vals.append("".join(x.text or "" for x in c.iter(f"{S}t")))
                    else:
                        vals.append(v.text if v is not None else "")
                if any(x.strip() for x in vals):
                    rows.append("\t".join(vals))
            out.append((f"sheet '{titles[k] if k < len(titles) else k + 1}'", "\n".join(rows)))
        return out


def read_text(path):
    return [("text", path.read_text(encoding="utf-8-sig", errors="replace"))]


READERS = {".pdf": read_pdf, ".docx": read_docx, ".pptx": read_pptx, ".xlsx": read_xlsx,
           ".csv": read_text, ".txt": read_text, ".md": read_text}


def extract(paths, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in TYPES and not f.name.startswith(("~", ".")))
        elif p.exists():
            files.append(p)
        else:
            print(f"NOT FOUND  {p}")
    index, problems = [], []
    for f in files:
        reader = READERS.get(f.suffix.lower())
        if not reader:
            problems.append(f"{f.name}: file type not supported (save it as PDF, Word, PowerPoint, Excel or text)")
            continue
        try:
            parts = reader(f)
        except Exception as e:  # report and keep going; the review must say this file was not read
            problems.append(f"{f.name}: could not be read ({type(e).__name__}: {e})")
            continue
        chunks = []
        for loc, text in parts:
            text = clean(text)
            index.append({"file": f.name, "location": loc, "chars": len(text)})
            if not text and loc.startswith("page"):
                problems.append(f"{f.name} {loc}: no text (probably a scanned image); this page was NOT read")
            chunks.append(f"=== [{f.name} | {loc}] ===\n{text}\n")
        (out_dir / f"{f.name}.txt").write_text("\n".join(chunks), encoding="utf-8")
        print(f"READ       {f.name}: {len(parts)} part(s), {sum(len(c) for c in chunks):,} characters")
    (out_dir / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    for p in problems:
        print(f"PROBLEM    {p}")
    print(f"\nText saved in {out_dir}/ ({len(files) - len([p for p in problems if 'could not' in p])} file(s)). "
          "Read all of it before reviewing; quote from it word for word.")
    return index, problems


def load_corpus(out_dir):
    """{file name: full text} for every extracted file."""
    return {p.name[:-4]: p.read_text(encoding="utf-8") for p in Path(out_dir).glob("*.txt")}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        raise SystemExit(__doc__)
    out = "corpus"
    if "--out" in args:
        k = args.index("--out"); out = args[k + 1]; del args[k:k + 2]
    _, problems = extract(args, out)
    sys.exit(1 if any("could not" in p for p in problems) else 0)


if __name__ == "__main__":
    main()
