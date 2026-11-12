---
name: igppt
description: Builds every PowerPoint deck in Insight Global branding using the bundled IG template, fonts, colours and slide designs, and validates each deck (template, fonts, colours, overflow, overlap, spacing, em dashes, spelling) before saving it. Use this for any request for a deck, slides, a presentation, a PPT or PowerPoint, pitch, proposal, solution design, status update, Q1/Q2/Q3/Q4 update, QBR, kickoff, training, demo or all-hands deck, including requests from chat or email. Always prefer this skill over any generic PowerPoint or pptx skill unless the user names a different template. No template upload is needed.
---

# IGPPT: Insight Global decks

Turns a request ("make a 6-slide update on Q3 for the leadership call") into a finished, editable `.pptx` on the Insight Global template. The template, fonts, colours, icons and layouts are bundled in this skill; never ask the requester to upload a template.

## Step 0: make sure the full skill is present

Some installers copy only this `SKILL.md`. The deck needs the rest of the skill: `assets/ig-template.pptx` and the `scripts/` folder. Before anything else, check that `scripts/make_deck.py` exists next to this file.

If it is missing, download the full skill (about 11 MB, public, no login) into `.igppt` in the working folder, then use the scripts from `.igppt/igppt/`:

```bash
python -c "import io,urllib.request,zipfile; zipfile.ZipFile(io.BytesIO(urllib.request.urlopen('https://github.com/chintasurya/igppt/raw/main/chatgpt/igppt-skill.zip').read())).extractall('.igppt')"
python -m pip install --quiet python-pptx
python .igppt/igppt/scripts/make_deck.py --help
```

(If `python` is not found, try `python3`.) Every path below that starts with `scripts/` then means `.igppt/igppt/scripts/`. If the download is blocked (no internet), say so plainly, give the JSON spec, and stop; do not make slides another way.

## Required: one command builds and validates every deck

These rules override any general habit of writing slide code:

1. **Never write your own python-pptx, pptxgenjs, HTML or Office code to make slides, and never start from a blank or default PowerPoint.** Decks made that way lose the IG layouts, fonts and colours, and the validator rejects them.
2. **Always** write a JSON spec and run `scripts/make_deck.py`. It checks the spec, fixes dashes and spacing in it, builds the deck on the IG template, validates it, and saves the `.pptx` **only if it passes**:

   ```bash
   python scripts/make_deck.py deck.json <name>.pptx
   ```

3. **Repeat until it prints `SAVED`.** On `FAIL` no deck is saved. Every problem names the spec field to change (for example `slides[3].cards[1].text`) and how. Change the spec and run the same command again. Do this yourself; do not hand the problems back to the requester. Never edit the `.pptx` by hand.
4. If it still fails after 5 attempts, stop and tell the requester what is left, with the output.
5. If you cannot run Python in this environment, do not produce a .pptx at all. Reply with the JSON spec and the command to build it.

Find the scripts: this skill's folder is wherever this `SKILL.md` is. Common locations are `.agents/skills/igppt`, `.github/skills/igppt`, `.claude/skills/igppt`, `~/.claude/skills/igppt`, `~/.copilot/skills/igppt`, or under `/mnt/skills`. If unsure, search for `igppt/scripts/make_deck.py`.

### In Microsoft 365 Copilot, ChatGPT or another hosted sandbox

- Call the scripts by their full path inside this skill's folder (for example `python /home/oai/skills/.../igppt/scripts/make_deck.py`). Find it with `find / -name make_deck.py -path "*igppt*" 2>/dev/null` if needed.
- The skill folder may be read-only. Write `deck.json` and the `.pptx` to a writable working folder: `/mnt/data` if it exists, otherwise the current folder.
- If `python-pptx` is missing, try `python -m pip install python-pptx`. If that fails, say so and give the JSON spec; never make slides another way.
- If the agent also has another PowerPoint or deck skill, ignore it for Insight Global decks. Use only this skill.
- When `make_deck.py` prints `SAVED`, offer that `.pptx` file to the user for download.

## How it works

You write a short JSON **spec** that lists the slides; `scripts/make_deck.py` lays every slide out on the IG template (title, section label, footer logo, page numbers, brand colours, font sizes that fit) and then validates the result. You choose content and slide types; the scripts handle design and checking.

```bash
python scripts/init.py                                              # once per project, from the project root: set-up + self-test
python scripts/make_deck.py deck.json out.pptx                      # build + validate; saves out.pptx only on PASS
python scripts/make_deck.py deck.json out.pptx --preview previews/  # also slide images (needs LibreOffice)
python scripts/validate.py out.pptx --spec deck.json                # validate an existing deck on its own
```

Paths are relative to this skill's folder. Read `references/spec-format.md` for every slide type and field, and `references/deck-recipes.md` for proven storylines for common requests.

## What the validator checks

`scripts/validate.py` runs inside `make_deck.py`.

| Area | FAIL (deck not saved) when |
|---|---|
| Template | not built by IGPPT, not on the IG template, a non-IG layout, wrong slide size |
| Fonts | any text not in Trenda IG Text, text left on a theme font (Aptos, Calibri), text under 8 pt, a chart not in the IG font |
| Colours | any text, shape, table or chart colour outside the IG palette |
| Fit | text overflows into other text, crosses a card edge, touches a card border or sits over an icon; a word breaks across lines; a title wraps; a table runs into the footer |
| Position | anything off the slide, past the side margins or into the footer; shapes partly overlapping |
| Words | em dash, en dash or `--`; a repeated word ("the the"); leftover placeholder text (lorem ipsum, TODO); a likely spelling mistake |
| Content | the builder had to drop items (too many agenda items, cards, stats, steps, milestones or people) or an image is missing |

