# IGPPT agent in Microsoft 365 Copilot

Set it up once, then share the agent. People who use it only open the agent and type.

You need: Microsoft 365 Copilot (Agent Builder) with **skills** available in your tenant. Microsoft has described skills as a preview feature in some tenants; if you do not see "Skills" when editing an agent, ask IT.

## 1. Download the skill package

Download `igppt-m365-skill.zip` from this folder:
https://github.com/chintasurya/igppt/raw/main/copilot/igppt-m365-skill.zip

Do not unzip it. `SKILL.md` is at the root of the zip, which is what Agent Builder requires. (The `chatgpt/igppt-skill.zip` file has a folder inside and will not work here.)

## 2. Create the agent (or edit the one you made)

1. In Microsoft 365 Copilot, open **Agents**, then **Create agent** (or open your agent and choose **Edit**).
2. Switch to the **Configure** tab.
3. **Name:** `IGPPT`
4. **Description:** `Creates Insight Global branded PowerPoint decks from your notes, emails or numbers. Every deck is built on the IG template and checked before you get it.`
5. **Instructions:** paste everything in the "Instructions" box below.
6. **Skills:** if a skill called `igppt-deck-builder` (or any other PowerPoint skill) is listed, **remove it**. Copilot made that one by itself; it does not use the IG template. Then add a skill and upload `igppt-m365-skill.zip`.
7. **Capabilities:** turn on **Create documents, charts, and code** (code interpreter). The skill runs Python.
8. **Starter prompts:** add the four below.
9. Select **Create** (or **Update**), test it, then **Share** it with leadership.

### Instructions

```
You build Insight Global branded PowerPoint decks. You have one tool for this: the igppt skill. Always use it, for every deck.

How to make a deck:
1. Read the igppt skill's SKILL.md, then references/deck-recipes.md and references/spec-format.md from the same skill.
2. Work out purpose, audience, length and key messages from the request, pasted notes, email or files. Use sensible defaults instead of asking. List your assumptions.
3. Write the slides as a JSON spec (deck.json) in a writable folder (/mnt/data if it exists).
4. Run: python <igppt skill folder>/scripts/make_deck.py deck.json <Name>.pptx
5. If it prints FAIL, each problem names the spec field to change and how. Change deck.json and run the same command again, until it prints SAVED. Fix problems yourself; never ask the user to fix them. After 5 failed attempts, show the user what is left.
6. Give the user the saved .pptx to download, the slide list, and any assumptions or [placeholders] to confirm.

Never:
- write your own python-pptx, pptxgenjs, HTML or Office code to make slides
- use any other PowerPoint skill or template, or start from a blank presentation
- edit the .pptx after make_deck.py saved it
- invent numbers, use em dashes, or put one client's data in another client's deck
If the igppt skill cannot run here, say so plainly and give the JSON spec instead of a deck.
```

### Starter prompts

| Title | Prompt |
|---|---|
| Quarterly update | Make a 6-slide Q3 update deck for the leadership call. Here are the results, risks and Q4 plans: |
| Deck from an email | Turn this email or chat thread into a short IG deck for leadership: |
| Proposal | Create a 5-slide proposal deck for this client. Problem, our solution, timeline, team, next steps: |
| Change a deck | Change my last deck: |

## 3. Test

Ask: `Create a 3-slide solution design deck for ShieldForge` with the test notes. A correct run shows the agent running `make_deck.py` and printing `SAVED`. The deck has the IG title slide, the black and gradient IG backgrounds, the IG footer logo and page numbers.

If you see it running a script called `main.py`, or slides with a plain black background and Calibri text, it is not using the IGPPT skill: check step 6 again.

## Updating later

When IGPPT changes, download the new `igppt-m365-skill.zip`, edit the agent, remove the old igppt skill, upload the new zip, and select **Update**. Everyone the agent is shared with gets the new version.
