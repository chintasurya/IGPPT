#!/usr/bin/env node
// IGPPT installer: installs the IGPPT skill and creates the IGPPT agent.
//   npx github:chintasurya/igppt            install into the current project
//   npx github:chintasurya/igppt --global   install for your user (all projects)
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");

const PKG = path.resolve(__dirname, "..");
const args = process.argv.slice(2);
const isGlobal = args.includes("--global") || args.includes("-g");
const root = isGlobal ? os.homedir() : process.cwd();

const skillDirs = isGlobal
  ? [".copilot/skills", ".agents/skills", ".claude/skills"]
  : [".github/skills", ".agents/skills", ".claude/skills"];
const agentFiles = isGlobal
  ? [".copilot/agents/igppt.agent.md", ".claude/agents/igppt.md"]
  : [".github/agents/igppt.agent.md", ".claude/agents/igppt.md"];

const skip = (src) => !/__pycache__/.test(src);
console.log(`\nInstalling IGPPT ${isGlobal ? "for your user" : "into " + root}\n`);

for (const d of skillDirs) {
  const dst = path.join(root, d, "igppt");
  fs.rmSync(dst, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.cpSync(path.join(PKG, "igppt"), dst, { recursive: true, filter: skip });
  console.log("  skill  ->", path.join(d, "igppt"));
}

const agentSrc = fs.readFileSync(path.join(PKG, "copilot", "agents", "igppt.agent.md"), "utf8");
for (const f of agentFiles) {
  const dst = path.join(root, f);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.writeFileSync(dst, agentSrc);
  console.log("  agent  ->", f);
}

function python() {
  for (const cmd of ["python3", "python", "py"]) {
    const r = spawnSync(cmd, ["--version"], { encoding: "utf8" });
    if (r.status === 0) return cmd;
  }
  return null;
}
const py = python();
if (!py) {
  console.log("\n  Python 3.9+ is needed to build decks. Install it, then run:");
  console.log(isGlobal ? "    pip install python-pptx" : "    python .github/skills/igppt/scripts/init.py");
  process.exit(0);
}
if (isGlobal) {
  const r = spawnSync(py, ["-m", "pip", "install", "--quiet", "python-pptx"], { stdio: "inherit" });
  console.log(r.status === 0 ? "  python-pptx installed" : "  run: pip install python-pptx");
} else {
  console.log("\nRunning set-up and self-test:\n");
  const r = spawnSync(py, [path.join(root, ".github", "skills", "igppt", "scripts", "init.py")], { cwd: root, stdio: "inherit" });
  if (r.status !== 0) process.exit(r.status || 1);
}
console.log(`
Done. To use it:
  GitHub Copilot (VS Code): reload the window, open Copilot Chat in Agent mode, pick the IGPPT agent (or type /igppt), and ask for a deck.
  Copilot CLI: start copilot, type /agent and choose igppt, then ask for a deck.
  Claude Code, Codex, Cursor, Gemini CLI: just ask for a presentation.
`);