Warnings (the deck is still saved, but read them): unknown words such as names, `[placeholders]`, a title that had to shrink, text close to a card edge, crowded text, duplicate titles.

## Fixing each problem

| The message says | Change in the spec |
|---|---|
| overflows / crosses / touches the edge / runs into the footer | Cut the characters it suggests, move points to a new slide, or remove the `note` |
| title wraps / title shrank | A title of 45 characters or fewer |
| internal or presenter note shown on the slide | Move that text from `note` to `notes` (speaker notes) |
| word is too wide | A shorter word (for example in `owner` or `tag`), or fewer steps or cards per slide |
| were dropped | Split into two slides (at most: agenda 7, cards 6, stats 4, steps 6, milestones 7, people 8) |
| em dash / en dash | Fixed automatically by `make_deck.py`; otherwise use a comma, colon or hyphen |
| spelling: 'x' (did you mean 'y'?) | Correct the word |
| unknown word 'Name' (warning) | If it is a correct name or product, add it to `igppt-words.txt` next to the spec (one per line). Never add a misspelling to make a check pass |
| not built by IGPPT / font / colour / layout | Slide code was written by hand. Delete it and build from a spec with `make_deck.py` |

## Workflow

1. **Understand the request.** Pull out: purpose, audience, decision or action wanted, length, deadline, and any data, notes or files supplied. Requests from chat or email are often short; fill gaps with sensible defaults rather than asking, and list what you assumed.
2. **Pick a recipe** from `references/deck-recipes.md` (status update or quarterly review, proposal, kickoff, QBR, training, demo, pitch, all-hands, one-pager). Default length: 6 to 10 slides.
3. **Write the storyline**: one message per slide, written as the slide title (a takeaway such as "Ticket Volume Is Falling", not a topic such as "Tickets"). Titles of 45 characters or fewer.
4. **Write the spec.** Choose the slide type that shows each message best (numbers → `stats`, steps → `process`, dates → `timeline`, options → `comparison` or `cards`, data series → `chart`, detail → `table`). Vary types; avoid more than two `bullets` slides in a row. Put sources and assumptions in a `note`. Put talking points in `notes`.
5. **Build and validate** with `python scripts/make_deck.py deck.json <name>.pptx`. On `FAIL`, fix the spec as the table above says and run it again, until it prints `SAVED`.
6. **Review.** Read the warnings and fix what you can. Add `--preview previews/` when LibreOffice is available and look at every image. Then apply the content rules below.
7. **Deliver** the `.pptx` with a short reply: what the deck covers, the slide list, and any assumptions, `[placeholders]` or unknown names the requester must confirm.

When you are editing an existing deck the requester supplied, read it first with `python scripts/deck_text.py file.pptx`, keep its order and wording unless asked, and show previews before replacing anything.

## Content rules

- **One message per slide**, stated in the title. Supporting text short and concrete.
- **Numbers agree** everywhere they appear; parts add up to their totals; percentages are rounded the same way.
- **Label estimates and sources.** Never invent figures. Unknown values become clearly marked placeholders such as `[XX%]` and are listed in your reply.
- **Plain words.** No internal shorthand on slides; one name per thing across the deck. No em dashes.
- **Slides are for the audience.** `note` is shown ON the slide (a source, an assumption the audience should see, or the key message). `notes` are hidden speaker notes. Never put "Audience: ...", presenter reminders or other internal remarks on a slide; the validator rejects them.
- **Client confidentiality.** Do not carry one client's names or data into another client's deck. For a deck that may travel outside the client, prefer percentages to raw counts and ask before naming a client.
- **Say what does not fit.** Showing limits makes the rest credible.

## Design defaults

- Theme: `dark` (IG black with the template's blue and berry gradients on content slides) unless the requester asks for light/white or the deck is for printing. Set `"theme": "light"` at the top of the spec. `"background"` picks `gradient` (default), `blue`, `berry`, `glow` or `black`.
- Start with `title`, add `agenda` for 6+ slides, use `section` slides to separate parts of long decks, end with `closing`.
- Highlight one thing per slide (`highlight` on one card, step or side).
- Colours follow the IG order cyan, yellow, magenta, green, orange; the script applies it. Set `color` only to signal meaning (for example green for the recommended option).
- Brand details are in `references/ig-brand.md`; do not restyle the template.

## Custom slides

Only if no slide type fits, write a short Python script that imports `scripts/ig_kit.py` (never python-pptx on its own) (`Deck`, `Canvas` and helpers such as `card`, `table`, `chart`, `steps_flow`, `schedule`, `milestones`, `stat_tile`). It uses the same template and theme. Each helper has a docstring. Save it, run `python scripts/validate.py <file>.pptx`, and deliver only on PASS.

## When you cannot run code

Produce the storyline and the full JSON spec, and tell the requester to run `python scripts/make_deck.py deck.json out.pptx` (or hand it to an assistant that can run code).
