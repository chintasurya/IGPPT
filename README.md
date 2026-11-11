# IGPPT skill

Lets an AI assistant build any PowerPoint deck in Insight Global branding: status updates, proposals, kickoffs, QBRs, training, demos, pitches. The IG template, fonts, colours, icons and slide designs are bundled, so nobody uploads a template.

The assistant writes a short JSON list of slides; the skill turns it into a finished, editable `.pptx` on the IG template (dark or light), with layout and font sizes handled automatically.

It follows the open Agent Skills format (a folder with `SKILL.md`), so the same folder works in GitHub Copilot (VS Code agent mode, Copilot CLI, Copilot cloud agent) and Claude Code.

## Package contents

| Path | What it is |
|---|---|
| `igppt/SKILL.md` | Instructions the assistant loads |
| `igppt/references/deck-recipes.md` | Storylines for common deck requests |
| `igppt/references/spec-format.md` | Every slide type and field |
| `igppt/references/ig-brand.md` | IG layouts, colours, fonts, icons |
| `igppt/scripts/build_deck.py` | Builds a deck from a JSON spec |
| `igppt/scripts/ig_kit.py` | Library behind it, for custom slides |
| `igppt/scripts/render_preview.py` | Slide images for checking (needs LibreOffice) |
| `igppt/scripts/deck_text.py` | Reads an existing deck's text |
| `igppt/assets/ig-template.pptx` | The IG template (layouts only) |
| `igppt/examples/sample-deck.json` | A 13-slide example using every main slide type |
| `copilot/agents/igppt.agent.md` | "IGPPT" custom agent for Copilot |
| `chatgpt/GPT-instructions.md` | Set-up and instructions for a ChatGPT custom GPT |
| `chatgpt/igppt-skill.zip` | The skill packed for upload to a custom GPT |

## Install (one command, any AI tool)

Run this in a terminal inside the project where you want the skill. It needs Node.js (for `npx`), git, and Python 3.9+ for building decks. No GitHub login is needed.

```bash
npx skills add chintasurya/igppt
```

It asks which AI tools to install into. To choose them in the command instead:

```bash
npx skills add chintasurya/igppt -a github-copilot -a claude-code -a codex -a cursor -a gemini-cli --copy -y
```

Add `-g` to install for yourself across all projects. Then install the one Python library:

```bash
pip install python-pptx
```

This uses the open-source [skills CLI](https://github.com/vercel-labs/skills), which supports GitHub Copilot, OpenAI Codex, Claude Code, Cursor, Gemini CLI and many more. Skills land in `.agents/skills/igppt` (shared by Copilot, Codex, Cursor and Gemini CLI) and `.claude/skills/igppt`.

Update later with `npx skills update`; remove with `npx skills remove igppt`.

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
python igppt/scripts/build_deck.py igppt/examples/sample-deck.json sample.pptx
python igppt/scripts/build_deck.py igppt/examples/sample-deck.json sample-light.pptx --theme light
```

## Microsoft 365 Copilot (Teams, Outlook)

This skill runs in assistants that can run Python in a workspace (GitHub Copilot agent mode, Copilot CLI, Claude Code). Microsoft 365 Copilot agents built in Copilot Studio cannot run it directly. To trigger decks from Teams or email, host `build_deck.py` behind an internal service (for example an Azure Function that takes a JSON spec and returns the `.pptx`) and call it from a Copilot Studio action, with this skill's `SKILL.md` and references as the agent's instructions.

## Notes

- Install the IG brand fonts (Trenda IG Text) to see the real typeface; otherwise a substitute is shown.
- The template and brand assets belong to Insight Global, Inc.
- Icons: Font Awesome Free, CC BY 4.0.
