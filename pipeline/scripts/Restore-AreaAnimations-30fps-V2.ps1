param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [switch]$VerifyOnly
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

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant la verification ou restauration V2.' }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$backupRoot = (Resolve-Path -LiteralPath $BackupPath).Path
$manifestPath = Join-Path $backupRoot 'install-backup.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Manifest de sauvegarde absent : $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$replacedAssets = if ($null -ne $manifest.PSObject.Properties['ReplacedAssets']) { @($manifest.ReplacedAssets) } else { @() }
if ($manifest.Schema -ne 'bg2-upscale-area-animation-30fps-install-backup-v2' -or
    $manifest.Status -ne 'installed' -or $manifest.GameRoot -ne $gameRootPath -or
    (@($manifest.NewAssets).Count + $replacedAssets.Count) -lt 1) {
    throw 'Manifest de sauvegarde V2 incompatible.'
}

$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$assetsRoot = Join-Path $gameRootPath 'iee-assets'
$targetRegistry = Join-Path $assetsRoot 'AreaAnimations-X4.registry'
$backupDll = Join-Path $backupRoot 'InfinityEngine-Enhancer.dll'
$backupIni = Join-Path $backupRoot 'InfinityEngine-Enhancer.ini'
$backupRegistry = Join-Path $backupRoot 'AreaAnimations-X4.registry'
foreach ($required in @($targetDll, $iniPath, $targetRegistry, $backupDll, $backupIni, $backupRegistry)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier requis absent : $required" }
}
if ((Get-Sha256 $backupDll) -ne [string]$manifest.OriginalDllHash -or
    (Get-Sha256 $backupIni) -ne [string]$manifest.OriginalIniHash -or
    (Get-Sha256 $backupRegistry) -ne [string]$manifest.OriginalRegistryHash) {
    throw 'Sauvegarde V2 corrompue.'
}
if ((Get-Sha256 $targetDll) -ne [string]$manifest.InstalledDllHash -or
    (Get-Sha256 $iniPath) -ne [string]$manifest.InstalledIniHash -or
    (Get-Sha256 $targetRegistry) -ne [string]$manifest.InstalledRegistryHash) {
    throw 'DLL, INI ou registre modifies depuis l installation V2 ; restauration automatique refusee.'
}
foreach ($asset in @($manifest.NewAssets)) {
    $name = [string]$asset.Name
    $target = Join-Path $assetsRoot $name
    if ([IO.Path]::GetFileName($name) -ne $name -or
        -not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Item -LiteralPath $target).Length -ne [int64]$asset.Bytes -or
        (Get-Sha256 $target) -ne [string]$asset.Hash) {
        throw "Phase V2 modifiee ou absente depuis l installation : $name"
    }
}
foreach ($asset in $replacedAssets) {
    $name = [string]$asset.Name
    $target = Join-Path $assetsRoot $name
    $backupAsset = Join-Path $backupRoot (Join-Path 'iee-assets' $name)
    if ([IO.Path]::GetFileName($name) -ne $name -or
        -not (Test-Path -LiteralPath $backupAsset -PathType Leaf) -or
        (Get-Item -LiteralPath $backupAsset).Length -ne [int64]$asset.OriginalBytes -or
        (Get-Sha256 $backupAsset) -ne [string]$asset.OriginalHash -or
        -not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Item -LiteralPath $target).Length -ne [int64]$asset.Bytes -or
        (Get-Sha256 $target) -ne [string]$asset.Hash) {
        throw "Asset V2 remplace modifie, absent ou sauvegarde invalide : $name"
    }
}

if ($VerifyOnly) {
    Write-Host "Verification restauration V2 OK : $(@($manifest.NewAssets).Count) phases seront retirees et $($replacedAssets.Count) assets restaures."
    Write-Host 'Aucun fichier modifie.'
    exit 0
}

Copy-Item -LiteralPath $backupDll -Destination $targetDll -Force
Copy-Item -LiteralPath $backupIni -Destination $iniPath -Force
Copy-Item -LiteralPath $backupRegistry -Destination $targetRegistry -Force
foreach ($asset in @($manifest.NewAssets)) {
    Remove-Item -LiteralPath (Join-Path $assetsRoot ([string]$asset.Name)) -Force
}
foreach ($asset in $replacedAssets) {
    $name = [string]$asset.Name
    Copy-Item -LiteralPath (Join-Path $backupRoot (Join-Path 'iee-assets' $name)) -Destination (Join-Path $assetsRoot $name) -Force
}
if ((Get-Sha256 $targetDll) -ne [string]$manifest.OriginalDllHash -or
    (Get-Sha256 $iniPath) -ne [string]$manifest.OriginalIniHash -or
    (Get-Sha256 $targetRegistry) -ne [string]$manifest.OriginalRegistryHash) {
    throw 'Verification apres restauration V2 echouee.'
}
foreach ($asset in $replacedAssets) {
    $target = Join-Path $assetsRoot ([string]$asset.Name)
    if ((Get-Sha256 $target) -ne [string]$asset.OriginalHash) {
        throw "Verification de l asset restaure echouee : $($asset.Name)"
    }
}

Write-Host "Etat anterieur restaure depuis : $backupRoot"
