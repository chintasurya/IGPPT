"""Tests for the ig-proposal-review skill: extraction, evidence checks, maths, and the IG review deck.

    python tools/test_review.py

Builds a small fictional bid (ShieldForge RFP in Word, proposal deck built with IGPPT, pricing in Excel with a
deliberate arithmetic error), then checks that honest reviews pass and invented quotes, unsourced facts and
wrong maths fail. Needs python-pptx; python-docx and openpyxl are used to create the test files.
"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RS = ROOT / "ig-proposal-review" / "scripts"
PY = sys.executable
TMP = Path(tempfile.mkdtemp(prefix="igreview-test-"))
DOCS = TMP / "docs"
results = []


def run(*args):
    r = subprocess.run([PY, *map(str, args)], capture_output=True, text=True, cwd=TMP, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def test(name):
    def wrap(fn):
        try:
            fn(); results.append((True, name, ""))
        except AssertionError as e:
            results.append((False, name, str(e)))
        return fn
    return wrap


def expect(cond, msg, out=""):
    assert cond, f"{msg}\n----- output -----\n{out[-1800:]}"


# ---------------------------------------------------------------- fictional bid documents
def make_docs():
    DOCS.mkdir(parents=True)
    import docx
    d = docx.Document()
    d.add_heading("ShieldForge Request for Proposal: Managed SOC Support", 0)
    d.add_heading("Background", 1)
    d.add_paragraph("ShieldForge receives 4,500 security alerts per day, up 60% year over year. Average response time is 38 minutes.")
    d.add_heading("Requirements", 1)
    d.add_paragraph("The supplier shall provide 24x7 monitoring of all security alerts.")
    d.add_paragraph("The supplier must place certified analysts within 30 days of contract signature.")
    d.add_paragraph("The supplier shall deliver a monthly service report to the CISO.")
    d.add_paragraph("Analysts should hold a current Security+ or equivalent certification.")
    d.add_heading("Commercial", 1)
    d.add_paragraph("The total budget for the six month engagement is not to exceed $650,000.")
    d.add_paragraph("Price will account for 30% of the evaluation score.")
    d.save(DOCS / "ShieldForge RFP.docx")

    spec = {"theme": "dark", "slides": [
        {"type": "title", "title": "ShieldForge SOC Proposal", "subtitle": "Managed SOC staffing and automation", "date": "November 2026"},
        {"type": "process", "title": "Three Phases to a Stable SOC", "steps": [
            {"title": "Staff the gap", "owner": "Month 1", "text": "Place 6 certified SOC analysts within 30 days.", "icon": "users"},
            {"title": "Automate triage", "owner": "Months 2-3", "text": "Automate triage for the top 20 alert types.", "icon": "cogs"},
            {"title": "Hand over", "owner": "Months 4-6", "text": "Hand over runbooks and train the ShieldForge team.", "icon": "handshake"}]},
        {"type": "cards", "title": "Expected Results", "cards": [
            {"value": "<15 min", "title": "Response time", "text": "Down from 38 minutes today."},
            {"value": "40%", "title": "Fewer alerts", "text": "40% fewer alerts reaching analysts after automation."}]},
        {"type": "closing"}]}
    sp = TMP / "proposal.json"
    sp.write_text(json.dumps(spec), encoding="utf-8")
    code, out = run(ROOT / "igppt" / "scripts" / "make_deck.py", sp, DOCS / "ShieldForge Proposal.pptx")
    assert code == 0, out

    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Pricing"
    ws.append(["Item", "Count", "Rate", "Hours", "Total"])
    ws.append(["SOC Analyst", 6, 95, 1040, 595000])          # deliberate error: 6 x 95 x 1040 = 592,800
    ws.append(["Engagement Manager", 1, 140, 520, 72800])
    ws.append(["Total", None, None, None, 667800])
    wb.save(DOCS / "Pricing.xlsx")


def q(file, quote):
    return {"file": file, "quote": quote}


RFP, DECK, XLS = "ShieldForge RFP.docx", "ShieldForge Proposal.pptx", "Pricing.xlsx"
GOOD = {
    "customer": "ShieldForge", "opportunity": "Managed SOC staffing and automation", "review_date": "2026-11-12",
    "documents": [{"file": RFP, "role": "rfp"}, {"file": DECK, "role": "proposal"}, {"file": XLS, "role": "pricing"}],
    "summary": {"verdict": "needs work", "headline": "Fast staffing story, but 24x7 cover and reporting are not addressed",
                "points": ["6 analysts cannot staff 24x7 monitoring", "Monthly CISO report is missing", "Price is over budget"]},
    "requirements": [
        {"id": "R1", "text": "24x7 monitoring of all security alerts", "priority": "must",
         "source": q(RFP, "The supplier shall provide 24x7 monitoring of all security alerts"), "coverage": "partial",
         "proposal_evidence": q(DECK, "Place 6 certified SOC analysts within 30 days"), "comment": "No shift model; 6 analysts are too few for 24x7"},
        {"id": "R2", "text": "Certified analysts placed within 30 days", "priority": "must",
         "source": q(RFP, "must place certified analysts within 30 days"), "coverage": "met",
         "proposal_evidence": q(DECK, "Place 6 certified SOC analysts within 30 days")},
        {"id": "R3", "text": "Monthly service report to the CISO", "priority": "must",
         "source": q(RFP, "shall deliver a monthly service report to the CISO"), "coverage": "missing", "proposal_evidence": None},
        {"id": "R4", "text": "Security+ or equivalent certification", "priority": "should",
         "source": q(RFP, "Analysts should hold a current Security+ or equivalent certification"), "coverage": "unclear"}],
    "evaluation_criteria": [{"criterion": "Price", "weight": "30%", "source": q(RFP, "Price will account for 30% of the evaluation score")}],
    "gaps": [
        {"title": "24x7 cover is understaffed", "detail": "Coverage maths needs about 10 FTE; the deck offers 6",
         "severity": "high", "requirement_ids": ["R1"], "fix": "Add a shift roster and 4 analysts",
         "say": "The RFP requires 24x7 monitoring, and two analysts on shift around the clock needs about ten people once leave and training are counted. Six cannot hold that cover."},
        {"title": "No monthly CISO report", "detail": "A mandatory deliverable is not mentioned", "severity": "high",
         "requirement_ids": ["R3"], "fix": "Add a reporting slide with a sample monthly report",
         "say": "The RFP makes a monthly service report to the CISO mandatory, and our deck never mentions it. A sample report closes a disqualification risk."}],
    "research": {"performed": False, "findings": [], "not_found": ["ShieldForge company size and recent news (no web access)"]},
    "competitors": [{"name": "In-house hiring", "type": "alternative approach", "offer": "ShieldForge keeps recruiting its own analysts",
                     "basis": "The RFP describes their current hiring and response times", "how_we_differ": "Analysts in 30 days, not months"}],
    "differentiators": [{"title": "Analysts in 30 days", "detail": "Certified analysts placed within 30 days", "strength": "proven",
                         "proof": q(DECK, "Place 6 certified SOC analysts within 30 days"), "vs": "In-house hiring"}],
    "staffing": {
        "proposed": [{"role": "SOC analyst", "count": 6, "source": q(DECK, "Place 6 certified SOC analysts within 30 days")}],
        "models": [{"name": "24x7 monitoring", "type": "coverage", "seats": 2, "hours_per_week": 168, "hours_per_fte_week": 40, "shrinkage": 0.2,
                    "basis": {"seats": "assumption: 2 analysts on shift at all times for 4,500 alerts a day",
                              "hours_per_week": q(RFP, "The supplier shall provide 24x7 monitoring of all security alerts"),
                              "shrinkage": "assumption: 20% for leave, training and breaks"}}],
        "recommendation": "increase", "recommended_count": 10, "rationale": "Two seats around the clock need about 10 FTE"},
    "pricing": {"currency": "USD",
                "lines": [{"item": "SOC Analyst", "count": 6, "rate": 95, "unit": "hour", "quantity": 1040, "stated_total": 595000,
                           "source": q(XLS, "SOC Analyst 6 95 1040 595000")},
                          {"item": "Engagement Manager", "count": 1, "rate": 140, "unit": "hour", "quantity": 520, "stated_total": 72800,
                           "source": q(XLS, "Engagement Manager 1 140 520 72800")}],
                "stated_grand_total": 667800, "stated_grand_total_source": q(XLS, "Total 667800"),
                "budget": {"amount": 650000, "source": q(RFP, "budget for the six month engagement is not to exceed $650,000")},
                "assessment": "Analyst line has a 2,200 USD arithmetic error and the total is over budget"},
    "recommendations": [{"action": "Add a 24x7 shift roster and 4 analysts", "why": "R1 is mandatory", "priority": "high",
                         "say": "We recommend a three-shift roster with ten analysts because 24x7 cover is mandatory and the coverage maths shows six is not enough."},
                        {"action": "Add the monthly CISO report", "why": "R3 is mandatory and missing", "priority": "high",
                         "say": "We add a sample monthly CISO report because the RFP makes it mandatory and evaluators will look for it first."},
                        {"action": "Fix the analyst line total", "why": "6 x 95 x 1040 is 592,800, not 595,000", "priority": "medium",
                         "say": "The analyst line is overstated by 2,200 dollars; six people at 95 an hour for 1,040 hours is 592,800. Arithmetic errors cost trust."}],
    "assumptions": ["Two analysts must be on shift at all times"],
    "open_questions": ["Does Security+ have to be held on day one?"]}


def check(review, name):
    p = TMP / f"{name}.json"
    p.write_text(json.dumps(review, indent=1), encoding="utf-8")
    return run(RS / "check_review.py", p, "--corpus", TMP / "corpus", "--out", TMP / f"{name}.checked.json", "--report", TMP / f"{name}.md")


@test("extracts Word, PowerPoint and Excel with locations")
def _():
    make_docs()
    code, out = run(RS / "extract_docs.py", DOCS, "--out", TMP / "corpus")
    expect(code == 0 and "PROBLEM" not in out, "extraction should succeed", out)
    idx = json.loads((TMP / "corpus" / "index.json").read_text())
    locs = {(i["file"], i["location"].split()[0]) for i in idx}
    expect((RFP, "section") in locs and (DECK, "slide") in locs and (XLS, "sheet") in locs, "locations recorded", str(idx))


@test("an honest review passes, with maths recalculated")
def _():
    code, out = check(GOOD, "good")
    expect(code == 0 and "PASS" in out, "good review should pass", out)
    ck = json.loads((TMP / "good.checked.json").read_text())
    pr, st = ck["pricing"]["check"], ck["staffing"]["check"]
    expect(any("SOC Analyst" in f and "592,800" in f for f in pr["flags"]), "analyst arithmetic error found", out)
    expect(pr["budget_difference_pct"] > 0 and st["calculated_fte"] == 10.5 and st["calculated_verdict"] == "increase", "maths", json.dumps([pr, st]))
    md = (TMP / "good.md").read_text()
    expect("section 'Requirements'" in md and "Not performed" in md, "report cites locations and says research was not done", md[:1500])


@test("an invented quote fails")
def _():
    r = copy.deepcopy(GOOD)
    r["requirements"][1]["source"]["quote"] = "The supplier must place analysts within 14 days"
    code, out = check(r, "fakequote")
    expect(code == 1 and "quote not found" in out, "invented quote must fail", out)


@test("outside facts need a source link")
def _():
    r = copy.deepcopy(GOOD)
    r["research"] = {"performed": True, "method": "web", "findings": [{"topic": "customer", "claim": "ShieldForge has 1,200 employees", "confidence": "verified"}]}
    r["competitors"].append({"name": "Example MSSP", "type": "likely bidder", "offer": "Managed SOC", "how_we_differ": "We staff inside their tools"})
    code, out = check(r, "nosource")
    expect(code == 1 and out.count("needs a source_url") >= 2, "unsourced research and competitor must fail", out)


@test("a 'proven' differentiator without proof fails; generic claims warn")
def _():
    r = copy.deepcopy(GOOD)
    r["differentiators"] = [{"title": "World-class experienced team", "detail": "Best-in-class analysts", "strength": "proven"}]
    code, out = check(r, "noproof")
    expect(code == 1 and "needs proof" in out and "generic" in out, "proof and generic checks", out)


@test("staffing inputs need a basis, and the recommendation must match the maths")
def _():
    r = copy.deepcopy(GOOD)
    r["staffing"]["recommendation"] = "keep"
    r["staffing"]["models"][0]["basis"]["seats"] = "two seats"
    code, out = check(r, "staff")
    expect(code == 1 and "assumption:" in out and "calculation says 'increase'" in out, "basis and verdict checks", out)


@test("partial or missing requirements must be in a gap; dashes and long fields fail")
def _():
    r = copy.deepcopy(GOOD)
    r["gaps"] = r["gaps"][:1]
    r["summary"]["headline"] = "Good — but " + "x" * 100
    code, out = check(r, "rules")
    expect(code == 1 and "R3" in out and "not listed in any gap" in out and "em dash" in out and "characters" in out, "rules", out)


@test("every gap and recommendation needs a talk-track statement")
def _():
    r = copy.deepcopy(GOOD)
    del r["gaps"][0]["say"]
    r["recommendations"][1]["say"] = "Add it."
    code, out = check(r, "nosay")
    expect(code == 1 and "gaps[0].say" in out and "recommendations[1].say" in out, "missing or thin statements must fail", out)


@test("the review deck builds on the IG template and passes IGPPT validation")
def _():
    code, out = run(RS / "review_to_deck.py", TMP / "good.checked.json", TMP / "ShieldForge Proposal Review.pptx")
    expect(code == 0 and "SAVED" in out and (TMP / "ShieldForge Proposal Review.pptx").exists(), "review deck should be saved", out)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for ok, name, why in results:
        print(("PASS  " if ok else "FAIL  ") + name)
        if not ok:
            print("      " + why.replace("\n", "\n      "))
    failed = sum(not ok for ok, _, _ in results)
    print(f"\n{len(results) - failed}/{len(results)} tests passed")
    if "--keep" in sys.argv:
        print(f"files kept in {TMP}")
    else:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
