# IGPPT repository

This repository is the IGPPT skill (`igppt/`, Insight Global branded decks), the `ig-proposal-review` skill, and their installers and tools.

## Presentations: always use IGPPT

For any request to create, change or fix a presentation, deck, slides or PPT, use the skill in `igppt/` (read `igppt/SKILL.md` first). Never write python-pptx or other slide code by hand.

1. Write the slides as a JSON spec (see `igppt/references/spec-format.md` and `igppt/references/deck-recipes.md`).
2. Build: `python igppt/scripts/igppt.py build <spec>.json "<Name>.pptx"`. On FAIL, change the spec as each problem says and build again until it prints SAVED. Deliver the deck and its "IGPPT check.txt" report.
3. Follow every lesson the session-start hook lists (or `python igppt/scripts/learn.py list`).

## Learning from feedback (lessons are kept in git)

When the user says a deck is wrong or asks for a change that should always apply ("don't", "never", "always", "I told you"):

1. Record a lesson the code can check, proving it catches the mistake, and commit it:
   `python igppt/scripts/learn.py add --kind <kind> ... --mistake "..." --fix "..." --feedback "<user's words>" --spec <spec>.json --commit`
   In this repository lessons are saved to `igppt/assets/lessons.json`, so they ship with the skill to everyone.
2. Fix the spec and rebuild until SAVED.
3. Tell the user the lesson ID and that it is committed. Push only when the user asks.
4. When lessons change, run `python tools/test_igppt.py` and `python tools/build_zips.py` so the Microsoft 365 and ChatGPT zips carry them too.

The `.claude/settings.json` hooks remind you of the lessons at session start and when a message looks like feedback on a deck.

## Maintaining the skills

After changing `igppt/`, `ig-proposal-review/` or `copilot/`: run `python tools/test_igppt.py` and `python tools/test_review.py` (all must pass), `python tools/make_manifest.py`, and `python tools/build_zips.py`, then commit.
