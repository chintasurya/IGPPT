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
                    Deck, bullets_fit, columns, fit_size, icon_names, one_line_size, text_height)

WARNINGS = []      # (slide, message, fatal): fatal means content was lost, so the deck must not be delivered


def warn(i, msg, fatal=False):
    WARNINGS.append((i, msg, fatal))


def on_theme(c, colr):
    """White marks the neutral column or role on dark slides; on light slides it becomes the theme ink."""
    return c.t.ink if colr.upper() == "FFFFFF" and c.t is not DARK else colr


def color_of(item, k):
    c = item.get("color")
    named = {"cyan": "00D6F1", "yellow": "FFD700", "magenta": "FF0069", "pink": "FF0069", "green": "55E03A", "orange": "F98B34",
             "white": "FFFFFF", "navy": "00273B"}
    return named.get(str(c).lower(), c) if c else ACCENTS[k % len(ACCENTS)]


# Common names assistants use for icons, mapped to the bundled icon set (assets/icons).
ICON_ALIASES = {
    "people": "users", "team": "users", "teams": "users", "group": "users", "staff": "users", "person": "user-check",
    "user": "user-check", "employee": "user-check", "analyst": "user-check", "talent": "user-plus", "hire": "user-plus",
    "hiring": "user-plus", "recruit": "user-plus", "recruiting": "user-plus", "onboarding": "user-plus",
    "admin": "users-cog", "management": "users-cog", "manager": "users-cog", "governance": "users-cog",
    "gear": "cogs", "gears": "cogs", "cog": "cogs", "settings": "cogs", "automation": "cogs", "automate": "cogs",
    "process": "workflow", "flow": "workflow", "pipeline": "workflow", "integration": "workflow",
    "money": "dollar", "cost": "dollar", "costs": "dollar", "price": "dollar", "pricing": "dollar", "budget": "dollar",
    "savings": "dollar", "revenue": "dollar", "finance": "dollar",
    "time": "clock", "speed": "clock", "fast": "clock", "sla": "clock", "response": "clock",
    "date": "calendar", "schedule": "calendar", "timeline": "calendar", "plan": "calendar", "roadmap": "route",
    "journey": "route", "path": "route",
    "security": "shield", "secure": "shield", "protection": "shield", "cyber": "shield", "cybersecurity": "shield",
    "soc": "user-shield", "privacy": "lock", "access": "lock",
    "idea": "lightbulb", "innovation": "lightbulb", "insight": "lightbulb", "strategy": "lightbulb",
    "growth": "chart", "analytics": "chart", "metrics": "chart", "kpi": "chart", "trend": "chart", "results": "chart",
    "report": "chart", "reporting": "chart", "dashboard": "chart",
    "goal": "flag", "goals": "flag", "target": "flag", "milestone": "flag", "objective": "flag",
    "launch": "rocket", "start": "rocket", "deploy": "rocket", "deployment": "rocket", "go-live": "rocket",
    "data": "database", "storage": "database", "partner": "handshake", "partnership": "handshake",
    "agreement": "handshake", "handover": "handshake", "transition": "handshake", "support": "headset",
    "help": "headset", "service": "headset", "helpdesk": "headset", "done": "check-circle", "complete": "check-circle",
    "success": "check-circle", "quality": "check-circle", "risk": "warning", "alert": "warning", "issue": "warning",
    "research": "search", "discovery": "search", "find": "search", "analysis": "microscope", "assess": "microscope",
    "assessment": "microscope", "document": "file", "doc": "file", "documents": "file", "contract": "file",
    "tool": "tools", "build": "tools", "engineering": "tools", "view": "eye", "visibility": "eye", "monitor": "eye",
    "monitoring": "eye", "compliance": "clipboard-check", "audit": "clipboard-check", "checklist": "clipboard-check",
    "dev": "code", "development": "code", "software": "code", "compare": "balance", "fair": "balance",
    "tune": "sliders", "options": "sliders", "night": "moon", "24x7": "moon", "click": "pointer", "import": "file-import",
    "migration": "file-import", "tickets": "ticket", "incident": "ticket",
}


