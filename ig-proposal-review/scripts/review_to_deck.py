"""Turn a checked review into an Insight Global review deck, built and validated by the IGPPT skill.

    python review_to_deck.py review.checked.json <name>.pptx [--spec review-deck.json]

Run check_review.py first; it writes review.checked.json. This script writes the IGPPT spec (review-deck.json)
and runs IGPPT's make_deck.py on it, so the deck is on the IG template and validated. It needs the igppt skill
next to this one (any folder whose scripts/make_deck.py belongs to IGPPT), or set IGPPT_SCRIPTS to its scripts folder.
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEV_COLOR = {"high": "magenta", "medium": "yellow", "low": "cyan"}
COV_ORDER = {"missing": 0, "partial": 1, "unclear": 2, "met": 3}
PRI_ORDER = {"must": 0, "should": 1, "could": 2, "high": 0, "medium": 1, "low": 2}


def find_igppt():
    env = os.environ.get("IGPPT_SCRIPTS")
    cands = [Path(env) / "make_deck.py"] if env else []
    skills_dir = HERE.parent.parent
    cands += sorted(skills_dir.glob("*/scripts/make_deck.py")) + sorted(skills_dir.glob("*/*/scripts/make_deck.py"))
    for root in (Path.cwd(), Path("/mnt"), Path("/home/oai/skills"), Path.home() / ".claude" / "skills",
                 Path.home() / ".copilot" / "skills", Path.home() / ".agents" / "skills"):
        for depth in ("*", "*/*", "*/*/*"):                    # shallow search only
            try:
                cands += sorted(root.glob(f"{depth}/scripts/make_deck.py"))
            except OSError:
                pass
    for c in cands:
        if c.exists() and (c.parent / "validate.py").exists():
            return c
    return None


def money(v, cur):
    return f"{cur} {v:,.0f}".strip()


def short(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "..."


def build_spec(r):
    cur = (r.get("pricing") or {}).get("currency", "")
    date = r.get("review_date") or dt.date.today().isoformat()
    try:
        date = dt.date.fromisoformat(date).strftime("%d %B %Y").lstrip("0")
    except ValueError:
        pass
    reqs = r.get("requirements", [])
    gaps = sorted(r.get("gaps", []), key=lambda g: PRI_ORDER.get(g.get("severity"), 3))
    res = r.get("research") or {}
    slides, sections = [], []

    def add(slide, section):
        slides.append(slide); sections.append(section)

    add({"type": "title", "title": f"{r['customer']} Proposal Review", "subtitle": short(r.get("opportunity", ""), 80), "date": date},
        "customer, opportunity")

    # 1. readiness at a glance
    met = sum(q.get("coverage") == "met" for q in reqs)
    part = sum(q.get("coverage") == "partial" for q in reqs)
    miss = sum(q.get("coverage") == "missing" for q in reqs)
    tiles = [{"value": f"{met}/{len(reqs)}", "label": "Requirements met", "text": f"{part} partial, {miss} missing."},
             {"value": str(sum(g.get("severity") == "high" for g in gaps)), "label": "High-severity gaps",
              "text": f"{len(gaps)} gaps in total.", "color": "magenta"}]
    stc = ((r.get("staffing") or {}).get("check")) or {}
    if stc.get("calculated_fte") is not None:
        tiles.append({"value": f"{stc['proposed_fte']:g} vs {stc['calculated_fte']:g}", "label": "FTE proposed vs needed",
                      "text": f"Recommendation: {r['staffing'].get('recommendation', stc.get('calculated_verdict'))}."})
    prc = ((r.get("pricing") or {}).get("check")) or {}
    if prc.get("budget") is not None:
        tiles.append({"value": f"{prc['budget_difference_pct']:+.0f}%", "label": "Price vs budget",
                      "text": f"Budget {money(prc['budget'], cur)}.",
                      "color": "magenta" if prc["budget_difference_pct"] > 0 else "green"})
    elif prc:
        tiles.append({"value": str(len(prc.get("flags", []))), "label": "Pricing issues found",
                      "text": f"Total {money(prc['computed_grand_total'], cur)}."})
    verdict = r["summary"].get("verdict", "").title()
    note = None if res.get("performed") else "No outside research was done for this review (no web access)."
    s = {"type": "stats", "eyebrow": "Summary", "title": f"Verdict: {verdict}", "subtitle": r["summary"].get("headline", ""),
         "stats": tiles[:4], "notes": "\n".join(r["summary"].get("points", []))}
    if note:
        s["note"] = note
    add(s, "summary, requirements coverage, gaps, staffing, pricing")

    # 2. requirement coverage
    rows = sorted(reqs, key=lambda q: (PRI_ORDER.get(q.get("priority"), 3), COV_ORDER.get(q.get("coverage"), 4)))
    shown = rows[:10]
    s = {"type": "table", "eyebrow": "The ask", "title": "How the Proposal Covers the Ask",
         "columns": ["ID", "Requirement", "Priority", "Coverage"],
         "rows": [[q["id"], short(q["text"], 70), q.get("priority", "").title(), q.get("coverage", "").title()] for q in shown],
         "widths": [1, 7, 1.6, 1.6],
         "notes": "\n".join(f"{q['id']}: {q['comment']}" for q in shown if q.get("comment"))}
    if len(rows) > len(shown):
        s["note"] = f"Showing {len(shown)} of {len(rows)} requirements, most important first. Full list in the review report."
    add(s, "requirements (text 90 max)")

    # 3. research about the customer
    finds = [f for f in res.get("findings", []) if f.get("topic") in ("customer", "market")][:5]
    if finds:
        add({"type": "bullets", "eyebrow": "Research", "title": f"What We Learned About {short(r['customer'], 22)}",
             "bullets": [short(f["claim"], 160) for f in finds], "note": "Sources and access dates are in the review report.",
             "notes": "\n".join(f"{f['claim']} | {f['source_url']}" for f in finds)}, "research.findings (claim 160 max)")

    # 4. gaps
    if gaps:
        cards = [{"title": g["title"], "text": g.get("detail", ""), "tag": g.get("severity", "").title(),
                  "color": SEV_COLOR.get(g.get("severity"), "cyan"), "icon": "warning"} for g in gaps[:6]]
        if len(cards) == 1:
            cards.append({"title": "No other gaps found", "text": "Every other requirement is met or unclear.", "icon": "check-circle"})
        add({"type": "cards", "eyebrow": "Gaps", "title": "Gaps to Close Before Submission", "cards": cards,
             "notes": "\n".join(f"{g['title']}: fix: {g.get('fix', '')}" for g in gaps[:6])}, "gaps (title 40, detail 140 max)")

    # 5. competition
    comps = r.get("competitors", [])[:6]
    if comps:
        add({"type": "table", "eyebrow": "Competition", "title": "Competitors and Alternatives",
             "columns": ["Competitor or alternative", "What they offer", "How we differ"],
             "rows": [[short(c["name"], 40), short(c.get("offer", ""), 120), short(c.get("how_we_differ", ""), 120)] for c in comps],
             "widths": [2, 4, 4],
             "notes": "\n".join(f"{c['name']}: {c.get('source_url') or c.get('basis', '')}" for c in comps)},
            "competitors (offer, how_we_differ 120 max)")

    # 6. differentiators
    diffs = sorted(r.get("differentiators", []), key=lambda d: d.get("strength") != "proven")[:6]
    if diffs:
        cards = [{"title": d["title"], "text": d.get("detail", ""), "tag": "Proven" if d.get("strength") == "proven" else "Unproven",
                  "color": "green" if d.get("strength") == "proven" else "orange", "icon": "flag"} for d in diffs]
        if len(cards) == 1:
            cards.append({"title": "Find more proof points", "text": "Only one differentiator has evidence so far.", "icon": "search"})
        add({"type": "cards", "eyebrow": "Differentiators", "title": "Where We Stand Out", "cards": cards},
            "differentiators (title 40, detail 140 max)")

    # 7. team size
    st = r.get("staffing") or {}
    if stc.get("models"):
        tiles = [{"value": f"{stc['proposed_fte']:g}", "label": "FTE proposed", "text": "In the modelled roles."}]
        tiles += [{"value": f"{m['fte']:g}", "label": short(m["name"], 28), "text": f"Range {m['range'][0]:g} to {m['range'][1]:g} FTE."}
                  for m in stc["models"][:2]]
        if st.get("recommended_count"):
            tiles.append({"value": f"{st['recommended_count']:g}", "label": "Recommended", "text": f"{st.get('recommendation', '').title()} the team.",
                          "color": "green"})
        rec = st.get("recommendation", stc.get("calculated_verdict", "keep"))
        title = {"increase": "Team Size Should Increase", "decrease": "Team Size Can Come Down", "keep": "Team Size Holds Up"}[rec]
        add({"type": "stats", "eyebrow": "Team size", "title": title, "stats": tiles[:4], "note": short(st.get("rationale", ""), 160),
             "notes": "\n".join(f"{m['name']}: {m['formula']} = {m['fte']} FTE" for m in stc["models"])},
            "staffing (rationale 160 max)")

    # 8. pricing
    if prc.get("lines"):
        rows = []
        for ln in prc["lines"][:9]:
            diff = ln.get("difference")
            check = "No total given" if diff is None else ("Correct" if abs(diff) <= max(1, 0.001 * ln["computed_total"]) else f"Off by {money(diff, cur)}")
            rows.append([short(ln["item"], 30), money(ln["computed_total"], cur),
                         money(ln["stated_total"], cur) if ln.get("stated_total") is not None else "n/a", check])
        tot = f"Calculated total {money(prc['computed_grand_total'], cur)}"
        if prc.get("stated_grand_total") is not None:
            tot += f", stated {money(prc['stated_grand_total'], cur)}"
        if prc.get("blended_hourly_rate"):
            tot += f", blended rate {money(prc['blended_hourly_rate'], cur)}/hour"
        add({"type": "table", "eyebrow": "Pricing", "title": "Pricing Check", "columns": ["Item", "Calculated", "Stated", "Check"],
             "rows": rows, "widths": [3, 2, 2, 2], "note": short(r["pricing"].get("assessment") or tot + ".", 160),
             "notes": tot + "\n" + "\n".join(prc.get("flags", [])) + "\n" + "\n".join(f"{ln['item']}: {ln['formula']}" for ln in prc["lines"])},
            "pricing (assessment 160 max)")

    # 9. recommendations
    recs = sorted(r.get("recommendations", []), key=lambda x: PRI_ORDER.get(x.get("priority"), 3))[:7]
    add({"type": "bullets", "eyebrow": "Next steps", "title": "Recommended Changes", "bullets": [x["action"] for x in recs],
         "callout": {"value": str(sum(x.get("priority") == "high" for x in r.get("recommendations", []))), "label": "High priority",
                     "color": "magenta"},
         "notes": "\n".join(f"{x['action']}: {x.get('why', '')}" for x in recs)}, "recommendations (action 90 max)")

    # 10. questions and assumptions
    qs, asm = r.get("open_questions", [])[:4], r.get("assumptions", [])[:4]
    if qs or asm:
        add({"type": "comparison", "eyebrow": "Before we submit", "title": "Questions and Assumptions",
             "left": {"tag": "Ask", "heading": "Open questions", "points": qs or ["None"]},
             "right": {"tag": "Check", "heading": "Assumptions we made", "points": asm or ["None"]}},
            "open_questions, assumptions (140 max each)")
    add({"type": "closing"}, "")
    return {"theme": "dark", "slides": slides}, sections


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if len(args) < 2 or "-h" in args or "--help" in args:
        raise SystemExit(__doc__)
    spec_path = None
    if "--spec" in args:
        k = args.index("--spec"); spec_path = Path(args[k + 1]); del args[k:k + 2]
    review = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    if "check" not in (review.get("pricing") or {}) and "check" not in (review.get("staffing") or {}) and review.get("pricing"):
        print("Run check_review.py first and pass review.checked.json."); sys.exit(1)
    spec, sections = build_spec(review)
    out = Path(args[1])
    spec_path = spec_path or out.with_name(out.stem + "-spec.json")
    spec_path.write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
    make = find_igppt()
    if not make:
        print(f"Wrote the deck spec {spec_path}, but the igppt skill was not found next to this skill. "
              "Add the igppt skill to the agent, or set IGPPT_SCRIPTS, then run: python <igppt>/scripts/make_deck.py "
              f"{spec_path} {out}")
        sys.exit(1)
    r = subprocess.run([sys.executable, str(make), str(spec_path), str(out)], text=True, capture_output=True,
                       encoding="utf-8", errors="replace")
    print(r.stdout + r.stderr)
    if r.returncode:
        print("The review deck did not pass IGPPT validation. Slides come from these parts of review.json:")
        for k, sec in enumerate(sections, 1):
            if sec:
                print(f"  slide {k}: {sec}")
        print("Shorten the fields named above in review.json, run check_review.py, then this script again.")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
