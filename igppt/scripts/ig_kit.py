"""ig_kit: build Insight Global decks on the bundled IG template with python-pptx.

Most decks should be built from a JSON spec with build_deck.py. Use this module directly only
for a slide the spec cannot express:

    import sys; sys.path.insert(0, "<skill>/scripts")
    from ig_kit import *

    deck = Deck(theme="dark")                     # or "light"
    deck.title("Quarterly Update", "Delivery team", "Nov 2026")
    c = deck.slide("One Message Per Slide", eyebrow="Section", subtitle="A line that frames it")
    w, xs = columns(3)
    for x in xs:
        c.card(x, c.top, w, 2.0)
    deck.save("out.pptx")

Positions and sizes are inches on a 13.33 x 7.5 slide; colours are 6-digit hex strings.
The template draws the title, section label, footer logo and page number. Draw the body
between x 0.6 and 12.73, and between `c.top` and 6.85.
"""
import math
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "ig-template.pptx"
ICONS = ROOT / "assets" / "icons"

# ---- Insight Global brand colours (template theme) ----
BLACK, WHITE = "000000", "FFFFFF"
CYAN, YELLOW, MAGENTA, GREEN, ORANGE, NAVY = "00D6F1", "FFD700", "FF0069", "55E03A", "F98B34", "00273B"
ACCENTS = [CYAN, YELLOW, MAGENTA, GREEN, ORANGE]          # use in this order, never cycle randomly
FONT, FONT_LIGHT = "Trenda IG Text", "Trenda IG Text Light"

# ---- page geometry ----
LEFT, RIGHT, BOTTOM = 0.6, 12.73, 6.85
WIDTH = RIGHT - LEFT
TOP_WITH_SUBTITLE, TOP_NO_SUBTITLE = 2.12, 1.9

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
_ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}


class Theme:
    def __init__(self, name, content_layout, agenda_layout, ink, muted, dim, card, card_alt, line, chip_fill, grid,
                 accent_text):
        self.name, self.content_layout, self.agenda_layout = name, content_layout, agenda_layout
        self.ink, self.muted, self.dim = ink, muted, dim
        self.card, self.card_alt, self.line, self.chip_fill, self.grid = card, card_alt, line, chip_fill, grid
        self._accent_text = accent_text

    def accent(self, color):
        """Colour to use when an accent colour is used for TEXT (darkened on light backgrounds)."""
        return self._accent_text.get(color, color)


DARK = Theme("dark", "Dark Title Only", "Dark Title Only_Color",
             ink=WHITE, muted="AEB4BC", dim="7A828D", card="111317", card_alt="171A1F", line="2A2E35",
             chip_fill="15171C", grid="16222B", accent_text={})
LIGHT = Theme("light", "Light Title Only", "Light Title Only",
              ink="111418", muted="4A5561", dim="7A8590", card="F2F4F6", card_alt="FFFFFF", line="D9DEE3",
              chip_fill="FFFFFF", grid="E3E7EB",
              accent_text={CYAN: "0089A3", YELLOW: "9A7B00", MAGENTA: "D1005A", GREEN: "2E8B16", ORANGE: "C2631A"})
THEMES = {"dark": DARK, "light": LIGHT}


def rgb(hex_color):
    return RGBColor.from_string(hex_color.upper())


def columns(n, gap=0.2, x0=LEFT, total=WIDTH):
    """Split a width into n equal columns. Returns (column_width, [x positions])."""
    w = (total - gap * (n - 1)) / n
    return w, [x0 + i * (w + gap) for i in range(n)]


def text_height(text, w, size, line_spacing=1.22, para_gap=0.35):
    """Estimated height (inches) of `text` (str or list of paragraphs) at `size` pt in a box `w` wide."""
    paras = [text] if isinstance(text, str) else list(text)
    cpl = max(1, (w * 72) / (0.48 * size))                    # rough characters per line for Trenda
    lines = sum(max(1, math.ceil(len(p) / cpl)) for p in paras)
    return (lines * size * line_spacing + (len(paras) - 1) * size * para_gap) / 72


def fit_size(text, w, h, max_size=18, min_size=9, line_spacing=1.22, para_gap=0.35):
    """Largest font size (pt) at which `text` (str, or list of paragraph strings) fits a w x h box."""
    size = max_size
    while size > min_size:
        if text_height(text, w, size, line_spacing, para_gap) <= h:
            return size
        size -= 0.5
    return min_size


