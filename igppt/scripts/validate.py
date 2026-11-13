"""Validate an IGPPT deck before it is delivered. Exit code 0 = PASS, 1 = FAIL.

    python validate.py deck.pptx [--spec deck.json] [--words igppt-words.txt] [--json]

Checks every slide of the finished .pptx:

  Template   built by IGPPT on the bundled IG template; only IG layouts; 16:9 size
  Fonts      every run is Trenda IG Text (regular, light or bold); no theme fonts such as Aptos/Calibri;
             no text under 8 pt; charts use the IG font
  Colours    only IG brand and IGPPT theme colours in text, shapes, tables and charts
  Fit        no text overflows its box, no word is broken across lines, no title wraps, tables fit the page
  Overlap    no text overlaps other text, crosses the edge of a card, or sits over an icon; no shapes partly
             overlap each other; nothing runs off the slide, past the side margins or into the footer
  Spacing    cards in a row keep a gap; text keeps padding inside its card (warnings)
  Words      no em dashes, en dashes or "--"; no repeated words; no leftover placeholder text;
             spelling (likely typos fail, unknown names and terms are listed as warnings)

With --spec, each problem names the spec field to change (for example slides[3].cards[1].text), so the
fix goes into the JSON spec and the deck is rebuilt. Never edit the .pptx by hand.
Text is measured with the same character widths that build_deck.py uses (ig_metrics.py).
"""
import json
import re
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Emu

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ig_metrics as M  # noqa: E402
import ig_text  # noqa: E402
from ig_kit import ACCENTS, BLACK, DARK, LIGHT, NAVY, WHITE  # noqa: E402

MARKER = "Built with IGPPT"
IG_LAYOUTS = {"Proposal Title Slide", "Dark Title Only", "Dark 1-Column_6", "Dark 1-Column_11", "Dark Title Only_Color",
              "Light Title Only", "Pink Divider_1", "Navy Statement Left", "Closer_1", "Closer_4", "Closer_5", "Closer_6"}
FOOTER_LAYOUTS = IG_LAYOUTS - {"Proposal Title Slide", "Pink Divider_1", "Closer_1", "Closer_4", "Closer_5", "Closer_6"}
SLIDE_W, SLIDE_H = 13.333, 7.5
SIDE_MIN, SIDE_MAX, BODY_BOTTOM = 0.45, 12.9, 6.95
MIN_PT = 8
EPS = 0.02                       # inches of tolerance for touching edges
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
A = "{%s}" % NS["a"]


def ig_palette():
    cols = {BLACK, WHITE, NAVY, *ACCENTS, "4A515C", "B8C0C8", "B4E3E4", "E8E8E8"}
    for t in (DARK, LIGHT):
        cols |= {t.ink, t.muted, t.dim, t.card, t.card_alt, t.line, t.chip_fill, t.grid, *t._accent_text.values()}
    return {c.upper() for c in cols}


PALETTE = ig_palette()


def inches(v):
    return Emu(v).inches if v is not None else 0.0


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, slide, msg, text=None, fix=None):
        self.items.append({"level": level, "slide": slide, "message": msg, "text": text, "fix": fix})

    def fails(self):
        return [i for i in self.items if i["level"] == "FAIL"]


