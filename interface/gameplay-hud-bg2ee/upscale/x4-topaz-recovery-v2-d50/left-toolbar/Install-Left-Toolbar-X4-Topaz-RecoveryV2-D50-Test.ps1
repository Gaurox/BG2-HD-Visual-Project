param(
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
$running = Get-Process -Name Baldur, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw "Quittez complètement BG2EE et InfinityLoader avant l’installation." }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..\..')).Path
$builtDll = Join-Path $projectRoot 'engine\InfinityEngine-Enhancer\source-patchee\build-filter-diagnostic-v142\Release\InfinityEngine-Enhancer.dll'
$assets = @(
    @{ Name = 'HUD-MOS0140-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\HUD-MOS0140-x4.dxt5'); Bytes = 16777216 },
    @{ Name = 'HUD-MOS0141-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\HUD-MOS0141-x4.dxt5'); Bytes = 4194304 }
)
foreach ($required in @($builtDll) + $assets.Source) {
    if (!(Test-Path -LiteralPath $required)) { throw "Fichier requis introuvable : $required" }
}
foreach ($asset in $assets) {
    if ((Get-Item -LiteralPath $asset.Source).Length -ne $asset.Bytes) { throw "Taille invalide : $($asset.Source)" }
}

$backupRoot = Join-Path $PSScriptRoot 'backups'
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backup = Join-Path $backupRoot ('backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath (Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll') -Destination (Join-Path $backup 'InfinityEngine-Enhancer.dll')

$destinationRoot = Join-Path $gameRootPath 'iee-assets'
foreach ($asset in $assets) {
    $destination = Join-Path $destinationRoot $asset.Name
    if (Test-Path -LiteralPath $destination) {
        Copy-Item -LiteralPath $destination -Destination (Join-Path $backup $asset.Name)
    } else {
        New-Item -ItemType File -Path (Join-Path $backup ($asset.Name + '.was-absent.marker')) | Out-Null
    }
}
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backup 'InfinityEngine-Enhancer.dll') |
    Format-Table -AutoSize | Out-String | Set-Content -LiteralPath (Join-Path $backup 'SHA256.txt')

Copy-Item -LiteralPath $builtDll -Destination (Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll') -Force
New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
foreach ($asset in $assets) {
    Copy-Item -LiteralPath $asset.Source -Destination (Join-Path $destinationRoot $asset.Name) -Force
}
Write-Host "Test x4 de la colonne gauche installé. Sauvegarde créée : $backup"
