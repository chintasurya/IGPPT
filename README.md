# IGPPT skill

Lets an AI assistant build any PowerPoint deck in Insight Global branding: status updates, proposals, kickoffs, QBRs, training, demos, pitches. The IG template, fonts, colours, icons and slide designs are bundled, so nobody uploads a template.

The assistant writes a short JSON list of slides; the skill turns it into a finished, editable `.pptx` on the IG template (dark or light), with layout and font sizes handled automatically, and validates the deck before saving it: IG template, fonts and colours, no overflowing or overlapping text, spacing, no em dashes, spelling.

It follows the open Agent Skills format (a folder with `SKILL.md`), so the same folder works in GitHub Copilot (VS Code agent mode, Copilot CLI, Copilot cloud agent) and Claude Code.

## Package contents

| Path | What it is |
|---|---|
| `igppt/SKILL.md` | Instructions the assistant loads |
| `igppt/references/deck-recipes.md` | Storylines for common deck requests |
| `igppt/references/spec-format.md` | Every slide type and field |
| `igppt/references/ig-brand.md` | IG layouts, colours, fonts, icons |
| `igppt/scripts/make_deck.py` | The one command: checks and fixes the spec, builds, validates, saves only on PASS |
| `igppt/scripts/validate.py` | Validates a deck: template, fonts, colours, fit, overlap, spacing, dashes, spelling |
| `igppt/scripts/build_deck.py` | Builds a deck from a JSON spec (used by `make_deck.py`) |
| `igppt/scripts/ig_kit.py` | Library behind it, for custom slides |
| `igppt/scripts/ig_metrics.py`, `ig_text.py` | Text measuring and text rules shared by the builder and the validator |
| `igppt/scripts/init.py` | One-time project set-up and self-test |
| `igppt/scripts/check_deck.py` | Older name for `validate.py` |
| `igppt/scripts/vendor/spellchecker` | Bundled spell checker (pyspellchecker, MIT), so no install is needed |
| `igppt/assets/wordlist.txt` | Business and technology words the spell check accepts |
| `igppt/scripts/render_preview.py` | Slide images for checking (needs LibreOffice) |
| `igppt/scripts/deck_text.py` | Reads an existing deck's text |
| `igppt/assets/ig-template.pptx` | The IG template (layouts only) |
| `igppt/examples/sample-deck.json` | A 13-slide example using every main slide type |
| `igppt/examples/project-spotlight-*.json` | Project Spotlight specs: blank template and a filled, fictional sample |
| `templates/project-spotlight/` | Project Spotlight master deck (`.pptx`), filled sample and a guide for PMs |
| `copilot/agents/igppt.agent.md` | "IGPPT" custom agent for Copilot |
| `chatgpt/GPT-instructions.md` | Set-up and instructions for a ChatGPT custom GPT |
| `chatgpt/igppt-skill.zip` | The skill packed for upload to a custom GPT |
| `tools/test_igppt.py` | Regression tests: clean decks pass, broken decks fail |

## Install: one command

Paste this into Copilot (or any assistant that can run commands, or a terminal) inside the project:

```bash
npx -y https://codeload.github.com/chintasurya/igppt/tar.gz/refs/heads/main
```

It downloads the latest IGPPT over HTTPS every time it runs (no git and no login needed), writes the full skill with the IG template to `.claude/skills/igppt`, `.github/skills/igppt` and `.agents/skills/igppt`, creates the **IGPPT agent**, writes the "always use IGPPT for presentations" rule, installs `python-pptx`, and builds a test deck that must pass. Run the same command again to update. Add `--global` at the end to install for your user across all projects.

Needs Node.js and Python 3.9+.

## Install with the skills CLI (alternative)

Run this in a terminal inside the project where you want the skill. It needs Node.js (for `npx`), git, and Python 3.9+ for building decks. No GitHub login is needed.

```bash
npx skills add chintasurya/igppt
```

It asks which AI tools to install into. To choose them in the command instead:

```bash
npx skills add chintasurya/igppt -a github-copilot -a claude-code -a codex -a cursor -a gemini-cli --copy -y
```

Add `-g` to install for yourself across all projects.