def resolve_icon(i, name):
    """Bundled icon for `name` (exact, alias or plural), or None with a warning."""
    if not name:
        return None
    key = str(name).strip().lower()
    names = icon_names()
    for k in (key, ICON_ALIASES.get(key), key.rstrip("s"), ICON_ALIASES.get(key.rstrip("s"))):
        if k and k in names:
            return k
    warn(i, f"unknown icon '{name}', used a number instead (icons: {', '.join(names)})")
    return None


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
        warn(i, f"agenda shows at most 7 items; {len(items) - 7} were dropped: merge or remove items", fatal=True)
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
        if len(cards) > 6:
            warn(i, f"cards shows at most 6 cards; {len(cards) - 6} were dropped: split the slide", fatal=True)
        else:
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
        icon = resolve_icon(i, card.get("icon"))
        bar = False
        if card.get("value"):
            c.text(x + 0.25, y + 0.15, w - 0.5, 0.75, card["value"], size=fit_size(card["value"], w - 0.5, 0.7, 40, 22),
                   color=c.t.accent(col), light=True)
        elif icon:
            c.icon_circle(x + 0.22, y + 0.22, 0.5, col, icon)
        elif s.get("numbered"):
            c.oval(x + 0.22, y + 0.22, 0.5, fill=col, text=str(k + 1), text_size=16)
        else:   # executive default: a short accent bar, no icon or number
            bar = True
            c.rect(x + 0.25, y + 0.26, 0.34, 0.05, col)
        title = card.get("title", "")
        if bar:
            tw = w - (1.95 if card.get("tag") else 0.5)
            c.text(x + 0.25, y + 0.44, tw, 0.42, title, size=fit_size(title, tw, 0.42, 16, 11, bold=True), bold=True)
            ty = y + 0.94
        elif compact and not card.get("value"):
            c.text(x + 0.9, y + 0.22, w - (2.4 if card.get("tag") else 1.1), 0.5, title,
                   size=fit_size(title, w - (2.4 if card.get("tag") else 1.1), 0.5, 15, 11, bold=True), bold=True, valign="middle")
            ty = y + 0.9
        else:
            ty0 = y + (0.95 if card.get("value") else 0.92)
            c.text(x + 0.25, ty0, w - 0.5, 0.42, title, size=fit_size(title, w - 0.5, 0.42, 16, 11, bold=True), bold=True)
            ty = ty0 + 0.5
        body = card.get("text", "")
        pts = card.get("bullets")
        if pts:
            c.bullets(x + 0.25, ty, w - 0.5, y + h - ty - 0.2, pts, color=c.t.muted, fit=(16, 10), gap=4)
        elif body:
            c.text(x + 0.25, ty, w - 0.5, y + h - ty - 0.2, body, fit=(16, 10), color=c.t.muted)


def s_stats(deck, s, i):
    c = content(deck, s, i)
    if len(s.get("stats", [])) > 4:
        warn(i, f"stats shows at most 4 tiles; {len(s['stats']) - 4} were dropped: split the slide", fatal=True)
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
        c.text(x + 0.3, y + 1.45, w - 0.6, 0.5, st.get("label", ""), size=fit_size(st.get("label", ""), w - 0.6, 0.5, 16, 11, bold=True), bold=True)
        if st.get("text"):
            c.text(x + 0.3, y + 2.0, w - 0.6, h - 2.15, st["text"], fit=(15, 10), color=c.t.muted)


def s_process(deck, s, i):
    c = content(deck, s, i)
    steps = s.get("steps", [])
    if not 2 <= len(steps) <= 6:
        warn(i, "process works best with 2 to 6 steps" + ("; extra steps were dropped" if len(steps) > 6 else ""), fatal=len(steps) > 6)
        steps = steps[:6]
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    rows = []
    for k, st in enumerate(steps):
        icon = resolve_icon(i, st.get("icon"))
        rows.append((icon, st.get("owner", ""), color_of(st, k), st.get("title", ""), st.get("text", "")))
    h = min(2.7 if s.get("bullets") else 3.2, bottom - c.top - 0.2)
    y0 = c.top + 0.15 if s.get("bullets") else c.top + max(0.15, (bottom - c.top - h) / 2 - 0.25)
    c.steps_flow(y0, rows, h=h, highlight=s.get("highlight"))
    if s.get("bullets") and bottom - (y0 + h + 0.45) > 0.8:
        y = y0 + h + 0.45
        c.bullets(LEFT, y, WIDTH, bottom - y, s["bullets"], fit=(18, 11))
    elif s.get("bullets"):
        warn(i, "no room for the bullets under the steps (they were dropped): remove the note or the bullets", fatal=True)


