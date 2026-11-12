"""IGPPT lessons: turn feedback into rules that every future deck is checked against.

    python learn.py start                                  start of every chat: load shared lessons, then list them
    python learn.py list                                   show every lesson in force
    python learn.py add --kind <kind> [options] --mistake "..." --fix "..." --feedback "user's words" [--spec deck.json]
    python learn.py test deck.json                         check a spec against the lessons (exit 1 on FAIL)
    python learn.py export [--all]                         print the lessons as a block to paste into the agent's instructions
    python learn.py import <file> [...]                    load lessons from a JSON file or any text containing a block
    python learn.py sync [--url URL]                       download the shared lessons from GitHub (needs internet)
    python learn.py remove <id>

The model itself cannot be retrained, so a lesson is a written rule. make_deck.py refuses to save a deck that
breaks a FAIL lesson, so a mistake that has become a lesson cannot reach the user again.

Kinds (checked automatically):
  banned_text     --word WORD or --pattern REGEX, --scope title|subtitle|body|note|notes|any   text that must not appear
                  (--word matches a whole word or phrase and is safest; matching ignores case unless --match-case)
  required_text   --word / --pattern, --scope ...            text that must appear somewhere in the deck
  max_length      --field title|subtitle|text|... --max N                        longest allowed value of a field
  max_items       --slide-type bullets|cards|... --field bullets|cards|... --max N
  first_slide     --slide-type title          the deck must start with this slide type
  last_slide      --slide-type closing        the deck must end with this slide type
  forbidden_type  --slide-type statement      this slide type must not be used
Kind not checkable by code:
  guidance        --text "..."                read before writing every deck; not enforced, so prefer a checked kind

How lessons survive from one chat to the next (Microsoft 365 Copilot wipes the sandbox after each chat):
  1. Lessons block in the agent's instructions: after learning, `export` prints a block; the agent owner pastes it
     at the end of the instructions. At the start of each chat the agent writes that block to a file and `start`
     loads it. The block carries a count and checksum, so a copying mistake is detected.
  2. GitHub: `start` downloads igppt/assets/lessons.json from the repository when the sandbox has internet, so
     lessons merged there (tools/merge_lessons.py) reach every chat without re-uploading the skill.
  3. Files: an igppt-lessons.json (or any text file with a block) attached to the chat is loaded by `start`.
  4. The skill itself: assets/lessons.json, updated by the owner with tools/merge_lessons.py and a re-upload.

Where lessons are read from (all are combined): <skill>/assets/lessons.json, the data folder ($IGPPT_DATA,
default /mnt/data) igppt-lessons.json and igppt-lessons-shared.json, igppt-lessons.json next to the spec and in
the current folder, and $IGPPT_LESSONS. New lessons are saved to $IGPPT_LESSONS, else <data folder>/igppt-lessons.json
when it is writable, else ./igppt-lessons.json.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BUNDLED = SKILL / "assets" / "lessons.json"
DATA = Path(os.environ.get("IGPPT_DATA", "/mnt/data"))
SHARED_URL = "https://raw.githubusercontent.com/chintasurya/igppt/main/igppt/assets/lessons.json"
KEEP = ("id", "kind", "level", "word", "pattern", "match_case", "scope", "field", "slide_type", "max", "text", "mistake", "fix", "added")
BLOCK = re.compile(r"<<<IGPPT-LESSONS v1 count=(\d+) sum=([0-9a-f]{8})\s*(.*?)\s*IGPPT-LESSONS>>>", re.S)
KINDS = {"banned_text", "required_text", "max_length", "max_items", "first_slide", "last_slide", "forbidden_type", "guidance"}
SCOPES = {"title", "subtitle", "body", "note", "notes", "any"}
SKIP_KEYS = {"type", "color", "icon", "theme", "background", "image", "style", "highlight", "grid", "widths", "number_format"}


def lesson_files(spec_dir=None):
    files = [BUNDLED]
    env = os.environ.get("IGPPT_LESSONS")
    if env:
        files.append(Path(env))
    files += [DATA / "igppt-lessons.json", DATA / "igppt-lessons-shared.json"]
    if spec_dir:
        files.append(Path(spec_dir) / "igppt-lessons.json")
    files += [Path.cwd() / "igppt-lessons.json", Path.cwd() / "igppt-lessons-shared.json"]
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
    if DATA.is_dir() and os.access(DATA, os.W_OK):
        return DATA / "igppt-lessons.json"
    return Path.cwd() / "igppt-lessons.json"


def data_dir():
    return DATA if DATA.is_dir() and os.access(DATA, os.W_OK) else Path.cwd()


# ---------------------------------------------------------------- lessons block (for the agent's instructions)
def canonical(lessons):
    clean = [{k: l[k] for k in KEEP if k in l and l[k] not in (None, "", False)} for l in lessons]
    return clean, json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_block(lessons):
    clean, text = canonical(lessons)
    return f"<<<IGPPT-LESSONS v1 count={len(clean)} sum={hashlib.sha256(text.encode()).hexdigest()[:8]}\n{text}\nIGPPT-LESSONS>>>"


def parse_blocks(text):
    """[(lessons, problem or None)] for every lessons block in a piece of text."""
    out = []
    for m in BLOCK.finditer(text):
        count, total, body = int(m.group(1)), m.group(2), m.group(3)
        try:
            items = json.loads(body)
        except json.JSONDecodeError as e:
            out.append(([], f"the block is not valid JSON ({e.msg}); copy it again exactly")); continue
        _, canon = canonical(items)
        problem = None
        if len(items) != count:
            problem = f"the block says {count} lessons but contains {len(items)}; it was copied incompletely"
        elif hashlib.sha256(canon.encode()).hexdigest()[:8] != total:
            problem = "the checksum does not match; some text in the block was changed while copying"
        out.append((items, problem))
    return out


def valid(l):
    if l.get("kind") not in KINDS:
        return False
    try:
        if l.get("pattern"):
            re.compile(l["pattern"])
    except re.error:
        return False
    return True


def merge_into(target, lessons, origin):
    """Add lessons to a lessons file, skipping duplicates. Returns the number added."""
    have = read_file(target) if Path(target).is_file() else []
    seen = {signature(x) for x in have} | {signature(x) for x in read_file(BUNDLED)}
    new = []
    for l in lessons:
        if isinstance(l, dict) and valid(l) and signature(l) not in seen:
            seen.add(signature(l)); new.append({k: v for k, v in l.items() if k != "_file"})
    if new:
        items = [{k: v for k, v in x.items() if k != "_file"} for x in have] + [dict(l, origin=origin) for l in new]
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_text(json.dumps({"lessons": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(new)


def read_file(f):
    try:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data.get("lessons", []) if isinstance(data, dict) else data
    return [dict(x, _file=str(f)) for x in items if isinstance(x, dict)]


def signature(l):
    return (l.get("kind"), l.get("word"), l.get("pattern"), l.get("scope"), l.get("field"), l.get("slide_type"), l.get("max"), l.get("text"),
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
            pat = rf"\b{re.escape(l['word'])}\b" if l.get("word") else l.get("pattern")
            rx = re.compile(pat, 0 if l.get("match_case") else re.I) if pat else None
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
        m = l.get("word") or l.get("pattern")
        what = {"banned_text": f"never '{m}' in {l.get('scope', 'any')}",
                "required_text": f"always '{m}' in {l.get('scope', 'any')}",
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
    for flag, key in (("--word", "word"), ("--pattern", "pattern"), ("--scope", "scope"), ("--field", "field"), ("--slide-type", "slide_type"),
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
    if kind in ("banned_text", "required_text") and l.get("word"):
        l["pattern_from"] = "word"
    need = {"banned_text": ("text_match", "mistake", "fix"), "required_text": ("text_match", "mistake", "fix"),
            "max_length": ("field", "max", "mistake", "fix"), "max_items": ("slide_type", "field", "max", "mistake", "fix"),
            "first_slide": ("slide_type", "mistake", "fix"), "last_slide": ("slide_type", "mistake", "fix"),
            "forbidden_type": ("slide_type", "mistake", "fix"), "guidance": ("text",)}[kind]
    l.pop("pattern_from", None)
    if l.get("word") or l.get("pattern"):
        l["text_match"] = True
    missing = [("word or --pattern" if k == "text_match" else k) for k in need if k not in l]
    l.pop("text_match", None)
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
    print("Next: run `python learn.py export` and give the user the block it prints, so the agent owner can paste it "
          "into the agent's instructions and the lesson applies in every future chat.")
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


def cmd_export(args):
    lessons = load(Path.cwd())
    if "--all" not in args:
        bundled = {signature(x) for x in read_file(BUNDLED)}
        lessons = [l for l in lessons if signature(l) not in bundled]
    if not lessons:
        print("No lessons to export (lessons already in the skill are left out; add --all to include them)."); return 0
    block = make_block(lessons)
    out = data_dir() / "igppt-lessons-block.txt"
    out.write_text(block + "\n", encoding="utf-8")
    print(block)
    print(f"\n{len(lessons)} lesson(s), {len(block)} characters, also saved to {out}.")
    print("To keep these lessons in every chat: the agent owner opens the agent, Edit, Configure, Instructions, and "
          "replaces the old lessons block (from <<<IGPPT-LESSONS to IGPPT-LESSONS>>>) with this one, or adds it at the end.")
    return 0


def import_text(text, origin):
    """Load lessons from JSON or from blocks inside any text. Returns (added, problems)."""
    added, problems, found = 0, [], False
    for items, problem in parse_blocks(text):
        found = True
        if problem:
            problems.append(problem)
        else:
            added += merge_into(save_target(), items, origin)
    if not found:
        try:
            data = json.loads(text)
            items = data.get("lessons", []) if isinstance(data, dict) else data
            if isinstance(items, list):
                found = True
                added += merge_into(save_target(), items, origin)
        except json.JSONDecodeError:
            pass
    if not found:
        problems.append("no lessons block or lessons JSON found")
    return added, problems


def cmd_import(args):
    code = 0
    for f in args:
        try:
            text = Path(f).read_text(encoding="utf-8-sig", errors="replace")
        except OSError as e:
            print(f"could not read {f}: {e}"); code = 1; continue
        added, problems = import_text(text, Path(f).name)
        print(f"{f}: {added} new lesson(s) loaded" + "".join(f"\n  PROBLEM: {p}" for p in problems))
        code = code or (1 if problems else 0)
    return code


def cmd_sync(args):
    url = opt(args, "--url", SHARED_URL)
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # no internet in many sandboxes: say so and carry on
        print(f"Shared lessons not downloaded ({type(e).__name__}: {str(e)[:80]}); using the lessons in the skill and the instructions.")
        return 0
    items = [l for l in (data.get("lessons", []) if isinstance(data, dict) else data) if isinstance(l, dict) and valid(l)]
    target = data_dir() / "igppt-lessons-shared.json"
    target.write_text(json.dumps({"lessons": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Shared lessons downloaded: {len(items)} from {url}")
    return 0


def cmd_start(args):
    """Start of every chat: shared lessons from GitHub, then any lessons block or file in the data folder."""
    cmd_sync(list(args))
    own = {"igppt-lessons.json", "igppt-lessons-shared.json"}
    for folder in dict.fromkeys([data_dir(), Path.cwd()]):
        for f in sorted(folder.glob("*")):
            if not f.is_file() or f.name in own or f.suffix.lower() not in (".txt", ".json", ".md"):
                continue
            if f.stat().st_size > 2_000_000:
                continue
            text = f.read_text(encoding="utf-8-sig", errors="replace")
            if "IGPPT-LESSONS" in text or (f.name.startswith("igppt-lessons") and f.suffix == ".json"):
                added, problems = import_text(text, f.name)
                print(f"Loaded {added} lesson(s) from {f.name}" + "".join(f"\n  PROBLEM: {p}" for p in problems))
    print()
    return cmd_list([])


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
    fn = {"list": cmd_list, "add": cmd_add, "test": cmd_test, "remove": cmd_remove, "export": cmd_export,
          "import": cmd_import, "sync": cmd_sync, "start": cmd_start}.get(cmd)
    if not fn or (cmd in ("test", "remove", "import") and not rest):
        raise SystemExit(__doc__)
    sys.exit(fn(rest))


if __name__ == "__main__":
    main()
