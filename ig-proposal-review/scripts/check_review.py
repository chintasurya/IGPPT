"""Check a proposal review before anything is built from it. Exit code 0 = PASS, 1 = FAIL.

    python check_review.py review.json [--corpus corpus] [--out review.checked.json] [--report review.md]

It enforces the honesty rules of the ig-proposal-review skill:
  - every quote (requirements, proposal evidence, differentiator proof, staffing and pricing sources) must appear
    word for word in the extracted documents (spacing, case and quote marks are ignored);
  - every outside fact, named competitor and price benchmark needs a web link and an access date;
  - pricing totals and team sizes are recalculated by calc.py and any mismatch becomes a finding;
  - every staffing input is either quoted from a document or labelled "assumption: ...";
  - a requirement marked met or partial needs proposal evidence; partial or missing ones must appear in a gap;
  - short fields fit their slide (length limits) and contain no em or en dashes.
On PASS it writes review.checked.json (with the calculations) and the full report review.md.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calc  # noqa: E402
from extract_docs import load_corpus  # noqa: E402

LIMITS = {"summary.headline": 90, "summary.points": 120, "requirements.text": 90, "requirements.comment": 140,
          "gaps.title": 40, "gaps.detail": 140, "gaps.fix": 140, "research.findings.claim": 160,
          "competitors.offer": 120, "competitors.how_we_differ": 120, "differentiators.title": 40,
          "differentiators.detail": 140, "staffing.rationale": 160, "pricing.assessment": 160,
          "recommendations.action": 90, "recommendations.why": 140, "assumptions": 140, "open_questions": 140}
ENUMS = {"summary.verdict": {"ready", "needs work", "not ready"}, "requirements.priority": {"must", "should", "could"},
         "requirements.coverage": {"met", "partial", "missing", "unclear"}, "gaps.severity": {"high", "medium", "low"},
         "research.findings.confidence": {"verified", "reported"},
         "competitors.type": {"named in RFP", "likely bidder", "alternative approach"},
         "differentiators.strength": {"proven", "claimed"}, "staffing.recommendation": {"increase", "decrease", "keep"},
         "recommendations.priority": {"high", "medium", "low"}}
GENERIC = re.compile(r"\b(world[- ]class|best[- ]in[- ]class|industry[- ]leading|cutting[- ]edge|proven track record|"
                     r"customer[- ]centric|experienced team|highly skilled|one[- ]stop|seamless|end[- ]to[- ]end|"
                     r"synerg\w*|trusted partner|flexible approach)\b", re.I)
DASH = re.compile(r"[–—―]|--")


def norm(s):
    s = str(s).lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[–—―]", "-", s)
    s = re.sub(r"[^\w%$'.,/+-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class Checker:
    def __init__(self, review, corpus):
        self.r, self.corpus = review, corpus
        self.sections = {}                     # file -> [(location, normalised text)]
        for f, t in corpus.items():
            parts = re.split(r"=== \[.+? \| (.+?)\] ===", t)
            self.sections[f] = [(parts[k], norm(parts[k + 1])) for k in range(1, len(parts) - 1, 2)] or [("", norm(t))]
        self.fails, self.warns = [], []

    def fail(self, where, msg):
        self.fails.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warns.append(f"{where}: {msg}")

    # ----- evidence
    def locate(self, quote_obj, where):
        """Verify a quote; returns 'file | location' or None (and records a FAIL)."""
        if not isinstance(quote_obj, dict) or not quote_obj.get("quote"):
            self.fail(where, "needs {\"file\": ..., \"quote\": ...} copied from a document")
            return None
        q = norm(quote_obj["quote"])
        has_number = bool(re.search(r"\d{2,}", q))       # short spreadsheet rows such as "Total 667800" are specific
        if len(q.split()) < 4 and len(q) < 20 and not (has_number and len(q.split()) >= 2):
            self.fail(where, f"quote '{quote_obj['quote']}' is too short to verify; copy at least 4 words")
            return None
        f = quote_obj.get("file", "")
        files = [f] if f in self.corpus else list(self.corpus)
        for name in files:
            for loc, text in self.sections[name]:
                if q in text:
                    if f and f != name:
                        self.warn(where, f"quote found in '{name}', not in '{f}'; corrected the file name")
                        quote_obj["file"] = name
                    quote_obj["location"] = loc
                    return f"{name} | {loc}"
        known = ", ".join(self.corpus) or "none: run extract_docs.py first"
        self.fail(where, f"quote not found word for word in {'the documents' if f not in self.corpus else repr(f)}: "
                         f"'{quote_obj['quote'][:80]}'. Copy it exactly, or remove the claim. (Documents: {known})")
        return None

    def source(self, item, where, required=True):
        url = str(item.get("source_url", ""))
        if not url.startswith("http"):
            if required:
                self.fail(where, "needs a source_url (http...) for this outside fact; without one, move it to "
                                 "research.not_found or open_questions")
            return False
        acc = item.get("accessed")
        try:
            if acc and dt.date.fromisoformat(acc) > dt.date.today() + dt.timedelta(days=1):
                self.fail(where, f"accessed date {acc} is in the future")
        except ValueError:
            self.fail(where, f"accessed must be a date like 2026-11-12, not '{acc}'")
        if not acc:
            self.warn(where, "add the date the source was accessed")
        return True

    def basis(self, value, where):
        if isinstance(value, dict):
            return self.locate(value, where) is not None
        if isinstance(value, str) and value.lower().startswith("assumption:") and len(value) > 15:
            return True
        self.fail(where, "each input needs a quote from a document or a string starting 'assumption: ...' saying why")
        return False

    # ----- text rules
    def text_rules(self, node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("quote", "source_url", "file"):
                    continue
                self.text_rules(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                self.text_rules(v, f"{path}[{i}]")
        elif isinstance(node, str):
            key = re.sub(r"\[\d+\]", "", path)
            lim = LIMITS.get(key)
            if lim and len(node) > lim:
                self.fail(path, f"{len(node)} characters; keep it to {lim} so it fits its slide")
            if DASH.search(node):
                self.fail(path, "contains an em dash, en dash or '--'; use a comma, colon or hyphen")
            enum = ENUMS.get(key)
            if enum and node not in enum:
                self.fail(path, f"'{node}' must be one of: {', '.join(sorted(enum))}")

    # ----- sections
    def run(self):
        r = self.r
        if not self.corpus:
            self.fail("corpus", "no extracted documents found; run extract_docs.py on the shared files first")
        for k in ("customer", "summary", "requirements", "gaps", "recommendations"):
            if not r.get(k):
                self.fail(k, "is required")
        self.text_rules(r)

        req_ids = set()
        for i, q in enumerate(r.get("requirements", [])):
            w = f"requirements[{i}] {q.get('id', '')}"
            req_ids.add(q.get("id"))
            self.locate(q.get("source"), w + ".source")
            cov = q.get("coverage")
            ev = q.get("proposal_evidence")
            if cov in ("met", "partial"):
                if not ev:
                    self.fail(w, f"coverage '{cov}' needs proposal_evidence quoted from the proposal")
                else:
                    self.locate(ev, w + ".proposal_evidence")
            elif cov == "missing" and ev:
                self.warn(w, "marked missing but has proposal evidence; check the coverage value")
        in_gaps = {rid for g in r.get("gaps", []) for rid in g.get("requirement_ids", [])}
        for q in r.get("requirements", []):
            if q.get("coverage") in ("partial", "missing") and q.get("id") not in in_gaps:
                self.fail(f"requirement {q.get('id')}", f"is '{q.get('coverage')}' but not listed in any gap")
        for i, g in enumerate(r.get("gaps", [])):
            for rid in g.get("requirement_ids", []):
                if rid not in req_ids:
                    self.fail(f"gaps[{i}]", f"refers to unknown requirement '{rid}'")
        for i, c in enumerate(r.get("evaluation_criteria", [])):
            self.locate(c.get("source"), f"evaluation_criteria[{i}].source")

        res = r.get("research") or {}
        if not res:
            self.fail("research", "say whether research was performed ({\"performed\": false} if there was no web access)")
        elif not res.get("performed"):
            if res.get("findings"):
                self.fail("research", "performed is false but findings are listed; findings need real sources")
            self.warn("research", "no outside research was done; the report will say so")
        for i, f in enumerate(res.get("findings", [])):
            self.source(f, f"research.findings[{i}]")

        for i, c in enumerate(r.get("competitors", [])):
            w = f"competitors[{i}] {c.get('name', '')}"
            if c.get("type") == "alternative approach":
                if not c.get("basis") and not c.get("source_url"):
                    self.fail(w, "an alternative approach needs a basis (why it is a real option) or a source_url")
            else:
                self.source(c, w)

        for i, d in enumerate(r.get("differentiators", [])):
            w = f"differentiators[{i}] {d.get('title', '')}"
            proof = d.get("proof")
            if d.get("strength") == "proven":
                if isinstance(proof, dict) and proof.get("quote"):
                    self.locate(proof, w + ".proof")
                elif isinstance(proof, dict) and proof.get("source_url"):
                    self.source(proof, w + ".proof")
                else:
                    self.fail(w, "'proven' needs proof: a quote from the documents or a source_url; otherwise mark it 'claimed'")
            else:
                self.warn(w, "claimed without proof; the report lists it as unproven")
            if GENERIC.search(f"{d.get('title', '')} {d.get('detail', '')}"):
                self.warn(w, "sounds generic (every bidder says this); make it specific and measurable")

        st = r.get("staffing") or {}
        if st:
            for i, p in enumerate(st.get("proposed", [])):
                self.locate(p.get("source"), f"staffing.proposed[{i}].source")
            numeric = {"coverage": ("seats", "hours_per_week", "shrinkage"),
                       "workload": ("volume", "minutes_per_item", "automation_reduction", "shrinkage")}
            for i, m in enumerate(st.get("models", [])):
                if m.get("type") not in numeric:
                    self.fail(f"staffing.models[{i}]", "type must be coverage or workload"); continue
                for k in numeric[m["type"]]:
                    if k in m or k != "automation_reduction":
                        self.basis((m.get("basis") or {}).get(k), f"staffing.models[{i}].basis.{k}")
            try:
                st["check"] = calc.staffing(st)
            except (KeyError, ValueError, TypeError) as e:
                self.fail("staffing", f"cannot calculate: {type(e).__name__} {e}")
            else:
                for fl in st["check"]["flags"]:
                    self.fail("staffing", fl)
        else:
            self.warn("staffing", "no team size check; add one if the proposal states a team")

        pr = r.get("pricing") or {}
        if pr:
            for i, ln in enumerate(pr.get("lines", [])):
                self.locate(ln.get("source"), f"pricing.lines[{i}].source")
            if pr.get("stated_grand_total") is not None:
                self.locate(pr.get("stated_grand_total_source"), "pricing.stated_grand_total_source")
            if pr.get("budget"):
                self.locate(pr["budget"].get("source"), "pricing.budget.source")
            for i, b in enumerate(pr.get("benchmarks", [])):
                if not self.source(b, f"pricing.benchmarks[{i}]"):
                    pass
            try:
                pr["check"] = calc.pricing(pr)
            except (KeyError, ValueError, TypeError) as e:
                self.fail("pricing", f"cannot calculate: {type(e).__name__} {e}")
        else:
            self.warn("pricing", "no pricing check; add one if pricing was shared")
        return self


# ---------------------------------------------------------------- report
def report_md(r):
    cur = (r.get("pricing") or {}).get("currency", "")
    L = [f"# Proposal review: {r.get('customer', '')}", "",
         f"**Opportunity:** {r.get('opportunity', '')}  ", f"**Reviewed:** {r.get('review_date', dt.date.today().isoformat())}  ",
         f"**Verdict:** {r['summary'].get('verdict', '')}: {r['summary'].get('headline', '')}", ""]
    L += [f"- {p}" for p in r["summary"].get("points", [])] + [""]
    L += ["## Documents reviewed", ""] + [f"- {d.get('file')} ({d.get('role', '')})" for d in r.get("documents", [])] + [""]

    def cite(q):
        return f"{q.get('file', '')}{', ' + q['location'] if q.get('location') else ''}: \"{q.get('quote', '')}\"" if q else "none"
    L += ["## What the customer asked for", "", "| ID | Requirement | Priority | Coverage | Evidence in the RFP | Evidence in our proposal | Comment |",
          "|---|---|---|---|---|---|---|"]
    for q in r.get("requirements", []):
        L.append(f"| {q.get('id')} | {q.get('text')} | {q.get('priority')} | {q.get('coverage')} | {cite(q.get('source'))} | "
                 f"{cite(q.get('proposal_evidence'))} | {q.get('comment', '')} |")
    if r.get("evaluation_criteria"):
        L += ["", "**Evaluation criteria:** " + "; ".join(f"{c['criterion']} {c.get('weight', '')}".strip() for c in r["evaluation_criteria"])]
    L += ["", "## Gaps", ""]
    for g in sorted(r.get("gaps", []), key=lambda g: ["high", "medium", "low"].index(g.get("severity", "low"))):
        L += [f"- **{g['title']}** ({g.get('severity')}, {', '.join(g.get('requirement_ids', []))}): {g.get('detail', '')} "
              f"**Fix:** {g.get('fix', '')}"]
    res = r.get("research") or {}
    L += ["", "## Research", "", f"Method: {res.get('method', 'not performed') if res.get('performed') else 'Not performed (no web access). Nothing below is outside research.'}", ""]
    for f in res.get("findings", []):
        L.append(f"- {f['claim']} ({f.get('confidence')}; [{f.get('source_title') or f['source_url']}]({f['source_url']}), accessed {f.get('accessed', '')})")
    if res.get("not_found"):
        L += ["", "Could not be confirmed:"] + [f"- {x}" for x in res["not_found"]]
    if r.get("competitors"):
        L += ["", "## Competition and alternatives", "", "| Competitor or alternative | Type | What they offer | How we differ | Source |", "|---|---|---|---|---|"]
        for c in r["competitors"]:
            src = f"[link]({c['source_url']})" if c.get("source_url") else c.get("basis", "")
            L.append(f"| {c['name']} | {c.get('type')} | {c.get('offer', '')} | {c.get('how_we_differ', '')} | {src} |")
    L += ["", "## Differentiators", ""]
    for d in r.get("differentiators", []):
        p = d.get("proof") or {}
        proof = cite(p) if p.get("quote") else (f"[source]({p['source_url']})" if p.get("source_url") else "no proof yet")
        L.append(f"- **{d['title']}** ({d.get('strength')}{', vs ' + d['vs'] if d.get('vs') else ''}): {d.get('detail', '')} Proof: {proof}")
    st = r.get("staffing") or {}
    if st.get("check"):
        ck = st["check"]
        L += ["", "## Team size", "", f"Proposed: {ck['proposed_fte']:g} FTE in the modelled roles. Calculated need: "
              f"{ck.get('calculated_fte', 'n/a')} FTE (range {ck.get('calculated_range', ['n/a'])[0]} to {ck.get('calculated_range', [0, 'n/a'])[1]}). "
              f"Recommendation: **{st.get('recommendation', ck.get('calculated_verdict'))}**"
              + (f" to {st['recommended_count']}" if st.get("recommended_count") else "") + f". {st.get('rationale', '')}", ""]
        for m, src in zip(ck["models"], st.get("models", [])):
            L.append(f"- {m['name']}: {m['fte']} FTE (range {m['range'][0]} to {m['range'][1]}) = {m['formula']}")
            for k, v in (src.get("basis") or {}).items():
                L.append(f"  - {k}: {cite(v) if isinstance(v, dict) else v}")
    pr = r.get("pricing") or {}
    if pr.get("check"):
        ck = pr["check"]
        L += ["", "## Pricing", "", "| Item | Calculation | Calculated | Stated | Difference |", "|---|---|---|---|---|"]
        for ln in ck["lines"]:
            L.append(f"| {ln['item']} | {ln['formula']} | {calc.money(ln['computed_total'], cur)} | "
                     f"{calc.money(ln['stated_total'], cur) if ln['stated_total'] is not None else 'n/a'} | "
                     f"{calc.money(ln['difference'], cur) if ln['difference'] is not None else 'n/a'} |")
        L += ["", f"Calculated total {calc.money(ck['computed_grand_total'], cur)}"
              + (f"; stated total {calc.money(ck['stated_grand_total'], cur)}" if ck.get("stated_grand_total") is not None else "")
              + (f"; blended rate {calc.money(ck['blended_hourly_rate'], cur)}/hour" if ck.get("blended_hourly_rate") else "")
              + (f"; budget {calc.money(ck['budget'], cur)} ({ck['budget_difference_pct']:+}%)" if ck.get("budget") is not None else "") + "."]
        L += [f"- {f}" for f in ck["flags"]]
        if ck["benchmarks"]:
            L += [f"- {b['item']}: {calc.money(b['our_hourly'], cur)}/hour is {b['position']} the range "
                  f"{calc.money(b['benchmark_low'], cur)} to {calc.money(b['benchmark_high'], cur)} ([source]({b['source_url']}))" for b in ck["benchmarks"]]
        else:
            L.append("- No sourced market benchmark was available, so rates were not compared with the market.")
        if pr.get("assessment"):
            L += ["", pr["assessment"]]
    L += ["", "## Recommended changes", ""]
    L += [f"{k}. **{x['action']}** ({x.get('priority', '')}): {x.get('why', '')}" for k, x in enumerate(r.get("recommendations", []), 1)]
    for title, key in (("Assumptions", "assumptions"), ("Open questions", "open_questions")):
        if r.get(key):
            L += ["", f"## {title}", ""] + [f"- {x}" for x in r[key]]
    L += ["", "---", "Quotes were checked word for word against the shared documents. Outside facts carry their source links. "
          "Pricing and team-size figures were calculated by script from the inputs shown."]
    return "\n".join(L) + "\n"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        raise SystemExit(__doc__)

    def opt(name, default):
        if name in args:
            k = args.index(name); v = args[k + 1]; del args[k:k + 2]; return v
        return default
    corpus_dir, out, rep = opt("--corpus", None), opt("--out", None), opt("--report", None)
    path = Path(args[0])
    try:
        review = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        print(f"FAIL: {path} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}"); sys.exit(2)
    corpus_dir = Path(corpus_dir) if corpus_dir else path.parent / "corpus"
    ck = Checker(review, load_corpus(corpus_dir) if corpus_dir.exists() else {}).run()
    for w in ck.fails:
        print("FAIL ", w)
    for w in ck.warns:
        print("WARN ", w)
    pr = (review.get("pricing") or {}).get("check")
    if pr:
        for f in pr["flags"]:
            print("FIND ", "pricing:", f)
    if ck.fails:
        print(f"\nFAIL: {len(ck.fails)} problem(s). Fix review.json and run this again. Nothing was written.")
        sys.exit(1)
    out = Path(out) if out else path.with_name("review.checked.json")
    rep = Path(rep) if rep else path.with_name("review.md")
    out.write_text(json.dumps(review, indent=1, ensure_ascii=False), encoding="utf-8")
    rep.write_text(report_md(review), encoding="utf-8")
    print(f"\nPASS: every quote verified, sources present, maths recalculated ({len(ck.warns)} warning(s)).")
    print(f"Wrote {out.name} and {rep.name}. Next: python review_to_deck.py {out.name} <name>.pptx")


if __name__ == "__main__":
    main()