This uses the open-source [skills CLI](https://github.com/vercel-labs/skills), which supports GitHub Copilot, OpenAI Codex, Claude Code, Cursor, Gemini CLI and many more. Skills land in `.agents/skills/igppt` (shared by Copilot, Codex, Cursor and Gemini CLI) and `.claude/skills/igppt`.

Update later with `npx skills update`; remove with `npx skills remove igppt`.

### Initialise the project (required, once per project)

Right after installing, run the init command from the project's root folder:

```bash
python .agents/skills/igppt/scripts/init.py
```

(Use `.github/skills/...` or `.claude/skills/...` instead if that is where the skill was installed.)

It checks Python and installs `python-pptx`, checks the IG template, writes the standing rule that makes assistants use IGPPT for every presentation request (`.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`), adds a `/igppt` command to Copilot Chat, turns on agent skills in VS Code for the project, and builds and checks a test deck. It ends with "Ready." when everything works. Safe to run again.

Then reload VS Code, open Copilot Chat in **Agent** mode, and simply ask for a presentation (or type `/igppt`).

## Claude (claude.ai, desktop and mobile apps)

Upload once and Claude uses it in every new chat:

1. Download the skill zip: https://github.com/chintasurya/igppt/raw/main/chatgpt/igppt-skill.zip
2. In Claude, open **Settings → Capabilities**. Make sure **Code execution and file creation** is on.
3. Under **Skills**, choose **Upload skill** and select `igppt-skill.zip`. Turn the skill on.
4. Optional, to make it the default every time: in **Settings → Profile**, add to your personal preferences: "When I ask for a presentation, deck, slides or PPT, always use the IGPPT skill."

On Team and Enterprise plans an admin may need to allow skills first, and can share the skill with the whole organisation.

## Claude Code

Install for yourself across all projects:

```bash
npx skills add chintasurya/igppt -g -a claude-code
```

Optional: add the line "For any presentation, deck or slides, use the igppt skill." to `~/.claude/CLAUDE.md`.

## ChatGPT

Do not paste the `npx` command into ChatGPT; ChatGPT cannot run terminal commands. Download `chatgpt/igppt-skill.zip` and either upload it under ChatGPT **Skills → Create → Upload from your computer**, or add it to a custom GPT (Configure tab, Code Interpreter on). Steps are in `chatgpt/GPT-instructions.md`.

## Install from a downloaded copy (also adds the Copilot IGPPT agent)

Clone or download this repository, then run the installer from the downloaded folder:

Mac or Linux:

```bash
./install.sh /path/to/project
```

Windows PowerShell:

```powershell
.\install.ps1 -Project C:\path\to\project
```

This copies the skill to `.github/skills/igppt` and `.claude/skills/igppt`, adds the agent at `.github/agents/igppt.agent.md`, and installs `python-pptx`. For a personal install across all projects use `./install.sh --user` or `.\install.ps1 -User`.

To roll it out to a team, commit `.github/skills/igppt` and `.github/agents/igppt.agent.md` to the team's repository.

## Use

In Copilot chat (agent mode) choose the **IGPPT** agent, type `/igppt`, or just ask:

> Make a 7-slide Q3 update for the leadership call. Results: SLA 98%, 1,240 tickets, 312 story points. Risks: February platform release, one engineer leaving.

Paste a chat thread or email and ask for a deck from it; the agent works out the storyline itself.

Try the example yourself:

```bash
python igppt/scripts/make_deck.py igppt/examples/sample-deck.json sample.pptx
python igppt/scripts/make_deck.py igppt/examples/sample-deck.json sample-light.pptx --theme light
```

## Validation

`make_deck.py` saves a deck only when `validate.py` passes it. On FAIL nothing is saved, and every problem names the spec field to change, so the assistant fixes the spec and runs the same command again without a person stepping in. For example:

```text
FAIL  slide 3: spelling: 'buisness' (did you mean 'business'?): 'About 19 per buisness day.'
      fix: correct the spelling in slides[2].stats[1].text
FAIL  slide 6: text overflows its box by 0.34 in and crosses the edge of a card or shape: 'Moved every release onto...'
      fix: cut about 49 characters (or move some of it to another slide) in slides[5].steps[0].text
```

What fails: a deck not built by IGPPT or not on the IG template; any font other than Trenda IG Text; colours outside the IG palette; text that overflows into other text, crosses a card edge or sits over an icon; words broken across lines; titles that wrap; anything off the slide, past the margins or into the footer; shapes overlapping; em dashes, en dashes and `--` (fixed automatically in the spec); repeated words; leftover placeholder text; likely spelling mistakes; content the builder would have dropped. Unknown names are warnings; add correct ones to `igppt-words.txt` next to the spec.

Limits to know about:

- Text is measured with Inter's character widths, because the Trenda IG Text font files are not bundled. Measurements match LibreOffice renders closely and include a 2% safety margin, but Trenda in real PowerPoint may lay out a little differently. If you have the Trenda files, `python tools/make_font_metrics.py regular.otf bold.otf light.otf` rebuilds the widths from the real font.
- Spelling is English (US and UK spellings). It cannot judge grammar, wrong-but-real words ("form" for "from"), or whether a name is spelled right.
- The validator checks geometry and text; it does not look at the rendered picture. Use `--preview` for a final look when LibreOffice is installed.

## Microsoft 365 Copilot (Teams, Outlook)

This skill runs in assistants that can run Python in a workspace (GitHub Copilot agent mode, Copilot CLI, Claude Code). Microsoft 365 Copilot agents built in Copilot Studio cannot run it directly. To trigger decks from Teams or email, host `make_deck.py` behind an internal service (for example an Azure Function that takes a JSON spec and returns the `.pptx`) and call it from a Copilot Studio action, with this skill's `SKILL.md` and references as the agent's instructions.

## Notes

- Install the IG brand fonts (Trenda IG Text) to see the real typeface; otherwise a substitute is shown.
- The template and brand assets belong to Insight Global, Inc.
- Icons: Font Awesome Free, CC BY 4.0.

## Maintainers

After changing anything in `igppt/` or `copilot/`:

1. `python tools/test_igppt.py` (all tests must pass),
2. `python tools/make_manifest.py`,
3. rebuild `chatgpt/igppt-skill.zip` (the `igppt/` folder, without `__pycache__`),

then commit; the installer downloads the files listed in `manifest.json`.