def s_timeline(deck, s, i):
    c = content(deck, s, i)
    ms = s.get("milestones", [])
    if not 2 <= len(ms) <= 7:
        warn(i, "timeline works best with 2 to 7 milestones" + ("; extra milestones were dropped" if len(ms) > 7 else ""), fatal=len(ms) > 7)
        ms = ms[:7]
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
        c.text(x + 0.3, y, w - 0.6, 0.5, sd.get("heading", ""), size=fit_size(sd.get("heading", ""), w - 0.6, 0.5, 20, 13, bold=True), bold=True,
               color=c.t.accent(col))
        y += 0.65
        c.bullets(x + 0.3, y, w - 0.6, c.top + h - y - 0.2, sd.get("points", []), fit=(20, 11), gap=10)


def s_image(deck, s, i, base):
    c = content(deck, s, i)
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    path = (base / s["image"]) if s.get("image") else None
    if not path or not path.exists():
        warn(i, f"image not found: {s.get('image')}", fatal=True); return
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
    if len(s.get("members", [])) > 8:
        warn(i, f"team shows at most 8 people; {len(s['members']) - 8} were dropped: split the slide", fatal=True)
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
        c.text(x + 1.1, y + 0.25, w - 1.3, 0.35, p.get("name", ""), size=fit_size(p.get("name", ""), w - 1.3, 0.35, 15, 11, bold=True), bold=True)
        c.text(x + 1.1, y + 0.62, w - 1.3, 0.35, p.get("role", ""), size=11, color=c.t.accent(col))
        if p.get("text"):
            c.text(x + 0.25, y + 1.12, w - 0.5, h - 1.25, p["text"], fit=(14, 9), color=c.t.muted)


# ---------------------------------------------------------------- executive solution slides
def _runs_line(label, title, color, size, label_size=8):
    """Runs for '<LABEL>  title' on one line: a spaced accent label followed by regular text."""
    out = []
    if label:
        out.append({"text": label.upper() + " ", "size": label_size, "bold": True, "spacing": 1.5, "color": color})
    out.append({"text": title, "size": size})
    return out


def bands(c, items, y, h=0.62, x0=LEFT, total=WIDTH, i=0):
    """Full-width foundation bands under a diagram: [{"label", "title", "text", "color", "dashed"}]."""
    if not items:
        return
    weights = [float(b.get("width", 1)) for b in items]
    gap = 0.18
    avail = total - gap * (len(items) - 1)
    x = x0
    for k, b in enumerate(items):
        w = avail * weights[k] / sum(weights)
        col = color_of(b, k)
        if b.get("dashed"):
            c.outline(x, y, w, h, col, radius=0.12)
        else:
            c.card(x, y, w, h, fill=NAVY if k == 0 and c.t is DARK and not b.get("plain") else c.t.card_alt,
                   border=NAVY if k == 0 and c.t is DARK and not b.get("plain") else c.t.line)
        tw = w - 0.4
        label, title, text = b.get("label", ""), b.get("title", ""), b.get("text", "")
        first = (label.upper() + " " if label else "") + title
        size = one_line_size(first, tw, 11, 8.5)
        if size <= 8.5 and title:
            warn(i, f"band '{label}' text is too long for one line; shorten it", fatal=False)
        runs = _runs_line(label, title, c.t.accent(col), size)
        if text:
            runs[-1]["br"] = True
            runs.append({"text": text, "size": max(8.0, min(9.5, one_line_size(text, tw, 9.5, 8))), "color": c.t.muted})
        c.text(x + 0.2, y + 0.06, tw, h - 0.12, runs, valign="middle")
        x += w + gap


PADY, TGAP, IGAP = 0.08, 0.04, 0.05      # architecture item padding, title-to-text gap, gap between nested items


