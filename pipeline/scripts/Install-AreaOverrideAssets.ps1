# Installe les fichiers override d'une zone (ARE repointe + BAM duplique) de facon reversible.
#
# Pourquoi : le runtime d'animation indexe une texture de remplacement sur le seul resref BAM.
# Deux occurrences du meme resref partagent donc la meme texture, ce qui bloque des que leur
# occlusion doit differer -- cas des deux spheres d'AR0900, dont le decor est en miroir. Donner
# a une occurrence son propre resref est la seule voie qui ne touche pas au moteur : le champ
# BAM de son entree ARE est repointe sur une copie du BAM, et le pack porte alors deux
# ressources independantes.
#
# Le champ `name` de l'entree ARE n'est jamais modifie : un script qui reference l'animation
# par son nom continue de fonctionner.
#
# ATTENTION : les sauvegardes Infinity Engine embarquent une copie du .ARE des zones deja
# visitees. Sur une partie ou AR0900 a deja ete chargee, la version sauvegardee prime sur
# l'override et le repointage restera invisible. Tester depuis une partie n'ayant pas encore
# visite la zone.

param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$BackupRoot,
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

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant installation.' }

$sourcePath = (Resolve-Path -LiteralPath $SourceRoot).Path
$gamePath = (Resolve-Path -LiteralPath $GameRoot).Path
$overrideDir = Join-Path $gamePath 'override'
if (-not (Test-Path -LiteralPath $overrideDir -PathType Container)) {
    throw "Dossier override absent : $overrideDir"
}

$manifestPath = Join-Path $sourcePath 'manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifeste absent : $manifestPath"
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'bg2-upscale-area-animation-override-assets-v1' -or
    $manifest.status -ne 'completed') {
    throw 'Manifeste d assets override incompatible.'
}

# Chaque source est revalidee avant toute ecriture : un ARE divergent casserait la zone.
$plan = @()
foreach ($property in $manifest.files.PSObject.Properties) {
    $name = $property.Name
    if ([IO.Path]::GetFileName($name) -ne $name) { throw "Nom de fichier non securise : $name" }
    $source = Join-Path $sourcePath $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Source absente : $source" }
    if ((Get-Item -LiteralPath $source).Length -ne [int64]$property.Value.bytes -or
        (Get-Sha256 $source) -ne ([string]$property.Value.sha256).ToLowerInvariant()) {
        throw "Source corrompue : $source"
    }
    $plan += [PSCustomObject]@{
        Name = $name; Source = $source
        Target = (Join-Path $overrideDir $name)
        Hash = ([string]$property.Value.sha256).ToLowerInvariant()
    }
}

Write-Host ("Prevalidation reussie : {0} fichier(s) pour {1}." -f $plan.Count, $manifest.area)
foreach ($entry in $plan) {
    $state = if (Test-Path -LiteralPath $entry.Target -PathType Leaf) { 'remplace' } else { 'nouveau' }
    Write-Host ("  {0,-16} {1}" -f $entry.Name, $state)
}
if ($VerifyOnly) { Write-Host 'VerifyOnly : aucune ecriture effectuee.'; return }

if (-not $BackupRoot) { $BackupRoot = Join-Path $sourcePath 'install-backups' }
$backupDirectory = Join-Path ([IO.Path]::GetFullPath($BackupRoot)) ('override-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $backupDirectory) { throw "Sauvegarde deja presente : $backupDirectory" }
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null

$record = [ordered]@{
    schema = 'bg2-upscale-area-override-install-backup-v1'
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    GameRoot = $gamePath
    SourceRoot = $sourcePath
    Files = @()
}
foreach ($entry in $plan) {
    $existed = Test-Path -LiteralPath $entry.Target -PathType Leaf
    if ($existed) { Copy-Item -LiteralPath $entry.Target -Destination (Join-Path $backupDirectory $entry.Name) }
    $record.Files += [ordered]@{
        Name = $entry.Name
        PresentBefore = $existed
        PreviousSha256 = if ($existed) { Get-Sha256 $entry.Target } else { $null }
        InstalledSha256 = $entry.Hash
    }
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backupDirectory 'install-backup.json') -Encoding UTF8

foreach ($entry in $plan) { Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force }
foreach ($entry in $plan) {
    if ((Get-Sha256 $entry.Target) -ne $entry.Hash) {
        throw "Verification post-installation echouee : $($entry.Target)"
    }
}

Write-Host ("Installation terminee : {0} fichier(s) sous {1}." -f $plan.Count, $overrideDir)
Write-Host ("Sauvegarde : {0}" -f $backupDirectory)
Write-Host 'Rappel : une sauvegarde ayant deja visite la zone embarque son propre .ARE.'
Write-Host 'Le jeu n a pas ete lance.'
