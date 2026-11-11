#!/usr/bin/env bash
# Install the IGPPT skill (and the Copilot agent) into a project or your user profile.
#   ./install.sh /path/to/project     -> project install for Copilot and Claude Code
#   ./install.sh --user               -> personal install (~/.copilot/skills and ~/.claude/skills)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "Usage: $0 /path/to/project | --user"; exit 1; }

copy_skill() { mkdir -p "$1"; rm -rf "$1/igppt"; cp -R "$HERE/igppt" "$1/igppt"; echo "  skill  -> $1/igppt"; }

if [ "$TARGET" = "--user" ]; then
  copy_skill "$HOME/.copilot/skills"
  copy_skill "$HOME/.claude/skills"
else
  [ -d "$TARGET" ] || { echo "Not a folder: $TARGET"; exit 1; }
  copy_skill "$TARGET/.github/skills"
  copy_skill "$TARGET/.claude/skills"
  mkdir -p "$TARGET/.github/agents"
  cp "$HERE/copilot/agents/igppt.agent.md" "$TARGET/.github/agents/igppt.agent.md"
  echo "  agent  -> $TARGET/.github/agents/igppt.agent.md"
fi

if [ "$TARGET" != "--user" ]; then
  if command -v python3 >/dev/null 2>&1; then (cd "$TARGET" && python3 .github/skills/igppt/scripts/init.py)
  else echo "  Python 3 not found: install it, then run: python .github/skills/igppt/scripts/init.py"; fi
else
  python3 -m pip install --quiet -r "$HERE/igppt/requirements.txt" 2>/dev/null && echo "  python-pptx installed"
fi
command -v soffice >/dev/null 2>&1 || echo "  Optional: install LibreOffice so the skill can render slide previews."
echo "Done."
