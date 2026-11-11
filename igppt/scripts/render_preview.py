"""Render a .pptx to one image per slide so the slides can be checked before they are shared.

    python render_preview.py deck.pptx [out_dir] [--dpi 110]

Needs LibreOffice (soffice) for the PDF step. Images are made with pdftoppm (Poppler) if present,
otherwise with PyMuPDF (`pip install pymupdf`). With neither, the PDF is left in out_dir.
Set the SOFFICE environment variable to point at the soffice program if it is not on PATH.
"""
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_soffice():
    if os.environ.get("SOFFICE"):
        return shlex.split(os.environ["SOFFICE"])
    for name in ("soffice", "libreoffice"):
        if shutil.which(name):
            return [shutil.which(name)]
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe", "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if Path(p).exists():
            return [p]
    sys.exit("LibreOffice not found. Install it, or set SOFFICE to the soffice program.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    dpi = int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 110
    deck = Path(args[0]).resolve()
    out = Path(args[1] if len(args) > 1 else deck.parent / "previews").resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:      # private profile: avoids clashes with an open LibreOffice
        cmd = find_soffice() + [f"-env:UserInstallation={Path(profile).as_uri()}", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(deck)]
        subprocess.run(cmd, check=True, timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = out / (deck.stem + ".pdf")
    if not pdf.exists():
        sys.exit("LibreOffice did not produce a PDF.")
    for old in out.glob("slide-*.jpg"):
        old.unlink()
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-jpeg", "-r", str(dpi), str(pdf), str(out / "slide")], check=True)
    else:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            print(f"PDF written to {pdf}. Install Poppler or PyMuPDF to get images.")
            return
        for i, page in enumerate(fitz.open(pdf), 1):
            page.get_pixmap(dpi=dpi).save(out / f"slide-{i:02d}.jpg")
    for f in sorted(out.glob("slide-*.jpg")):
        print(f)


if __name__ == "__main__":
    main()
