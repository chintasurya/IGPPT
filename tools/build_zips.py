"""Rebuild the two upload packages of the skill. Run after any change to igppt/.

    python tools/build_zips.py

  chatgpt/igppt-skill.zip       igppt/SKILL.md inside an igppt folder (ChatGPT, claude.ai, SKILL.md download fallback)
  copilot/igppt-m365-skill.zip  SKILL.md at the root of the zip, as Microsoft 365 Copilot Agent Builder requires

Before building, it checks the skill against Agent Builder's upload rules (file types, scripts/ holds code only,
folder depth, sizes) and stops if anything would be rejected.
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


# Microsoft 365 Copilot Agent Builder skill rules ("Skills in declarative agents", Microsoft Learn)
SCRIPT_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".mts", ".sh", ".bash"}
RESOURCE_EXT = {".json", ".xml", ".yaml", ".yml", ".ini", ".config", ".utf8", ".docx", ".doc", ".docm", ".pdf", ".txt",
                ".rtf", ".md", ".ppt", ".pptx", ".ppsm", ".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".html", ".htm",
                ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".log"}
MAX_DEPTH, MAX_FILE_MB, MAX_FILES, MAX_ZIP_MB, MAX_SKILL_CHARS = 3, 25, 350, 50, 20000


def m365_problems():
    """Every way the skill would be rejected by Agent Builder's upload. Empty list = OK."""
    out = []
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if len(skill_md) >= MAX_SKILL_CHARS:
        out.append(f"SKILL.md is {len(skill_md)} characters (limit {MAX_SKILL_CHARS})")
    head = skill_md.split("---")[1] if skill_md.startswith("---") else ""
    for key in ("name:", "description:"):
        if key not in head:
            out.append(f"SKILL.md front matter has no {key[:-1]}")
    fs = files()
    if len(fs) > MAX_FILES:
        out.append(f"{len(fs)} files (limit {MAX_FILES})")
    for p in fs:
        rel = p.relative_to(SKILL)
        ext = p.suffix.lower()
        if rel.parts[0] == "scripts" and ext not in SCRIPT_EXT:
            out.append(f"{rel.as_posix()}: '{ext or 'no extension'}' is not allowed in scripts/ (code files only)")
        elif ext not in SCRIPT_EXT | RESOURCE_EXT:
            out.append(f"{rel.as_posix()}: file type '{ext or 'no extension'}' is not allowed")
        if len(rel.parts) - 1 > MAX_DEPTH:
            out.append(f"{rel.as_posix()}: folders nested {len(rel.parts) - 1} deep (limit {MAX_DEPTH})")
        if p.stat().st_size > MAX_FILE_MB * 1e6:
            out.append(f"{rel.as_posix()}: {p.stat().st_size / 1e6:.1f} MB (limit {MAX_FILE_MB} MB per file)")
    return out


if __name__ == "__main__":
    problems = m365_problems()
    if problems:
        print("The skill breaks Microsoft 365 Copilot's upload rules:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    build(ROOT / "chatgpt" / "igppt-skill.zip", "igppt/")
    out = ROOT / "copilot" / "igppt-m365-skill.zip"
    build(out, "")
    if out.stat().st_size > MAX_ZIP_MB * 1e6:
        raise SystemExit(f"{out.name} is over {MAX_ZIP_MB} MB")
    print("Microsoft 365 Copilot upload rules: OK")