def _item_height(it, w, ts, xs):
    """Height of one architecture item (pill, or a group with nested items) at title size ts and text size xs."""
    tw = w - (0.42 if it.get("accent") is not False and not it.get("items") else 0.26)
    h = 2 * PADY + text_height(it.get("title", ""), tw, ts, bold=True)
    if it.get("text"):
        h += TGAP + text_height(it["text"], tw, xs)
    subs = it.get("items") or []
    if subs:
        h += 0.06 + sum(_item_height(sub, w - 0.2, max(8.0, ts - 0.5), max(8.0, xs - 0.5)) for sub in subs) + IGAP * (len(subs) - 1)
    return max(0.34, h)


def _draw_item(c, it, x, y, w, h, ts, xs, col, fill):
    if it.get("dashed"):
        c.card(x, y, w, h, fill=NAVY if c.t is DARK else c.t.card, border=c.t.muted, dash=True, radius=0.1)
    else:
        c.card(x, y, w, h, fill=fill, border=fill, radius=0.1)
    subs = it.get("items") or []
    dot = it.get("accent") is not False and not subs
    tx = x + (0.3 if dot else 0.14)
    tw = w - (tx - x) - 0.12
    th = text_height(it.get("title", ""), tw, ts, bold=True)
    bh = text_height(it["text"], tw, xs) if it.get("text") else 0
    content_h = th + (TGAP + bh if bh else 0)
    ty = y + PADY if subs else y + (h - content_h) / 2
    if dot:
        c.oval(x + 0.12, ty + th / 2 - 0.045, 0.09, fill=color_of(it, 0) if it.get("color") else col)
    c.text(tx, ty, tw, th + 0.01, it.get("title", ""), size=ts, bold=True)
    yy = ty + th
    if bh:
        c.text(tx, yy + TGAP, tw, bh + 0.01, it["text"], size=xs, color=c.t.muted)
        yy += TGAP + bh
    if subs:
        yy += 0.06
        fill_inner = c.t.card if fill != c.t.card else c.t.card_alt
        for sub in subs:
            sts, sxs = max(8.0, ts - 0.5), max(8.0, xs - 0.5)
            sh = _item_height(sub, w - 0.2, sts, sxs)
            _draw_item(c, sub, x + 0.1, yy, w - 0.2, sh, sts, sxs, col, fill_inner)
            yy += sh + IGAP


