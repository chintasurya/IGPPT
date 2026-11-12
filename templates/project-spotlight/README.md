# Project Spotlight template

A standard way for every PM to present a project on the Insight Global template. Each project is summarised on one **snapshot** slide. A PM can add the optional deep-dive slides when they present their own project.

| File | What it is |
|---|---|
| `Project-Spotlight-Template.pptx` | The master deck: blank, with `[square-bracket]` placeholders and field guidance in the speaker notes |
| `Project-Spotlight-Sample.pptx` | The same deck filled in for a **fictional** project, to show the expected detail. Do not reuse its names or figures |
| `../../igppt/examples/project-spotlight-template.json` | The template as an IGPPT spec, for building a deck with the IGPPT assistant |
| `../../igppt/examples/project-spotlight-sample.json` | The sample as an IGPPT spec |

## What the snapshot slide covers

| Field | What to write |
|---|---|
| Title | Project name and the result in a few words. 45 characters or fewer, one line |
| Subtitle | Client (or sector, if the deck may leave the account), practice, PM, dates |
| Practice | The IG practice the work sits in (use the official practice name) |
| Team size | Peak FTE, with the onshore / offshore split |
| Project length | Months, with start and end month |
| ACV | Annual contract value |
| TCV | Total contract value over the full term. For a flat contract ACV x years = TCV |
| Customer Problem | The client's pain in their terms, ideally with a number. 3 short bullets |
| Scope | What is in, and at least one thing that is out |
| Technologies | Up to 6 named platforms, languages or tools, one per tag |
| How We Found the Need | What triggered it, how discovery was done, who approved it |
| Deal of Delivery (DOD) | Whether a DOD was created and when, what it commits to, who agreed it and where it is kept. Write "Not created" if there is none |
| Outcomes (optional) | Measured results so far, or "In progress" |

## Option 1: in PowerPoint

1. Open `Project-Spotlight-Template.pptx` and save a copy under your project name.
2. **Main deck:** copy slide 3 (the snapshot) into the main deck, one slide per project. Use **Paste > Use Destination Theme** so the IG layout is kept.
3. **Your own presentation:** keep slides 3 to 12, fill them in and delete slide 2 ("How to Use This Template").
4. Replace every `[square-bracket]` placeholder and remove the brackets. Delete any slide or card you do not need, such as Outcomes.
5. Keep the text short. The template is sized for about 3 short bullets per card. If text spills over a card edge, cut it rather than shrinking the font.

## Option 2: with the IGPPT assistant (checked automatically)

Copy `igppt/examples/project-spotlight-template.json`, replace the placeholders with your project's details (or paste your notes to the IGPPT agent and ask for a project spotlight), then build it:

```bash
python igppt/scripts/make_deck.py my-project.json My-Project-Spotlight.pptx
```

The deck is saved only if it passes the IG checks: template, fonts, colours, no overflowing text and spelling. For a portfolio deck, put one `snapshot` slide per project in a single spec. The slide type is documented in `igppt/references/spec-format.md`.

## Before you share

- The numbers agree everywhere: the same team size, length, ACV and TCV on the snapshot and on the deep-dive slides.
- Estimates are labelled, and nothing is invented.
- If the deck may go outside the account, name the sector instead of the client and check with the account lead.
