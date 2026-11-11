"""Make an Insight Global deck from a JSON spec: check, fix, build, validate, and only then save it.

    python make_deck.py deck.json out.pptx [--theme dark|light] [--no-fix] [--preview previews/]

This is the one command to use. It:
  1. checks the spec (valid JSON, known slide types, required fields),
  2. fixes mechanical text problems in the spec itself (em and en dashes, double spaces) and saves the spec,
  3. builds a draft on the IG template with build_deck.py,
  4. validates the draft with validate.py (template, fonts, colours, overflow, overlap, spacing, dashes, spelling),
  5. saves out.pptx ONLY if everything passes. On FAIL nothing is saved: each problem names the spec field
     to change. Change the spec and run the same command again.

Exit code 0 = PASS (deck saved), 1 = FAIL (deck not saved), 2 = the spec could not be read.
Words the spell check does not know (client or product names) go in igppt-words.txt next to the spec.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_deck  # noqa: E402
import ig_text  # noqa: E402
import validate as V  # noqa: E402

TEXT_SKIP = {"type", "color", "icon", "theme", "background", "image", "style", "number_format"}
CONTENT = {"bullets", "cards", "stats", "process", "timeline", "table", "chart", "comparison", "image", "team"}
REQUIRED = {"title": ["title"], "section": ["title"], "statement": ["text"], "quote": ["text"], "agenda": ["items"],
            "bullets": ["title", "bullets"], "cards": ["title", "cards"], "stats": ["title", "stats"],
            "process": ["title", "steps"], "timeline": ["title", "milestones"], "table": ["title", "rows"],
            "chart": ["title", "chart"], "comparison": ["title", "left", "right"], "image": ["title", "image"],
            "team": ["title", "members"], "closing": []}


def fix_spec(node, path="", changes=None):
    """Apply ig_text.fix_text to every text field. Returns (new_node, [(path, change)])."""
    changes = [] if changes is None else changes
    if isinstance(node, dict):
        return {k: (v if k in TEXT_SKIP else fix_spec(v, f"{path}.{k}" if path else k, changes)[0]) for k, v in node.items()}, changes
    if isinstance(node, list):
        return [fix_spec(v, f"{path}[{i}]", changes)[0] for i, v in enumerate(node)], changes
    if isinstance(node, str):
        new, ch = ig_text.fix_text(node)
        for c in ch:
            changes.append((path, f"{c}: '{V.short(node, 50)}' -> '{V.short(new, 50)}'"))
        return new, changes
    return node, changes


def check_spec(spec):
    """Structural problems that would make a wrong or empty deck. Returns [(level, slide, message)]."""
    out = []
    slides = spec.get("slides") if isinstance(spec, dict) else None
    if not isinstance(slides, list) or not slides:
        return [("FAIL", 0, "the spec needs a non-empty \"slides\" list")]
    if spec.get("theme", "dark") not in ("dark", "light"):
        out.append(("FAIL", 0, f"theme must be dark or light, not '{spec.get('theme')}'"))
    for i, s in enumerate(slides, 1):
        if not isinstance(s, dict):
            out.append(("FAIL", i, "each slide must be a JSON object")); continue
        kind = s.get("type")
        if kind not in build_deck.TYPES:
            out.append(("FAIL", i, f"unknown slide type '{kind}' (types: {', '.join(build_deck.TYPES)})")); continue
        for field in REQUIRED.get(kind, []):
            if not s.get(field):
                out.append(("FAIL", i, f"{kind} slide needs \"{field}\" (slides[{i - 1}].{field})"))
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if len(args) < 2 or "-h" in args or "--help" in args:
        raise SystemExit(__doc__)

    def opt(name):
        if name in args:
            k = args.index(name); v = args[k + 1]; del args[k:k + 2]; return v
        return None
    theme, preview = opt("--theme"), opt("--preview")
    no_fix = "--no-fix" in args
    args = [a for a in args if not a.startswith("--")]
    spec_path, out = Path(args[0]), Path(args[1])
    if out.suffix.lower() != ".pptx":
        out = out.with_suffix(".pptx")

    # 1. read the spec
    try:
        raw = spec_path.read_text(encoding="utf-8-sig")
        spec = json.loads(raw)
    except FileNotFoundError:
        print(f"FAIL: spec not found: {spec_path}"); sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"FAIL: {spec_path} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}"); sys.exit(2)

    # 2. fix mechanical text problems in the spec and save it, so the spec and the deck agree
    if not no_fix:
        spec, changes = fix_spec(spec)
        if changes:
            spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Fixed {len(changes)} text problem(s) in {spec_path.name}:")
            for p, c in changes:
                print(f"  {p}: {c}")
    problems = check_spec(spec)
    if any(level == "FAIL" for level, _, _ in problems):
        for level, i, msg in problems:
            print(f"{level}  {'slide ' + str(i) if i else 'spec'}: {msg}")
        print("\nFAIL: fix the spec and run this command again. No deck was saved.")
        sys.exit(1)

    # 3. build a draft
    draft = out.with_name(f".{out.stem}.igppt-draft.pptx")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        build_deck.build(spec, draft, base=spec_path.resolve().parent, theme=theme)
    except SystemExit as e:
        print(f"FAIL: {e}"); sys.exit(1)

    # 4. validate the draft
    lists = V.find_word_lists(spec_path.resolve().parent, Path.cwd())
    report = V.validate(draft, spec, lists)
    for level, i, msg in problems:
        report.add(level, i, msg)
    for i, msg, fatal in build_deck.WARNINGS:
        report.add("FAIL" if fatal else "WARN", i, msg, fix=f"change slides[{i - 1}]")
    n = len(spec["slides"])
    V.print_report(report, n)

    # 5. save only on PASS
    if report.fails():
        draft.unlink(missing_ok=True)
        if out.exists():
            try:
                stale = V.Presentation(str(out)).core_properties.content_status == V.MARKER
            except Exception:
                stale = False
            if stale:
                out.unlink()
                print(f"Removed the older {out.name} so an out-of-date deck cannot be delivered by mistake.")
        print(f"NOT SAVED: {out}. Change {spec_path.name} as listed above and run the same command again.")
        sys.exit(1)
    os.replace(draft, out)
    print(f"SAVED: {out} ({n} slides)")
    if preview:
        import subprocess
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("render_preview.py")), str(out), preview])
        if r.returncode == 0:
            print(f"Previews in {preview}: look at every slide before delivering.")
    sys.exit(0)


if __name__ == "__main__":
    main()
