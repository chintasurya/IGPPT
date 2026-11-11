"""Text measurement for IGPPT: how wide a string is, where it wraps, and how tall a block of text is.

Used by ig_kit (to pick font sizes that fit) and validate.py (to prove nothing overflows or overlaps),
so the builder and the validator agree. Widths come from assets/font-metrics.json (per-character
advance widths in em; see tools/make_font_metrics.py). Units: inches and points.
"""
import json
import math
from pathlib import Path

_DATA = json.loads((Path(__file__).resolve().parent.parent / "assets" / "font-metrics.json").read_text(encoding="utf-8"))
LINE_HEIGHT = _DATA.get("line_height", 1.2)        # single line spacing, as a multiple of the font size
WIDTH_SLACK = 1.02                                  # measure 2% wide: the real font may differ a little
# Light text is measured with the regular widths: a little wider, so the check stays on the safe side.
_TABLES = {"regular": _DATA["regular"], "bold": _DATA["bold"], "light": _DATA["regular"]}
_FALLBACK = {w: sum(t.values()) / len(t) for w, t in _TABLES.items()}


def weight_of(font_name=None, bold=False):
    if bold or (font_name and "bold" in font_name.lower()):
        return "bold"
    if font_name and "light" in font_name.lower():
        return "light"
    return "regular"


def char_width(ch, size, weight="regular", spacing=0.0):
    """Advance width of one character in inches. spacing = extra letter spacing in points."""
    em = _TABLES[weight].get(ch)
    if em is None:
        em = 1.0 if ord(ch) > 0x2E80 else _FALLBACK[weight]     # CJK and emoji are about one em
    return (em * size * WIDTH_SLACK + spacing) / 72


def text_width(text, size, weight="regular", spacing=0.0):
    return sum(char_width(ch, size, weight, spacing) for ch in text)


def wrap_runs(runs, width):
    """Greedy word wrap like PowerPoint. runs = [(text, size, weight, spacing)].
    Returns (lines, split_words): lines = [(text, max_size, width_used)], split_words = words that had
    to be broken mid-word because they are wider than the box."""
    chars = [(ch, size, char_width(ch, size, weight, spacing)) for text, size, weight, spacing in runs for ch in text]
    lines, split, i, n = [], [], 0, len(chars)
    if n == 0:
        size = runs[0][1] if runs else 12
        return [("", size, 0.0)], split
    while i < n:
        while i < n and chars[i][0] == " " and lines:   # leading spaces after a wrap are dropped
            i += 1
        start, used, brk = i, 0.0, None
        while i < n:
            ch, _, cw = chars[i]
            if ch == "\n":
                break
            if used + cw > width + 1e-6 and ch != " ":
                break
            used += cw
            if ch in " -/–—":
                brk = i + 1
            i += 1
        if i < n and chars[i][0] == "\n":
            end, nxt = i, i + 1
        elif i >= n:
            end, nxt = n, n
        elif brk and brk > start:
            end, nxt = brk, brk
        else:                                            # one word wider than the line
            end = max(i, start + 1); nxt = end
            word_start = start
            while word_start > 0 and chars[word_start - 1][0] != " ":
                word_start -= 1
            word_end = end
            while word_end < n and chars[word_end][0] not in " \n":
                word_end += 1
            split.append("".join(c[0] for c in chars[word_start:word_end]))
        seg = chars[start:end]
        text = "".join(c[0] for c in seg).rstrip()
        w = sum(c[2] for c in seg[:len(text)]) if text else 0.0
        size = max((c[1] for c in seg), default=chars[min(start, n - 1)][1])
        lines.append((text, size, w))
        i = nxt
    return lines, list(dict.fromkeys(split))


def paragraph_height(lines, line_spacing=1.0, exact_pts=None):
    """Height in inches of wrapped lines. line_spacing is a multiple of single spacing; exact_pts overrides it."""
    if exact_pts:
        return len(lines) * exact_pts / 72
    return sum(size * LINE_HEIGHT * line_spacing for _, size, _ in lines) / 72


def measure(paragraphs, width):
    """paragraphs = [{"runs": [(text, size, weight, spacing)], "indent": inches, "line_spacing": 1.0,
    "exact_pts": None, "before": pt, "after": pt}]. Returns dict(height, width, lines, split_words)."""
    total, widest, n_lines, split = 0.0, 0.0, 0, []
    for k, p in enumerate(paragraphs):
        avail = max(0.05, width - p.get("indent", 0.0))
        lines, sp = wrap_runs(p["runs"], avail)
        split += sp
        if k:
            total += p.get("before", 0) / 72
        total += paragraph_height(lines, p.get("line_spacing", 1.0), p.get("exact_pts"))
        if k < len(paragraphs) - 1:
            total += p.get("after", 0) / 72
        widest = max([widest] + [w + p.get("indent", 0.0) for _, _, w in lines])
        n_lines += len(lines)
    return {"height": total, "width": widest, "lines": n_lines, "split_words": split}


def text_height(text, w, size, line_spacing=1.0, para_gap=0.35, weight="regular"):
    """Height (inches) of `text` (str or list of paragraph strings) at `size` pt in a box `w` inches wide.
    para_gap is the space between paragraphs as a multiple of the font size."""
    paras = [text] if isinstance(text, str) else list(text)
    ps = [{"runs": [(p, size, weight, 0.0)], "line_spacing": line_spacing, "after": size * para_gap} for p in paras]
    return measure(ps, w)["height"]


def fit_size(text, w, h, max_size=18, min_size=9, line_spacing=1.0, para_gap=0.35, weight="regular"):
    """Largest font size (pt, in 0.5 steps) at which `text` fits a w x h box without breaking a word."""
    paras = [text] if isinstance(text, str) else list(text)
    size = max_size
    while size > min_size:
        ps = [{"runs": [(p, size, weight, 0.0)], "line_spacing": line_spacing, "after": size * para_gap} for p in paras]
        m = measure(ps, w)
        if m["height"] <= h and not m["split_words"]:
            return size
        size -= 0.5
    return min_size


def lines_needed(text, w, size, weight="regular"):
    return len(wrap_runs([(text, size, weight, 0.0)], w)[0])


def ceil_to(x, step=0.5):
    return math.ceil(x / step) * step
