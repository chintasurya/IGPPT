"""IGPPT in one command: what an agent runs, from the first message of a chat to the delivered deck.

    python igppt.py start                         once per chat: checks set-up, loads lessons, prints the exact commands
    python igppt.py build deck.json "Name.pptx"   build + validate + check lessons; saves only on PASS, with a check report
    python igppt.py verify "Name.pptx"            was this deck built and validated by IGPPT? validates it again now

`build` writes two files on PASS: the deck and "<Name> - IGPPT check.txt" (the validation report). A deck delivered
without that report was not validated. Exit codes: 0 PASS, 1 FAIL, 2 cannot run.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent


def work_dir():
    d = Path(os.environ.get("IGPPT_DATA", "/mnt/data"))
    return d if d.is_dir() and os.access(d, os.W_OK) else Path.cwd()


def run(script, *args):
    return subprocess.run([sys.executable, str(HERE / script), *map(str, args)]).returncode


def start():
    ok = True
    print(f"IGPPT skill: {SKILL}")
    print(f"Python {sys.version.split()[0]}")
    try:
        import pptx  # noqa: F401
        print("python-pptx: installed")
    except ImportError:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "python-pptx"])
        try:
            import pptx  # noqa: F401,F811
            print("python-pptx: installed now")
        except ImportError:
            ok = False
            print("python-pptx: MISSING and could not be installed. Decks cannot be built here: tell the user and give "
                  "the JSON spec instead. Do not make slides another way.")
    tpl = SKILL / "assets" / "ig-template.pptx"
    print("IG template: " + ("found" if tpl.is_file() else "MISSING (re-upload the igppt skill)"))
    ok = ok and tpl.is_file()
    wd = work_dir()
    print(f"Work folder: {wd}\n")
    run("learn.py", "start")
    me = HERE / "igppt.py"
    print(f"""
{'READY' if ok else 'NOT READY'}. Use exactly these commands in this chat:
  build:   python {me} build {wd / 'deck.json'} "{wd / '<Name>.pptx'}"
  verify:  python {me} verify "{wd / '<Name>.pptx'}"
  lesson:  python {HERE / 'learn.py'} add --kind ... (see SKILL.md, "Learning from feedback")
Follow every lesson listed above. Read SKILL.md, references/deck-recipes.md and references/spec-format.md before
the first deck. A deck is finished only when build prints SAVED; deliver the .pptx and its "IGPPT check.txt" report.""")
    return 0 if ok else 2


def build(spec, out):
    return run("make_deck.py", spec, out)


def verify(path):
    from pptx import Presentation
    p = Path(path)
    if not p.is_file():
        print(f"Not found: {p}"); return 2
    props = Presentation(str(p)).core_properties
    built = props.content_status == "Built with IGPPT"
    stamp = props.comments or ""
    print(f"Built by IGPPT: {'yes' if built else 'NO'}")
    print(f"Validation stamp: {stamp if stamp.startswith('IGPPT') else 'none (this deck was not saved by igppt.py build / make_deck.py)'}")
    report = p.with_name(p.stem + " - IGPPT check.txt")
    print(f"Check report: {'found, ' + report.name if report.is_file() else 'not found'}")
    print("Validating the deck again now:\n")
    code = run("validate.py", p)
    return code if built else 1


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    if a[0] == "start":
        sys.exit(start())
    if a[0] == "build" and len(a) >= 3:
        sys.exit(build(a[1], a[2]))
    if a[0] == "verify" and len(a) >= 2:
        sys.exit(verify(a[1]))
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
