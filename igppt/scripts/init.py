"""One-time IGPPT set-up for a project. Run from the project's root folder:

    python <skill>/scripts/init.py            e.g. python .agents/skills/igppt/scripts/init.py

It:
  1. checks Python and installs python-pptx if missing,
  2. checks the bundled IG template,
  3. writes the standing rule that makes assistants use IGPPT for every presentation request
     (.github/copilot-instructions.md for GitHub Copilot, AGENTS.md for Codex, Cursor and Gemini CLI,
      CLAUDE.md for Claude Code), with the exact script paths for this project,
  4. adds a /igppt command for Copilot Chat (.github/prompts/igppt.prompt.md),
  5. turns on agent skills in VS Code for this project (.vscode/settings.json),
  6. adds igppt-words.txt for client and product names the spell check should accept,
  7. builds and validates a test deck to prove everything works.
Safe to run again: it updates its own sections and leaves everything else alone.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
START, END = "<!-- IGPPT:START -->", "<!-- IGPPT:END -->"


def say(ok, msg):
    print(("  OK    " if ok else "  FIX   ") + msg)


def rel(p, root):
    try:
        return Path(os.path.relpath(p, root)).as_posix()
    except ValueError:  # different drive on Windows
        return Path(p).as_posix()


def upsert(path, block):
    """Insert or replace the IGPPT section in a text file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    section = f"{START}\n{block.strip()}\n{END}\n"
    if START in text and END in text:
        head, rest = text.split(START, 1)
        text = head + section + rest.split(END, 1)[1].lstrip("\n")
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + section
    path.write_text(text, encoding="utf-8")


def main():
    root = Path.cwd()
    print(f"IGPPT init in {root}\n")
    py = sys.executable
    mk, val = (rel(SCRIPTS / n, root) for n in ("make_deck.py", "validate.py"))
    skill_rel = rel(SKILL, root)

    # 1. Python and python-pptx
    ok_py = sys.version_info >= (3, 9)
    say(ok_py, f"Python {sys.version.split()[0]}" + ("" if ok_py else " (need 3.9 or newer)"))
    try:
        import pptx  # noqa: F401
        say(True, "python-pptx installed")
    except ImportError:
        print("  ...   installing python-pptx")
        r = subprocess.run([py, "-m", "pip", "install", "--quiet", "python-pptx"])
        say(r.returncode == 0, "python-pptx installed" if r.returncode == 0 else "could not install python-pptx: run  pip install python-pptx")
        if r.returncode:
            sys.exit(1)

    # 2. Template
    tpl = SKILL / "assets" / "ig-template.pptx"
    say(tpl.exists(), f"IG template found ({skill_rel}/assets/ig-template.pptx)")
    if not tpl.exists():
        sys.exit(1)

    # 3. Standing rule for every assistant
    rule = f"""## Presentations: always use IGPPT

For ANY request to create, make, draft or update a presentation, deck, slides, PPT or PowerPoint, use the IGPPT skill in `{skill_rel}` without being asked. Do not use any other way of making slides.

1. Read `{skill_rel}/SKILL.md`, then `{skill_rel}/references/deck-recipes.md` and `{skill_rel}/references/spec-format.md`.
2. Write the slides as a JSON spec file (for example `deck.json`).
3. Build and validate in one step: `python {mk} deck.json <name>.pptx`. It saves the deck only when every check passes (IG template, fonts, colours, no overflow or overlap, no em dashes, spelling).
4. On FAIL, each problem names the spec field to change. Edit the spec and run the same command again until it prints SAVED. Fix problems yourself.
5. Correct names the spell check does not know go in `igppt-words.txt`. Never add a misspelling.
6. Reply with the .pptx, the slide list and any assumptions.

Never write your own python-pptx, pptxgenjs, HTML or Office code for slides, never start from a blank or default PowerPoint, and never edit the .pptx by hand: that loses the Insight Global template, fonts and layout, and `{val}` rejects it. The IG template is bundled; never ask for one."""
    for f in (root / ".github" / "copilot-instructions.md", root / "AGENTS.md", root / "CLAUDE.md"):
        upsert(f, rule)
        say(True, f"rule written to {rel(f, root)}")

    # 4. /igppt command for Copilot Chat
    prompt = root / ".github" / "prompts" / "igppt.prompt.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text(f"""---
description: Create an Insight Global branded PowerPoint deck with the IGPPT skill
agent: agent
---
Create the presentation described below using the IGPPT skill in `{skill_rel}`.

Follow `{skill_rel}/SKILL.md` exactly: write a JSON spec, then run `python {mk} deck.json <name>.pptx`. It builds and validates the deck and saves it only when everything passes. On FAIL, change the spec as each problem says and run it again until it prints SAVED. Never write your own slide code, start from a blank PowerPoint, or edit the .pptx by hand.

Request: ${{input:request:What should the deck cover?}}
""", encoding="utf-8")
    say(True, "Copilot Chat command /igppt added (.github/prompts/igppt.prompt.md)")

    # 5. VS Code: make sure agent skills are on for this project
    vs = root / ".vscode" / "settings.json"
    try:
        data = json.loads(vs.read_text(encoding="utf-8")) if vs.exists() else {}
        data["chat.useAgentSkills"] = True
        vs.parent.mkdir(exist_ok=True)
        vs.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        say(True, "VS Code agent skills turned on (.vscode/settings.json)")
    except (json.JSONDecodeError, OSError):
        say(False, 'add  "chat.useAgentSkills": true  to .vscode/settings.json by hand')

    # 6. Word list for names the spell check should accept
    words = root / "igppt-words.txt"
    if not words.exists():
        words.write_text("# Names and terms the IGPPT spell check should accept: clients, products, people.\n"
                         "# One per line. Never add a misspelling here.\n", encoding="utf-8")
    say(True, "word list for names: igppt-words.txt")

    # 7. Prove it works: build and validate the sample deck
    with tempfile.TemporaryDirectory() as tmp:
        spec = Path(tmp) / "sample.json"
        spec.write_text((SKILL / "examples" / "sample-deck.json").read_text(encoding="utf-8"), encoding="utf-8")
        out = Path(tmp) / "igppt-test.pptx"
        r = subprocess.run([py, str(SCRIPTS / "make_deck.py"), str(spec), str(out)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        works = r.returncode == 0 and out.exists()
        say(works, "test deck built and validated: PASS" if works else "test deck failed:\n" + (r.stdout + r.stderr)[-1200:])
    print("\nReady." if works else "\nNot ready: fix the items above and run init again.")
    sys.exit(0 if works else 1)


if __name__ == "__main__":
    main()
