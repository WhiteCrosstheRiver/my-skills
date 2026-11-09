# Incremental-update helper: what changed in the project since the explainer was last stamped?
#   powershell -File check.ps1 [-Dir <.explainer folder>] [-Stamp]
# Reads  <Dir>/sources.json       (hand-written: which files feed which sections)
# Uses   <Dir>/fingerprints.json  (machine-written by -Stamp after a successful update)
# Prints changed/new/missing sources, the sections they feed, the first new line of append-only
# logs (read only from there), and extract scripts whose inputs changed. Exit code 0 always.
param([string]$Dir = $PSScriptRoot, [switch]$Stamp)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$Dir = (Resolve-Path $Dir).Path
$cfg = [IO.File]::ReadAllText((Join-Path $Dir 'sources.json'), $utf8) | ConvertFrom-Json
if ([IO.Path]::IsPathRooted($cfg.project_root)) { $root = [IO.Path]::GetFullPath($cfg.project_root) }
else { $root = [IO.Path]::GetFullPath((Join-Path $Dir $cfg.project_root)) }
$fpPath = Join-Path $Dir 'fingerprints.json'
$old = @{}; $oldSeen = @{}
if (Test-Path $fpPath) {
  $fp = [IO.File]::ReadAllText($fpPath, $utf8) | ConvertFrom-Json
  foreach ($p in $fp.files.PSObject.Properties) { $old[$p.Name] = $p.Value }
  foreach ($p in $fp.watch_seen.PSObject.Properties) { $oldSeen[$p.Name] = @($p.Value) }
  "last stamp: $($fp.stamped)"
} else { "no fingerprints yet: everything counts as new (run with -Stamp after the first build)" }

function Get-Fp([string]$rel) {
  $f = Join-Path $root $rel
  if (-not (Test-Path $f)) { return $null }
  $bytes = [IO.File]::ReadAllBytes($f)
  $sha = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($bytes)).Replace('-','').ToLower()
  $lines = 0; foreach ($b in $bytes) { if ($b -eq 10) { $lines++ } }
  [ordered]@{ size = $bytes.Length; lines = $lines; sha256 = $sha }
}

$files = [ordered]@{}; $sections = @{}; $changedPaths = @{}
"`n== sources =="
foreach ($s in $cfg.sources) {
  $cur = Get-Fp $s.path; $prev = $old[$s.path]; $feeds = ($s.feeds -join ',')
  if ($cur) { $files[$s.path] = $cur }
  if (-not $cur) { "MISSING   $($s.path)  [$feeds]"; continue }
  if (-not $prev) { "NEW       $($s.path)  [$feeds]"; $changedPaths[$s.path]=1; $s.feeds | ForEach-Object { $sections[$_]=1 }; continue }
  if ($prev.sha256 -eq $cur.sha256) { continue }
  $changedPaths[$s.path]=1; $s.feeds | ForEach-Object { $sections[$_]=1 }
  if ($s.kind -eq 'append' -and $cur.size -gt $prev.size) {
    "APPENDED  $($s.path)  [$feeds]  read from line $([int]$prev.lines + 1) (+$($cur.lines - $prev.lines) lines)"
  } else { "CHANGED   $($s.path)  [$feeds]  $($prev.size) -> $($cur.size) bytes" }
}

$seen = [ordered]@{}
if ($cfg.watch) {
  "`n== watched folders =="
  foreach ($w in $cfg.watch) {
    $d = Join-Path $root $w.dir
    $names = @(); if (Test-Path $d) { $names = @(Get-ChildItem $d -File -Filter $w.pattern | Sort-Object Name | ForEach-Object Name) }
    $seen[$w.dir + '|' + $w.pattern] = $names
    $prevNames = $oldSeen[$w.dir + '|' + $w.pattern]
    foreach ($n in $names) { if (-not $prevNames -or ($prevNames -notcontains $n)) { "NEW FILE  $($w.dir)/$n  [$($w.feeds -join ',')]"; $w.feeds | ForEach-Object { $sections[$_]=1 } } }
  }
}

if ($cfg.extracts) {
  "`n== extracts to re-run =="
  foreach ($x in $cfg.extracts) {
    $hit = @($x.inputs | Where-Object { $changedPaths[$_] })
    if ($hit.Count) { "RE-RUN    $($x.script)  (input changed: $($hit -join ', '))  -> $($x.output)" }
  }
}

"`n== sections to revisit =="
if ($sections.Count) { ($sections.Keys | Sort-Object) -join ', ' } else { 'none: the explainer is up to date with its sources' }

if ($Stamp) {
  $obj = [ordered]@{ stamped = (Get-Date).ToString('s'); files = $files; watch_seen = $seen }
  [IO.File]::WriteAllText($fpPath, ($obj | ConvertTo-Json -Depth 5), $utf8)
  "`nstamped $($files.Count) files -> fingerprints.json"
}
