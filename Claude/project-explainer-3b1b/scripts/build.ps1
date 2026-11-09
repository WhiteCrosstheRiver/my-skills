# Build a single self-contained explainer HTML from report.json (Windows, no Python needed).
# usage: powershell -File build.ps1 -Report report.json -Out out.html [-Template ..\assets\template.html]
param(
  [Parameter(Mandatory=$true)][string]$Report,
  [Parameter(Mandatory=$true)][string]$Out,
  [string]$Template = ''
)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
if (-not $Template) {   # vendored copy beside this script wins, else the skill's asset
  $Template = Join-Path $PSScriptRoot 'template.html'
  if (-not (Test-Path $Template)) { $Template = Join-Path $PSScriptRoot '..\assets\template.html' }
}
$reportPath = (Resolve-Path $Report).Path
$reportDir = Split-Path $reportPath -Parent
$raw = [IO.File]::ReadAllText($reportPath, $utf8)

# {"$include": "data/x.json"} -> contents of that JSON file (keeps big arrays out of report.json).
$raw = [regex]::Replace($raw, '\{\s*"\$include"\s*:\s*"([^"]+)"\s*\}', {
  param($m)
  [IO.File]::ReadAllText((Join-Path $reportDir $m.Groups[1].Value), $utf8).Trim()
})

# Validate JSON early (PowerShell 5.1 parser; content is embedded verbatim, not re-serialised).
$null = $raw | ConvertFrom-Json

# Inline "file": "x.svg" figure references as data URIs.
$raw = [regex]::Replace($raw, '"file"\s*:\s*"([^"]+)"', {
  param($m)
  $f = Join-Path $reportDir $m.Groups[1].Value
  $ext = [IO.Path]::GetExtension($f).ToLower()
  $mime = @{ '.svg'='image/svg+xml'; '.png'='image/png'; '.jpg'='image/jpeg'; '.jpeg'='image/jpeg'; '.webp'='image/webp'; '.gif'='image/gif' }[$ext]
  if (-not $mime) { $mime = 'application/octet-stream' }
  '"src": "data:' + $mime + ';base64,' + [Convert]::ToBase64String([IO.File]::ReadAllBytes($f)) + '"'
})

$title = 'Explainer'
$mt = [regex]::Match($raw, '"short"\s*:\s*(?:\{\s*"en"\s*:\s*)?"([^"]+)"')
if ($mt.Success) { $title = $mt.Groups[1].Value }

$html = [IO.File]::ReadAllText((Resolve-Path $Template).Path, $utf8)
$html = $html.Replace('/*__REPORT_JSON__*/', $raw.Replace('</', '<\/')).Replace('__TITLE__', $title)
if ([IO.Path]::IsPathRooted($Out)) { $outFull = $Out } else { $outFull = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Out)) }
New-Item -ItemType Directory -Force (Split-Path $outFull -Parent) | Out-Null
[IO.File]::WriteAllText($outFull, $html, $utf8)
"wrote $outFull ({0:N0} KB)" -f ((Get-Item $outFull).Length / 1KB)
