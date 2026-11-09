# Create the hidden build workspace for a project's explainer (or refresh its vendored engine).
#   powershell -File init.ps1 -Project <project root> [-RefreshEngine]
# Creates <project>/.explainer/{data,extract,assets,engine}, copies template + build/check scripts
# into engine/, marks the folder hidden on Windows, and writes starter sources.json / CHANGELOG.md.
param([Parameter(Mandatory=$true)][string]$Project, [switch]$RefreshEngine)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$skill = Split-Path $PSScriptRoot -Parent
$x = Join-Path (Resolve-Path $Project).Path '.explainer'
foreach ($d in 'data','extract','assets','engine') { New-Item -ItemType Directory -Force (Join-Path $x $d) | Out-Null }
(Get-Item $x -Force).Attributes = 'Directory,Hidden'
Copy-Item (Join-Path $skill 'assets\template.html') (Join-Path $x 'engine') -Force
foreach ($f in 'build.ps1','build.py','check.ps1','check.py') { Copy-Item (Join-Path $PSScriptRoot $f) (Join-Path $x 'engine') -Force }
if ($RefreshEngine) { "engine refreshed in $x\engine"; return }
$name = Split-Path (Resolve-Path $Project).Path -Leaf
$src = Join-Path $x 'sources.json'
if (-not (Test-Path $src)) {
  [IO.File]::WriteAllText($src, @"
{
  "project_root": "..",
  "report": "report.json",
  "output": "../${name}_explainer.html",
  "sources": [],
  "watch": [],
  "extracts": []
}
"@, $utf8)
}
$cl = Join-Path $x 'CHANGELOG.md'
if (-not (Test-Path $cl)) { [IO.File]::WriteAllText($cl, "# Explainer changelog`n`n", $utf8) }
"workspace ready: $x"
