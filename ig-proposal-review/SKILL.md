---
name: ig-proposal-review
description: Reviews an Insight Global proposal against the customer's RFP and documents. Extracts the customer's requirements, researches the customer and competing options with cited sources, finds gaps, sharpens differentiators, checks the team size and pricing with calculations, and produces a review report, an IG review deck and (on request) a corrected proposal deck built with the igppt skill. Use for any request to review, check, critique, score, red-team or improve a proposal, bid, RFP or RFI response, SOW or pricing.
---

# IG proposal review

Turns shared documents (RFP, RFI, SOW, emails, the proposal deck, pricing sheets, team plans) into an honest, evidence-based review: what the customer asked for, where the proposal falls short, how it compares with the competition, whether the team size and price hold up, and exactly what to change.

## The honesty rules (they override everything else)

1. **Quote, do not paraphrase.** Every statement about what the RFP or the proposal says carries a word-for-word quote. `check_review.py` rejects any quote it cannot find in the documents.
2. **No source, no fact.** Anything from outside the documents (company facts, news, competitors, market rates) needs a web link and access date. If you cannot find a source, put the question in `research.not_found` or `open_questions`. Never present general knowledge or memory as a fact.
3. **Never invent numbers.** No made-up competitor prices, market rates, volumes, budgets or win probabilities. A figure is either quoted, sourced, calculated by `calc.py`, or labelled `assumption:` with the reason.
4. **Calculate, do not estimate.** All pricing and team-size maths is done by `scripts/calc.py` (run by `check_review.py`). Use its numbers, not your own.
5. **Say what you could not do.** Unreadable files, scanned pages, no web access, missing pricing: say so in the review and the reply.
6. **Be direct.** If the proposal is weak, say so and why. If it is strong, say that. No flattery and no generic advice ("strengthen the value proposition").

## Tools

Scripts are in this skill's `scripts/` folder. Write all working files (corpus, review.json, decks) to a writable folder: `/mnt/data` if it exists, otherwise the current folder.

```bash
python scripts/extract_docs.py <files or folder> --out corpus          # 1. read every document, with page/slide markers
python scripts/check_review.py review.json --corpus corpus             # 2. verify quotes, sources and maths (repeat until PASS)
python scripts/review_to_deck.py review.checked.json "<Customer> Proposal Review.pptx"   # 3. IG review deck via igppt
```

The decks need the **igppt** skill (installed next to this one). The corrected proposal deck is built with igppt's `make_deck.py` directly.

## Workflow

1. **Collect and read.** Run `extract_docs.py` on every shared file. Read all of the extracted text, not just the first pages. Note every `PROBLEM` line (unreadable files, scanned pages).
2. **Understand the ask.** From the RFP and related documents, list every requirement with its quote and priority (must/shall/required = must; should = should; may/could/nice to have = could). Also capture: evaluation criteria and weights, budget, timeline and deadlines, mandatory formats or page limits, team or certification requirements, volumes and service levels, and anything that disqualifies a bid. See `references/review-method.md`.
3. **Research** (only with a web search tool; otherwise set `"research": {"performed": false}` and continue):
   - the customer: business, size, recent news, priorities, technology, anything that explains why they are buying;
   - the competition: firms named in the documents, likely bidders for this kind of work, and alternative approaches (in-house hiring, another delivery model, a software product). For each, what they offer and how we differ.
   Cite every finding. Prefer primary sources (the company's own site, filings, press releases) and mark news or secondary sources as `reported`.
4. **Review the proposal.** For each requirement: met, partial, missing or unclear, with the proposal quote that shows it. Then list the gaps (severity high, medium, low) with a concrete fix each. Look also for: unanswered evaluation criteria, missing mandatory items, inconsistent numbers, vague claims, risks we take on without pricing them, and anything that would confuse an evaluator.
5. **Differentiators.** Keep only what is specific, true and provable for this customer, tied to their evaluation criteria (for example "analysts placed in 30 days versus their 74-day hiring time"). Mark each `proven` (with a quote or source) or `claimed`. Flag generic claims every bidder makes. Say how to stand out against each competitor or alternative.
6. **Team size.** Build at least one staffing model from the documents (`coverage` for hours that must be staffed, `workload` for volumes) in `review.json`. Every input is quoted or an explicit assumption. `check_review.py` calculates the need and a range; recommend increase, decrease or keep, and say which roles.
7. **Pricing.** Enter every price line exactly as the pricing document states it. `check_review.py` recalculates each line and the total, the blended hourly rate, the difference from any stated budget, and the position against market benchmarks, but only benchmarks with a source link. Judge whether the price fits the scope and the risk (too low means delivery risk; over budget means it may be rejected). If no benchmark can be sourced, say so; do not guess a market rate.
8. **Write the talk track.** Every gap and every recommendation gets a `say` field: one to three sentences the presenter can read aloud on a call, stating what is missing or what we propose, why it matters to this customer, and the evidence (the quote, number or source). `check_review.py` fails a gap or recommendation without one. `review.md` lists them under "Talk track".
9. **Write `review.json`** in the format in `references/review-schema.md`, then run `check_review.py`. On FAIL, fix each listed item (copy quotes exactly, add sources or remove the claim, correct inputs) and run it again until it prints PASS. It writes `review.checked.json` and the full report `review.md`.
10. **Build the review deck** with `review_to_deck.py`. It writes an IGPPT spec and runs igppt's `make_deck.py`, which validates the deck. If it fails, shorten the fields it names in `review.json`, rerun `check_review.py`, then this step.
11. **Corrected proposal deck** (when the user asks for it, or offer it): write an IGPPT spec that keeps the original deck's order and wording where it is fine and applies the recommended changes. Read the original with the extracted corpus. Set `"talk_track": true`: each slide's `notes` (speaker notes, never on the slide) says what changed, what was missing before, and why the change is stronger, with the evidence. Show the solution once: one `architecture` slide, one `flow`, one `roles`; never repeat a view, and leave icons out unless they carry meaning. Do not add facts or numbers that are not in the documents or the checked review. Build it with igppt: `python <igppt>/scripts/make_deck.py corrected.json "<Customer> Proposal (revised).pptx"` and repeat until SAVED.
12. **Reply** with: the verdict in one line; the top gaps; the team-size and pricing conclusions with their numbers; how to stand out; what could not be checked (files, research, benchmarks); and the files (review.md, review deck, corrected deck).

## What good looks like

- A requirement table that an evaluator would recognise as their own RFP.
- Gaps that name the requirement, the evidence and the fix.
- Differentiators a competitor could not copy onto their own slide.
- A team size and a price with visible working, so the bid team can challenge the inputs rather than the arithmetic.
- A clear list of what is unknown and who should answer it.
