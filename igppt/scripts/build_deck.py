"""Build an Insight Global deck from a JSON spec.

    python build_deck.py spec.json out.pptx [--theme dark|light]

The spec format is documented in references/spec-format.md. Minimal example:

    {"theme": "dark",
     "slides": [
       {"type": "title", "title": "Q3 Delivery Update", "subtitle": "Platform team", "date": "Oct 2026"},
       {"type": "bullets", "title": "Where We Are", "bullets": ["On track for the March release", "Two risks need decisions"]},
       {"type": "closing"}]}

Every slide type lays itself out, picks font sizes to fit, and uses the IG template's layouts,
fonts, colours, footer and page numbers. Warnings are printed for text that is likely too long.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ig_kit import (ACCENTS, BOTTOM, DARK, LEFT, NAVY, RIGHT, WIDTH,  # noqa: E402
                    Deck, columns, fit_size, icon_names, text_height)

WARNINGS = []


def warn(i, msg):
    WARNINGS.append(f"slide {i}: {msg}")


def color_of(item, k):
    c = item.get("color")
    named = {"cyan": "00D6F1", "yellow": "FFD700", "magenta": "FF0069", "pink": "FF0069", "green": "55E03A", "orange": "F98B34"}
    return named.get(str(c).lower(), c) if c else ACCENTS[k % len(ACCENTS)]


def note_band(c, text, y=None):
    """Full-width band for a source, assumption or key message at the bottom of a slide."""
    y = y if y is not None else BOTTOM - 0.62
    c.card(LEFT, y, WIDTH, 0.62, fill=NAVY if c.t is DARK else c.t.card, border=NAVY if c.t is DARK else c.t.line)
    c.text(LEFT + 0.25, y, WIDTH - 0.5, 0.62, text, size=fit_size(text, WIDTH - 0.5, 0.5, 13, 10),
           color="FFFFFF" if c.t is DARK else c.t.ink, valign="middle")
    return y - 0.2


# ---------------------------------------------------------------- slide types
def s_title(deck, s, i):
    deck.title(s.get("title", ""), s.get("subtitle", ""), s.get("date", ""), notes=s.get("notes", ""))


def s_agenda(deck, s, i):
    items = s.get("items", [])
    if len(items) > 7:
        warn(i, "agenda shows at most 7 items; the rest were dropped")
    deck.agenda(items, title=s.get("title", "Agenda"), notes=s.get("notes", ""))


def s_section(deck, s, i):
    deck.section(s.get("title", ""), notes=s.get("notes", ""))


def s_statement(deck, s, i):
    deck.statement(s.get("text", ""), eyebrow=s.get("eyebrow", ""), attribution=s.get("attribution", ""), notes=s.get("notes", ""))


def s_closing(deck, s, i):
    deck.closing(s.get("style", "thank-you"), notes=s.get("notes", ""))


def content(deck, s, i):
    title = s.get("title", "")
    if len(title) > 55:
        warn(i, f"title is {len(title)} characters; aim for 45 or fewer")
    return deck.slide(title, eyebrow=s.get("eyebrow", ""), subtitle=s.get("subtitle", ""), notes=s.get("notes", ""),
                      theme=s.get("theme"), background=s.get("background"))


def s_bullets(deck, s, i):
    c = content(deck, s, i)
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    items = s.get("bullets", [])
    if len(items) > 7:
        warn(i, f"{len(items)} bullets; consider splitting the slide")
    co = s.get("callout")
    if co:
        c.bullets(LEFT, c.top + 0.1, 7.9, bottom - c.top - 0.1, items)
        col = color_of(co, 0)
        x, w, h = 8.85, RIGHT - 8.85, min(bottom - c.top, 3.4)
        c.card(x, c.top, w, h, border=col)
        c.text(x + 0.3, c.top + 0.25, w - 0.6, 1.1, co.get("value", ""), size=fit_size(co.get("value", ""), w - 0.6, 1.0, 60, 28),
               color=c.t.accent(col), light=True)
        c.text(x + 0.3, c.top + 1.4, w - 0.6, 0.5, co.get("label", ""), size=15, bold=True)
        if co.get("text"):
            c.text(x + 0.3, c.top + 1.95, w - 0.6, h - 2.1, co["text"], fit=(13, 10), color=c.t.muted)
    else:
        c.bullets(LEFT, c.top + 0.1, min(WIDTH, 11.2), bottom - c.top - 0.1, items, fit=(20, 11))


def s_cards(deck, s, i):
    c = content(deck, s, i)
    cards = s.get("cards", [])
    if not 2 <= len(cards) <= 6:
        warn(i, "cards works best with 2 to 6 cards")
        cards = cards[:6]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    avail = bottom - c.top
    rows = 2 if len(cards) == 6 or (len(cards) == 4 and s.get("grid")) else 1
    per_row = math.ceil(len(cards) / rows)
    w, xs = columns(per_row)
    if rows == 2:
        h = (avail - 0.2) / 2
    else:  # size the row to its content: header + body text + padding
        need = 0
        for card in cards:
            body = card.get("bullets") or card.get("text", "")
            bsize = fit_size(body, w - 0.5, avail - 1.8, 16, 10) if body else 0
            need = max(need, 1.55 + (text_height(body, w - 0.5, bsize) if body else 0) + 0.35)
        h = min(avail, max(2.4, need))
    compact = h < 2.6
    for k, card in enumerate(cards):
        x, y = xs[k % per_row], c.top + (k // per_row) * (h + 0.2)
        col = color_of(card, k)
        c.card(x, y, w, h, border=col if card.get("highlight") else None)
        if card.get("tag"):
            c.chip(x + w - 1.45, y + 0.22, 1.25, card["tag"], col)
        icon = card.get("icon")
        if icon and icon not in icon_names():
            warn(i, f"unknown icon '{icon}', used a number instead"); icon = None
        if card.get("value"):
            c.text(x + 0.25, y + 0.15, w - 0.5, 0.75, card["value"], size=fit_size(card["value"], w - 0.5, 0.7, 40, 22),
                   color=c.t.accent(col), light=True)
        elif icon:
            c.icon_circle(x + 0.22, y + 0.22, 0.5, col, icon)
        else:
            c.oval(x + 0.22, y + 0.22, 0.5, fill=col, text=str(k + 1), text_size=16)
        title = card.get("title", "")
        if compact and not card.get("value"):
            c.text(x + 0.9, y + 0.22, w - (2.4 if card.get("tag") else 1.1), 0.5, title,
                   size=fit_size(title, w - 1.1, 0.5, 15, 11), bold=True, valign="middle")
            ty = y + 0.9
        else:
            ty0 = y + (0.95 if card.get("value") else 0.92)
            c.text(x + 0.25, ty0, w - 0.5, 0.42, title, size=fit_size(title, w - 0.5, 0.42, 16, 11), bold=True)
            ty = ty0 + 0.5
        body = card.get("text", "")
        pts = card.get("bullets")
        if pts:
            c.bullets(x + 0.25, ty, w - 0.5, y + h - ty - 0.2, pts, color=c.t.muted, fit=(16, 10), gap=4)
        elif body:
            c.text(x + 0.25, ty, w - 0.5, y + h - ty - 0.2, body, fit=(16, 10), color=c.t.muted)


def s_stats(deck, s, i):
    c = content(deck, s, i)
    stats = s.get("stats", [])[:4]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    w, xs = columns(len(stats))
    h = min(bottom - c.top, 3.2)
    y = c.top + max(0, (bottom - c.top - h) / 2 - 0.2)
    for k, (x, st) in enumerate(zip(xs, stats)):
        col = color_of(st, k)
        c.card(x, y, w, h, border=col if st.get("highlight") else None)
        v = str(st.get("value", ""))
        c.text(x + 0.3, y + 0.25, w - 0.6, 1.15, v, size=fit_size(v, w - 0.6, 1.05, 64, 28), color=c.t.accent(col), light=True)
        c.text(x + 0.3, y + 1.45, w - 0.6, 0.5, st.get("label", ""), size=fit_size(st.get("label", ""), w - 0.6, 0.5, 16, 11), bold=True)
        if st.get("text"):
            c.text(x + 0.3, y + 2.0, w - 0.6, h - 2.15, st["text"], fit=(15, 10), color=c.t.muted)


def s_process(deck, s, i):
    c = content(deck, s, i)
    steps = s.get("steps", [])
    if not 2 <= len(steps) <= 6:
        warn(i, "process works best with 2 to 6 steps"); steps = steps[:6]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    rows = []
    for k, st in enumerate(steps):
        icon = st.get("icon") if st.get("icon") in icon_names() else None
        if st.get("icon") and not icon:
            warn(i, f"unknown icon '{st['icon']}'")
        rows.append((icon, st.get("owner", ""), color_of(st, k), st.get("title", ""), st.get("text", "")))
    h = min(2.7 if s.get("bullets") else 3.2, bottom - c.top - 0.2)
    y0 = c.top + 0.15 if s.get("bullets") else c.top + max(0.15, (bottom - c.top - h) / 2 - 0.25)
    c.steps_flow(y0, rows, h=h, highlight=s.get("highlight"))
    if s.get("bullets") and bottom - (y0 + h + 0.45) > 0.8:
        y = y0 + h + 0.45
        c.bullets(LEFT, y, WIDTH, bottom - y, s["bullets"], fit=(18, 11))


def s_timeline(deck, s, i):
    c = content(deck, s, i)
    ms = s.get("milestones", [])
    if not 2 <= len(ms) <= 7:
        warn(i, "timeline works best with 2 to 7 milestones"); ms = ms[:7]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    c.milestones(c.top + max(0.3, (bottom - c.top - 3.2) / 2), [(m.get("date", ""), m.get("title", ""), m.get("text", "")) for m in ms],
                 colors=[color_of(m, k) for k, m in enumerate(ms)])


def s_table(deck, s, i):
    c = content(deck, s, i)
    head, rows = s.get("columns", []), s.get("rows", [])
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    n = len(head) or (len(rows[0]) if rows else 1)
    if s.get("widths"):
        tot = float(sum(s["widths"])); widths = [WIDTH * v / tot for v in s["widths"]]
    else:
        lens = [max([len(str(head[j])) if head else 0] + [len(str(r[j])) if j < len(r) else 0 for r in rows]) for j in range(n)]
        lens = [min(max(L, 6), 60) for L in lens]
        widths = [WIDTH * L / sum(lens) for L in lens]
    all_rows = ([head] if head else []) + rows
    size, row_h = (15, 0.55) if len(all_rows) <= 6 else (13, 0.44) if len(all_rows) <= 9 else (11, 0.36) if len(all_rows) <= 12 else (10, 0.3)
    if (len(all_rows)) * row_h > bottom - c.top:
        warn(i, f"{len(rows)} rows may not fit; split the table")
    c.table(LEFT, c.top + 0.05, widths, all_rows, header=bool(head), row_h=row_h, size=size, bold_last=s.get("bold_last", False))


def s_chart(deck, s, i):
    c = content(deck, s, i)
    ch = s.get("chart", {})
    series = ch.get("series") or [{"name": ch.get("name", "Value"), "values": ch.get("values", [])}]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    tk = s.get("takeaways")
    w = 7.9 if tk else WIDTH
    c.chart(LEFT, c.top + 0.05, w, bottom - c.top - 0.05, ch.get("type", "column"), ch.get("categories", []), series,
            number_format=ch.get("number_format"), max_value=ch.get("max"))
    if tk:
        x, cw = 8.85, RIGHT - 8.85
        c.card(x, c.top, cw, bottom - c.top)
        c.label(x + 0.25, c.top + 0.22, cw - 0.5, s.get("takeaways_label", "Key takeaways"))
        c.bullets(x + 0.25, c.top + 0.6, cw - 0.5, bottom - c.top - 0.8, tk, fit=(17, 10), gap=10)


def s_comparison(deck, s, i):
    c = content(deck, s, i)
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    sides = [s.get("left", {}), s.get("right", {})]
    w, xs = columns(2, gap=0.3)
    need = 0
    for sd in sides:  # size both cards to the longer side
        pts = [p if isinstance(p, str) else p.get("text", "") for p in sd.get("points", [])]
        need = max(need, (1.3 if sd.get("tag") else 0.95) + text_height(pts, w - 0.9, fit_size(pts, w - 0.9, bottom - c.top - 1.5, 20, 11), para_gap=0.6) + 0.5)
    for k, (x, sd) in enumerate(zip(xs, sides)):
        col = color_of(sd, k if k == 0 else 2)
        h = min(bottom - c.top, max(2.8, need))
        c.card(x, c.top, w, h, border=col if sd.get("highlight") else None)
        y = c.top + 0.25
        if sd.get("tag"):
            c.label(x + 0.3, y, w - 0.6, sd["tag"], color=col); y += 0.35
        c.text(x + 0.3, y, w - 0.6, 0.5, sd.get("heading", ""), size=fit_size(sd.get("heading", ""), w - 0.6, 0.5, 20, 13), bold=True,
               color=c.t.accent(col))
        y += 0.65
        c.bullets(x + 0.3, y, w - 0.6, c.top + h - y - 0.2, sd.get("points", []), fit=(20, 11), gap=10)


def s_image(deck, s, i, base):
    c = content(deck, s, i)
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    path = (base / s["image"]) if s.get("image") else None
    if not path or not path.exists():
        warn(i, f"image not found: {s.get('image')}"); return
    pts = s.get("bullets")
    cap_h = 0.4 if s.get("caption") else 0
    iw = 7.4 if pts else WIDTH
    c.image_fit(path, LEFT, c.top, iw, bottom - c.top - cap_h)
    if s.get("caption"):
        c.text(LEFT, bottom - 0.32, iw, 0.3, s["caption"], size=10.5, color=c.t.muted, italic=True)
    if pts:
        x = LEFT + iw + 0.4
        c.bullets(x, c.top + 0.1, RIGHT - x, bottom - c.top - 0.1, pts, fit=(17, 10))


def s_team(deck, s, i):
    c = content(deck, s, i)
    people = s.get("members", [])[:8]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    per_row = min(4, len(people)) or 1
    rows = math.ceil(len(people) / per_row)
    w, xs = columns(per_row)
    h = min(2.2, (bottom - c.top - 0.2 * (rows - 1)) / rows)
    for k, p in enumerate(people):
        x, y = xs[k % per_row], c.top + (k // per_row) * (h + 0.2)
        col = color_of(p, k)
        c.card(x, y, w, h)
        initials = "".join(part[0] for part in p.get("name", "?").split()[:2]).upper()
        c.oval(x + 0.25, y + 0.25, 0.7, fill=col, text=initials, text_size=16)
        c.text(x + 1.1, y + 0.25, w - 1.3, 0.35, p.get("name", ""), size=fit_size(p.get("name", ""), w - 1.3, 0.35, 15, 11), bold=True)
        c.text(x + 1.1, y + 0.62, w - 1.3, 0.35, p.get("role", ""), size=11, color=c.t.accent(col))
        if p.get("text"):
            c.text(x + 0.25, y + 1.12, w - 0.5, h - 1.25, p["text"], fit=(14, 9), color=c.t.muted)


TYPES = {"title": s_title, "agenda": s_agenda, "section": s_section, "statement": s_statement, "quote": s_statement,
         "closing": s_closing, "bullets": s_bullets, "cards": s_cards, "stats": s_stats, "process": s_process,
         "timeline": s_timeline, "table": s_table, "chart": s_chart, "comparison": s_comparison, "image": s_image,
         "team": s_team}


def build(spec, out, base=Path("."), theme=None):
    deck = Deck(theme=theme or spec.get("theme", "dark"), background=spec.get("background", "gradient"))
    for i, s in enumerate(spec.get("slides", []), 1):
        kind = s.get("type")
        if kind not in TYPES:
            raise SystemExit(f"slide {i}: unknown type '{kind}'. Types: {', '.join(TYPES)}")
        if kind == "image":
            s_image(deck, s, i, base)
        else:
            TYPES[kind](deck, s, i)
    deck.save(out)
    return out


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__); return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__)
    theme = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else None
    spec_path = Path(args[0])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    build(spec, args[1], base=spec_path.resolve().parent, theme=theme)
    print(f"saved {args[1]} ({len(spec.get('slides', []))} slides)")
    for w in WARNINGS:
        print("WARNING", w)


if __name__ == "__main__":
    main()
