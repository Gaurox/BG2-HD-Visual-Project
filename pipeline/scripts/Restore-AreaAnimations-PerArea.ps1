# Restaure l'etat precedant une installation de packs par zone.
#
# Remet la DLL et l'INI sauvegardes, puis retablit exactement le dossier iee-assets\areas
# tel qu'il etait : reinstalle s'il existait, supprime s'il n'existait pas. Le registre
# global historique n'est jamais touche, ni a l'installation ni ici.

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'

function Assert-GameClosed {
    $running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
    if ($running) {
        throw 'Quittez completement BG2EE et InfinityLoader avant restauration.'
    }
}

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

Assert-GameClosed

$backupDirectory = (Resolve-Path -LiteralPath $BackupPath).Path
$manifestPath = Join-Path $backupDirectory 'backup-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifeste de sauvegarde absent : $manifestPath"
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'bg2-upscale-area-animation-per-area-install-backup-v1') {
    throw 'Sauvegarde incompatible avec cette restauration.'
}

$gameRootPath = (Resolve-Path -LiteralPath ([string]$manifest.GameRoot)).Path
$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$areasDirectory = Join-Path $gameRootPath 'iee-assets\areas'
$backupDll = Join-Path $backupDirectory 'InfinityEngine-Enhancer.dll'
$backupIni = Join-Path $backupDirectory 'InfinityEngine-Enhancer.ini'
$backupAreas = Join-Path $backupDirectory 'areas'

foreach ($required in @($backupDll, $backupIni)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier de sauvegarde absent : $required" }
}
if ((Get-Sha256 $backupDll) -ne ([string]$manifest.PreviousDllSha256).ToLowerInvariant()) {
    throw 'DLL sauvegardee divergente de son manifeste ; restauration refusee.'
}

# Une installation modifiee depuis la sauvegarde signale un etat que cette restauration ne
# decrit plus : on le signale au lieu de l'ecraser en silence.
$installedDllHash = Get-Sha256 $targetDll
if ($installedDllHash -ne ([string]$manifest.SourceDllSha256).ToLowerInvariant()) {
    Write-Warning ("DLL installee inattendue (attendu {0}, trouve {1})." -f `
        $manifest.SourceDllSha256, $installedDllHash)
}

$hadAreas = [bool]$manifest.PreviousAreasPresent
Write-Host ("Restauration prevue : DLL + INI ; dossier areas {0}." -f `
    ($(if ($hadAreas) { 'remis a son contenu sauvegarde' } else { 'supprime (absent avant installation)' })))

if ($VerifyOnly) {
    Write-Host 'VerifyOnly : aucune ecriture effectuee.'
    return
}

if (Test-Path -LiteralPath $areasDirectory -PathType Container) {
    Remove-Item -LiteralPath $areasDirectory -Recurse -Force
}
if ($hadAreas) {
    if (-not (Test-Path -LiteralPath $backupAreas -PathType Container)) {
        throw "Sauvegarde du dossier areas absente : $backupAreas"
    }
    Copy-Item -LiteralPath $backupAreas -Destination $areasDirectory -Recurse
}
Copy-Item -LiteralPath $backupDll -Destination $targetDll -Force
Copy-Item -LiteralPath $backupIni -Destination $iniPath -Force

if ((Get-Sha256 $targetDll) -ne ([string]$manifest.PreviousDllSha256).ToLowerInvariant()) {
    throw 'Verification post-restauration de la DLL echouee.'
}

Write-Host 'Restauration terminee. Le jeu n a pas ete lance.'
