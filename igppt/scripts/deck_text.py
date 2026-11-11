"""Print the text of an existing deck, slide by slide, including tables and speaker notes.

    python deck_text.py deck.pptx

Use it at intake to read a client's or colleague's deck before changing or reusing it.
"""
import sys
from pptx import Presentation


def shape_text(shape, out):
    if shape.shape_type == 6:  # group
        for s in shape.shapes:
            shape_text(s, out)
    elif shape.has_text_frame and shape.text_frame.text.strip():
        out.append(shape.text_frame.text.strip())
    elif getattr(shape, "has_table", False) and shape.has_table:
        for row in shape.table.rows:
            out.append(" | ".join(c.text.strip() for c in row.cells))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    prs = Presentation(sys.argv[1])
    for i, slide in enumerate(prs.slides, 1):
        lines = []
        for shape in slide.shapes:
            shape_text(shape, lines)
        print(f"--- Slide {i} ({slide.slide_layout.name}) ---")
        print("\n".join(lines))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            print("[Notes] " + slide.notes_slide.notes_text_frame.text.strip())
        print()


if __name__ == "__main__":
    main()
