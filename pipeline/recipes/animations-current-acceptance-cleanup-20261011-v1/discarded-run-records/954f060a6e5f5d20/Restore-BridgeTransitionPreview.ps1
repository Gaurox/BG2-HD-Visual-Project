[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = 'Stop'

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$backupRoot = (Resolve-Path -LiteralPath $BackupPath).Path
$manifestPath = Join-Path $backupRoot 'install-backup.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Manifeste introuvable : $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'ar1300-bridge-transition-preview-install-v1' -or $manifest.status -ne 'installed') {
    throw 'Sauvegarde de preview AR1300 invalide.'
}
$gameRoot = [IO.Path]::GetFullPath([string]$manifest.game_root)
$targetDll = Join-Path $gameRoot 'InfinityEngine-Enhancer.dll'
$targetIni = Join-Path $gameRoot 'InfinityEngine-Enhancer.ini'
$targetAssets = Join-Path $gameRoot 'iee-assets\bridge-transition'
if (Get-Process -Name 'Baldur*','InfinityLoader*' -ErrorAction SilentlyContinue) {
    throw 'Fermez Baldur''s Gate II et InfinityLoader avant la restauration.'
}
if ((Get-Sha256 $targetDll) -ne [string]$manifest.installed_dll_sha256 -or
    (Get-Sha256 $targetIni) -ne [string]$manifest.installed_ini_sha256) {
    throw 'Refus de restaurer : DLL ou INI ont ete modifies depuis cette installation.'
}
foreach ($asset in @($manifest.assets)) {
    $path = Join-Path $targetAssets ([string]$asset.name)
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
        (Get-Item -LiteralPath $path).Length -ne [int64]$asset.bytes -or
        (Get-Sha256 $path) -ne [string]$asset.sha256) {
        throw "Refus de supprimer un asset different : $path"
    }
}

Copy-Item -LiteralPath (Join-Path $backupRoot 'InfinityEngine-Enhancer.dll') -Destination $targetDll -Force
Copy-Item -LiteralPath (Join-Path $backupRoot 'InfinityEngine-Enhancer.ini') -Destination $targetIni -Force
Remove-Item -LiteralPath $targetAssets -Recurse -Force
Write-Host "Preview AR1300 restauree depuis : $backupRoot"
