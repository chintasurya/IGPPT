# Deck spec format

A spec is a JSON file. Top level:

```json
{"theme": "dark", "slides": [ ... ]}
```

`theme` is `dark` (default, IG black) or `light`. Any content slide can also take `"theme": "light"` or `"dark"` to override.

`talk_track` (true or false, top level): for decks presented to client executives, proposals and solution reviews. Every content slide then needs `notes` of at least 120 characters: the statement the presenter reads aloud (what we propose, why, and the evidence). `make_deck.py` fails without it and writes `<Name> - talk track.md` next to the deck.

`background` (dark theme) sets the IG template background for content slides: `gradient` (default: alternates the template's blue and berry gradients), `blue`, `berry`, `glow` (colour glow along the bottom; avoid with a `note`), or `black`. Any content slide can also take its own `"background"`.

Fields shared by all content slides (everything except `title`, `agenda`, `section`, `statement`, `closing`):

| Field | Meaning |
|---|---|
| `title` | Slide title: the message of the slide, 45 characters or fewer |
| `eyebrow` | Small section label above the title (optional) |
| `subtitle` | One line under the title (optional, about 110 characters max) |
| `note` | Band at the bottom, shown ON the slide: a source, an assumption or a key message for the audience (optional). Never audience or presenter remarks |
| `notes` | Hidden speaker notes (optional, any slide type): talking points, audience, reminders |

Colours: wherever `color` is allowed, use `cyan`, `yellow`, `magenta`, `green`, `orange` or a hex code. Leave it out to follow the IG order.

Icons: optional, and off by default. Without an `icon`, cards show a short accent bar and steps show a light step number, which is the executive style. Add an icon only when it carries meaning the words do not; `"numbered": true` on a cards slide shows numbered circles instead. Wherever `icon` is allowed, use a name from `references/ig-brand.md`. Common words also work (people, team, gear, settings, money, time, security, growth, goal, launch, risk, research, support and more map to the nearest icon). Unknown names fall back to a number with a warning.

## Slide types

### title
`{"type": "title", "title": "Quarterly Update", "subtitle": "Platform team", "date": "Oct 2026"}`

### agenda
`{"type": "agenda", "items": ["Results", "Roadmap", "Risks"]}` (up to 7 items; optional `title`)

### section
`{"type": "section", "title": "Part Two: Results"}` (full-colour divider; also good as a "LIVE DEMO" holding slide)

### statement
`{"type": "statement", "text": "One big message.", "eyebrow": "Our focus", "attribution": "optional, for a quote"}` (`quote` is an alias)

### bullets
```json
{"type": "bullets", "title": "Risks and Decisions",
 "bullets": ["A point", {"text": "A point with detail", "sub": ["Detail one", "Detail two"]}],
 "callout": {"value": "3", "label": "P1 incidents", "text": "optional", "color": "magenta"}}
```
Up to about 7 bullets. `callout` adds a big-number card on the right.

### cards
```json
{"type": "cards", "title": "What We Delivered",
 "cards": [{"icon": "rocket", "title": "Short heading", "text": "One or two sentences.", "tag": "optional chip", "highlight": true}]}
```
2 to 6 cards (6 makes a 2 x 3 grid; add `"grid": true` with 4 cards for 2 x 2). A card can use `value` (a big number) instead of an icon, or `bullets` instead of `text`.

### stats
`{"type": "stats", "title": "Q3 at a Glance", "stats": [{"value": "98%", "label": "SLA attainment", "text": "Up from 95%."}]}` (2 to 4 tiles)

### process
```json
{"type": "process", "title": "How a Change Reaches Production",
 "steps": [{"title": "Request", "owner": "Business", "text": "Raised in ServiceNow.", "icon": "ticket"}],
 "highlight": 2, "bullets": ["optional points under the steps"]}
```
2 to 6 steps joined by arrows. `owner` shows above each step title. `highlight` is the zero-based index of a step to outline.

### timeline
`{"type": "timeline", "title": "Q4 Roadmap", "milestones": [{"date": "Oct", "title": "Clean-up", "text": "One line."}]}` (2 to 7 milestones)

### table
```json
{"type": "table", "title": "Service Levels", "columns": ["Priority", "Response", "Resolution"],
 "rows": [["P1", "15 min", "3 hours"]], "widths": [2, 1, 1], "bold_last": true}
```
Up to about 12 rows. `widths` are relative (optional; otherwise sized to the text).

### chart
```json
{"type": "chart", "title": "Ticket Volume Is Falling",
 "chart": {"type": "column", "categories": ["Apr", "May"], "series": [{"name": "Requests", "values": [310, 300]}],
           "number_format": "0%", "max": 500},
 "takeaways": ["optional bullets in a panel on the right"]}
```
Chart `type`: `column`, `bar` (horizontal), `stacked-column`, `line`, `pie`, `doughnut`. For one series you can write `"values": [...]` instead of `series`. Charts are native and editable in PowerPoint.

### comparison
```json
{"type": "comparison", "title": "Before and After",
 "left": {"tag": "Before", "heading": "Manual and slow", "points": ["..."]},
 "right": {"tag": "After", "heading": "Automated", "points": ["..."], "highlight": true}}
```

### image
`{"type": "image", "title": "Dashboard", "image": "files/screen.png", "caption": "optional", "bullets": ["optional"]}` (path relative to the spec file; the picture keeps its shape)

### team
`{"type": "team", "title": "Who to Contact", "members": [{"name": "Alex Morgan", "role": "Delivery Lead", "text": "optional"}]}` (up to 8; initials in coloured circles)

### architecture
The one solution or architecture view of a deck: columns left to right joined by arrows, an optional revision loop and foundation bands. Use it once per deck.
```json
{"type": "architecture", "title": "Solution Architecture", "subtitle": "One line on accountability",
 "columns": [
   {"label": "Inputs", "sub": "Client brands", "color": "cyan", "width": 1, "items": [
     {"title": "Request brief", "text": "optional second line"},
     {"title": "Ticket and plan", "accent": false}]},
   {"label": "Platform", "sub": "Marketing platform", "color": "magenta", "items": [
     {"title": "Customer data", "text": "Owned by the client", "dashed": true},
     {"title": "Content library", "text": "The asset", "items": [{"title": "Approved blocks"}, {"title": "Personalization"}]}]}],
 "loop": {"text": "Review changes come back to the team", "from": 2, "to": 1},
 "bands": [{"label": "Client environment", "title": "Client tools", "text": "Full visibility", "color": "cyan"}]}
```
2 to 5 columns (`width` is relative), about 3 to 5 items each. An item has `title`, optional `text`, `"accent": false` to drop its dot, `"dashed": true` for a dependency owned by someone else, and `items` for a group of nested items. `loop` numbers columns from 1. Up to 3 `bands` (the first is navy). Text sizes are picked to fit; the build fails if a column is too full.

### flow
An end-to-end process as numbered step cards: up to 10 steps, two rows when there are more than 5, joined by arrows.
```json
{"type": "flow", "title": "How Each Request Moves",
 "owners": {"client": {"label": "Client-led", "color": "magenta"}, "pod": {"label": "IG pod", "color": "cyan"}},
 "marker": {"step": 2, "text": "IG accountable from here"},
 "steps": [{"title": "Request", "owner": "client", "text": "One line"}],
 "bands": [{"label": "Parallel track", "title": "One line", "color": "orange", "dashed": true}]}
```
`owners` colour the steps and draw a legend; `marker` labels where accountability starts; `bands` (up to 3) sit under the steps.

### roles
Team structure: 2 to 5 role cards with a big count, a short line and responsibilities, and an optional headcount ramp.
```json
{"type": "roles", "title": "Pod Structure and Ramp",
 "roles": [{"count": "2", "title": "Builders", "sub": "Daily production", "points": ["Builds", "Revisions"]}],
 "ramp": {"label": "Headcount ramp, 2027", "categories": ["J", "F", "M"], "values": [2, 3, 4], "highlight": 3,
          "highlight_label": "Q1 ramp", "full_label": "Full team", "optional": {"from": 7, "add": 1, "label": "Optional"},
          "note": "One line on the scale trigger"}}
```

### Solution views are never repeated
`architecture`, `flow` and `process` slides each show how the solution works from one angle. `make_deck.py` fails a deck with two `architecture` slides, or a `flow` or `process` slide whose parts mostly repeat another view (3 or more of the same names, half or more of the smaller view). Show the system once (architecture), the sequence once (flow), and the people once (roles).

### closing
`{"type": "closing", "style": "thank-you"}` (`style`: `thank-you`, `tagline`, `tagline-texture`, `logo`)

## Building and validating

Run `python scripts/make_deck.py deck.json out.pptx`. It fixes dashes and double spaces in the spec, builds the deck, validates it, and saves `out.pptx` only on PASS. Each problem names the spec field to change, for example `slides[3].cards[1].text`. Limits that fail the build because content would be dropped: agenda 7 items, cards 6, stats 4, process steps 6, flow steps 10, architecture columns 5, roles 5, timeline milestones 7, team members 8. Unknown icons fall back to a number with a warning.

Text rules: no em dashes, en dashes or `--` (use a comma, colon or hyphen); no leftover placeholder text such as lorem ipsum or TODO. `[XX%]`-style placeholders are allowed but reported. Names the spell check does not know go in `igppt-words.txt` next to the spec.
