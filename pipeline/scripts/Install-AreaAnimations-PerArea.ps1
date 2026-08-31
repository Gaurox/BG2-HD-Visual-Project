# Installe un jeu de packs d'animations decoupe par zone (sortie de
# split_animation_pack_by_area.py) plus la DLL qui sait les charger a chaque LoadArea.
#
# Pourquoi : le runtime ne chargeait qu'un seul AreaAnimations-X4.registry global, dont la
# charge RGBA est plafonnee a 512 Mio. Ce plafond est cumulatif sur toutes les zones deja
# converties et ne redescend jamais, alors que l'inventaire complet du jeu pese plusieurs
# gigaoctets. Avec iee-assets\areas\<ZONE>\, seule la zone courante est residente et le
# plafond devient une limite par zone.
#
# Le repli est integre : une zone sans pack relache le pack resident et le moteur affiche
# ses propres BAM. Le registre global historique reste en place mais devient inerte des que
# iee-assets\areas existe ; il est sauvegarde et laisse tel quel.

param(
    [Parameter(Mandatory = $true)]
    [string]$SplitRoot,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$SourceDll,
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

function Assert-GameClosed {
    $running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
    if ($running) {
        throw 'Quittez completement BG2EE et InfinityLoader avant installation des packs par zone.'
    }
}

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Set-IniValue {
    param([string]$Path, [string]$Key, [string]$Value)

    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in [IO.File]::ReadAllLines($Path)) { $lines.Add($line) }
    for ($index = $lines.Count - 1; $index -ge 0; --$index) {
        if ($lines[$index] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) { $lines.RemoveAt($index) }
    }
    $shadersIndex = -1
    for ($index = 0; $index -lt $lines.Count; ++$index) {
        if ($lines[$index] -match '^\s*\[Shaders\]\s*$') { $shadersIndex = $index; break }
    }
    if ($shadersIndex -lt 0) {
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') { $lines.Add('') }
        $lines.Add('[Shaders]')
        $shadersIndex = $lines.Count - 1
    }
    $insertAt = $lines.Count
    for ($index = $shadersIndex + 1; $index -lt $lines.Count; ++$index) {
        if ($lines[$index] -match '^\s*\[[^]]+\]\s*$') { $insertAt = $index; break }
    }
    $lines.Insert($insertAt, "$Key = $Value")
    [IO.File]::WriteAllLines($Path, $lines, [Text.UTF8Encoding]::new($false))
}

Assert-GameClosed

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$splitRootPath = (Resolve-Path -LiteralPath $SplitRoot).Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if (-not $SourceDll) {
    $SourceDll = Join-Path $projectRoot 'engine\InfinityEngine-Enhancer\source-patchee\build-filter-diagnostic-v142\Release\InfinityEngine-Enhancer.dll'
}
$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$assetsDirectory = Join-Path $gameRootPath 'iee-assets'
$areasDirectory = Join-Path $assetsDirectory 'areas'
$indexPath = Join-Path $splitRootPath 'manifest.json'