class Deck:
    """A presentation on the bundled Insight Global template."""

    def __init__(self, theme="dark", template=TEMPLATE):
        self.prs = Presentation(str(template))
        self.theme = THEMES[theme] if isinstance(theme, str) else theme

    # ----- slide types that use the template's own design -----
    def title(self, title, subtitle="", date="", notes=""):
        s = self._new("Proposal Title Slide", notes)
        self._fill(s, 0, title); self._fill(s, 10, subtitle); self._fill(s, 13, date)
        return s

    def agenda(self, items, title="Agenda", notes=""):
        """Numbered agenda, up to 7 items."""
        t = self.theme
        s = self._new(t.agenda_layout, notes)
        self._fill(s, 0, title); self._fill(s, 21, "")
        c = Canvas(s, t)
        items = list(items)[:7]
        step = min(0.665, 4.6 / max(len(items), 1))
        for i, item in enumerate(items):
            y = 2.01 + i * step
            c.oval(2.71, y, 0.35, fill=None, line=t.ink, line_width=1.5, text=str(i + 1), text_size=11, text_color=t.ink)
            c.text(3.26, y - 0.06, 8.8, 0.47, item, size=20, valign="middle")
        return s

    def section(self, title, notes=""):
        """Full-bleed divider between sections (also good as a 'LIVE DEMO' holding slide)."""
        s = self._new("Pink Divider_1", notes)
        self._fill(s, 0, title)
        return s

    def statement(self, text, eyebrow="", attribution="", notes=""):
        """One big message or a quote on the navy statement layout."""
        s = self._new("Navy Statement Left", notes)
        self._fill(s, 21, eyebrow)
        for ph in s.placeholders:
            if ph.placeholder_format.idx == 0:
                ph.text_frame.text = text
                ph.text_frame.paragraphs[0].runs[0].font.size = Pt(fit_size(text, 8.0, 2.6, 44, 24))
        if attribution:
            Canvas(s, DARK).text(0.56, 5.25, 8.2, 0.4, attribution, size=14, color=CYAN)
        return s

    def closing(self, style="thank-you", notes=""):
        """style: thank-you, tagline, tagline-texture, logo."""
        layouts = {"thank-you": "Closer_1", "tagline": "Closer_5", "tagline-texture": "Closer_4", "logo": "Closer_6"}
        return self._new(layouts[style], notes)

    # ----- free-form content slide -----
    def slide(self, title, eyebrow="", subtitle="", notes="", theme=None):
        """Content slide with the template title and section label. Returns a Canvas."""
        t = THEMES[theme] if isinstance(theme, str) else (theme or self.theme)
        s = self._new(t.content_layout, notes)
        self._fill(s, 0, title); self._fill(s, 21, eyebrow)
        for ph in s.placeholders:  # lift the title a little so a subtitle fits beneath it
            if ph.placeholder_format.idx == 0:
                ph.left, ph.top, ph.width, ph.height = Inches(0.556), Inches(0.822), Inches(12.08), Inches(0.968)
                ph.text_frame.paragraphs[0].runs[0].font.size = Pt(fit_size(title, 12.0, 0.9, 40, 28, line_spacing=1.1))
        c = Canvas(s, t)
        c.top = TOP_WITH_SUBTITLE if subtitle else TOP_NO_SUBTITLE
        if subtitle:
            c.text(0.56, 1.62, 12.1, 0.37, subtitle, size=fit_size(subtitle, 12.1, 0.3, 15, 12), color=t.muted)
        return c

    def save(self, path):
        self.prs.save(str(path))
        return path

    # ----- internals -----
    def _new(self, layout, notes=""):
        s = self.prs.slides.add_slide(self.prs.slide_layouts.get_by_name(layout))
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    @staticmethod
    def _fill(slide, idx, text):
        for ph in list(slide.placeholders):
            if ph.placeholder_format.idx == idx:
                if text:
                    ph.text_frame.text = text
                else:
                    ph._element.getparent().remove(ph._element)


