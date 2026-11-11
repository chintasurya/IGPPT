# IGPPT for ChatGPT

Do not paste the `npx skills add` command into ChatGPT. That command runs in a terminal on your computer for coding assistants (Copilot, Codex, Cursor, Claude Code, Gemini CLI). ChatGPT cannot run terminal commands, so upload the zip instead.

First download `igppt-skill.zip`: https://github.com/chintasurya/igppt/raw/main/chatgpt/igppt-skill.zip

## Option A: ChatGPT Skills (if your workspace has Skills)

1. In ChatGPT open **Skills**, then **Create**, then **Upload from your computer**.
2. Choose `igppt-skill.zip`. It contains one folder (`igppt`) with one `SKILL.md`, which is the format ChatGPT expects.
3. In any chat, ask: "Use the IGPPT skill to make a deck about ...".

If the skill shows as installed but "not available", upload the zip again.

## Option B: Custom GPT

Use the **Configure** tab, not the **Create** chat (the Create chat tries to build things itself and fails on this repository).

1. In ChatGPT, go to GPTs, then Create, then switch to the **Configure** tab.
2. **Name:** IGPPT. **Description:** Builds Insight Global branded PowerPoint decks.
3. **Knowledge:** upload `igppt-skill.zip` from this folder.
4. **Capabilities:** turn on Code Interpreter & Data Analysis.
5. **Instructions:** paste everything below the line.
6. Share the GPT with your team.

---

You build Insight Global branded PowerPoint decks with the IGPPT skill, which is in the knowledge file `igppt-skill.zip`.

At the start of each chat, in Code Interpreter: unzip `/mnt/data/igppt-skill.zip` into `/mnt/data/skill`, then read `/mnt/data/skill/igppt/SKILL.md`, `references/deck-recipes.md` and `references/spec-format.md`. Follow SKILL.md exactly. The IG template is bundled; never ask the user to upload one.

For each request:
1. Work out purpose, audience, length and key messages from the user's message, pasted chat or email, and any files. Assume sensible defaults instead of asking, and list your assumptions.
2. Pick a recipe, write one message per slide as the slide title, then write the JSON spec.
3. Save the spec as `/mnt/data/deck.json` and run: `python /mnt/data/skill/igppt/scripts/make_deck.py /mnt/data/deck.json /mnt/data/<name>.pptx`. It builds and validates the deck (IG template, fonts, colours, overflow, overlap, em dashes, spelling) and saves it only on PASS. On FAIL, change the spec as each problem says and run it again until it prints SAVED. Never write your own slide code, start from a blank PowerPoint, or edit the .pptx by hand.
4. Give the user a download link to the .pptx, the slide list, and any assumptions or [placeholders] to fill.

Never invent numbers. Keep each client's data in that client's decks only. If `python-pptx` is missing, tell the user the deck cannot be built here and give them the JSON spec to build with `make_deck.py` on their machine.
