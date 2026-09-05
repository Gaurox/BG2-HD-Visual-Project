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
if (Get-Process -Name Baldur, InfinityLoader -ErrorAction SilentlyContinue) {
    throw "Quittez complètement BG2EE et InfinityLoader avant l’installation."
}

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
$dll = Join-Path $projectRoot 'engine\InfinityEngine-Enhancer\source-patchee\build-filter-diagnostic-v142\Release\InfinityEngine-Enhancer.dll'
$config = Join-Path $PSScriptRoot '..\InfinityEngine-Enhancer-x4-topaz-recovery-v2-d50.ini'
$assets = @(
    @{ Name = 'MAINMENU-MOS0181-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\MAINMENU-MOS0181-x4.dxt5'); Bytes = 16777216 },
    @{ Name = 'SELECTOR-MOS0182-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\SELECTOR-MOS0182-x4.dxt5'); Bytes = 4194304 },
    @{ Name = 'SELECTOR-MOS0183-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\SELECTOR-MOS0183-x4.dxt5'); Bytes = 4194304 },
    @{ Name = 'SELECTOR-MOS0184-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\SELECTOR-MOS0184-x4.dxt5'); Bytes = 4194304 },
    @{ Name = 'SELECTOR-MOS0185-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\SELECTOR-MOS0185-x4.dxt5'); Bytes = 4194304 },
    @{ Name = 'MAINMENU-MOS0258-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\MAINMENU-MOS0258-x4.dxt5'); Bytes = 16777216 },
    @{ Name = 'SELECTOR-MOS0259-x4.dxt5'; Source = (Join-Path $PSScriptRoot 'assets\SELECTOR-MOS0259-x4.dxt5'); Bytes = 4194304 }
)
foreach ($required in @($dll, $config) + $assets.Source) {
    if (!(Test-Path -LiteralPath $required)) { throw "Fichier requis introuvable : $required" }
}
foreach ($asset in $assets) {
    if ((Get-Item -LiteralPath $asset.Source).Length -ne $asset.Bytes) { throw "Taille invalide : $($asset.Source)" }
}

$backupRoot = Join-Path $PSScriptRoot 'backups'
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backup = Join-Path $backupRoot ('selector-overlay-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($name in 'InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini') {
    Copy-Item -LiteralPath (Join-Path $gameRootPath $name) -Destination (Join-Path $backup $name)
}
$destinationRoot = Join-Path $gameRootPath 'iee-assets'
foreach ($asset in $assets) {
    $destination = Join-Path $destinationRoot $asset.Name
    if (Test-Path -LiteralPath $destination) {
        Copy-Item -LiteralPath $destination -Destination (Join-Path $backup $asset.Name)
    } else {
        New-Item -ItemType File -Path (Join-Path $backup ($asset.Name + '.was-absent.marker')) | Out-Null
    }
}
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backup 'InfinityEngine-Enhancer.dll'), (Join-Path $backup 'InfinityEngine-Enhancer.ini') |
    Format-Table -AutoSize | Out-String | Set-Content -LiteralPath (Join-Path $backup 'SHA256.txt')

Copy-Item -LiteralPath $dll -Destination (Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll') -Force
Copy-Item -LiteralPath $config -Destination (Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini') -Force
New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
foreach ($asset in $assets) {
    Copy-Item -LiteralPath $asset.Source -Destination (Join-Path $destinationRoot $asset.Name) -Force
}
Write-Host "Overlay sélecteur des trois jeux x4 installé. Sauvegarde créée : $backup"