# ---------------------------------------------------------------- effective text properties
class TextStyle:
    """Resolves font, size, bold, spacing and insets through slide shape -> layout -> master -> defaults."""

    def __init__(self, prs):
        self.prs = prs
        root = prs.part._element
        self.default_style = root.find("p:defaultTextStyle", NS)
        theme = None
        try:
            master = prs.slide_masters[0]
            for rel in master.part.rels.values():
                if rel.reltype.endswith("/theme"):
                    theme = etree.fromstring(rel.target_part.blob)
        except Exception:
            pass
        self.theme_fonts = {}
        if theme is not None:
            for kind, key in (("majorFont", "+mj-lt"), ("minorFont", "+mn-lt")):
                el = theme.find(f".//a:{kind}/a:latin", NS)
                if el is not None:
                    self.theme_fonts[key] = el.get("typeface")

    @staticmethod
    def chain(shape):
        els = [shape._element]
        if getattr(shape, "is_placeholder", False):
            base = shape
            for _ in range(3):
                try:
                    base = base._base_placeholder
                except Exception:
                    base = None
                if base is None:
                    break
                els.append(base._element)
        return els

    def master_style(self, shape, slide):
        if not getattr(shape, "is_placeholder", False):
            return [self.default_style] if self.default_style is not None else []
        tx = slide.slide_layout.slide_master._element.find("p:txStyles", NS)
        ptype = shape.placeholder_format.type
        if ptype in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE):
            name = "titleStyle"
        elif ptype in (PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER):
            name = "otherStyle"
        else:
            name = "bodyStyle"
        st = tx.find(f"p:{name}", NS) if tx is not None else None
        return [st] if st is not None else []

    def body_pr(self, shape):
        out = {"lIns": 91440, "tIns": 45720, "rIns": 91440, "bIns": 45720, "anchor": "t", "wrap": "square", "autofit": None}
        found = {}
        for el in self.chain(shape):
            bp = el.find(".//a:bodyPr", NS)
            if bp is None:
                continue
            for k in ("lIns", "tIns", "rIns", "bIns", "anchor", "wrap"):
                if k not in found and bp.get(k) is not None:
                    found[k] = bp.get(k)
            if "autofit" not in found:
                if bp.find("a:normAutofit", NS) is not None:
                    found["autofit"] = "shrink"
                elif bp.find("a:spAutoFit", NS) is not None:
                    found["autofit"] = "grow"
                elif bp.find("a:noAutofit", NS) is not None:
                    found["autofit"] = None
        out.update(found)
        for k in ("lIns", "tIns", "rIns", "bIns"):
            out[k] = int(out[k]) / 914400
        return out

    def levels(self, shape, slide, lvl):
        """pPr-like elements for paragraph level lvl (1-based), most specific first."""
        out = []
        for el in self.chain(shape):
            ls = el.find(".//a:lstStyle", NS)
            if ls is not None:
                p = ls.find(f"a:lvl{lvl}pPr", NS)
                if p is not None:
                    out.append(p)
        for st in self.master_style(shape, slide):
            p = st.find(f"a:lvl{lvl}pPr", NS)
            if p is not None:
                out.append(p)
        return out

    def paragraph(self, p_el, shape, slide):
        ppr = p_el.find("a:pPr", NS)
        lvl = int(ppr.get("lvl", 0)) + 1 if ppr is not None else 1
        chain = ([ppr] if ppr is not None else []) + self.levels(shape, slide, lvl)

        def attr(name, default=None):
            for e in chain:
                if e.get(name) is not None:
                    return e.get(name)
            return default

        def child(path):
            for e in chain:
                c = e.find(path, NS)
                if c is not None:
                    return c
            return None

        marL = int(attr("marL", 0)) / 914400
        indent = int(attr("indent", 0)) / 914400
        ln = child("a:lnSpc")
        line_spacing, exact = 1.0, None
        if ln is not None:
            pct, pts = ln.find("a:spcPct", NS), ln.find("a:spcPts", NS)
            if pct is not None:
                line_spacing = int(pct.get("val")) / 100000
            elif pts is not None:
                exact = int(pts.get("val")) / 100

        def spacing(tag):
            sp = child(f"a:{tag}")
            if sp is None:
                return 0.0, 0.0
            pts, pct = sp.find("a:spcPts", NS), sp.find("a:spcPct", NS)
            return (int(pts.get("val")) / 100, 0.0) if pts is not None else (0.0, int(pct.get("val")) / 100000 if pct is not None else 0.0)

        defs = [e.find("a:defRPr", NS) for e in chain]
        defs = [d for d in defs if d is not None]
        bullet = child("a:buChar") is not None and child("a:buNone") is None
        return {"marL": marL, "indent": indent, "line_spacing": line_spacing, "exact": exact,
                "before": spacing("spcBef"), "after": spacing("spcAft"), "defs": defs, "bullet": bullet}

    def run(self, r_el, para):
        rpr = r_el.find("a:rPr", NS)
        chain = ([rpr] if rpr is not None else []) + para["defs"]
        explicit = rpr is not None and rpr.get("sz") is not None
        size = next((int(e.get("sz")) / 100 for e in chain if e.get("sz")), None)
        if size is None:
            size = 18.0
        bold = next((e.get("b") in ("1", "true") for e in chain if e.get("b") is not None), False)
        font, inherited = None, False
        for k, e in enumerate(chain):
            lat = e.find("a:latin", NS)
            if lat is not None and lat.get("typeface"):
                font, inherited = lat.get("typeface"), k > 0 or rpr is None
                break
        if font in self.theme_fonts:
            font = f"{self.theme_fonts[font]} (theme font)"
        spc = next((int(e.get("spc")) / 100 for e in chain if e.get("spc")), 0.0)
        color = None
        if rpr is not None:
            c = rpr.find("a:solidFill/a:srgbClr", NS)
            color = c.get("val").upper() if c is not None else None
        return {"size": size, "bold": bold, "font": font, "spacing": spc, "color": color, "inherited": inherited,
                "explicit_size": explicit}


