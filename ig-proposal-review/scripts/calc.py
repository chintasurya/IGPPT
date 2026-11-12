"""Pricing and team-size arithmetic for a proposal review. The AI never does this maths in its head.

    python calc.py pricing review.json      check the pricing section of a review
    python calc.py staffing review.json     check the staffing section of a review

Formats are in references/review-schema.md. Every result carries the formula used, so the report can show
its working. Units for rates: hour, day (8 h), week (40 h), month (160 h), year (1,920 h), or fixed.
"""
import json
import sys
from pathlib import Path

HOURS = {"hour": 1, "day": 8, "week": 40, "month": 160, "year": 1920}
TOLERANCE = 0.001          # 0.1%: smaller differences are treated as rounding (for example rates in cents)


def money(v, cur=""):
    return f"{cur} {v:,.0f}".strip() if v is not None else "n/a"


# ---------------------------------------------------------------- pricing
def pricing(p):
    """Recompute every line and the total. Returns dict with lines, totals, flags (list of strings)."""
    cur = p.get("currency", "")
    hpm = p.get("hours_per_month", HOURS["month"])
    hours_per = dict(HOURS, month=hpm)
    lines, flags = [], []
    total, hourly_total, hours_sum, cost_total = 0.0, 0.0, 0.0, 0.0
    for k, ln in enumerate(p.get("lines", [])):
        unit = ln.get("unit", "hour")
        count = float(ln.get("count", 1) or 1)
        rate = float(ln["rate"])
        qty = float(ln.get("quantity", 1) or 1)
        if unit == "fixed":
            computed, hours = rate * count, None
            formula = f"{count:g} x {money(rate, cur)} fixed"
        else:
            computed = count * rate * qty
            hours = count * qty * hours_per.get(unit, 1)
            formula = f"{count:g} x {money(rate, cur)}/{unit} x {qty:g} {unit}s"
        stated = ln.get("stated_total")
        diff = None if stated is None else float(stated) - computed
        row = {"item": ln.get("item", f"line {k + 1}"), "computed_total": round(computed, 2), "stated_total": stated,
               "difference": None if diff is None else round(diff, 2), "formula": formula, "hours": hours}
        if hours:
            row["hourly_equivalent"] = round(computed / hours, 2)
            hourly_total += computed; hours_sum += hours
        if diff is not None and abs(diff) > max(1.0, TOLERANCE * computed):
            flags.append(f"{row['item']}: stated {money(stated, cur)} but {formula} = {money(computed, cur)} "
                         f"(difference {money(diff, cur)})")
        if ln.get("cost_rate") is not None and unit != "fixed":
            cost = count * float(ln["cost_rate"]) * qty
            cost_total += cost
            row["margin_pct"] = round(100 * (computed - cost) / computed, 1) if computed else None
        lines.append(row)
        total += computed
    out = {"currency": cur, "lines": lines, "computed_grand_total": round(total, 2), "flags": flags}
    stated_total = p.get("stated_grand_total")
    if stated_total is not None:
        d = float(stated_total) - total
        out["stated_grand_total"] = stated_total
        out["grand_total_difference"] = round(d, 2)
        if abs(d) > max(1.0, TOLERANCE * total):
            flags.append(f"grand total: stated {money(stated_total, cur)} but the lines add up to {money(total, cur)} "
                         f"(difference {money(d, cur)})")
    if hours_sum:
        out["blended_hourly_rate"] = round(hourly_total / hours_sum, 2)
        out["total_hours"] = round(hours_sum, 1)
    if cost_total and hourly_total:
        out["gross_margin_pct"] = round(100 * (hourly_total - cost_total) / hourly_total, 1)
    budget = (p.get("budget") or {}).get("amount")
    if budget is not None:
        price = float(stated_total) if stated_total is not None else total
        out["budget"] = budget
        out["budget_difference"] = round(price - float(budget), 2)
        out["budget_difference_pct"] = round(100 * (price - float(budget)) / float(budget), 1)
        if price > float(budget):
            flags.append(f"price {money(price, cur)} is {out['budget_difference_pct']}% over the stated budget {money(budget, cur)}")
    bench = []
    for b in p.get("benchmarks", []):
        if not str(b.get("source_url", "")).startswith("http"):
            continue                                   # unsourced benchmarks are ignored (see check_review.py)
        match = next((l for l, src in zip(lines, p.get("lines", [])) if src.get("item") == b.get("item")), None)
        if not match or "hourly_equivalent" not in match:
            continue
        unit_h = HOURS.get(b.get("unit", "hour"), 1)
        low, high = float(b["low"]) / unit_h, float(b["high"]) / unit_h
        r = match["hourly_equivalent"]
        pos = "below" if r < low else "above" if r > high else "within"
        bench.append({"item": b["item"], "our_hourly": r, "benchmark_low": round(low, 2), "benchmark_high": round(high, 2),
                      "position": pos, "source_url": b["source_url"]})
        if pos != "within":
            flags.append(f"{b['item']}: {money(r, cur)}/hour is {pos} the sourced range {money(low, cur)} to {money(high, cur)}")
    out["benchmarks"] = bench
    return out


