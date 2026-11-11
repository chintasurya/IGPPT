"""Regenerate manifest.json: the files the installer downloads. Run before every commit that changes igppt/ or copilot/."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
files = sorted(p.relative_to(root).as_posix() for base in ("igppt", "copilot") for p in (root / base).rglob("*")
               if p.is_file() and "__pycache__" not in p.parts)
(root / "manifest.json").write_text(json.dumps({"files": files}, indent=1) + "\n")
print(f"manifest.json: {len(files)} files")