def s_architecture(deck, s, i):
    """Layered solution view: columns left to right joined by arrows, an optional revision loop and
    foundation bands. Use it once per deck for the solution or architecture view."""
    c = content(deck, s, i)
    cols = s.get("columns", [])
    if not 2 <= len(cols) <= 5:
        warn(i, "architecture needs 2 to 5 columns" + ("; extra columns were dropped" if len(cols) > 5 else ""),
             fatal=len(cols) > 5 or len(cols) < 2)
        cols = cols[:5]
        if len(cols) < 2:
            return
    band_items = s.get("bands", [])[:3]
    bottom = BOTTOM
    if band_items:
        bands(c, band_items, bottom - 0.56, h=0.56, i=i)
        bottom -= 0.56 + 0.14
    loop = s.get("loop")
    if loop:
        bottom -= 0.38
    gap = 0.36
    weights = [float(col.get("width", 1)) for col in cols]
    avail = WIDTH - gap * (len(cols) - 1)
    widths = [avail * wt / sum(weights) for wt in weights]
    xs, x = [], LEFT
    for w in widths:
        xs.append(x); x += w + gap
    has_sub = any(col.get("sub") for col in cols)
    box_top = c.top + (0.54 if has_sub else 0.3)
    box_h = bottom - box_top
    pad = 0.12
    # pick the largest text that fits every column
    ts = 10.5
    while True:
        xs_ = max(8.0, ts - 2)
        need = []
        for col, w in zip(cols, widths):
            items = col.get("items", [])
            need.append(sum(_item_height(it, w - 2 * pad, ts, xs_) for it in items) + 0.06 * max(0, len(items) - 1))
        if max(need or [0]) <= box_h - 2 * pad or ts <= 8:
            break
        ts -= 0.5
    if max(need or [0]) > box_h - 2 * pad:
        warn(i, "an architecture column has too many items or too much text to fit: shorten item text or move items", fatal=True)
    for k, (col, x, w) in enumerate(zip(cols, xs, widths)):
        colr = on_theme(c, color_of(col, k))
        lw = w + (gap - 0.1 if k < len(cols) - 1 else 0)
        c.text(x, c.top - 0.04, lw, 0.22, [{"text": f"{k + 1:02d} " + col.get("label", "").upper(), "spacing": 2}],
               size=one_line_size(f"{k + 1:02d} " + col.get("label", "").upper(), lw - 0.3, 9, 8, bold=True), bold=True,
               color=c.t.accent(colr))
        if col.get("sub"):
            c.text(x, c.top + 0.22, lw, 0.26, col["sub"], size=one_line_size(col["sub"], lw, 11, 8.5), color=c.t.muted)
        c.card(x, box_top, w, box_h, border=colr, radius=0.08)
        items = col.get("items", [])
        heights = [_item_height(it, w - 2 * pad, ts, xs_) for it in items]
        spare = box_h - 2 * pad - sum(heights)
        g = min(0.16, max(0.06, spare / max(1, len(items) - 1))) if len(items) > 1 else 0
        yy = box_top + pad
        for it, h in zip(items, heights):
            _draw_item(c, it, x + pad, yy, w - 2 * pad, h, ts, xs_, colr, c.t.card_alt)
            yy += h + g
        if k < len(cols) - 1:
            my = box_top + box_h / 2
            c.arrow(x + w + 0.05, my, x + w + gap - 0.05, my, color=c.t.ink)
    if loop:
        frm = loop.get("from", len(cols)) - 1 if isinstance(loop, dict) else len(cols) - 1
        to = loop.get("to", 2) - 1 if isinstance(loop, dict) else 1
        text = loop.get("text", "") if isinstance(loop, dict) else str(loop)
        lc = color_of(loop, 2) if isinstance(loop, dict) else color_of({}, 2)
        fx, tx_ = xs[frm] + widths[frm] / 2, xs[to] + widths[to] / 2
        ly = bottom + 0.12
        c.line(fx, bottom, fx, ly, color=lc, width=1)
        c.line(fx, ly, tx_, ly, color=lc, width=1)
        c.arrow(tx_, ly, tx_, bottom + 0.02, color=lc, width=1)
        lw = abs(fx - tx_) - 0.3
        c.text(min(fx, tx_) + 0.15, ly + 0.05, lw, 0.2, text, size=max(8.0, one_line_size(text, lw, 9, 8)),
               color=c.t.accent(lc), align="center")


