# Deck spec format

A spec is a JSON file. Top level:

```json
{"theme": "dark", "slides": [ ... ]}
```

`theme` is `dark` (default, IG black) or `light`. Any content slide can also take `"theme": "light"` or `"dark"` to override.

Fields shared by all content slides (everything except `title`, `agenda`, `section`, `statement`, `closing`):

| Field | Meaning |
|---|---|
| `title` | Slide title: the message of the slide, 45 characters or fewer |
| `eyebrow` | Small section label above the title (optional) |
| `subtitle` | One line under the title (optional, about 110 characters max) |
| `note` | Band at the bottom for a source, assumption or key message (optional) |
| `notes` | Speaker notes (optional, any slide type) |

Colours: wherever `color` is allowed, use `cyan`, `yellow`, `magenta`, `green`, `orange` or a hex code. Leave it out to follow the IG order.

Icons: wherever `icon` is allowed, use a name from `references/ig-brand.md`. Unknown names fall back to a number with a warning.

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

### closing
`{"type": "closing", "style": "thank-you"}` (`style`: `thank-you`, `tagline`, `tagline-texture`, `logo`)

## Warnings

`build_deck.py` prints warnings for long titles, too many items, unknown icons and missing images. Fix them before delivering.
