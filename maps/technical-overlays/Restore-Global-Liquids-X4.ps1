param(
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$BackupRoot = (Join-Path $PSScriptRoot 'backups\global-liquids-x4-20260823')
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
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant restauration.' }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$overridePath = Join-Path $gameRootPath 'override'
$backupPath = [IO.Path]::GetFullPath($BackupRoot)
$manifestPath = Join-Path $backupPath 'install-backup.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Sauvegarde introuvable : $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.Schema -ne 'bg2-upscale-global-liquids-x4-install-v1') { throw 'Sauvegarde incompatible.' }

foreach ($file in @($manifest.Files)) {
    $destination = Join-Path $overridePath $file.Name
    if ($file.WasPresent) {
        $source = Join-Path $backupPath $file.Name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Original sauvegarde absent : $source" }
        Copy-Item -LiteralPath $source -Destination $destination -Force
        if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.OriginalHash) {
            throw "Verification de restauration echouee : $($file.Name)"
        }
    } elseif (Test-Path -LiteralPath $destination -PathType Leaf) {
        $currentHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($currentHash -ne $file.InstalledHash) { throw "Refus de supprimer un fichier modifie : $($file.Name)" }
        Remove-Item -LiteralPath $destination -Force
    }
}

Write-Host 'Overlays liquides x4 retires : les versions precedentes sont restaurees.'
