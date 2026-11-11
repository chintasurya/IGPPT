"""Check that a .pptx was built with IGPPT on the Insight Global template, and look for text that may not fit.

    python check_deck.py deck.pptx

Prints PASS or a list of problems. Exit code 1 means the deck must not be delivered:
rebuild it with build_deck.py instead of fixing it by hand.
"""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ig_kit import FONT, FONT_LIGHT, text_height  # noqa: E402

IG_LAYOUTS = {"Proposal Title Slide", "Dark Title Only", "Dark 1-Column_6", "Dark 1-Column_11", "Dark Title Only_Color", "Light Title Only", "Pink Divider_1",
              "Navy Statement Left", "Closer_1", "Closer_4", "Closer_5", "Closer_6"}
IG_FONTS = {FONT, FONT_LIGHT, None}


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    prs = Presentation(sys.argv[1])
    problems = []
    if not any(l.name == "Pink Divider_1" for l in prs.slide_layouts):
        problems.append("deck is not based on the IG template (IG layouts missing)")
    for i, slide in enumerate(prs.slides, 1):
        if slide.slide_layout.name not in IG_LAYOUTS:
            problems.append(f"slide {i}: layout '{slide.slide_layout.name}' is not an IGPPT layout")
        for shape in slide.shapes:
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            sizes, bold = [], False
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.name not in IG_FONTS:
                        problems.append(f"slide {i}: font '{r.font.name}' used instead of {FONT}")
                        break
                    if r.font.size:
                        sizes.append(r.font.size.pt)
                    bold = bold or bool(r.font.bold)
            if shape.is_placeholder and shape.placeholder_format.type is not None and "TITLE" in str(shape.placeholder_format.type) \
                    and sizes and slide.slide_layout.name in ("Dark Title Only", "Light Title Only", "Dark 1-Column_6", "Dark 1-Column_11", "Dark Title Only_Color"):
                if text_height(shape.text_frame.text, Emu(shape.width).inches * 0.87, max(sizes), line_spacing=1.1) > 0.7:
                    problems.append(f"slide {i}: title wraps onto two lines: '{shape.text_frame.text[:50]}'")
                continue
            if sizes and shape.width and shape.height and not shape.is_placeholder:
                w, h = Emu(shape.width).inches * (0.9 if bold else 1), Emu(shape.height).inches
                paras = [p.text for p in shape.text_frame.paragraphs if p.text.strip()]
                if w > 0.4 and text_height(paras, w, max(sizes)) > h * 1.35 + 0.15:
                    problems.append(f"slide {i}: text may overflow its box: '{shape.text_frame.text.strip()[:50]}'")
    problems = list(dict.fromkeys(problems))
    if problems:
        print("FAIL: this deck was not built correctly with IGPPT. Rebuild it with build_deck.py.")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print(f"PASS: {len(prs.slides)} slides on the IG template.")


if __name__ == "__main__":
    main()
