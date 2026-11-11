"""Rebuild the two upload packages of the skill. Run after any change to igppt/.

    python tools/build_zips.py

  chatgpt/igppt-skill.zip       igppt/SKILL.md inside an igppt folder (ChatGPT, claude.ai, SKILL.md download fallback)
  copilot/igppt-m365-skill.zip  SKILL.md at the root of the zip, as Microsoft 365 Copilot Agent Builder requires
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "igppt"


def files():
    return sorted(p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def build(out, prefix):
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        dirs = set()
        for p in files():
            rel = p.relative_to(SKILL)
            for d in list(rel.parents)[::-1][1:]:
                name = prefix + d.as_posix() + "/"
                if name not in dirs:
                    dirs.add(name); z.writestr(name, "")
            z.write(p, prefix + rel.as_posix())
    print(f"{out.relative_to(ROOT)}: {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    build(ROOT / "chatgpt" / "igppt-skill.zip", "igppt/")
    build(ROOT / "copilot" / "igppt-m365-skill.zip", "")