# ---------------------------------------------------------------- staffing
def fte(model, shrinkage=None, minutes_factor=1.0):
    s = model.get("shrinkage", 0.2) if shrinkage is None else shrinkage
    week = float(model.get("hours_per_fte_week", 40)) * (1 - s)
    if model["type"] == "coverage":
        need = float(model["seats"]) * float(model["hours_per_week"])
        return need / week, f"{model['seats']} seat(s) x {model['hours_per_week']} h/week / ({model.get('hours_per_fte_week', 40)} h x (1 - {s:g} shrinkage))"
    per_week = {"day": float(model.get("days_per_week", 5)), "week": 1.0, "month": 12 / 52}[model.get("period", "day")]
    volume = float(model["volume"]) * per_week * (1 - float(model.get("automation_reduction", 0)))
    hours = volume * float(model["minutes_per_item"]) * minutes_factor / 60
    return hours / week, (f"{model['volume']} per {model.get('period', 'day')} x {per_week:g} x (1 - {model.get('automation_reduction', 0):g} automated)"
                          f" x {float(model['minutes_per_item']) * minutes_factor:g} min / 60 / ({model.get('hours_per_fte_week', 40)} h x (1 - {s:g}))")


def staffing(st):
    proposed = sum(float(r.get("count", 0)) for r in st.get("proposed", []) if r.get("in_scope_of_models", True))
    models, flags = [], []
    for m in st.get("models", []):
        base, formula = fte(m)
        low = min(fte(m, shrinkage=0.15, minutes_factor=0.75)[0], base)
        high = max(fte(m, shrinkage=0.30, minutes_factor=1.25)[0], base)
        models.append({"name": m.get("name", m["type"]), "type": m["type"], "fte": round(base, 1),
                       "range": [round(low, 1), round(high, 1)], "formula": formula})
    out = {"proposed_fte": proposed, "models": models, "flags": flags}
    if models:
        need = max(x["fte"] for x in models)
        lo, hi = max(x["range"][0] for x in models), max(x["range"][1] for x in models)
        out["calculated_fte"] = need
        out["calculated_range"] = [lo, hi]
        verdict = "increase" if proposed < lo - 0.5 else "decrease" if proposed > hi + 0.5 else "keep"
        out["calculated_verdict"] = verdict
        rec = st.get("recommendation")
        if rec and rec != verdict:
            flags.append(f"the review recommends '{rec}' but the calculation says '{verdict}' (proposed {proposed:g} FTE, "
                         f"calculated {need:g}, range {lo:g} to {hi:g}); explain why in the rationale or change it")
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 3 or sys.argv[1] not in ("pricing", "staffing"):
        raise SystemExit(__doc__)
    review = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    part = review.get(sys.argv[1]) or {}
    result = pricing(part) if sys.argv[1] == "pricing" else staffing(part)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
