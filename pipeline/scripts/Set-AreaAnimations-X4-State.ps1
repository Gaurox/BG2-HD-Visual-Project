param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x1', 'x4')]
    [string]$Mode,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT
)

$workspaceRoot = $PSScriptRoot
while ($workspaceRoot -and -not (Test-Path -LiteralPath (Join-Path $workspaceRoot 'config\workspace-paths.json') -PathType Leaf)) {
    $workspaceRoot = Split-Path -Parent $workspaceRoot
}
if ([string]::IsNullOrWhiteSpace($workspaceRoot)) { throw 'Racine du workspace BG2 Upscale introuvable.' }
. (Join-Path $workspaceRoot 'pipeline\scripts\WorkspacePaths.ps1')
if ((Get-Variable -Name GameRoot -ErrorAction SilentlyContinue) -and [string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
}

$ErrorActionPreference = 'Stop'

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant de basculer le pack x4.' }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
if (-not (Test-Path -LiteralPath $iniPath -PathType Leaf)) { throw "INI absente : $iniPath" }

$lines = [Collections.Generic.List[string]]::new()
foreach ($line in [IO.File]::ReadAllLines($iniPath)) { $lines.Add($line) }
for ($index = $lines.Count - 1; $index -ge 0; --$index) {
    if ($lines[$index] -match '^\s*EnableAreaAnimationX4\s*=') { $lines.RemoveAt($index) }
}
$shadersIndex = -1
for ($index = 0; $index -lt $lines.Count; ++$index) {
    if ($lines[$index] -match '^\s*\[Shaders\]\s*$') { $shadersIndex = $index; break }
}
if ($shadersIndex -lt 0) {
    if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') { $lines.Add('') }
    $lines.Add('[Shaders]')
    $shadersIndex = $lines.Count - 1
}
$insertAt = $lines.Count
for ($index = $shadersIndex + 1; $index -lt $lines.Count; ++$index) {
    if ($lines[$index] -match '^\s*\[[^]]+\]\s*$') { $insertAt = $index; break }
}
$value = if ($Mode -eq 'x4') { 'true' } else { 'false' }
$lines.Insert($insertAt, "EnableAreaAnimationX4 = $value")
[IO.File]::WriteAllLines($iniPath, $lines, [Text.UTF8Encoding]::new($false))
Write-Host "Area animations : $Mode"
