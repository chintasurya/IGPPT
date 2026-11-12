"""IGPPT lessons: turn feedback into rules that every future deck is checked against.

    python learn.py list                                   show every lesson in force
    python learn.py add --kind <kind> [options] --mistake "..." --fix "..." --feedback "user's words" [--spec deck.json]
    python learn.py test deck.json                         check a spec against the lessons (exit 1 on FAIL)
    python learn.py remove <id>

The model itself cannot be retrained, so a lesson is a written rule. make_deck.py refuses to save a deck that
breaks a FAIL lesson, so a mistake that has become a lesson cannot reach the user again.

Kinds (checked automatically):
  banned_text     --pattern REGEX --scope title|subtitle|body|note|notes|any   text that must not appear
                  (patterns ignore case unless you add --match-case)
  required_text   --pattern REGEX --scope ...                                    text that must appear somewhere in the deck
  max_length      --field title|subtitle|text|... --max N                        longest allowed value of a field
  max_items       --slide-type bullets|cards|... --field bullets|cards|... --max N
  first_slide     --slide-type title          the deck must start with this slide type
  last_slide      --slide-type closing        the deck must end with this slide type
  forbidden_type  --slide-type statement      this slide type must not be used
Kind not checkable by code:
  guidance        --text "..."                read before writing every deck; not enforced, so prefer a checked kind

Where lessons live (all are loaded and combined):
  <skill>/assets/lessons.json          lessons shipped with the skill (permanent, for everyone)
  /mnt/data/igppt-lessons.json         lessons learned in this chat (Microsoft 365 Copilot, ChatGPT)
  ./igppt-lessons.json                 lessons for this project (VS Code, Claude Code), next to the spec or here
  $IGPPT_LESSONS                       any other file
New lessons are saved to the first writable of: $IGPPT_LESSONS, /mnt/data/igppt-lessons.json, ./igppt-lessons.json.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BUNDLED = SKILL / "assets" / "lessons.json"
KINDS = {"banned_text", "required_text", "max_length", "max_items", "first_slide", "last_slide", "forbidden_type", "guidance"}
SCOPES = {"title", "subtitle", "body", "note", "notes", "any"}
SKIP_KEYS = {"type", "color", "icon", "theme", "background", "image", "style", "highlight", "grid", "widths", "number_format"}


def lesson_files(spec_dir=None):
    files = [BUNDLED]
    env = os.environ.get("IGPPT_LESSONS")
    if env:
        files.append(Path(env))
    files.append(Path("/mnt/data/igppt-lessons.json"))
    if spec_dir:
        files.append(Path(spec_dir) / "igppt-lessons.json")
    files.append(Path.cwd() / "igppt-lessons.json")
    out = []
    for f in files:
        try:
            r = f.resolve()
        except OSError:
            continue
        if r not in out:
            out.append(r)
    return out


def save_target():
    env = os.environ.get("IGPPT_LESSONS")
    if env:
        return Path(env)
    if Path("/mnt/data").is_dir() and os.access("/mnt/data", os.W_OK):
        return Path("/mnt/data/igppt-lessons.json")
    return Path.cwd() / "igppt-lessons.json"


def read_file(f):
    try:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data.get("lessons", []) if isinstance(data, dict) else data
    return [dict(x, _file=str(f)) for x in items if isinstance(x, dict)]


def signature(l):
    return (l.get("kind"), l.get("pattern"), l.get("scope"), l.get("field"), l.get("slide_type"), l.get("max"), l.get("text"),
            bool(l.get("match_case")))


def load(spec_dir=None):
    seen, out = set(), []
    for f in lesson_files(spec_dir):
        if f.is_file():
            for l in read_file(f):
                if signature(l) not in seen:
                    seen.add(signature(l)); out.append(l)
    return out


# ---------------------------------------------------------------- checking
def leaves(node, path="", key=""):
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in SKIP_KEYS:
                yield from leaves(v, f"{path}.{k}" if path else k, k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from leaves(v, f"{path}[{i}]", key)
    elif isinstance(node, str):
        yield path, key, node


def scope_of(key):
    return key if key in ("title", "subtitle", "note", "notes") else "body"


def in_scope(lesson_scope, key):
    s = scope_of(key)
    return lesson_scope == s or (lesson_scope == "any" and s != "notes")


def check(spec, lessons):
    """[(level, slide number or 0, message)] for every lesson the spec breaks."""
    out = []
    slides = spec.get("slides", []) if isinstance(spec, dict) else []
    for l in lessons:
        kind, level = l.get("kind"), l.get("level", "FAIL")
        tag = f"lesson {l.get('id', '?')}: {l.get('mistake', '')}".rstrip(": ")
        fix = l.get("fix", "")
        try:
            rx = re.compile(l["pattern"], 0 if l.get("match_case") else re.I) if l.get("pattern") else None
        except re.error:
            continue
        if kind == "banned_text":
            for i, s in enumerate(slides, 1):
                for path, key, text in leaves(s, f"slides[{i - 1}]"):
                    if in_scope(l.get("scope", "any"), key) and rx and rx.search(text):
                        out.append((level, i, f"{tag} ('{rx.search(text).group(0)}' in {path}). Fix: {fix}"))
        elif kind == "required_text":
            hit = any(rx and rx.search(t) for s in slides for _, k, t in leaves(s) if in_scope(l.get("scope", "any"), k))
            if not hit:
                out.append((level, 0, f"{tag} (not found in the deck). Fix: {fix}"))
        elif kind == "max_length":
            for i, s in enumerate(slides, 1):
                for path, key, text in leaves(s, f"slides[{i - 1}]"):
                    if key == l.get("field") and len(text) > int(l["max"]):
                        out.append((level, i, f"{tag} ({path} is {len(text)} characters, limit {l['max']}). Fix: {fix}"))
        elif kind == "max_items":
            for i, s in enumerate(slides, 1):
                if s.get("type") == l.get("slide_type") and len(s.get(l.get("field"), []) or []) > int(l["max"]):
                    out.append((level, i, f"{tag} ({len(s[l['field']])} {l['field']}, limit {l['max']}). Fix: {fix}"))
        elif kind in ("first_slide", "last_slide") and slides:
            s = slides[0] if kind == "first_slide" else slides[-1]
            if s.get("type") != l.get("slide_type"):
                out.append((level, 1 if kind == "first_slide" else len(slides),
                            f"{tag} (deck {'starts' if kind == 'first_slide' else 'ends'} with '{s.get('type')}'). Fix: {fix}"))
        elif kind == "forbidden_type":
            for i, s in enumerate(slides, 1):
                if s.get("type") == l.get("slide_type"):
                    out.append((level, i, f"{tag} (slide type '{s['type']}'). Fix: {fix}"))
    return out


# ---------------------------------------------------------------- command line
def opt(args, name, default=None):
    if name in args:
        k = args.index(name)
        v = args[k + 1] if k + 1 < len(args) else ""
        del args[k:k + 2]
        return v
    return default


def cmd_list(args):
    lessons = load(Path.cwd())
    if not lessons:
        print("No lessons yet."); return 0
    for l in lessons:
        what = {"banned_text": f"never '{l.get('pattern')}' in {l.get('scope', 'any')}",
                "required_text": f"always '{l.get('pattern')}' in {l.get('scope', 'any')}",
                "max_length": f"{l.get('field')} at most {l.get('max')} characters",
                "max_items": f"{l.get('slide_type')}.{l.get('field')} at most {l.get('max')}",
                "first_slide": f"start with a {l.get('slide_type')} slide", "last_slide": f"end with a {l.get('slide_type')} slide",
                "forbidden_type": f"never use a {l.get('slide_type')} slide",
                "guidance": f"READ: {l.get('text')}"}.get(l.get("kind"), l.get("kind"))
        print(f"{l.get('id', '?'):<14} {l.get('level', 'FAIL'):<5} {what}")
        if l.get("mistake") and l.get("kind") != "guidance":
            print(f"{'':20}mistake: {l['mistake']}  fix: {l.get('fix', '')}")
        print(f"{'':20}from {Path(l['_file']).name}")
    return 0


def cmd_add(args):
    kind = opt(args, "--kind")
    if kind not in KINDS:
        print(f"--kind must be one of: {', '.join(sorted(KINDS))}"); return 2
    l = {"kind": kind, "added": dt.date.today().isoformat()}
    for flag, key in (("--pattern", "pattern"), ("--scope", "scope"), ("--field", "field"), ("--slide-type", "slide_type"),
                      ("--mistake", "mistake"), ("--fix", "fix"), ("--feedback", "feedback"), ("--text", "text"), ("--level", "level")):
        v = opt(args, flag)
        if v:
            l[key] = v
    if "--match-case" in args:
        args.remove("--match-case"); l["match_case"] = True
    mx = opt(args, "--max")
    if mx:
        l["max"] = int(mx)
    spec_for_test = opt(args, "--spec")
    target = Path(opt(args, "--save") or save_target())
    need = {"banned_text": ("pattern", "mistake", "fix"), "required_text": ("pattern", "mistake", "fix"),
            "max_length": ("field", "max", "mistake", "fix"), "max_items": ("slide_type", "field", "max", "mistake", "fix"),
            "first_slide": ("slide_type", "mistake", "fix"), "last_slide": ("slide_type", "mistake", "fix"),
            "forbidden_type": ("slide_type", "mistake", "fix"), "guidance": ("text",)}[kind]
    missing = [k for k in need if k not in l]
    if missing:
        print("missing: " + ", ".join("--" + k.replace("_", "-") for k in missing)); return 2
    if l.get("pattern"):
        try:
            re.compile(l["pattern"], re.I)
        except re.error as e:
            print(f"--pattern is not a valid regular expression: {e}"); return 2
    if l.get("scope", "any") not in SCOPES:
        print(f"--scope must be one of: {', '.join(sorted(SCOPES))}"); return 2
    if l.get("level", "FAIL") not in ("FAIL", "WARN"):
        print("--level must be FAIL or WARN"); return 2
    existing = load(Path.cwd())
    if any(signature(x) == signature(l) for x in existing):
        print("This lesson already exists; nothing added."); return 0
    try:
        data = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {"lessons": []}
    except json.JSONDecodeError:
        data = {"lessons": []}
    items = data["lessons"] if isinstance(data, dict) else data
    l["id"] = f"L{dt.date.today():%Y%m%d}-{len(existing) + 1:02d}"
    items.append(l)
    # a rule that rejects the bundled sample deck is probably too broad
    sample = SKILL / "examples" / "sample-deck.json"
    if sample.is_file() and kind != "guidance":
        hits = check(json.loads(sample.read_text(encoding="utf-8")), [l])
        if hits:
            print(f"Note: this lesson also rejects the bundled sample deck ({hits[0][2][:120]}). Check it is not too broad.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"lessons": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"LEARNED {l['id']} ({kind}) saved to {target}")
    if spec_for_test and kind != "guidance":
        spec = json.loads(Path(spec_for_test).read_text(encoding="utf-8"))
        caught = check(spec, [l])
        print(("It catches the reported mistake in " if caught else "WARNING: it does NOT catch anything in ")
              + f"{spec_for_test}" + (f": {caught[0][2][:140]}" if caught else "; make the rule match the mistake."))
    if str(target).startswith("/mnt/data"):
        print("This lesson applies for the rest of this chat. To keep it for every chat, give the user "
              f"{target.name} to download and send to the IGPPT owner (or attach it to the next chat).")
    return 0


def cmd_test(args):
    spec_path = Path(args[0])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    probs = check(spec, load(spec_path.resolve().parent))
    for level, i, msg in probs:
        print(f"{level}  {'slide ' + str(i) if i else 'deck'}: {msg}")
    fails = [p for p in probs if p[0] == "FAIL"]
    print(f"\n{'FAIL' if fails else 'PASS'}: {len(fails)} lesson(s) broken, {len(probs) - len(fails)} warning(s).")
    return 1 if fails else 0


def cmd_remove(args):
    lid = args[0]
    for f in lesson_files(Path.cwd()):
        if f.is_file() and f != BUNDLED.resolve():
            data = json.loads(f.read_text(encoding="utf-8"))
            items = data["lessons"] if isinstance(data, dict) else data
            keep = [x for x in items if x.get("id") != lid]
            if len(keep) != len(items):
                f.write_text(json.dumps({"lessons": keep}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f"Removed {lid} from {f}"); return 0
    print(f"{lid} not found in a writable lessons file (lessons shipped with the skill are removed by its owner).")
    return 1


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    cmd, rest = args[0], args[1:]
    fn = {"list": cmd_list, "add": cmd_add, "test": cmd_test, "remove": cmd_remove}.get(cmd)
    if not fn or (cmd in ("test", "remove") and not rest):
        raise SystemExit(__doc__)
    sys.exit(fn(rest))


if __name__ == "__main__":
    main()
