#!/usr/bin/env node
// IGPPT installer: installs the IGPPT skill, the IGPPT agent, the standing instructions and the starter prompts.
//   npx igppt@latest              install or update in the current project (run it in the project folder)
//   npx igppt@latest --global     install for your user (all projects)
//   npx igppt@latest --offline    use the copy inside this package instead of downloading the newest from GitHub
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");

const BUNDLED = path.resolve(__dirname, "..");
const REPO = "chintasurya/igppt";
const args = process.argv.slice(2);
const isGlobal = args.includes("--global") || args.includes("-g");
const offline = args.includes("--offline");
const root = isGlobal ? os.homedir() : process.cwd();

const skillDirs = isGlobal
  ? [".copilot/skills", ".agents/skills", ".claude/skills"]
  : [".github/skills", ".agents/skills", ".claude/skills"];
const agentFiles = isGlobal
  ? [".copilot/agents/igppt.agent.md", ".claude/agents/igppt.md"]
  : [".github/agents/igppt.agent.md", ".claude/agents/igppt.md"];

const skip = (src) => !/__pycache__/.test(src);

// Fetch the latest files from GitHub (like claude-code-templates), so re-running always updates.
// Falls back to the copy npx downloaded if GitHub cannot be reached.
async function latestSource() {
  if (offline || typeof fetch !== "function") return BUNDLED;
  try {
    // pin to the newest commit so a fresh push is picked up immediately (the "main" file cache lags a few minutes)
    let ref = "main";
    try {
      const c = await fetch(`https://api.github.com/repos/${REPO}/commits/main`, { headers: { Accept: "application/vnd.github.sha" } });
      if (c.ok) ref = (await c.text()).trim();
    } catch (_) { /* keep "main" */ }
    const RAW = `https://raw.githubusercontent.com/${REPO}/${ref}/`;
    const res = await fetch(RAW + "manifest.json");
    if (!res.ok) throw new Error("manifest " + res.status);
    const { files } = await res.json();
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "igppt-"));
    let i = 0;
    await Promise.all(Array.from({ length: 6 }, async () => {
      while (i < files.length) {
        const f = files[i++];
        const r = await fetch(RAW + f.split("/").map(encodeURIComponent).join("/"));
        if (!r.ok) throw new Error(f + " " + r.status);
        const dst = path.join(tmp, f);
        fs.mkdirSync(path.dirname(dst), { recursive: true });
        fs.writeFileSync(dst, Buffer.from(await r.arrayBuffer()));
      }
    }));
    console.log(`  Downloaded the latest IGPPT (${files.length} files) from GitHub`);
    return tmp;
  } catch (e) {
    console.log("  Could not reach GitHub (" + e.message + "); installing the bundled copy");
    return BUNDLED;
  }
}

(async () => {
const PKG = await latestSource();
console.log(`\nInstalling IGPPT ${isGlobal ? "for your user" : "into " + root}\n`);

function countFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true })
    .reduce((n, e) => n + (e.isDirectory() ? countFiles(path.join(dir, e.name)) : 1), 0);
}
for (const d of skillDirs) {
  const dst = path.join(root, d, "igppt");
  fs.rmSync(dst, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.cpSync(path.join(PKG, "igppt"), dst, { recursive: true, filter: skip });
  console.log(`  Writes ${countFiles(dst)} files to ${path.join(d, "igppt")}/`);
}

const agentSrc = fs.readFileSync(path.join(PKG, "copilot", "agents", "igppt.agent.md"), "utf8");
for (const f of agentFiles) {
  const dst = path.join(root, f);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  // Claude Code agent names must be lower case
  fs.writeFileSync(dst, f.includes(".claude") ? agentSrc.replace(/^name: IGPPT$/m, "name: igppt") : agentSrc);
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
Done. IGPPT is installed with the Insight Global template, the IGPPT agent, the standing
instructions and the starter prompts. Every deck is validated before it is saved.

Next:
  1. Reload VS Code (Ctrl+Shift+P, "Developer: Reload Window").
  2. Open Copilot Chat in Agent mode and pick the IGPPT agent (or just ask for a deck).
  3. Try a starter prompt:
       /igppt              any deck
       /igppt-quarterly    Q1-Q4 update or QBR
       /igppt-from-notes   paste an email, chat or notes
       /igppt-proposal     proposal or solution design
       /igppt-update-deck  change an existing deck
     or simply type, for example:
       "Make a 7-slide Q3 update for the leadership call. SLA 98%, 1,240 tickets."
  4. Allow Copilot to run the terminal command it proposes; that is how the deck is built and checked.

Run the same command again at any time to update to the latest version.
` + (isGlobal ? `
Note: with --global the skill and agent are installed for your user. The starter prompts and the
"always use IGPPT" instructions are per project: run the command without --global inside a project.
` : ""));
})();
