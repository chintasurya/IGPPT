# review.json format

Write the review as `review.json`, then run `scripts/check_review.py`. Every quote is checked word for word against the extracted documents, every outside fact needs a link, and all pricing and team-size maths is done by `scripts/calc.py`. Short fields (marked with a character limit) go onto slides, so keep them within the limit.

A **quote** is `{"file": "<file name as extracted>", "quote": "<words copied exactly from the document>"}`. Copy at least 4 words. Do not paraphrase, fix typos or join text from different places inside one quote. If the document says it in two places, pick one.

```json
{
  "customer": "ShieldForge",
  "opportunity": "Managed SOC staffing and automation",
  "review_date": "2026-11-12",
  "documents": [
    {"file": "ShieldForge RFP.docx", "role": "rfp"},
    {"file": "ShieldForge Proposal.pptx", "role": "proposal"},
    {"file": "Pricing.xlsx", "role": "pricing"}
  ],

  "summary": {
    "verdict": "needs work",                              // ready | needs work | not ready
    "headline": "Strong staffing story, weak on 24x7 cover",  // 90 characters max
    "points": ["Up to 3 short points, 120 characters max each"]
  },

  "requirements": [
    {"id": "R1", "text": "24x7 monitoring coverage",    // 90 max
     "priority": "must",                                 // must | should | could (from the RFP wording: must/shall = must)
     "source": {"file": "ShieldForge RFP.docx", "quote": "The supplier shall provide 24x7 monitoring"},
     "coverage": "partial",                              // met | partial | missing | unclear
     "proposal_evidence": {"file": "ShieldForge Proposal.pptx", "quote": "Place 6 certified SOC analysts"},
     "comment": "6 analysts cannot staff 24x7 without overtime"}  // 140 max
  ],

  "evaluation_criteria": [
    {"criterion": "Price", "weight": "30%", "source": {"file": "ShieldForge RFP.docx", "quote": "Price will account for 30%"}}
  ],

  "gaps": [
    {"title": "24x7 cover is understaffed",               // 40 max
     "detail": "Coverage math needs 9 to 11 FTE; the deck offers 6",   // 140 max
     "severity": "high",                                 // high | medium | low
     "requirement_ids": ["R1"],
     "fix": "Add a 3-shift roster and 4 more analysts, or price an on-call model",  // 140 max
     "say": "The RFP requires 24x7 monitoring. Two analysts on shift around the clock need about ten people once leave is counted, so six cannot hold that cover."}  // 80 to 450: the talk track the presenter reads aloud
  ],

  "research": {
    "performed": true,                                   // false if no web access: then findings is empty
    "method": "Copilot web search",                      // how it was done
    "findings": [
      {"topic": "customer",                              // customer | market | competitor | pricing
       "claim": "ShieldForge announced a cloud expansion in 2026",   // 160 max, one fact
       "source_url": "https://...", "source_title": "Press release", "accessed": "2026-11-12",
       "confidence": "verified"}                         // verified (primary source) | reported (news, secondary)
    ],
    "not_found": ["Questions you looked for and could not answer"]
  },

  "competitors": [
    {"name": "Example MSSP Inc.", "type": "likely bidder",   // named in RFP | likely bidder | alternative approach
     "offer": "Fully managed SOC with its own tooling",      // 120 max
     "source_url": "https://...",                            // required unless type is "alternative approach"
     "basis": "",                                            // for an alternative approach: why it is a real option
     "how_we_differ": "We staff inside their tools; no platform migration"}  // 120 max
  ],

  "differentiators": [
    {"title": "Analysts in 30 days",                     // 40 max
     "detail": "Placement within 30 days versus 74-day hiring today",  // 140 max
     "proof": {"file": "ShieldForge Proposal.pptx", "quote": "Place 6 certified SOC analysts within 30 days"},
     "strength": "proven",                               // proven (proof given) | claimed (no proof yet)
     "vs": "In-house hiring"}
  ],

  "staffing": {
    "proposed": [
      {"role": "SOC analyst", "count": 6, "source": {"file": "ShieldForge Proposal.pptx", "quote": "Place 6 certified SOC analysts"}},
      {"role": "Engagement manager", "count": 1, "in_scope_of_models": false, "source": {"file": "...", "quote": "..."}}
    ],
    "models": [
      {"name": "24x7 monitoring", "type": "coverage",
       "seats": 2, "hours_per_week": 168, "hours_per_fte_week": 40, "shrinkage": 0.2,
       "basis": {"seats": "assumption: 2 analysts on shift at all times for 4,500 alerts a day",
                 "hours_per_week": {"file": "ShieldForge RFP.docx", "quote": "The supplier shall provide 24x7 monitoring"},
                 "shrinkage": "assumption: 20% for leave, training and breaks"}},
      {"name": "Alert workload", "type": "workload",
       "volume": 4500, "period": "day", "days_per_week": 7, "minutes_per_item": 2, "automation_reduction": 0.4,
       "hours_per_fte_week": 40, "shrinkage": 0.2,
       "basis": {"volume": {"file": "ShieldForge RFP.docx", "quote": "4,500 security alerts per day"},
                 "minutes_per_item": "assumption: 2 minutes average triage per alert",
                 "automation_reduction": {"file": "ShieldForge Proposal.pptx", "quote": "40% fewer alerts reaching analysts"}}}
    ],
    "recommendation": "increase",                        // increase | decrease | keep
    "recommended_count": 10,
    "rationale": "Both models need more than 6 FTE once shrinkage is counted"   // 160 max
  },

  "pricing": {
    "currency": "USD",
    "lines": [
      {"item": "SOC analyst", "count": 6, "rate": 95, "unit": "hour", "quantity": 1040, "stated_total": 592800,
       "source": {"file": "Pricing.xlsx", "quote": "SOC Analyst 6 95 1040 592800"}}
    ],
    "stated_grand_total": 700000,
    "stated_grand_total_source": {"file": "Pricing.xlsx", "quote": "Total 700000"},
    "budget": {"amount": 650000, "source": {"file": "ShieldForge RFP.docx", "quote": "budget not to exceed $650,000"}},
    "benchmarks": [
      {"item": "SOC analyst", "low": 70, "high": 110, "unit": "hour",
       "source_url": "https://...", "source_title": "...", "accessed": "2026-11-12"}
    ],
    "assessment": "Rates are within the sourced range; the total is over budget"   // 160 max
  },

  "recommendations": [
    {"action": "Add 24x7 roster and 4 analysts", "why": "Coverage requirement R1 is not met with 6 FTE", "priority": "high",
     "say": "We recommend a three-shift roster with ten analysts because 24x7 cover is mandatory and the coverage maths shows six is not enough."}  // action 90 max, why 140 max, say 80 to 450
  ],
  "assumptions": ["Each 140 max"],
  "open_questions": ["Each 140 max: what to ask the customer or our team"]
}
```

`calc.py` units: `hour`, `day` (8 h), `week` (40 h), `month` (160 h, or set `hours_per_month`), `year` (1,920 h), `fixed`. `quantity` is the number of units per person over the contract (for example 1,040 hours for 6 months). Leave `stated_total` out if the document gives no total for that line.

Staffing models:
- `coverage`: seats that must be staffed at the same time x hours per week to cover / productive hours per FTE.
- `workload`: items per period x minutes per item, less automation / productive hours per FTE.
`shrinkage` is the share of paid time not available for the work (leave, training, meetings); 0.2 is a common planning figure but it is an assumption unless a document states it. Every numeric input needs an entry in `basis`: a quote, or a string starting with `assumption:`.