# ---------------------------------------------------------------- geometry helpers
class Box:
    def __init__(self, x, y, w, h, kind, shape=None, text=""):
        self.x0, self.y0, self.x1, self.y1 = x, y, x + w, y + h
        self.kind, self.shape, self.text = kind, shape, text
        self.over = 0.0          # how far the text is taller than its box (inches)

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    def inter(self, o):
        w = min(self.x1, o.x1) - max(self.x0, o.x0)
        h = min(self.y1, o.y1) - max(self.y0, o.y0)
        return (w, h) if w > EPS and h > EPS else None

    def inside(self, o, tol=EPS):
        return self.x0 >= o.x0 - tol and self.y0 >= o.y0 - tol and self.x1 <= o.x1 + tol and self.y1 <= o.y1 + tol


def short(text, n=60):
    t = " ".join(str(text).split())
    return t if len(t) <= n else t[: n - 3] + "..."


# ---------------------------------------------------------------- spec mapping
def spec_leaves(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("type", "color", "icon", "theme", "background", "image", "style", "highlight", "grid", "widths"):
                continue
            yield from spec_leaves(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from spec_leaves(v, f"{path}[{i}]")
    elif isinstance(node, (str, int, float)) and not isinstance(node, bool):
        yield path, str(node)


def locate(spec, slide_no, text):
    """Spec field(s) that produced `text` on slide `slide_no`."""
    if not spec or not text:
        return None
    slides = spec.get("slides", [])
    if not 1 <= slide_no <= len(slides):
        return None
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()  # noqa: E731
    t = norm(text)
    leaves = list(spec_leaves(slides[slide_no - 1], f"slides[{slide_no - 1}]"))
    exact = [p for p, v in leaves if norm(v) == t]
    if exact:
        return exact[0]
    part = [p for p, v in leaves if norm(v) and (norm(v) in t or t in norm(v))]
    return ", ".join(part[:3]) if part else f"slides[{slide_no - 1}]"


# ---------------------------------------------------------------- the checks
class Validator:
    def __init__(self, path, spec=None, words=None, spelling=True):
        self.path = Path(path)
        self.prs = Presentation(str(path))
        self.style = TextStyle(self.prs)
        self.spec = spec
        self.spelling = spelling
        self.r = Report()
        for w in words or []:
            ig_text.load_words(w)

    def add(self, level, slide, msg, text=None, fix=None):
        where = locate(self.spec, slide, text) if text else None
        if where:
            fix = f"{fix} in {where}" if fix else f"change {where}"
        self.r.add(level, slide, msg, text, fix)

    # ----- deck level
    def deck_checks(self):
        prs = self.prs
        names = {l.name for l in prs.slide_layouts}
        if "Pink Divider_1" not in names or "Navy Statement Left" not in names:
            self.r.add("FAIL", 0, "deck is not based on the IG template (IG layouts missing)", fix="build it with make_deck.py")
        if abs(inches(prs.slide_width) - SLIDE_W) > 0.01 or abs(inches(prs.slide_height) - SLIDE_H) > 0.01:
            self.r.add("FAIL", 0, f"slide size is {inches(prs.slide_width):.2f} x {inches(prs.slide_height):.2f} in, not the IG 13.33 x 7.5")
        if (prs.core_properties.content_status or "") != MARKER:
            self.r.add("FAIL", 0, "deck was not built by the IGPPT scripts", fix="write a JSON spec and build it with make_deck.py; never write your own slide code")
        if not len(prs.slides):
            self.r.add("FAIL", 0, "deck has no slides")
            return
        first, last = prs.slides[0].slide_layout.name, prs.slides[-1].slide_layout.name
        if first != "Proposal Title Slide":
            self.r.add("WARN", 1, "deck does not start with a title slide")
        if not last.startswith("Closer"):
            self.r.add("WARN", len(prs.slides), "deck does not end with a closing slide")
        titles = {}
        for i, s in enumerate(prs.slides, 1):
            t = s.shapes.title.text_frame.text.strip() if s.shapes.title is not None and s.shapes.title.has_text_frame else ""
            if t:
                if t.lower() in titles:
                    self.r.add("WARN", i, f"same title as slide {titles[t.lower()]}: '{short(t)}'")
                titles.setdefault(t.lower(), i)

    # ----- one slide
    def slide_checks(self, i, slide):
        layout = slide.slide_layout.name
        if layout not in IG_LAYOUTS:
            self.add("FAIL", i, f"layout '{layout}' is not an IGPPT layout")
        boxes = []
        content = 0
        for shape in slide.shapes:
            boxes += self.shape_checks(i, slide, shape, layout)
            if not shape.is_placeholder:
                content += 1
        if layout in FOOTER_LAYOUTS - {"Navy Statement Left"} and content == 0:
            self.add("FAIL", i, "content slide has no content")
        self.overlap_checks(i, boxes)
        self.spacing_checks(i, boxes)
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text if slide.notes_slide.notes_text_frame else ""
            for level, msg in ig_text.check_text(notes, spelling=False):
                if "dash" in msg and "speaker notes" not in msg:
                    self.add("WARN", i, f"speaker notes {msg}", notes, fix="rewrite the notes")

    def shape_checks(self, i, slide, shape, layout):
        boxes = []
        x, y, w, h = inches(shape.left), inches(shape.top), inches(shape.width), inches(shape.height)
        is_bg = w * h > 0.6 * SLIDE_W * SLIDE_H
        name = short(shape.text_frame.text, 40) if shape.has_text_frame and shape.text_frame.text.strip() else shape.name
        # bounds
        if not is_bg and shape.shape_type != MSO_SHAPE_TYPE.LINE:
            if x < -EPS or y < -EPS or x + w > SLIDE_W + EPS or y + h > SLIDE_H + EPS:
                self.add("FAIL", i, f"'{name}' runs off the slide")
            elif not shape.is_placeholder and (x < SIDE_MIN or x + w > SIDE_MAX):
                self.add("FAIL", i, f"'{name}' is outside the IG side margins (0.6 to 12.73 in)")
            elif not shape.is_placeholder and layout in FOOTER_LAYOUTS and y + h > BODY_BOTTOM + EPS:
                self.add("FAIL", i, f"'{name}' runs into the footer (bottom {y + h:.2f} in, limit 6.85 in)",
                         shape.text_frame.text if shape.has_text_frame else None, fix="use fewer items or shorter text")
        # colours of the shape itself
        self.colour_checks(i, shape._element.find("p:spPr", NS) if shape._element.find("p:spPr", NS) is not None else None, name)
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            for sub in shape.shapes:
                boxes += self.shape_checks(i, slide, sub, layout)
            return boxes
        if shape.has_chart:
            self.chart_checks(i, shape)
            boxes.append(Box(x, y, w, h, "chart", shape))
            return boxes
        if shape.has_table:
            bottom = self.table_checks(i, slide, shape)
            boxes.append(Box(x, y, w, bottom - y, "table", shape))
            if layout in FOOTER_LAYOUTS and bottom > BODY_BOTTOM + EPS:
                self.add("FAIL", i, f"table grows to {bottom:.2f} in and runs into the footer (limit 6.85 in)",
                         fix="use fewer rows, shorter cell text, or split the table across two slides")
            return boxes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            if not is_bg:
                boxes.append(Box(x, y, w, h, "picture", shape))
            return boxes
        if shape.shape_type in (MSO_SHAPE_TYPE.LINE,) or shape._element.tag.endswith("cxnSp"):
            return boxes
        filled = self.is_filled(shape)
        if filled and not is_bg:
            boxes.append(Box(x, y, w, h, "shape", shape))
        if shape.has_text_frame and shape.text_frame.text.strip():
            tb = self.text_checks(i, slide, shape, x, y, w, h, layout)
            if tb is not None:
                boxes.append(tb)
        return boxes

    @staticmethod
    def is_filled(shape):
        sppr = shape._element.find("p:spPr", NS)
        if sppr is None:
            return False
        if sppr.find("a:solidFill", NS) is not None or sppr.find("a:gradFill", NS) is not None:
            return True
        ln = sppr.find("a:ln", NS)
        return ln is not None and ln.find("a:solidFill", NS) is not None

    def colour_checks(self, i, el, name):
        if el is None:
            return
        for c in el.iter(f"{A}srgbClr"):
            v = (c.get("val") or "").upper()
            if v and v not in PALETTE:
                self.add("FAIL", i, f"colour #{v} on '{name}' is not an IG colour", fix="use IG colours only (cyan, yellow, magenta, green, orange, navy, black, white)")
                return

    # ----- text in a shape
    def paragraphs(self, txBody, shape, slide, i, label):
        """Measurable paragraphs plus font, size and colour checks for every run."""
        paras, raw = [], []
        for p_el in txBody.findall("a:p", NS):
            para = self.style.paragraph(p_el, shape, slide)
            runs = []
            for r_el in p_el.findall("a:r", NS):
                t = r_el.findtext("a:t", default="", namespaces=NS)
                if not t:
                    continue
                ro = self.style.run(r_el, para)
                font = ro["font"]
                if font is None:
                    self.add("FAIL", i, f"text '{short(t, 40)}' has no font set and falls back to the theme font", t,
                             fix="build it with make_deck.py (ig_kit sets Trenda IG Text)")
                elif not font.startswith("Trenda IG Text"):
                    self.add("FAIL", i, f"font '{font}' used instead of Trenda IG Text: '{short(t, 40)}'", t)
                if ro["size"] < MIN_PT and ro["explicit_size"]:      # sizes the template itself sets are by design
                    self.add("FAIL", i, f"text is {ro['size']:g} pt, below the {MIN_PT} pt minimum: '{short(t, 40)}'", t, fix="shorten the text")
                if ro["color"] and ro["color"] not in PALETTE:
                    self.add("FAIL", i, f"text colour #{ro['color']} is not an IG colour: '{short(t, 40)}'", t)
                runs.append((t, ro["size"], "bold" if ro["bold"] else "regular", ro["spacing"]))
            for br in p_el.findall("a:br", NS):
                pass
            size = max((r[1] for r in runs), default=12)
            raw.append("".join(r[0] for r in runs))
            if not runs:
                ep = p_el.find("a:endParaRPr", NS)
                sz = int(ep.get("sz")) / 100 if ep is not None and ep.get("sz") else size
                runs = [("", sz, "regular", 0.0)]
            b_pt, b_pct = para["before"]; a_pt, a_pct = para["after"]
            paras.append({"runs": runs, "indent": max(para["marL"], para["marL"] + para["indent"]) if not para["bullet"] else para["marL"],
                          "line_spacing": para["line_spacing"], "exact_pts": para["exact"],
                          "before": b_pt + b_pct * size * M.LINE_HEIGHT, "after": a_pt + a_pct * size * M.LINE_HEIGHT})
        return paras, raw

    def text_checks(self, i, slide, shape, x, y, w, h, layout):
        txt = shape.text_frame.text
        bp = self.style.body_pr(shape)
        paras, raw = self.paragraphs(shape.text_frame._txBody, shape, slide, i, txt)
        self.words(i, " ".join(raw).strip() if len(raw) > 1 else txt, raw)
        iw = w - bp["lIns"] - bp["rIns"]
        ih = h - bp["tIns"] - bp["bIns"]
        if bp["wrap"] == "none":
            m = M.measure([{**p, "runs": p["runs"]} for p in paras], 1e6)
        else:
            m = M.measure(paras, iw)
        is_title = shape.is_placeholder and shape.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)
        content_title = is_title and layout in FOOTER_LAYOUTS - {"Navy Statement Left"}
        if content_title and m["lines"] > 1:
            self.add("FAIL", i, f"title wraps onto {m['lines']} lines: '{short(txt)}'", txt,
                     fix=f"shorten the title to about {int(len(txt) * iw / max(m['width'], 0.01) * 0.85)} characters")
        if m["split_words"]:
            self.add("FAIL", i, f"word '{m['split_words'][0]}' is too wide for its box and breaks across lines", txt,
                     fix="use a shorter word or less text")
        if bp["wrap"] == "none" and m["width"] > iw + EPS:
            self.add("FAIL", i, f"text '{short(txt, 40)}' is {m['width']:.2f} in wide but its box is {iw:.2f} in", txt, fix="shorten the text")
        over = m["height"] - ih
        if over > EPS and bp["autofit"] == "shrink":
            self.add("WARN", i, f"text is too big for its box; PowerPoint will shrink it: '{short(txt)}'", txt, fix="shorten the text")
            over = 0.0
        # where the text actually sits
        th = m["height"] if bp["autofit"] != "shrink" else min(m["height"], ih)
        if bp["anchor"] == "ctr":
            ty = y + bp["tIns"] + (ih - th) / 2
        elif bp["anchor"] == "b":
            ty = y + h - bp["bIns"] - th
        else:
            ty = y + bp["tIns"]
        tw = min(m["width"], max(iw, m["width"]))
        algn = None
        p0 = shape.text_frame._txBody.find("a:p/a:pPr", NS)
        if p0 is not None:
            algn = p0.get("algn")
        if algn == "ctr":
            tx = x + bp["lIns"] + (iw - tw) / 2
        elif algn == "r":
            tx = x + w - bp["rIns"] - tw
        else:
            tx = x + bp["lIns"]
        if layout in FOOTER_LAYOUTS and not shape.is_placeholder and ty + th > BODY_BOTTOM + EPS:
            self.add("FAIL", i, f"text runs into the footer: '{short(txt)}'", txt, fix=self.cut_fix(txt, ty + th - BODY_BOTTOM, th))
        if content_title and m["lines"] == 1:
            size = max((r[1] for p in paras for r in p["runs"]), default=0)
            if size and size < 32:
                self.add("WARN", i, f"title shrank to {size:g} pt to fit one line (other titles are up to 40 pt): '{short(txt)}'", txt,
                         fix="shorten the title to 45 characters or fewer")
        box = Box(tx, ty, tw, th, "text", shape, txt)
        box.over = max(0.0, over)
        return box

    @staticmethod
    def cut_fix(txt, over, height):
        cut = max(5, int(len(txt) * over / max(height, 0.01)) + 5)
        return f"cut about {cut} characters (or move some of it to another slide)"

    def words(self, i, text, paras=None):
        for level, msg in ig_text.check_text(text, spelling=self.spelling):
            fix = None
            if "dash" in msg:
                fix = "make_deck.py fixes dashes automatically; or rewrite"
            elif "speaker notes" in msg:
                fix = "move this text to the slide's \"notes\" field (speaker notes)"
            elif msg.startswith("spelling"):
                fix = "correct the spelling"
            target = text
            if paras and len(paras) > 1:            # point at the paragraph (bullet) that has the problem
                key = re.findall(r"'([^']+)'", msg)
                for p in paras:
                    if (key and key[0] in p) or ("dash" in msg and re.search(r"[–—―]|--", p)):
                        target = p
                        break
            self.add(level, i, f"{msg}: '{short(target, 50)}'", target, fix)

    # ----- tables
    def table_checks(self, i, slide, gf):
        tbl = gf.table
        y = inches(gf.top)
        total = 0.0
        for r, row in enumerate(tbl.rows):
            need = inches(row.height)
            for c, cell in enumerate(row.cells):
                tc = cell._tc
                txt = cell.text_frame.text
                if not txt.strip():
                    continue
                self.colour_checks(i, tc.find("a:tcPr", NS), f"table cell '{short(txt, 30)}'")
                paras, raw = self.paragraphs(tc.find("a:txBody", NS), gf, slide, i, txt)
                self.words(i, txt)
                cw = inches(tbl.columns[c].width) - inches(cell.margin_left) - inches(cell.margin_right)
                m = M.measure(paras, cw)
                if m["split_words"]:
                    self.add("FAIL", i, f"table cell word '{m['split_words'][0]}' is too wide for its column", txt,
                             fix="widen the column (widths) or shorten the text")
                need = max(need, m["height"] + inches(cell.margin_top) + inches(cell.margin_bottom))
            total += need
        return y + total

    # ----- charts
    def chart_checks(self, i, gf):
        chart = gf.chart
        xml = chart._chartSpace
        fonts = {lat.get("typeface") for lat in xml.iter(f"{A}latin")}
        if not fonts or any(f and not f.startswith("Trenda IG Text") for f in fonts):
            self.add("FAIL", i, f"chart font is {', '.join(sorted(f for f in fonts if f)) or 'not set'}, not Trenda IG Text")
        self.colour_checks(i, xml, "chart")

    # ----- overlap and spacing
    def overlap_checks(self, i, boxes):
        texts = [b for b in boxes if b.kind == "text"]
        solids = [b for b in boxes if b.kind != "text"]
        seen, hit = set(), set()

        def why(t):
            return f"text overflows its box by {t.over:.2f} in and " if t.over > EPS else "text "
        for a_i, a in enumerate(texts):
            for b in texts[a_i + 1:]:
                if a.inter(b):
                    key = ("tt", a.text, b.text)
                    if key not in seen:
                        seen.add(key); hit |= {id(a), id(b)}
                        t = a if a.over >= b.over else b
                        o = b if t is a else a
                        self.add("FAIL", i, f"{why(t)}overlaps other text: '{short(t.text, 40)}' and '{short(o.text, 30)}'", t.text,
                                 fix=self.cut_fix(t.text, max(t.over, 0.1), t.h) if t.over > EPS else "shorten one of them")
            for s in solids:
                if s.shape is a.shape:
                    continue
                if a.inter(s) and not a.inside(s):
                    hit.add(id(a))
                    what = {"picture": "an icon or picture", "chart": "a chart", "table": "a table"}.get(s.kind, "the edge of a card or shape")
                    self.add("FAIL", i, f"{why(a)}crosses {what}: '{short(a.text)}'", a.text,
                             fix=self.cut_fix(a.text, max(a.over, 0.1), a.h))
        for a in texts:
            if a.over > EPS and id(a) not in hit:
                self.add("WARN", i, f"text is {a.over:.2f} in taller than its box but has room around it: '{short(a.text)}'", a.text,
                         fix="shorten it a little to be safe")
        for a_i, a in enumerate(solids):
            for b in solids[a_i + 1:]:
                if a.inter(b) and not a.inside(b) and not b.inside(a):
                    an = short(a.shape.name, 25); bn = short(b.shape.name, 25)
                    self.add("FAIL", i, f"shapes overlap: '{an}' and '{bn}'", fix="fewer items or less text on the slide")

    def spacing_checks(self, i, boxes):
        cards = [b for b in boxes if b.kind == "shape" and b.w > 1.0 and b.h > 0.8]
        for a_i, a in enumerate(cards):
            for b in cards[a_i + 1:]:
                if a.inside(b) or b.inside(a):
                    continue
                same_row = abs(a.y0 - b.y0) < 0.05
                gap = max(b.x0 - a.x1, a.x0 - b.x1) if same_row else max(b.y0 - a.y1, a.y0 - b.y1)
                if 0 <= gap < 0.12 and (same_row or abs(a.x0 - b.x0) < 0.05):
                    self.add("WARN", i, f"cards are only {gap:.2f} in apart")
        texts = [b for b in boxes if b.kind == "text"]
        for a_i, a in enumerate(texts):
            for b in texts[a_i + 1:]:
                if min(a.x1, b.x1) - max(a.x0, b.x0) > 0.2:            # one above the other
                    gap = max(b.y0 - a.y1, a.y0 - b.y1)
                    if 0 <= gap < 0.04 and not a.inter(b):
                        upper = a if a.y0 < b.y0 else b
                        self.add("WARN", i, f"text blocks nearly touch ({gap:.2f} in apart): '{short(upper.text, 40)}'", upper.text,
                                 fix="shorten it so it stays on fewer lines")
        for t in texts:
            for c in cards:
                if t.inside(c):
                    pad = min(t.x0 - c.x0, c.x1 - t.x1, t.y0 - c.y0, c.y1 - t.y1)
                    if pad < 0.04:
                        self.add("FAIL", i, f"text touches the edge of its card ({max(pad, 0):.2f} in): '{short(t.text, 40)}'", t.text,
                                 fix=self.cut_fix(t.text, 0.1 + max(t.over, 0), t.h))
                    elif pad < 0.08:
                        self.add("WARN", i, f"text sits {pad:.2f} in from the edge of its card: '{short(t.text, 40)}'", t.text)

    def run(self):
        self.deck_checks()
        for i, slide in enumerate(self.prs.slides, 1):
            self.slide_checks(i, slide)
        if self.spelling and not ig_text.spelling_available():
            self.r.add("FAIL", 0, f"the bundled spell checker could not load: {ig_text.spell_error}",
                       fix="reinstall the skill so scripts/spellchecker and assets/spell-en.json are complete")
        seen, items = set(), []
        for it in self.r.items:
            k = (it["level"], it["slide"], it["message"])
            if k not in seen:
                seen.add(k); items.append(it)
        self.r.items = items
        return self.r


def validate(path, spec=None, words=None, spelling=True):
    return Validator(path, spec, words, spelling).run()


def print_report(report, n_slides, out=sys.stdout):
    fails, warns = report.fails(), [i for i in report.items if i["level"] == "WARN"]
    for it in fails + warns:
        where = f"slide {it['slide']}" if it["slide"] else "deck"
        print(f"{it['level']}  {where}: {it['message']}", file=out)
        if it["fix"]:
            print(f"      fix: {it['fix']}", file=out)
    if fails:
        print(f"\nFAIL: {len(fails)} problem(s), {len(warns)} warning(s). Fix the spec and rebuild; do not deliver this deck.", file=out)
    else:
        print(f"\nPASS: {n_slides} slides on the IG template, fonts, colours, fit, overlap, dashes and spelling checked"
              + (f" ({len(warns)} warning(s) to review)." if warns else "."), file=out)


def find_word_lists(*dirs):
    out = []
    for d in dirs:
        if d:
            for name in ("igppt-words.txt", ".igppt-words.txt"):
                p = Path(d) / name
                if p.is_file() and p not in out:
                    out.append(p)
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        raise SystemExit(__doc__)

    def opt(name):
        if name in args:
            k = args.index(name); v = args[k + 1]; del args[k:k + 2]; return v
        return None
    spec_path, words, as_json = opt("--spec"), opt("--words"), "--json" in args
    args = [a for a in args if not a.startswith("--")]
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8")) if spec_path else None
    lists = ([Path(words)] if words else []) + find_word_lists(Path(spec_path).parent if spec_path else None, Path.cwd())
    v = Validator(args[0], spec, lists)
    rep = v.run()
    if as_json:
        print(json.dumps({"pass": not rep.fails(), "problems": rep.items}, indent=1))
    else:
        print_report(rep, len(v.prs.slides))
    sys.exit(1 if rep.fails() else 0)


if __name__ == "__main__":
    main()
