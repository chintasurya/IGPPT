"""Make lessons permanent: merge downloaded igppt-lessons.json files into the skill, for everyone.

    python tools/merge_lessons.py igppt-lessons.json [more.json ...] [--dry-run]

Users of the Microsoft 365 or ChatGPT agent download igppt-lessons.json after giving feedback and send it to
the IGPPT owner. This adds those lessons to igppt/assets/lessons.json (duplicates are skipped), shows each one
for review, and checks that none of them rejects the bundled sample deck. Then run the tests, rebuild the zips
(python tools/build_zips.py), commit, and re-upload igppt-m365-skill.zip to the agents.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "igppt" / "scripts"))
import learn  # noqa: E402

BUNDLED = ROOT / "igppt" / "assets" / "lessons.json"


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        raise SystemExit(__doc__)
    current = learn.read_file(BUNDLED)
    seen = {learn.signature(l) for l in current}
    sample = json.loads((ROOT / "igppt" / "examples" / "sample-deck.json").read_text(encoding="utf-8"))
    added = []
    for f in files:
        for l in learn.read_file(f):
            if learn.signature(l) in seen or l.get("kind") not in learn.KINDS:
                continue
            seen.add(learn.signature(l))
            l = {k: v for k, v in l.items() if k != "_file"}
            hits = learn.check(sample, [l]) if l["kind"] != "guidance" else []
            print(f"{'ADD ' if not hits else 'SKIP'} {l.get('id')} {l['kind']}: {l.get('mistake') or l.get('text')}"
                  + (f"\n     feedback: {l['feedback']}" if l.get("feedback") else "")
                  + (f"\n     rejects the sample deck, too broad: {hits[0][2][:120]}" if hits else ""))
            if not hits:
                added.append(l)
    if dry or not added:
        print(f"\n{len(added)} lesson(s) would be added." if dry else "\nNothing new to add.")
        return
    items = [{k: v for k, v in l.items() if k != "_file"} for l in current] + added
    BUNDLED.write_text(json.dumps({"lessons": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nAdded {len(added)} lesson(s) to {BUNDLED.relative_to(ROOT)}. Next: python tools/test_igppt.py, "
          "python tools/build_zips.py, commit, and re-upload igppt-m365-skill.zip to the agents.")


if __name__ == "__main__":
    main()
