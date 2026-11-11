# Install the IGPPT skill (and the Copilot agent) into a project or your user profile.
#   .\install.ps1 -Project C:\path\to\project   -> project install for Copilot and Claude Code
#   .\install.ps1 -User                         -> personal install (~\.copilot\skills and ~\.claude\skills)
param([string]$Project, [switch]$User)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Copy-Skill($Dest) {
  New-Item -ItemType Directory -Force -Path $Dest | Out-Null
  $Target = Join-Path $Dest "igppt"
  if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
  Copy-Item -Recurse (Join-Path $Here "igppt") $Target
  Write-Host "  skill  -> $Target"
}

if ($User) {
  Copy-Skill (Join-Path $HOME ".copilot\skills")
  Copy-Skill (Join-Path $HOME ".claude\skills")
} elseif ($Project) {
  if (-not (Test-Path $Project)) { throw "Not a folder: $Project" }
  Copy-Skill (Join-Path $Project ".github\skills")
  Copy-Skill (Join-Path $Project ".claude\skills")
  $Agents = Join-Path $Project ".github\agents"
  New-Item -ItemType Directory -Force -Path $Agents | Out-Null
  Copy-Item (Join-Path $Here "copilot\agents\igppt.agent.md") (Join-Path $Agents "igppt.agent.md") -Force
  Write-Host "  agent  -> $Agents\igppt.agent.md"
} else {
  Write-Host "Usage: .\install.ps1 -Project C:\path\to\project   or   .\install.ps1 -User"; exit 1
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "  Python not found: install it, then run: python .github\skills\igppt\scripts\init.py" }
elseif ($Project) { Push-Location $Project; python .github\skills\igppt\scripts\init.py; Pop-Location }
else { python -m pip install --quiet -r (Join-Path $Here "igppt\requirements.txt"); Write-Host "  python-pptx installed" }
if (-not (Get-Command soffice -ErrorAction SilentlyContinue)) { Write-Host "  Optional: install LibreOffice so the skill can render slide previews." }
Write-Host "Done."