def s_flow(deck, s, i):
    """End-to-end process as numbered step cards (2 to 10, two rows when more than 5), owner colours,
    an optional 'accountable from here' marker and bands for parallel tracks or ways of working."""
    c = content(deck, s, i)
    steps = s.get("steps", [])
    if not 2 <= len(steps) <= 10:
        warn(i, "flow needs 2 to 10 steps" + ("; extra steps were dropped" if len(steps) > 10 else ""), fatal=len(steps) > 10)
        steps = steps[:10]
    owners = s.get("owners", {})
    keys = list(owners)

    def ocol(st, k):
        o = owners.get(st.get("owner"))
        if o:
            return on_theme(c, color_of(o, keys.index(st["owner"])))
        return on_theme(c, color_of(st, k))
    band_items = s.get("bands", [])[:3]
    bottom = BOTTOM
    legend = bool(owners)
    bx0 = LEFT
    n = len(steps)
    per_row = n if n <= 5 else math.ceil(n / 2)
    rows = math.ceil(n / per_row)
    gap = 0.3
    w, xs = columns(per_row, gap=gap)
    if band_items or legend:
        bh = 0.42
        need = max(len(band_items) * (bh + 0.1), (len(owners) * 0.22 + 0.05) if legend else 0)
        top_b = bottom - need
        if legend:
            for k, key in enumerate(keys):
                o = owners[key]
                yy = top_b + 0.04 + k * 0.22
                c.oval(LEFT + 0.02, yy + 0.04, 0.11, fill=color_of(o, k))
                c.text(LEFT + 0.22, yy, xs[1] - LEFT - 0.35 if per_row > 1 else 2.0, 0.2, o.get("label", key), size=9, color=c.t.muted)
            bx0 = xs[1] if per_row > 1 else LEFT + 2.3
        for k, b in enumerate(band_items):
            bands(c, [dict(b, plain=True)], top_b + k * (bh + 0.1), h=bh, x0=bx0, total=RIGHT - bx0, i=i)
        bottom = top_b - 0.22
    top = c.top
    mk = s.get("marker")
    if mk:
        si = max(1, min(n, int(mk.get("step", 1)))) - 1
        mx = xs[si % per_row]
        label = mk.get("text", "").upper()
        lw = min(RIGHT - mx - 0.4, ig_metrics_width(label, 8.5) + 0.1)
        c.text(mx, top, lw, 0.2, [{"text": label, "spacing": 1.5}], size=8.5, bold=True, color=c.t.accent(color_of(mk, 0)))
        c.arrow(mx + lw + 0.1, top + 0.1, min(RIGHT, mx + lw + 0.6), top + 0.1, color=c.t.accent(color_of(mk, 0)), width=1)
        top += 0.32
    rgap = 0.38
    h = min(1.9, (bottom - top - rgap * (rows - 1)) / rows)
    t_size = min(one_line_size(st.get("title", ""), w - 0.36, 13, 9.5, bold=True) for st in steps)
    d_size = min([fit_size(st["text"], w - 0.36, h - 1.04, 10.5, 8) for st in steps if st.get("text")] or [10.5])
    for k, st in enumerate(steps):
        r, cidx = divmod(k, per_row)
        x, y = xs[cidx], top + r * (h + rgap)
        col = ocol(st, k)
        c.card(x, y, w, h, border=col if st.get("highlight") else None)
        c.text(x + 0.18, y + 0.1, 0.8, 0.46, f"{k + 1:02d}", size=22, light=True, color=c.t.accent(col), valign="middle")
        c.oval(x + w - 0.3, y + 0.24, 0.13, fill=col)
        title = st.get("title", "")
        c.text(x + 0.18, y + 0.6, w - 0.36, 0.3, title, size=t_size, bold=True)
        if st.get("text"):
            c.text(x + 0.18, y + 0.94, w - 0.36, h - 1.04, st["text"], size=d_size, color=c.t.muted)
        if cidx < per_row - 1 and k < n - 1:
            c.arrow(x + w + 0.04, y + h / 2, x + w + gap - 0.04, y + h / 2)
    if rows > 1:
        last = xs[per_row - 1] + w / 2
        y1 = top + h
        mid = y1 + rgap / 2
        c.line(last, y1, last, mid, color=c.t.ink, width=1)
        c.line(last, mid, xs[0] + w / 2, mid, color=c.t.ink, width=1)
        c.arrow(xs[0] + w / 2, mid, xs[0] + w / 2, y1 + rgap - 0.02)


def ig_metrics_width(text, size, bold=True):
    from ig_metrics import measure
    return measure([{"runs": [(text, size, "bold" if bold else "regular", 1.5)], "indent": 0, "after": 0}], 20)["width"]


