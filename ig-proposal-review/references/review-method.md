# Review method and checklists

## 1. Understanding the ask

Read the RFP (and SOW, Q&A answers, emails) end to end. Capture, each with a quote:

| What | Where it usually is | Why it matters |
|---|---|---|
| Mandatory requirements ("must", "shall", "required") | Scope, requirements, technical sections | A missing one can disqualify the bid |
| Desirable requirements ("should", "preferred") | Same | Scored, not pass/fail |
| Evaluation criteria and weights | "Evaluation", "Award", "Scoring" | Tells you what to emphasise; price weight sets the pricing strategy |
| Budget or price ceiling | Commercial section | Over-budget bids are often rejected |
| Volumes and service levels (tickets, alerts, users, hours, response times) | Scope, SLAs | Inputs for the team-size model |
| Coverage hours (business hours, 24x7, on-call) | Scope, SLAs | Coverage model input |
| Team, skills, certifications, clearances, location | Staffing, personnel | Gaps here are common and costly |
| Timeline, start date, milestones, transition | Schedule | Feasibility of mobilisation |
| Submission rules (format, page limits, deadline, forms) | Instructions to bidders | Non-compliance can disqualify |
| Contract terms that carry risk (penalties, liability, IP, non-solicit) | Terms | Risks to price or flag |

Write each requirement as one short line, in the customer's terms. Split compound requirements ("24x7 monitoring and monthly reporting") into separate items.

## 2. Coverage

| Coverage | Use when |
|---|---|
| met | The proposal clearly answers it; quote the proposal |
| partial | It answers part of it, or answers without the required detail, numbers or proof |
| missing | Nothing in the proposal addresses it |
| unclear | The requirement itself is ambiguous; turn it into an open question for the customer |

## 3. Gap severity

| Severity | Meaning |
|---|---|
| high | A mandatory requirement or a heavily weighted criterion is missing or wrong; a disqualification risk; a pricing or staffing error that changes the bid |
| medium | A scored item is weak; a claim lacks proof; a risk is not addressed |
| low | Wording, order, clarity or presentation |

## 4. Research checklist

Customer: what they do, size (employees, revenue if public), locations, recent news (funding, acquisitions, layoffs, incidents, leadership changes), stated strategy, technology they use, past suppliers if public, and why this RFP now.

Competition: named incumbents; firms that typically bid for this work in this market and region; alternative approaches the customer could choose instead (hire directly, offshore, a managed service, a software tool, do nothing). For each: what they offer, their likely strengths, and our angle.

Sources: the company's own website, annual reports and filings, press releases, reputable news. Note the date; prefer the last 24 months. Job boards and review sites are weak signals: mark them `reported`. Never treat search-result snippets as confirmed without opening the page.

## 5. Differentiators

A strong differentiator is specific (numbers, names, timeframes), relevant to a stated criterion, provable (case study, metric, certification, existing relationship), and hard for a competitor to claim. Weak ones are adjectives ("experienced", "flexible", "world-class"). For each competitor or alternative, write one line: why the customer should choose us over that option.

## 6. Team size

Use the RFP's numbers wherever they exist.

- **Coverage model**: FTE = seats x hours to cover per week / (paid hours per FTE per week x (1 - shrinkage)). 24x7 is 168 hours a week; business hours are often 40 to 50.
- **Workload model**: FTE = items per week x (1 - automation share) x minutes per item / 60 / (paid hours x (1 - shrinkage)).
- Shrinkage (leave, training, meetings, sickness) is commonly planned at 15% to 30%; state the figure you use as an assumption unless a document gives it.
- `calc.py` reports a range using shrinkage 15% to 30% and minutes per item plus or minus 25%. Recommend **increase** when the proposal is below the range, **decrease** when above it, **keep** when inside it, and name the roles (for example a team lead for every 8 to 10 analysts is a common span of control; say it is an assumption).
- Roles outside the models (managers, trainers) can be listed with `"in_scope_of_models": false`.

## 7. Pricing

Check, in this order:
1. **Arithmetic**: each line and the total (done by `calc.py`).
2. **Consistency**: the same rates, hours and team size across the deck, the pricing sheet and the staffing plan.
3. **Budget**: price against any stated budget or ceiling.
4. **Market**: rates against benchmarks, only with sources (published rate surveys, government rate schedules, our own rate card if the user shares it). Without a source, say "no benchmark available" and suggest where to get one.
5. **Risk**: penalties, overtime, ramp-up, transition, travel and tooling costs that the price does not cover.
6. **Fit**: given the evaluation weight on price, would a lower or higher price, a different model (fixed fee, outcome-based, phased) or options (good, better, best) help?

## 8. Recommendations

Each recommendation is an action a bid team can take this week, with the reason and priority. Order: disqualification risks, then high-weight criteria, then pricing and staffing, then presentation.
