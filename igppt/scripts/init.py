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
  6. builds and checks a test deck to prove everything works.
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
    b, chk, prev = (rel(SCRIPTS / n, root) for n in ("build_deck.py", "check_deck.py", "render_preview.py"))
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
3. Build: `python {b} deck.json <name>.pptx`
4. Check: `python {chk} <name>.pptx` and deliver only when it prints PASS. On FAIL, shorten the spec and rebuild.
5. Reply with the .pptx, the slide list and any assumptions.

Never write your own python-pptx, pptxgenjs, HTML or Office code for slides, and never start from a blank or default PowerPoint: that loses the Insight Global template, fonts and layout. The IG template is bundled; never ask for one."""
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

Follow `{skill_rel}/SKILL.md` exactly: write a JSON spec, build it with `python {b} deck.json <name>.pptx`, run `python {chk} <name>.pptx`, and deliver only when it prints PASS. Never write your own slide code or start from a blank PowerPoint.

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

    # 6. Prove it works
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "igppt-test.pptx"
        r1 = subprocess.run([py, str(SCRIPTS / "build_deck.py"), str(SKILL / "examples" / "sample-deck.json"), str(out)],
                            capture_output=True, text=True)
        r2 = subprocess.run([py, str(SCRIPTS / "check_deck.py"), str(out)], capture_output=True, text=True) if r1.returncode == 0 else r1
        works = r1.returncode == 0 and r2.returncode == 0
        say(works, "test deck built and checked: PASS" if works else "test deck failed:\n" + (r1.stdout + r1.stderr + r2.stdout)[-800:])
    print("\nReady." if works else "\nNot ready: fix the items above and run init again.")
    print("In VS Code: reload the window, open Copilot Chat in Agent mode, and ask for a presentation (or type /igppt).")
    sys.exit(0 if works else 1)


if __name__ == "__main__":
    main()
