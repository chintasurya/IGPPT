"""Regression tests for IGPPT: the builder makes clean decks and the validator catches broken ones.

    python tools/test_igppt.py

Run after any change to igppt/scripts. Needs python-pptx; no other packages.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "igppt" / "scripts"
SAMPLE = ROOT / "igppt" / "examples" / "sample-deck.json"
sys.path.insert(0, str(SCRIPTS))

PY = sys.executable
TMP = Path(tempfile.mkdtemp(prefix="igppt-test-"))
results = []


def run(*args, cwd=None):
    r = subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=cwd, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def make(spec, name, extra=()):
    path = TMP / f"{name}.json"
    path.write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
    code, out = run(SCRIPTS / "make_deck.py", path, TMP / f"{name}.pptx", *extra)
    return code, out, path


def test(name):
    def wrap(fn):
        try:
            fn()
            results.append((True, name, ""))
        except AssertionError as e:
            results.append((False, name, str(e)))
        return fn
    return wrap


def expect(cond, msg, out=""):
    assert cond, f"{msg}\n----- output -----\n{out[-1500:]}"


def deck(*slides, **top):
    return {"theme": top.get("theme", "dark"), "slides": [{"type": "title", "title": "Test Deck", "subtitle": "Checks", "date": "Nov 2026"},
                                                          *slides, {"type": "closing"}]}


# ---------------------------------------------------------------- clean decks pass
@test("sample deck builds and passes (dark)")
def _():
    code, out = run(SCRIPTS / "make_deck.py", SAMPLE, TMP / "sample.pptx", "--no-fix")
    expect(code == 0 and "SAVED" in out and (TMP / "sample.pptx").exists(), "sample should pass", out)


@test("sample deck builds and passes (light)")
def _():
    code, out = run(SCRIPTS / "make_deck.py", SAMPLE, TMP / "sample-light.pptx", "--theme", "light", "--no-fix")
    expect(code == 0, "light sample should pass", out)


@test("every slide type passes with ordinary content")
def _():
    spec = json.loads(SAMPLE.read_text(encoding="utf-8"))
    kinds = {s["type"] for s in spec["slides"]}
    expect({"title", "agenda", "stats", "cards", "chart", "process", "comparison", "timeline", "table", "bullets", "team",
            "statement", "closing"} <= kinds, "sample should cover the main slide types")


# ---------------------------------------------------------------- text rules
@test("em and en dashes are fixed in the spec automatically")
def _():
    code, out, path = make(deck({"type": "bullets", "title": "Where We Are", "bullets": ["On track — two risks remain", "Q1–Q2 plan agreed"]}), "dash")
    fixed = path.read_text(encoding="utf-8")
    expect(code == 0, "deck should pass after the automatic fix", out)
    expect("—" not in fixed and "–" not in fixed, "spec should no longer contain dashes", fixed)
    expect("Q1-Q2" in fixed and "On track, two risks remain" in fixed, "dashes should become a hyphen in ranges and a comma between clauses", fixed)


@test("em dashes fail when auto-fix is off")
def _():
    code, out, _ = make(deck({"type": "bullets", "title": "Where We Are", "bullets": ["On track — two risks remain"]}), "dash-nofix", ["--no-fix"])
    expect(code == 1 and "em dash" in out, "em dash must fail", out)


@test("misspelling fails and names the spec field")
def _():
    code, out, _ = make(deck({"type": "stats", "title": "Q3 at a Glance", "stats": [
        {"value": "98%", "label": "SLA attainment", "text": "Up from 95% in Q2."},
        {"value": "1,240", "label": "Tickets resolved", "text": "About 19 per buisness day."}]}), "spell")
    expect(code == 1 and "buisness" in out and "slides[1].stats[1].text" in out, "typo must fail with its spec path", out)


@test("unknown names warn, and igppt-words.txt clears them")
def _():
    spec = deck({"type": "team", "title": "Who to Contact", "members": [{"name": "Zorawar Okonkwo", "role": "Delivery Lead"}]})
    code, out, path = make(spec, "names")
    expect(code == 0 and "unknown word 'Zorawar'" in out, "unknown name should be a warning, not a failure", out)
    (TMP / "igppt-words.txt").write_text("Zorawar\nOkonkwo\n", encoding="utf-8")
    code, out, _ = make(spec, "names")
    (TMP / "igppt-words.txt").unlink()
    expect(code == 0 and "Zorawar" not in out, "word list should clear the warning", out)


@test("repeated words and leftover placeholder text fail")
def _():
    code, out, _ = make(deck({"type": "bullets", "title": "Next Steps", "bullets": ["Agree the the scope", "Lorem ipsum dolor"]}), "repeat")
    expect(code == 1 and "repeated word" in out and "lorem ipsum" in out.lower(), "both must fail", out)


@test("internal or presenter notes on a slide fail; speaker notes are fine")
def _():
    spec = deck({"type": "bullets", "title": "Where We Are", "bullets": ["On track"],
                 "note": "Audience: CISO and IT Director. Next step is scoping."})
    code, out, _ = make(spec, "internal")
    expect(code == 1 and "internal or presenter note" in out and "slides[1].note" in out, "on-slide audience note must fail", out)
    spec["slides"][1]["notes"] = spec["slides"][1].pop("note")
    code, out, _ = make(spec, "internal")
    expect(code == 0, "the same text in speaker notes must pass", out)


@test("common icon names map to the bundled icons")
def _():
    import build_deck
    expect(build_deck.resolve_icon(1, "people") == "users" and build_deck.resolve_icon(1, "gear") == "cogs"
           and build_deck.resolve_icon(1, "Security") == "shield" and build_deck.resolve_icon(1, "rockets") == "rocket",
           "aliases should resolve")
    code, out, _ = make(deck({"type": "process", "title": "How Work Flows", "steps": [
        {"title": "Staff", "text": "Place analysts.", "icon": "people"}, {"title": "Automate", "text": "Triage.", "icon": "gear"}]}), "icons")
    expect(code == 0 and "unknown icon" not in out, "aliased icons should build without warnings", out)


@test("a lesson learned from feedback stops the same mistake, then merges into the skill")
def _():
    import os
    lessons = TMP / "igppt-lessons.json"
    spec = deck({"type": "bullets", "title": "Staffing And Automation", "bullets": ["Six analysts in 30 days"]})
    path = TMP / "lesson.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    code, out = run(SCRIPTS / "learn.py", "add", "--kind", "banned_text", "--scope", "title", "--pattern", r"\bAnd\b",
                    "--match-case", "--mistake", "Title Case And", "--fix", "lower-case and", "--feedback", "test",
                    "--spec", path, "--save", lessons)
    expect(code == 0 and "It catches the reported mistake" in out, "lesson should be saved and catch the mistake", out)
    code, out = run(SCRIPTS / "make_deck.py", path, TMP / "lesson.pptx")
    expect(code == 1 and "lesson L" in out and not (TMP / "lesson.pptx").exists(), "the same mistake must now fail", out)
    spec["slides"][1]["title"] = "Staffing and Automation"
    path.write_text(json.dumps(spec), encoding="utf-8")
    code, out = run(SCRIPTS / "make_deck.py", path, TMP / "lesson.pptx")
    expect(code == 0, "the corrected deck must pass", out)
    for bad in (["--kind", "banned_text", "--pattern", "([", "--mistake", "x", "--fix", "y"], ["--kind", "nonsense"]):
        code, out = run(SCRIPTS / "learn.py", "add", *bad, "--save", TMP / "bad-lessons.json")
        expect(code == 2, "invalid lessons must be refused", out)
    bundled = ROOT / "igppt" / "assets" / "lessons.json"
    before = bundled.read_text(encoding="utf-8")
    try:
        code, out = run(ROOT / "tools" / "merge_lessons.py", lessons)
        expect(code == 0 and "Added 1 lesson" in out and "Title Case And" in bundled.read_text(encoding="utf-8"), "merge", out)
        lessons.unlink()
        code, out = run(SCRIPTS / "learn.py", "test", path)
        expect(code == 0, "merged lesson is now bundled and the fixed spec passes", out)
    finally:
        bundled.write_text(before, encoding="utf-8")
        lessons.unlink(missing_ok=True)


@test("lessons survive into a new chat through the instructions block, and a damaged block is rejected")
def _():
    import os
    chat1, chat2, chat3 = TMP / "chat1", TMP / "chat2", TMP / "chat3"
    for c in (chat1, chat2, chat3):
        c.mkdir()
    spec = deck({"type": "bullets", "title": "Staffing And Automation", "bullets": ["Six analysts in 30 days"]})
    path = TMP / "chat-spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    old = os.environ.get("IGPPT_DATA")
    try:
        os.environ["IGPPT_DATA"] = str(chat1)
        code, out = run(SCRIPTS / "learn.py", "add", "--kind", "banned_text", "--scope", "title", "--word", "And", "--match-case",
                        "--mistake", "Title Case And", "--fix", "lower-case and", "--spec", path, cwd=chat1)
        expect(code == 0 and "It catches" in out, "learn in chat 1", out)
        code, out = run(SCRIPTS / "learn.py", "export", cwd=chat1)
        block = out[out.index("<<<IGPPT-LESSONS"):out.index("IGPPT-LESSONS>>>") + len("IGPPT-LESSONS>>>")]
        expect("\\" not in block, "a --word lesson has no backslashes to mis-copy", block)
        os.environ["IGPPT_DATA"] = str(chat2)
        (chat2 / "igppt-lessons-block.txt").write_text("Instructions...\n" + block + "\n", encoding="utf-8")
        code, out = run(SCRIPTS / "learn.py", "start", "--url", (ROOT / "igppt" / "assets" / "lessons.json").as_uri(), cwd=chat2)
        expect(code == 0 and "Loaded 1 lesson" in out and "Shared lessons downloaded: 0" in out, "start loads the block and syncs", out)
        code, out = run(SCRIPTS / "make_deck.py", path, chat2 / "x.pptx", cwd=chat2)
        expect(code == 1 and "Title Case And" in out, "the lesson blocks the mistake in a new chat", out)
        os.environ["IGPPT_DATA"] = str(chat3)
        (chat3 / "igppt-lessons-block.txt").write_text(block.replace("lower-case", "lowercase"), encoding="utf-8")
        code, out = run(SCRIPTS / "learn.py", "start", "--url", "file:///no/such/file", cwd=chat3)
        expect("checksum does not match" in out and "Loaded 0 lesson" in out and "not downloaded" in out, "damaged block", out)
    finally:
        if old is None:
            os.environ.pop("IGPPT_DATA", None)
        else:
            os.environ["IGPPT_DATA"] = old


# ---------------------------------------------------------------- layout rules
LONG = ("Moved every release onto the automated pipeline, removed manual approvals, added smoke tests after each deploy, "
        "documented rollback for each service and trained the support team on the new runbook so they own incidents.")


@test("text that overflows into other text or past a card fails")
def _():
    code, out, _ = make(deck({"type": "stats", "title": "Q3 at a Glance", "note": "Source: ServiceNow and Jira, July to September 2026.",
                              "stats": [{"value": "98%", "label": "SLA attainment", "text": LONG * 2} for _ in range(4)]}), "overflow")
    expect(code == 1 and ("crosses" in out or "overlaps" in out), "overflow must fail", out)
    expect(not (TMP / "overflow.pptx").exists(), "no deck may be saved on FAIL", out)


@test("a word too wide for its box fails")
def _():
    steps = [{"title": "Request intake", "owner": "Business operations", "text": "Raised in ServiceNow.", "icon": "ticket"} for _ in range(6)]
    code, out, _ = make(deck({"type": "process", "title": "How Work Flows", "steps": steps}), "split")
    expect(code == 1 and "too wide" in out, "split word must fail", out)


@test("content the builder would drop fails")
def _():
    code, out, _ = make(deck({"type": "agenda", "items": [f"Item {k}" for k in range(1, 10)]}), "agenda")
    expect(code == 1 and "dropped" in out, "agenda over 7 items must fail", out)


@test("spec errors are reported before building")
def _():
    code, out, _ = make({"slides": [{"type": "slideshow", "title": "x"}]}, "badtype")
    expect(code == 1 and "unknown slide type" in out, "unknown type must fail", out)
    bad = TMP / "broken.json"
    bad.write_text('{"slides": [', encoding="utf-8")
    code, out = run(SCRIPTS / "make_deck.py", bad, TMP / "broken.pptx")
    expect(code == 2 and "not valid JSON" in out, "invalid JSON must exit 2", out)


@test("a stale deck is removed when a rebuild fails")
def _():
    good = deck({"type": "bullets", "title": "Where We Are", "bullets": ["On track"]})
    code, out, path = make(good, "stale")
    expect(code == 0 and (TMP / "stale.pptx").exists(), "first build should pass", out)
    good["slides"][1]["bullets"] = ["On track for the the release"]
    code, out, _ = make(good, "stale")
    expect(code == 1 and not (TMP / "stale.pptx").exists(), "older deck must be removed after a failed rebuild", out)


# ---------------------------------------------------------------- decks not made by IGPPT
@test("a plain python-pptx deck (how assistants go wrong) fails")
def _():
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt
    p = Presentation()
    s = p.slides.add_slide(p.slide_layouts[5])
    s.shapes.title.text = "Q3 Results"
    tb = s.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(1))
    r = tb.text_frame.paragraphs[0].add_run(); r.text = "Revenue grew"
    r.font.name = "Arial"; r.font.size = Pt(18); r.font.color.rgb = RGBColor(0x33, 0x66, 0x99)
    p.save(TMP / "plain.pptx")
    code, out = run(SCRIPTS / "validate.py", TMP / "plain.pptx")
    for must in ("not based on the IG template", "not built by the IGPPT scripts", "Arial", "#336699"):
        expect(code == 1 and must in out, f"plain deck must fail with '{must}'", out)


@test("custom ig_kit slides with overlapping cards or off-brand colours fail")
def _():
    from ig_kit import Deck
    d = Deck()
    d.title("Custom", "Test", "Nov 2026")
    c = d.slide("Overlapping Cards")
    c.card(0.6, 2.2, 5, 2)
    c.card(4.0, 3.0, 5, 2)
    c.text(0.9, 2.4, 4, 0.5, "Left card", size=16, color="123456")
    d.closing()
    d.save(TMP / "custom.pptx")
    code, out = run(SCRIPTS / "validate.py", TMP / "custom.pptx")
    expect(code == 1 and "shapes overlap" in out and "#123456" in out, "overlap and colour must fail", out)


@test("check_deck.py still works as an alias")
def _():
    code, out = run(SCRIPTS / "check_deck.py", TMP / "sample.pptx")
    expect(code == 0 and "PASS" in out, "alias should pass the sample", out)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for ok, name, why in results:
        print(("PASS  " if ok else "FAIL  ") + name)
        if not ok:
            print("      " + why.replace("\n", "\n      "))
    failed = sum(not ok for ok, _, _ in results)
    print(f"\n{len(results) - failed}/{len(results)} tests passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
