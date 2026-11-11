# Insight Global brand rules (as built into the skill)

Everything here is already applied by `build_deck.py` and `ig_kit.py`, and checked by `validate.py` (fonts, colours, layouts). Use the slide types and constants instead of restyling.

## Template

`assets/ig-template.pptx` is the IG PowerPoint template with layouts only. The skill uses these layouts:

| Use | Layout |
|---|---|
| Title | Proposal Title Slide |
| Agenda | Dark Title Only_Color (dark) / Light Title Only (light) |
| Content | Dark 1-Column_6 (blue gradient) and Dark 1-Column_11 (berry gradient), alternating by default; Dark Title Only_Color (bottom glow) or Dark Title Only (plain black) on request; Light Title Only (light theme) |
| Section divider | Pink Divider_1 |
| Statement or quote | Navy Statement Left |
| Closing | Closer_1 (thank you), Closer_5 (tagline), Closer_4 (tagline, texture), Closer_6 (IG logo) |

The template draws the section label, title, IG footer logo and page number. Never add another logo or footer.

## Colours

| Name | Hex | Role |
|---|---|---|
| Black | 000000 | Dark background |
| White | FFFFFF | Light background, text on dark |
| Cyan | 00D6F1 | First accent |
| Yellow | FFD700 | Second accent |
| Magenta | FF0069 | Third accent |
| Green | 55E03A | Fourth accent; "recommended" |
| Orange | F98B34 | Fifth accent |
| Navy | 00273B | Table headers, note bands |

On the light theme, accent colours used for text are darkened automatically so they stay readable. Text on accent fills is black.

## Type

Trenda IG Text (regular, bold) and Trenda IG Text Light (big numbers). Title about 40 pt; subtitle 15 pt; card headings 13 to 16 pt; body 10 to 20 pt chosen to fit. Machines without the IG fonts show a substitute; install the brand fonts to see the real ones.

## Icons

Font Awesome Free (CC BY 4.0), drawn in coloured circles. Names:

balance, calendar, chart, check, check-circle, clipboard-check, clock, code, cogs, database, dollar, eye, file, file-import, flag, handshake, headset, lightbulb, lock, microscope, moon, pointer, rocket, route, search, shield, sliders, ticket, tools, user-check, user-plus, user-shield, users, users-cog, warning, workflow
