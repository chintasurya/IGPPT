# IGPPT agents in Microsoft 365 Copilot

Two agents, each set up once and then shared. People who use them only open the agent and type.

- **Part A: IGPPT**, which builds Insight Global decks. Skill: `igppt-m365-skill.zip`.
- **Part B: IG Proposal Review**, which reviews a proposal against the RFP and builds a review deck and a corrected deck. Skills: `ig-proposal-review-m365-skill.zip` and `igppt-m365-skill.zip`.

# Part A: IGPPT

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

Learning from feedback:
- At the start of every chat, before the first deck: write the IGPPT-LESSONS block at the end of these instructions (if there is one), exactly as it is, to /mnt/data/igppt-lessons-block.txt, then run: python <igppt skill folder>/scripts/learn.py start. Follow every lesson it lists. If it reports a PROBLEM with the block, copy the block again exactly.
- When the user says something is wrong, record a lesson with learn.py add (see the skill's SKILL.md, "Learning from feedback"), fix the spec and rebuild until SAVED. Then run learn.py export and show the user the block, so the agent owner can paste it here.

(Lessons block: the agent owner pastes the latest block from learn.py export below this line, replacing the old one.)

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

### Making lessons last across chats

Microsoft 365 Copilot wipes the agent's working folder after each chat, so a lesson is kept in one of these places:

1. **The agent's instructions (recommended; about a minute, no re-upload).** After learning, the agent shows a block that starts with `<<<IGPPT-LESSONS` and ends with `IGPPT-LESSONS>>>`. The agent owner opens the agent, **Edit**, **Configure**, and pastes the block at the very end of **Instructions**, replacing the previous block (the newest block always contains every lesson learned in that chat plus those it loaded). Select **Update**. Every new chat, for every user, loads it. The block has a count and checksum, so if it is copied wrongly the agent says so instead of loading half of it. Instructions have a length limit (about 8,000 characters); when the block grows large, use option 3 and clear the block.
2. **GitHub (automatic when the sandbox has internet).** At the start of each chat the agent downloads `igppt/assets/lessons.json` from the repository. If your Copilot sandbox can reach GitHub, lessons merged there apply everywhere without touching the agent. If it cannot, the agent says so and uses options 1 and 3.
3. **The skill itself (permanent).** The owner runs `python tools/merge_lessons.py <block.txt or igppt-lessons.json>`, rebuilds the zips (`python tools/build_zips.py`), and re-uploads `igppt-m365-skill.zip`.

A user can also attach `igppt-lessons.json` (or a text file with a block) to a chat; it is loaded for that chat.

Fully automatic sharing (the agent saving lessons to SharePoint for everyone by itself) needs a Copilot Studio agent with a Power Automate flow; Agent Builder agents cannot write files outside the chat.

When IGPPT changes, download the new `igppt-m365-skill.zip`, edit the agent, remove the old igppt skill, upload the new zip, and select **Update**. Everyone the agent is shared with gets the new version. Do the same in the Proposal Review agent, which also uses the igppt skill.

# Part B: IG Proposal Review

A separate agent keeps each one simple: IGPPT for making decks, this one for reviewing bids.

## 1. Download both skill packages

- https://github.com/chintasurya/igppt/raw/main/copilot/ig-proposal-review-m365-skill.zip
- https://github.com/chintasurya/igppt/raw/main/copilot/igppt-m365-skill.zip (the review and corrected decks are built with it)

## 2. Create the agent

1. **Agents** → **Create agent** → **Configure** tab.
2. **Name:** `IG Proposal Review`
3. **Description:** `Reviews a proposal against the customer's RFP: requirements, gaps, competition, differentiators, team size and pricing, with quotes and sources. Produces a review report, an IG review deck and a corrected deck.`
4. **Instructions:** paste the box below.
5. **Skills:** upload both zips. Remove any skill Copilot created by itself.
6. **Capabilities:** turn on **Create documents, charts, and code**.
7. **Web search:** turn on searching the web (under Knowledge), if your organisation allows it. Without it the agent reviews only the shared documents and says that no outside research was done.
8. **Starter prompts:** add the four below. Then **Create**, test, and **Share**.

### Instructions

```
You review Insight Global proposals. For every review use the ig-proposal-review skill; for every deck use the igppt skill.

1. Read the ig-proposal-review skill's SKILL.md, then references/review-method.md and references/review-schema.md.
2. Find the files the user shared (often in /mnt/data; run ls if unsure) and run the skill's extract_docs.py on all of them. Read all of the extracted text.
3. Follow the skill's workflow: the customer's requirements, research on the customer and the competition (web search, with links), coverage and gaps, differentiators, team size and pricing.
4. Write review.json and run check_review.py. Fix every FAIL it lists and run it again until it prints PASS.
5. Build the review deck with review_to_deck.py until it prints SAVED.
6. If the user asks for a corrected proposal deck (offer it if they did not), write an igppt spec from the original deck plus the recommended changes and build it with the igppt skill's make_deck.py until SAVED. Note each change in that slide's speaker notes.
7. Reply with: the verdict, the top gaps, the team-size and pricing results with their numbers, how to stand out against the competition, what could not be checked, and the files (review.md, review deck, corrected deck).

Honesty rules, always:
- Quote the documents word for word; check_review.py rejects quotes it cannot find.
- Every fact from outside the documents needs a web link and date. No link, no fact: list it as an open question.
- Never invent numbers, competitor prices, market rates or win chances. Pricing and team-size maths comes from the skill's scripts.
- Say plainly what you could not read, find or check.
```

### Starter prompts

| Title | Prompt |
|---|---|
| Review a proposal | Review our proposal against the attached RFP. Find the gaps and tell me how to stand out. |
| Team size and pricing | Check whether the team size and pricing in our proposal hold up against the RFP. |
| Competition | Who are we likely competing against for this RFP, and how do we stand out? |
| Review and fix | Review the attached proposal and give me a corrected IG version of the deck. |

## 3. Test

Attach an RFP (Word or PDF), the proposal deck (PowerPoint) and the pricing (Excel), then use "Review a proposal". A correct run shows the agent running `extract_docs.py`, `check_review.py` (until PASS), and `review_to_deck.py` (SAVED). You get `review.md` and an IG review deck: verdict, requirement coverage, gaps, competition, differentiators, team size, pricing check, recommended changes, questions and assumptions.

Things it will not do, by design: guess a market rate, name a competitor without a source, or quote the RFP from memory.
