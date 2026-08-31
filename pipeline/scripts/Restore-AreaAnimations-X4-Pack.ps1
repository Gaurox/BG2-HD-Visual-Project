param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
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
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant restauration du pack x4.' }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$backupRoot = (Resolve-Path -LiteralPath $BackupPath).Path
$manifestPath = Join-Path $backupRoot 'install-backup.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Manifest de sauvegarde absent : $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.Schema -ne 'bg2-upscale-area-animation-install-backup-v2' -or
    $manifest.GameRoot -ne $gameRootPath -or @($manifest.Files).Count -lt 1) {
    throw 'Manifest de sauvegarde incompatible.'
}

$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$assetsDirectory = Join-Path $gameRootPath 'iee-assets'
$backupDll = Join-Path $backupRoot 'InfinityEngine-Enhancer.dll'
$backupIni = Join-Path $backupRoot 'InfinityEngine-Enhancer.ini'
foreach ($required in @($targetDll, $iniPath, $backupDll, $backupIni)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier requis absent : $required" }
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backupDll).Hash.ToLowerInvariant() -ne [string]$manifest.OriginalDllHash -or
    (Get-FileHash -Algorithm SHA256 -LiteralPath $backupIni).Hash.ToLowerInvariant() -ne [string]$manifest.OriginalIniHash) {
    throw 'La sauvegarde DLL/INI ne correspond pas au manifeste.'
}

foreach ($entry in @($manifest.Files)) {
    $name = [string]$entry.Name
    if ([IO.Path]::GetFileName($name) -ne $name) { throw "Nom d'asset non securise : $name" }
    $target = Join-Path $assetsDirectory $name
    if ([bool]$entry.WasPresent) {
        $source = Join-Path $backupRoot (Join-Path 'iee-assets' $name)
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Asset de sauvegarde absent : $source" }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant() -ne [string]$entry.OriginalHash) {
            throw "Asset de sauvegarde corrompu : $source"
        }
        Copy-Item -LiteralPath $source -Destination $target -Force
        continue
    }
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
        if ($currentHash -eq [string]$entry.InstalledHash) {
            Remove-Item -LiteralPath $target -Force
        } else {
            Write-Warning "Asset modifie depuis l'installation, preserve : $target"
        }
    }
}
Copy-Item -LiteralPath $backupDll -Destination $targetDll -Force
Copy-Item -LiteralPath $backupIni -Destination $iniPath -Force
Write-Host "Pack runtime x4 restaure depuis : $backupRoot"
