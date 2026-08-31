param(
    [Parameter(Mandatory = $true)] [string]$BackupDirectory,
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
if (Get-Process -Name Baldur, InfinityLoader -ErrorAction SilentlyContinue) { throw "Quittez BG2EE et InfinityLoader avant la restauration." }
$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
foreach ($name in 'InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini') {
    Copy-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $gameRootPath $name) -Force
}
$destinationRoot = Join-Path $gameRootPath 'iee-assets'
$assets = @('BIGLOGO-MOS0017-x4.dxt5', 'MAINMENU-MOS0181-x4.dxt5', 'MAINMENU-MOS0257-x4.dxt5', 'MAINMENU-MOS0258-x4.dxt5', 'MAINMENU-MOS0261-x4.dxt5', 'MAINMENU-MOS0262-x4.dxt5', 'MAINMENU-MOS0265-x4.dxt5', 'MAINMENU-MOS0266-x4.dxt5')
foreach ($name in $assets) {
    $saved = Join-Path $backup $name
    $marker = Join-Path $backup ($name + '.was-absent.marker')
    $destination = Join-Path $destinationRoot $name
    if (Test-Path -LiteralPath $saved) {
        New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null
        Copy-Item -LiteralPath $saved -Destination $destination -Force
    } elseif (Test-Path -LiteralPath $marker) {
        Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "Restauration terminee depuis : $backup"