foreach ($required in @($SourceDll, $targetDll, $iniPath, $indexPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier requis absent : $required" }
}

$index = Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json
if ($index.schema -ne 'bg2-upscale-area-animation-pack-index-v1' -or $index.status -ne 'completed') {
    throw 'Index de packs par zone incomplet ou incompatible.'
}
if (@($index.areas).Count -ne [int]$index.area_count -or [int]$index.area_count -le 0) {
    throw 'Inventaire de zones invalide.'
}
if (@($index.areas_over_budget).Count -gt 0) {
    throw ("Zones au-dela du budget runtime, installation refusee : " + ($index.areas_over_budget -join ', '))
}

# Chaque pack de zone est revalide ici : le runtime ne tolere aucun asset divergent, et une
# zone corrompue ne doit pas etre decouverte au moment du changement de carte.
$plan = @()
foreach ($area in @($index.areas)) {
    $areaId = [string]$area.area_id
    if ($areaId -notmatch '^[A-Za-z0-9]{1,8}$') { throw "Identifiant de zone non securise : $areaId" }
    $areaSource = Join-Path $splitRootPath ([string]$area.directory)
    $areaManifestPath = Join-Path $areaSource 'manifest.json'
    if (-not (Test-Path -LiteralPath $areaManifestPath -PathType Leaf)) {
        throw "Manifeste de zone absent : $areaManifestPath"
    }
    if ((Get-Sha256 $areaManifestPath) -ne ([string]$area.manifest_sha256).ToLowerInvariant()) {
        throw "Manifeste de zone divergent de l'index : $areaManifestPath"
    }
    $areaManifest = Get-Content -LiteralPath $areaManifestPath -Raw | ConvertFrom-Json
    if ($areaManifest.schema -ne 'bg2-upscale-area-animation-runtime-pack-v2' -or
        $areaManifest.status -ne 'completed' -or [int]$areaManifest.scale -ne 4 -or
        [int]$areaManifest.registry_version -notin @(2, 3) -or
        $areaManifest.registry -ne 'AreaAnimations-X4.registry') {
        throw "Pack de zone incompatible : $areaSource"
    }
    if ($areaManifest.runtime_budget_enforced -eq $false) {
        throw "Pack d'auteur non decoupe presente a l'installation : $areaSource"
    }

    $files = @([PSCustomObject]@{
        Name = 'AreaAnimations-X4.registry'
        Hash = ([string]$areaManifest.registry_sha256).ToLowerInvariant()
        Bytes = [int64]$areaManifest.registry_bytes
    })
    foreach ($resource in @($areaManifest.resources)) {
        foreach ($frame in @($resource.frames)) {
            $files += [PSCustomObject]@{
                Name = [string]$frame.asset
                Hash = ([string]$frame.sha256).ToLowerInvariant()
                Bytes = [int64]$frame.bytes
            }
        }
    }
    if ($files.Count -ne (1 + [int]$areaManifest.frame_count) -or
        (@($files.Name | Select-Object -Unique)).Count -ne $files.Count) {
        throw "Inventaire de zone invalide ou duplique : $areaSource"
    }
    foreach ($file in $files) {
        if ([IO.Path]::GetFileName($file.Name) -ne $file.Name) {
            throw "Nom d'asset non securise : $($file.Name)"
        }
        $sourcePath = Join-Path $areaSource $file.Name
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Asset absent : $sourcePath" }
        if ((Get-Item -LiteralPath $sourcePath).Length -ne $file.Bytes -or
            (Get-Sha256 $sourcePath) -ne $file.Hash) {
            throw "Asset corrompu : $sourcePath"
        }
    }
    $plan += [PSCustomObject]@{
        AreaId = $areaId; Source = $areaSource
        Target = (Join-Path $areasDirectory $areaId); Files = $files
    }
}

$totalFiles = ($plan | ForEach-Object { $_.Files.Count } | Measure-Object -Sum).Sum
Write-Host ("Prevalidation reussie : {0} zone(s), {1} fichier(s), plus lourde zone {2:N1} Mio (plafond {3:N0} Mio)." -f `
    $plan.Count, $totalFiles, ([double]$index.largest_area_raw_bytes / 1MB), ([double]$index.runtime_budget_bytes / 1MB))

if ($VerifyOnly) {
    Write-Host 'VerifyOnly : aucune ecriture effectuee.'
    return
}

if (-not $BackupRoot) { $BackupRoot = Join-Path $splitRootPath 'install-backups' }
$backupDirectory = Join-Path ([IO.Path]::GetFullPath($BackupRoot)) ('per-area-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $backupDirectory) { throw "Dossier de sauvegarde deja present : $backupDirectory" }
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
Copy-Item -LiteralPath $targetDll -Destination (Join-Path $backupDirectory 'InfinityEngine-Enhancer.dll')
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $backupDirectory 'InfinityEngine-Enhancer.ini')

# Un dossier areas\ preexistant appartient a une installation par zone anterieure : il est
# archive en entier, car l'installation en cours le remplace zone par zone.
$hadAreas = Test-Path -LiteralPath $areasDirectory -PathType Container
if ($hadAreas) {
    Copy-Item -LiteralPath $areasDirectory -Destination (Join-Path $backupDirectory 'areas') -Recurse
}

$backupManifest = [ordered]@{
    schema = 'bg2-upscale-area-animation-per-area-install-backup-v1'
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    GameRoot = $gameRootPath
    SplitRoot = $splitRootPath
    SourceDll = $SourceDll
    SourceDllSha256 = (Get-Sha256 $SourceDll)
    PreviousDllSha256 = (Get-Sha256 $targetDll)
    PreviousAreasPresent = $hadAreas
    AreaCount = $plan.Count
    Areas = @($plan | ForEach-Object { $_.AreaId })
}
$backupManifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backupDirectory 'backup-manifest.json') -Encoding UTF8

if ($hadAreas) { Remove-Item -LiteralPath $areasDirectory -Recurse -Force }
New-Item -ItemType Directory -Path $areasDirectory -Force | Out-Null
foreach ($entry in $plan) {
    New-Item -ItemType Directory -Path $entry.Target -Force | Out-Null
    foreach ($file in $entry.Files) {
        Copy-Item -LiteralPath (Join-Path $entry.Source $file.Name) -Destination (Join-Path $entry.Target $file.Name) -Force
    }
}
Copy-Item -LiteralPath $SourceDll -Destination $targetDll -Force
Set-IniValue -Path $iniPath -Key 'EnableAreaAnimationX4' -Value 'true'

# Controle apres ecriture : le runtime refuse tout le pack d'une zone sur un seul octet
# divergent, donc l'installation se verifie ici plutot qu'au prochain changement de carte.
foreach ($entry in $plan) {
    foreach ($file in $entry.Files) {
        $installed = Join-Path $entry.Target $file.Name
        if ((Get-Sha256 $installed) -ne $file.Hash) { throw "Verification post-installation echouee : $installed" }
    }
}
if ((Get-Sha256 $targetDll) -ne (Get-Sha256 $SourceDll)) { throw 'Verification de la DLL echouee.' }

Write-Host ("Installation terminee : {0} zone(s) sous {1}." -f $plan.Count, $areasDirectory)
Write-Host ("Sauvegarde : {0}" -f $backupDirectory)
Write-Host 'Le jeu n a pas ete lance.'