def s_roles(deck, s, i):
    """Team structure: role cards (2 to 5) with a big count, a short line and responsibilities, and an
    optional headcount ramp drawn on the right."""
    c = content(deck, s, i)
    roles = s.get("roles", [])
    if not 2 <= len(roles) <= 5:
        warn(i, "roles needs 2 to 5 role cards" + ("; extra roles were dropped" if len(roles) > 5 else ""), fatal=len(roles) > 5)
        roles = roles[:5]
    ramp = s.get("ramp")
    bottom = note_band(c, s["note"]) if s.get("note") else BOTTOM
    right = RIGHT - (3.55 if ramp else 0)
    w, xs = columns(len(roles), gap=0.16, total=right - LEFT)
    h = bottom - c.top
    bsize = min([bullets_fit(r["points"], w - 0.36, h - 2.1, (10.5, 8), 4) for r in roles if r.get("points")] or [10.5])
    tsize = min(fit_size(r.get("title", ""), w - 0.36, 0.5, 13, 9.5, bold=True) for r in roles)
    for k, (x, r) in enumerate(zip(xs, roles)):
        col = on_theme(c, color_of(r, k))
        c.card(x, c.top, w, h, radius=0.06)
        c.rect(x + 0.06, c.top + 0.02, w - 0.12, 0.06, col)
        cnt = str(r.get("count", ""))
        c.text(x + 0.18, c.top + 0.2, w - 0.36, 0.7, cnt, size=fit_size(cnt, w - 0.36, 0.7, 40, 20), light=True, color=c.t.accent(col))
        title = r.get("title", "")
        c.text(x + 0.18, c.top + 0.95, w - 0.36, 0.52, title, size=tsize, bold=True)
        if r.get("sub"):
            c.text(x + 0.18, c.top + 1.5, w - 0.36, 0.26, r["sub"], size=one_line_size(r["sub"], w - 0.36, 9.5, 8), color=c.t.muted)
        c.line(x + 0.18, c.top + 1.85, x + w - 0.18, c.top + 1.85, color=c.t.line, dash=True)
        if r.get("points"):
            c.bullets(x + 0.18, c.top + 1.98, w - 0.36, h - 2.1, r["points"], size=bsize, gap=4)
    if ramp:
        x0 = right + 0.55
        cw = RIGHT - x0
        c.text(right + 0.25, c.top, RIGHT - right - 0.25, 0.22, [{"text": ramp.get("label", "Headcount ramp").upper(), "spacing": 2}],
               size=8.5, bold=True)
        cats, vals = ramp.get("categories", []), ramp.get("values", [])
        opt = ramp.get("optional") or {}
        top_v = max([v + (opt.get("add", 0) if k >= opt.get("from", 99) - 1 else 0) for k, v in enumerate(vals)] + [1])
        ymax = top_v + 0.5
        chart_top, chart_h = c.top + 0.45, (bottom - c.top) - 2.35
        unit = chart_h / ymax
        base = chart_top + chart_h
        for g in range(1, int(top_v) + 1):
            gy = base - g * unit
            c.line(x0, gy, RIGHT, gy, color=c.t.grid, width=0.5)
            c.text(x0 - 0.3, gy - 0.09, 0.22, 0.18, str(g), size=8, color=c.t.dim, align="right")
        bw = cw / max(1, len(vals))
        hl = int(ramp.get("highlight", 0))
        for k, v in enumerate(vals):
            bx = x0 + k * bw + 0.03
            c.rect(bx, base - v * unit, bw - 0.06, v * unit, YELLOW_ if k < hl else c.t.ink)
            if opt and k >= opt.get("from", 99) - 1:
                c.outline(bx, base - (v + opt.get("add", 1)) * unit, bw - 0.06, opt.get("add", 1) * unit - 0.02, MAGENTA_)
            if k < len(cats):
                c.text(bx - 0.03, base + 0.06, bw, 0.18, str(cats[k]), size=8, color=c.t.muted, align="center")
        c.line(x0, base, RIGHT, base, color=c.t.ink, width=0.75)
        ly = base + 0.38
        leg = []
        if hl:
            leg.append(("fill", YELLOW_, ramp.get("highlight_label", "Ramp")))
        leg.append(("fill", c.t.ink, ramp.get("full_label", "Full team")))
        if opt:
            leg.append(("dash", MAGENTA_, opt.get("label", "Optional")))
        for k, (kind, colr, lab) in enumerate(leg):
            yy = ly + k * 0.24
            if kind == "fill":
                c.rect(x0, yy + 0.03, 0.16, 0.12, colr)
            else:
                c.outline(x0, yy + 0.03, 0.16, 0.12, colr)
            c.text(x0 + 0.26, yy, cw - 0.26, 0.2, lab, size=9, color=c.t.muted)
        if ramp.get("note"):
            ny = ly + len(leg) * 0.24 + 0.08
            c.text(right + 0.25, ny, RIGHT - right - 0.25, bottom - ny, ramp["note"], fit=(9, 8), color=c.t.muted)


YELLOW_, MAGENTA_ = ACCENTS[1], ACCENTS[2]


TYPES = {"title": s_title, "agenda": s_agenda, "section": s_section, "statement": s_statement, "quote": s_statement,
         "closing": s_closing, "bullets": s_bullets, "cards": s_cards, "stats": s_stats, "process": s_process,
         "timeline": s_timeline, "table": s_table, "chart": s_chart, "comparison": s_comparison, "image": s_image,
         "team": s_team, "architecture": s_architecture, "flow": s_flow, "roles": s_roles}


def build(spec, out, base=Path("."), theme=None):
    WARNINGS.clear()
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
    for i, msg, fatal in WARNINGS:
        print(f"{'ERROR' if fatal else 'WARNING'} slide {i}: {msg}")


if __name__ == "__main__":
    main()
