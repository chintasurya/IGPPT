"""Claude Code hooks for IGPPT: make learning from feedback automatic in a git repository.

    python claude_hook.py session     SessionStart hook: tells Claude which lessons are in force
    python claude_hook.py prompt      UserPromptSubmit hook: spots feedback about a deck and asks Claude to record it

Claude Code adds what these print to the conversation. They never block anything and never fail the session:
any error is swallowed and nothing is printed. Configure them in .claude/settings.json (init.py does this).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent
FEEDBACK = re.compile(r"\b(wrong|incorrect|not right|mistake|don'?t|do not|never|always|stop|should(?:n'?t| not| be| have)|"
                      r"instead|again|i told you|why did you|not what i|fix (?:this|that|it)|please change|too (?:long|small|big|many))\b", re.I)
DECK = re.compile(r"\b(slides?|decks?|ppt|pptx|powerpoint|presentation|titles?|subtitles?|fonts?|colou?rs?|bullets?|layout|"
                  r"charts?|cards?|tables?|agenda|closing|icons?|logo|template|theme|spacing|overlap\w*|igppt)\b", re.I)


def session():
    import learn
    lessons = learn.load(Path.cwd())
    lines = [f"IGPPT is available for any deck: python {HERE / 'igppt.py'} build <spec.json> <Name>.pptx (saves only on PASS)."]
    if lessons:
        lines.append(f"IGPPT lessons in force ({len(lessons)}), learned from earlier feedback. Follow them; make_deck.py enforces the checked ones:")
        lines += [f"- {l.get('id')}: {learn.describe(l)}" + (f" (fix: {l['fix']})" if l.get("fix") else "") for l in lessons[:40]]
        if len(lessons) > 40:
            lines.append(f"- ... and {len(lessons) - 40} more: python {HERE / 'learn.py'} list")
    print("\n".join(lines))


def prompt():
    data = json.loads(sys.stdin.read() or "{}")
    text = str(data.get("prompt", ""))
    if not (FEEDBACK.search(text) and DECK.search(text)):
        return
    print(f"""IGPPT feedback check: if this message corrects a deck, do all of this before replying:
1. Record it as a lesson the code can check (prefer --word; see SKILL.md "Learning from feedback"):
   python {HERE / 'learn.py'} add --kind <kind> ... --mistake "<what was wrong>" --fix "<what to do>" --feedback "<the user's words>" --spec <the deck's spec.json> --commit
   (--spec proves the lesson catches the mistake; --commit saves it in git so every later session and teammate gets it. Do not push unless the user asks.)
2. Fix the spec and rebuild with igppt.py build / make_deck.py until it prints SAVED.
3. Tell the user the lesson ID and that it is committed.
If the message is not feedback on a deck, ignore this note.""")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        mode = sys.argv[1] if len(sys.argv) > 1 else ""
        if mode == "session":
            session()
        elif mode == "prompt":
            prompt()
    except Exception:  # a hook must never break the session
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
