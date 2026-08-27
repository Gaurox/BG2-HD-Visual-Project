param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$GameRoot = "E:\Steam\steamapps\common\Baldur's Gate II Enhanced Edition"
)

$ErrorActionPreference = 'Stop'
$running = Get-Process -Name Baldur, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw "Quittez complètement BG2EE et InfinityLoader avant la restauration." }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$backupPath = (Resolve-Path -LiteralPath $BackupPath).Path
$destinationRoot = Join-Path $gameRootPath 'iee-assets'
Copy-Item -LiteralPath (Join-Path $backupPath 'InfinityEngine-Enhancer.dll') -Destination (Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll') -Force

foreach ($name in 'HUD-MOS0140-x4.dxt5', 'HUD-MOS0141-x4.dxt5') {
    $backupAsset = Join-Path $backupPath $name
    $marker = Join-Path $backupPath ($name + '.was-absent.marker')
    $destination = Join-Path $destinationRoot $name
    if (Test-Path -LiteralPath $backupAsset) {
        Copy-Item -LiteralPath $backupAsset -Destination $destination -Force
    } elseif (Test-Path -LiteralPath $marker) {
        Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    } else {
        throw "État de sauvegarde introuvable pour $name"
    }
}
Write-Host "Test x4 de la colonne gauche restauré depuis : $backupPath"
