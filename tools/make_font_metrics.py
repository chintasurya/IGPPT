"""Regenerate igppt/assets/font-metrics.json: per-character advance widths (in em) used to measure text.

    python tools/make_font_metrics.py [regular.otf bold.otf light.otf]

The Trenda IG Text font files are not bundled (they are licensed to Insight Global), so by default the
widths come from Inter (SIL Open Font License), a sans serif of similar proportions that LibreOffice also
substitutes for Trenda when Trenda is not installed. Pass the three Trenda files to measure with the real font.
"""
import json
import sys
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "igppt" / "assets" / "font-metrics.json"
DEFAULT = ["/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
           "/usr/share/fonts/opentype/inter/Inter-Light.otf"]
CHARS = [chr(c) for c in range(32, 127)] + list(" ’‘“”–—•…€£¥×÷±✓✔→←↑↓·°§©®™½¼¾éèêëáàâäíìîïóòôöúùûüñçÉÁÓÚÑ")
SIZE = 1000


def widths(path):
    f = ImageFont.truetype(path, SIZE)
    return {ch: round(f.getlength(ch) / SIZE, 4) for ch in CHARS}


def main():
    paths = sys.argv[1:4] if len(sys.argv) >= 4 else DEFAULT
    data = {"source": " / ".join(Path(p).name for p in paths), "line_height": 1.2,
            "regular": widths(paths[0]), "bold": widths(paths[1]), "light": widths(paths[2])}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) from {data['source']}")


if __name__ == "__main__":
    main()
