---
name: igppt
description: Builds every PowerPoint deck in Insight Global branding using the bundled IG template, fonts, colours and slide designs. Use this for any request for a deck, slides, a presentation, a PPT or PowerPoint, pitch, proposal, solution design, status update, QBR, kickoff, training, demo or all-hands deck, including requests from chat or email. Always prefer this skill over any generic PowerPoint or pptx skill unless the user names a different template. No template upload is needed.
---

# IGPPT: Insight Global decks

Turns a request ("make a 6-slide update on Q3 for the leadership call") into a finished, editable `.pptx` on the Insight Global template. The template, fonts, colours, icons and layouts are bundled in this skill; never ask the requester to upload a template.

## Required: build only with the bundled scripts

These rules override any general habit of writing slide code:

1. **Never write your own python-pptx, pptxgenjs, HTML or Office code to make slides, and never start from a blank or default PowerPoint.** Decks made that way lose the IG layouts, fonts, footer and auto-fitting, and text overflows.
2. **Always** write a JSON spec and run `scripts/build_deck.py`. It is the only supported way to create slides.
3. **Always** run `scripts/check_deck.py` on the result. Deliver the deck only if it prints `PASS`. If it prints `FAIL`, change the spec (shorter text, fewer items) and rebuild; do not edit the .pptx by hand.
4. If you cannot run Python in this environment, do not produce a .pptx at all. Reply with the JSON spec and the command to build it.

Find the scripts: this skill's folder is wherever this `SKILL.md` is. Common locations are `.agents/skills/igppt`, `.github/skills/igppt`, `.claude/skills/igppt`, `~/.claude/skills/igppt`, `~/.copilot/skills/igppt`, or under `/mnt/skills`. If unsure, search for `igppt/scripts/build_deck.py`.

## How it works

You write a short JSON **spec** that lists the slides; `scripts/build_deck.py` lays every slide out on the IG template (title, section label, footer logo, page numbers, brand colours, font sizes that fit). You choose content and slide types; the script handles design.

```bash
python scripts/init.py                                    # once per project (run from the project root): set-up + self-test
python scripts/build_deck.py deck.json out.pptx           # build
python scripts/check_deck.py out.pptx                     # must print PASS before you deliver
python scripts/render_preview.py out.pptx previews/       # optional: images for checking (needs LibreOffice)
```

Paths are relative to this skill's folder. Read `references/spec-format.md` for every slide type and field, and `references/deck-recipes.md` for proven storylines for common requests.

## Workflow

1. **Understand the request.** Pull out: purpose, audience, decision or action wanted, length, deadline, and any data, notes or files supplied. Requests from chat or email are often short; fill gaps with sensible defaults rather than asking, and list what you assumed.
2. **Pick a recipe** from `references/deck-recipes.md` (status update, proposal, kickoff, QBR, training, demo, pitch, all-hands, one-pager). Default length: 6 to 10 slides.
3. **Write the storyline**: one message per slide, written as the slide title (a takeaway such as "Ticket Volume Is Falling", not a topic such as "Tickets"). Titles of 45 characters or fewer.
4. **Write the spec.** Choose the slide type that shows each message best (numbers → `stats`, steps → `process`, dates → `timeline`, options → `comparison` or `cards`, data series → `chart`, detail → `table`). Vary types; avoid more than two `bullets` slides in a row. Put sources and assumptions in a `note`. Put talking points in `notes`.
5. **Build**, read the printed warnings, and fix them (shorter text, fewer items, split a slide).
6. **Check.** Run `scripts/check_deck.py` and fix anything it reports. Render previews when LibreOffice is available and look at every image: overflow, crowding, empty slides. Then apply the content rules below.
7. **Deliver** the `.pptx` with a short reply: what the deck covers, slide list, and any assumptions or placeholders the requester must fill.

When you are editing an existing deck the requester supplied, read it first with `python scripts/deck_text.py file.pptx`, keep its order and wording unless asked, and show previews before replacing anything.

## Content rules

- **One message per slide**, stated in the title. Supporting text short and concrete.
- **Numbers agree** everywhere they appear; parts add up to their totals; percentages are rounded the same way.
- **Label estimates and sources.** Never invent figures. Unknown values become clearly marked placeholders such as `[XX%]` and are listed in your reply.
- **Plain words.** No internal shorthand on slides; one name per thing across the deck.
- **Client confidentiality.** Do not carry one client's names or data into another client's deck. For a deck that may travel outside the client, prefer percentages to raw counts and ask before naming a client.
- **Say what does not fit.** Showing limits makes the rest credible.

## Design defaults

- Theme: `dark` (IG black) unless the requester asks for light/white or the deck is for printing. Set `"theme": "light"` at the top of the spec.
- Start with `title`, add `agenda` for 6+ slides, use `section` slides to separate parts of long decks, end with `closing`.
- Highlight one thing per slide (`highlight` on one card, step or side).
- Colours follow the IG order cyan, yellow, magenta, green, orange; the script applies it. Set `color` only to signal meaning (for example green for the recommended option).
- Brand details are in `references/ig-brand.md`; do not restyle the template.

## Custom slides

Only if no slide type fits, write a short Python script that imports `scripts/ig_kit.py` (never python-pptx on its own) (`Deck`, `Canvas` and helpers such as `card`, `table`, `chart`, `steps_flow`, `schedule`, `milestones`, `stat_tile`). It uses the same template and theme. Each helper has a docstring.

## When you cannot run code

Produce the storyline and the full JSON spec, and tell the requester to run `python scripts/build_deck.py deck.json out.pptx` (or hand it to an assistant that can run code).