class Canvas:
    """Drawing helpers for one slide. Colour arguments left as None follow the slide's theme."""

    def __init__(self, slide, theme=DARK):
        self.slide, self.shapes, self.t = slide, slide.shapes, theme
        self.top = TOP_WITH_SUBTITLE

    # ---------- text ----------
    def text(self, x, y, w, h, text, size=12, color=None, bold=False, light=False, italic=False,
             align="left", valign="top", spacing=0, fit=None):
        """Text box. `text` is a string or a list of runs {"text", "size", "color", "bold", "light", "italic",
        "spacing", "br"}; "br": True ends the paragraph after that run. fit=(max, min) picks the size automatically."""
        if fit and isinstance(text, str):
            size = fit_size(text, w, h, *fit)
        tb = self.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        self._frame(tf, valign)
        runs = [{"text": text}] if isinstance(text, str) else text
        base = dict(size=size, color=color or self.t.ink, bold=bold, light=light, italic=italic, spacing=spacing)
        p = tf.paragraphs[0]; p.alignment = _ALIGN[align]
        for r in runs:
            self._run(p, {**base, **{k: v for k, v in r.items() if v is not None}})
            if r.get("br"):
                p = tf.add_paragraph(); p.alignment = _ALIGN[align]
        return tb

    def label(self, x, y, w, text, color=CYAN, size=9.5):
        """Small spaced-out heading above a group, e.g. 'KEY RISKS'."""
        return self.text(x, y, w, 0.24, text.upper(), size=size, color=self.t.accent(color), bold=True, spacing=3)

    def bullets(self, x, y, w, h, items, size=None, color=None, marker="•", gap=6, fit=(18, 10)):
        """Bulleted list. Items are strings or {"text": ..., "sub": [...]} for one level of sub-points.
        Use marker "✓" for a checklist. Size is picked to fit unless given."""
        flat = []
        for it in items:
            if isinstance(it, dict):
                flat.append((it["text"], 0)); flat += [(s_, 1) for s_ in it.get("sub", [])]
            else:
                flat.append((str(it), 0))
        if size is None:
            size = fit_size([f for f, _ in flat], w - 0.3, h, *fit, para_gap=gap / 12)
        tb = self.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        self._frame(tf, "top")
        for i, (txt, lvl) in enumerate(flat):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(gap)
            self._run(p, dict(text=txt, size=size - 2 * lvl, color=(color or self.t.ink) if lvl == 0 else self.t.muted))
            ind = 0.28 + 0.3 * lvl
            ppr = p._p.get_or_add_pPr()
            ppr.set("marL", str(Inches(ind))); ppr.set("indent", str(-Inches(0.28)))
            bu = etree.SubElement(ppr, f"{{{_A}}}buChar"); bu.set("char", "–" if lvl else marker)
        return tb

    # ---------- shapes ----------
    def card(self, x, y, w, h, border=None, fill=None, radius=0.1, dash=False, border_width=1):
        """Rounded panel. Give one card a coloured border to highlight it."""
        sh = self._shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill or self.t.card, border or self.t.line, border_width)
        sh.adjustments[0] = min(0.5, radius / min(w, h))
        if dash:
            sh.line.dash_style = MSO_LINE.DASH
        return sh

    def rect(self, x, y, w, h, fill, line=None):
        return self._shape(MSO_SHAPE.RECTANGLE, x, y, w, h, fill, line)

    def oval(self, x, y, d, fill=CYAN, line=None, line_width=1, text=None, text_size=14, text_color=BLACK):
        """Circle; pass `text` for a numbered circle."""
        sh = self._shape(MSO_SHAPE.OVAL, x, y, d, d, fill, line, line_width)
        if text is not None:
            tf = sh.text_frame
            self._frame(tf, "middle"); tf.word_wrap = False
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
            self._run(p, dict(text=text, size=text_size, color=text_color, bold=True))
        return sh

    def chevron(self, x, y, w=0.12, h=0.26, fill=None):
        return self._shape(MSO_SHAPE.CHEVRON, x, y, w, h, fill or ("4A515C" if self.t is DARK else "B8C0C8"), None)

    def line(self, x1, y1, x2, y2, color=None, width=1, dash=False):
        ln = self.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        ln.line.color.rgb = rgb(color or self.t.line); ln.line.width = Pt(width)
        if dash:
            ln.line.dash_style = MSO_LINE.DASH
        return ln

    def image(self, path, x, y, w=None, h=None):
        return self.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)

    def image_fit(self, path, x, y, w, h):
        """Picture scaled to fit inside the box without distortion, centred."""
        pic = self.image(path, x, y, w=w)
        ratio = pic.height / pic.width
        if w * ratio > h:
            pic.height, pic.width = Inches(h), Inches(h / ratio)
        pic.left = Inches(x) + int((Inches(w) - pic.width) / 2)
        pic.top = Inches(y) + int((Inches(h) - pic.height) / 2)
        return pic

    # ---------- composites ----------
    def icon_circle(self, x, y, d, color, icon, icon_color="black"):
        """Coloured circle with an icon from assets/icons (names in references/ig-brand.md)."""
        self.oval(x, y, d, fill=color)
        f = ICONS / f"{icon}-{icon_color}.png"
        if not f.exists():
            raise ValueError(f"No icon '{icon}'. Available: {', '.join(icon_names())}")
        pad = d * 0.26
        self.image(f, x + pad, y + pad, d - 2 * pad, d - 2 * pad)

    def chip(self, x, y, w, text, color=CYAN):
        """Pill tag, e.g. 'RECOMMENDED'."""
        sh = self._shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, 0.28, self.t.chip_fill, color, 0.75)
        sh.adjustments[0] = 0.5
        self.text(x, y, w, 0.28, text.upper(), size=8, color=self.t.accent(color), bold=True, align="center",
                  valign="middle", spacing=1)

    def stat_tile(self, x, y, w, h, number, heading, desc="", color=CYAN, number_w=1.3, number_size=32):
        """Card with a big number on the left and a heading and line of text on the right."""
        self.card(x, y, w, h)
        self.text(x + 0.25, y, number_w, h, number, size=number_size, color=self.t.accent(color), light=True, valign="middle")
        tx, tw = x + 0.3 + number_w, w - number_w - 0.5
        top = y + h / 2 - (0.36 if desc else 0.14)
        self.text(tx, top, tw, 0.28, heading, size=12.5, bold=True)
        if desc:
            self.text(tx, top + 0.32, tw, h / 2, desc, size=10.5, color=self.t.muted)

    def stacked_bars(self, x, y, label_w, bar_w, rows, colors, row_h=0.34, gap=0.12, suffix="%", note=None):
        """100% stacked bars drawn as shapes. rows = [(label, [values...])]; colors = one per segment.
        note(values) -> text or runs shown to the right of each bar."""
        for r, (name, vals) in enumerate(rows):
            yy = y + r * (row_h + gap); xx = x + label_w; total = float(sum(vals))
            self.text(x, yy, label_w - 0.1, row_h, name, size=12, bold=True, valign="middle")
            for k, v in enumerate(vals):
                sw = v / total * bar_w
                self.rect(xx, yy, max(sw - 0.02, 0.02), row_h, colors[k])
                if sw > 0.45:
                    self.text(xx, yy, sw, row_h, f"{v:g}{suffix}", size=9, bold=True, align="center", valign="middle",
                              color=BLACK if colors[k] in (CYAN, YELLOW, GREEN, ORANGE, WHITE) else WHITE)
                xx += sw
            if note:
                self.text(xx + 0.12, yy, 2.0, row_h, note(vals), valign="middle")

    def table(self, x, y, col_widths, rows, header=True, row_h=0.36, size=11, bold_last=False, header_color=CYAN):
        """Table in IG style. rows = list of lists; the first row is the header when header=True."""
        n_rows, n_cols = len(rows), len(col_widths)
        gf = self.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y), Inches(sum(col_widths)), Inches(row_h * n_rows))
        tbl = gf.table
        tbl.first_row = False; tbl.horz_banding = False
        for j, cw in enumerate(col_widths):
            tbl.columns[j].width = Inches(cw)
        for i, row in enumerate(rows):
            tbl.rows[i].height = Inches(row_h)
            for j in range(n_cols):
                val = row[j] if j < len(row) else ""
                cell = tbl.cell(i, j)
                head = header and i == 0
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(NAVY if head else (self.t.card if i % 2 else self.t.card_alt))
                cell.margin_left = cell.margin_right = Inches(0.1); cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.text_frame.word_wrap = True
                self._run(cell.text_frame.paragraphs[0], dict(text=str(val), size=size - 1 if head else size,
                          color=header_color if head else self.t.ink, bold=head or (bold_last and j == n_cols - 1)))
                tcPr = cell._tc.get_or_add_tcPr()
                for k, side in enumerate(("lnL", "lnR", "lnT", "lnB")):
                    ln = etree.Element(f"{{{_A}}}{side}"); ln.set("w", str(Pt(0.5)))
                    sf = etree.SubElement(ln, f"{{{_A}}}solidFill"); etree.SubElement(sf, f"{{{_A}}}srgbClr").set("val", self.t.line)
                    tcPr.insert(k, ln)
        return gf

    def chart(self, x, y, w, h, kind, categories, series, number_format=None, max_value=None, colors=None):
        """Native, editable chart. kind: bar (horizontal), column, stacked-column, line, pie, doughnut.
        series = [{"name": ..., "values": [...]}]. One series gets value labels; several get a legend."""
        types = {"bar": XL_CHART_TYPE.BAR_CLUSTERED, "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
                 "stacked-column": XL_CHART_TYPE.COLUMN_STACKED, "line": XL_CHART_TYPE.LINE_MARKERS,
                 "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT}
        data = CategoryChartData(); data.categories = list(categories)
        for s_ in series:
            data.add_series(s_["name"], list(s_["values"]))
        chart = self.shapes.add_chart(types[kind], Inches(x), Inches(y), Inches(w), Inches(h), data).chart
        colors = colors or ACCENTS
        chart.font.size = Pt(12); chart.font.name = FONT; chart.font.color.rgb = rgb(self.t.muted)
        chart.has_title = False
        plot = chart.plots[0]
        round_ = kind in ("pie", "doughnut")
        many = len(series) > 1
        chart.has_legend = many or round_
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM if not round_ else XL_LEGEND_POSITION.RIGHT
            chart.legend.include_in_layout = False
            chart.legend.font.size = Pt(12); chart.legend.font.color.rgb = rgb(self.t.muted)
        if round_:
            for k, pt in enumerate(plot.series[0].points):
                pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(colors[k % len(colors)])
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.show_percentage, dl.show_value, dl.show_category_name = True, False, False
            dl.number_format, dl.number_format_is_linked = "0%", False
            dl.font.size = Pt(13); dl.font.bold = True; dl.font.color.rgb = rgb(BLACK)
            return chart
        for k, ser in enumerate(plot.series):
            c_ = colors[k % len(colors)]
            if kind == "line":
                ser.format.line.color.rgb = rgb(c_); ser.format.line.width = Pt(2.25); ser.smooth = False
                ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = rgb(c_)
                ser.marker.format.line.color.rgb = rgb(c_)
            else:
                ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(c_)
        if kind != "line":
            plot.gap_width = 55
            if kind == "stacked-column":
                plot.overlap = 100
        if not many:
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.position = XL_LABEL_POSITION.OUTSIDE_END if kind != "line" else XL_LABEL_POSITION.ABOVE
            dl.font.size = Pt(12); dl.font.color.rgb = rgb(self.t.ink)
            if number_format:
                dl.number_format, dl.number_format_is_linked = number_format, False
        va, ca = chart.value_axis, chart.category_axis
        va.has_major_gridlines = many or kind == "line"
        if va.has_major_gridlines:
            va.major_gridlines.format.line.color.rgb = rgb(self.t.grid); va.major_gridlines.format.line.width = Pt(0.5)
        va.visible = many or kind == "line"
        va.format.line.fill.background(); va.tick_labels.font.size = Pt(11)
        if number_format:
            va.tick_labels.number_format, va.tick_labels.number_format_is_linked = number_format, False
        if max_value:
            va.maximum_scale = max_value
        ca.format.line.color.rgb = rgb(self.t.line); ca.has_major_gridlines = False; ca.tick_labels.font.size = Pt(12)
        if kind == "bar":
            ca.reverse_order = True
        return chart

    def steps_flow(self, y, steps, h=1.62, gap=0.22, highlight=None):
        """Row of step cards joined by chevrons. steps = [(icon, owner, color, title, description)];
        icon may be None for a numbered circle. highlight = index of one step to outline."""
        w, xs = columns(len(steps), gap=gap)
        for i, (x, (icon, owner, color, title, desc)) in enumerate(zip(xs, steps)):
            self.card(x, y, w, h, border=color if i == highlight else None)
            if icon:
                self.icon_circle(x + 0.16, y + 0.16, 0.46, color, icon)
            else:
                self.oval(x + 0.16, y + 0.16, 0.46, fill=color, text=str(i + 1), text_size=15)
            head = [{"text": f"STEP {i + 1}", "color": self.t.dim, "br": bool(owner)}]
            if owner:
                head.append({"text": owner.upper(), "color": self.t.accent(color)})
            self.text(x + 0.72, y + 0.16, w - 0.85, 0.46, head, size=8.5, bold=True, spacing=2, valign="middle")
            self.text(x + 0.16, y + 0.74, w - 0.32, 0.36, title, size=fit_size(title, w - 0.32, 0.36, 15, 11), bold=True)
            self.text(x + 0.16, y + 1.14, w - 0.32, h - 1.24, desc, fit=(13, 9), color=self.t.muted)
            if i < len(steps) - 1:
                self.chevron(x + w + (gap - 0.12) / 2, y + h / 2 - 0.13)
        return w, xs

    def milestones(self, y, items, colors=None):
        """Horizontal roadmap. items = [(date, title, text)]. Uses about 3.2 inches of height from y."""
        n = len(items); colors = colors or ACCENTS
        w, xs = columns(n, gap=0.25)
        ly = y + 0.75
        self.line(LEFT, ly, RIGHT, ly, color=self.t.line, width=2)
        for i, (x, (date, title, text)) in enumerate(zip(xs, items)):
            c_ = colors[i % len(colors)]
            self.text(x, y, w, 0.4, date, size=15, bold=True, color=self.t.accent(c_))
            self.oval(x, ly - 0.16, 0.32, fill=c_)
            self.text(x, ly + 0.4, w, 0.42, title, size=fit_size(title, w, 0.42, 17, 11), bold=True)
            self.text(x, ly + 0.9, w, 1.6, text, fit=(14, 9.5), color=self.t.muted)

    def schedule(self, y, slots, rows, label_w=2.15, row_h=0.28, gap=0.07, sub_slots=None):
        """Shift or schedule chart. slots = column headers (e.g. hours); rows = [(label, [(start, end, color, text, dashed)])]
        with start/end as slot indexes. Returns the y just below the last row."""
        x0 = LEFT + label_w; sw = (RIGHT - x0) / len(slots)
        for i, s_ in enumerate(slots):
            self.text(x0 + i * sw - 0.2, y, 0.4, 0.2, s_, size=8, bold=True, align="center")
            if sub_slots:
                self.text(x0 + i * sw - 0.23, y + 0.22, 0.46, 0.2, sub_slots[i], size=6.5, color=self.t.accent(CYAN), align="center")
        top = y + (0.54 if sub_slots else 0.3)
        bottom = top + len(rows) * (row_h + gap)
        for i in range(len(slots) + 1):
            self.line(x0 + i * sw, top - 0.05, x0 + i * sw, bottom - 0.02, color=self.t.grid, width=0.5)
        for r, (label, bars) in enumerate(rows):
            yy = top + r * (row_h + gap)
            self.text(LEFT, yy, label_w - 0.05, row_h, label, size=9, valign="middle")
            for start, end, color, text, *rest in bars:
                dashed = bool(rest and rest[0])
                self.card(x0 + start * sw + 0.02, yy, (end - start) * sw - 0.04, row_h, border=color,
                          fill=self.t.chip_fill if dashed else color, radius=0.08, dash=dashed, border_width=1.25 if dashed else 0.5)
                if text:
                    self.text(x0 + start * sw, yy, (end - start) * sw, row_h, text, size=8, bold=True,
                              color=self.t.accent(color) if dashed else BLACK, align="center", valign="middle")
        return bottom

    # ---------- internals ----------
    def _shape(self, kind, x, y, w, h, fill, line, line_width=1):
        sh = self.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.shadow.inherit = False
        if fill:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line); sh.line.width = Pt(line_width)
        else:
            sh.line.fill.background()
        return sh

    @staticmethod
    def _frame(tf, valign):
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = _ANCHOR[valign]

    @staticmethod
    def _run(p, o):
        r = p.add_run()
        r.text = o["text"]
        f = r.font
        f.name = FONT_LIGHT if o.get("light") else FONT
        f.size = Pt(o.get("size", 12)); f.bold = bool(o.get("bold")); f.italic = bool(o.get("italic"))
        f.color.rgb = rgb(o.get("color", WHITE))
        if o.get("spacing"):
            r._r.get_or_add_rPr().set("spc", str(int(o["spacing"] * 100)))
        return r


def icon_names():
    return sorted({p.stem.rsplit("-", 1)[0] for p in ICONS.glob("*.png")})
