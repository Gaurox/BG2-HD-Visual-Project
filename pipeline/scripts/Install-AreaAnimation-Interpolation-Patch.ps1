param(
    [Parameter(Mandatory = $true)]
    [string]$PatchRoot,
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

$ErrorActionPreference = "Stop"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw "Quittez completement BG2EE et InfinityLoader avant l'installation." }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$patchRootPath = (Resolve-Path -LiteralPath $PatchRoot).Path
$manifestPath = Join-Path $patchRootPath "manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne "bg2-upscale-area-animation-frame-expansion-test-v1" -or
    $manifest.status -ne "completed" -or [int]$manifest.scale -ne 4 -or
    -not ([string]$manifest.resref -match "^[A-Z0-9]{1,8}$") -or
    [int]$manifest.frame_count -le 0 -or [int]$manifest.native_cycle_slots -ne [int]$manifest.frame_count) {
    throw "Manifest interpolation incompatible."
}

$assetsRoot = Join-Path $gameRootPath "iee-assets"
$sourceRegistry = Join-Path $patchRootPath ([string]$manifest.target_registry)
$targetRegistry = Join-Path $assetsRoot "AreaAnimations-X4.registry"
if ([IO.Path]::GetFileName([string]$manifest.target_registry) -ne "AreaAnimations-X4.registry" -or
    -not (Test-Path -LiteralPath $sourceRegistry -PathType Leaf) -or
    -not (Test-Path -LiteralPath $targetRegistry -PathType Leaf)) {
    throw "Registre de patch ou registre actif absent."
}
if ((Get-Sha256 $targetRegistry) -ne [string]$manifest.base_registry_sha256) {
    throw "Le registre actif ne correspond pas a la base attendue ; installation refusee."
}
if ((Get-Sha256 $sourceRegistry) -ne [string]$manifest.target_registry_sha256 -or
    (Get-Item -LiteralPath $sourceRegistry).Length -ne [int64]$manifest.target_registry_bytes) {
    throw "Le registre du patch est corrompu."
}

$baseByName = @{}
foreach ($frame in @($manifest.base_resource.frames)) {
    $name = [string]$frame.asset
    if ([IO.Path]::GetFileName($name) -ne $name -or $baseByName.ContainsKey($name)) {
        throw "Inventaire de base invalide : $name"
    }
    $baseByName[$name] = $frame
}

$entries = @()
foreach ($frame in @($manifest.frames | Sort-Object { [int]$_.frame })) {
    $index = [int]$frame.frame
    $name = [string]$frame.asset
    if ($name -ne ("AAX4-$($manifest.resref)-frame{0:D3}.rgba" -f $index) -or
        [IO.Path]::GetFileName($name) -ne $name) {
        throw "Nom d'asset runtime inattendu : $name"
    }
    $physical = @($frame.physical_size_x4)
    if ($physical.Count -ne 2 -or [int64]$frame.bytes -ne ([int64]$physical[0] * [int64]$physical[1] * 4)) {
        throw "Taille physique runtime invalide : $name"
    }
    $source = Join-Path $patchRootPath $name
    $target = Join-Path $assetsRoot $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or
        (Get-Sha256 $source) -ne [string]$frame.sha256 -or
        (Get-Item -LiteralPath $source).Length -ne [int64]$frame.bytes) {
        throw "Asset du patch corrompu : $source"
    }
    $wasPresent = $baseByName.ContainsKey($name)
    if ($wasPresent) {
        $base = $baseByName[$name]
        if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
            (Get-Sha256 $target) -ne [string]$base.sha256 -or
            (Get-Item -LiteralPath $target).Length -ne [int64]$base.bytes) {
            throw "Asset actif different de la base attendue : $target"
        }
    } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        throw "Asset supplementaire deja present ou ambigu : $target"
    }
    $entries += [PSCustomObject]@{
        Name = $name
        Source = $source
        Target = $target
        WasPresent = $wasPresent
        OriginalHash = if ($wasPresent) { Get-Sha256 $target } else { $null }
        TestHash = [string]$frame.sha256
        Bytes = [int64]$frame.bytes
    }
}
if ($entries.Count -ne [int]$manifest.frame_count) { throw "Inventaire de frames incomplet." }

$backupDirectory = Join-Path $patchRootPath ("install-backups\interpolation-$($manifest.resref)-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
if (Test-Path -LiteralPath $backupDirectory) { throw "Sauvegarde deja presente : $backupDirectory" }
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
Copy-Item -LiteralPath $targetRegistry -Destination (Join-Path $backupDirectory "AreaAnimations-X4.registry")
foreach ($entry in $entries) {
    if ($entry.WasPresent) { Copy-Item -LiteralPath $entry.Target -Destination (Join-Path $backupDirectory $entry.Name) }
}

$backupManifest = [ordered]@{
    Schema = "bg2-upscale-area-animation-interpolation-install-backup-v1"
    CreatedUtc = [DateTime]::UtcNow.ToString("o")
    GameRoot = $gameRootPath
    Resref = [string]$manifest.resref
    PatchManifestHash = Get-Sha256 $manifestPath
    OriginalRegistryHash = Get-Sha256 $targetRegistry
    TestRegistryHash = [string]$manifest.target_registry_sha256
    Files = @($entries | ForEach-Object {
        [ordered]@{
            Name = $_.Name
            WasPresent = [bool]$_.WasPresent
            OriginalHash = $_.OriginalHash
            TestHash = $_.TestHash
            Bytes = $_.Bytes
        }
    })
}
$backupManifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backupDirectory "install-backup.json") -Encoding UTF8

try {
    Copy-Item -LiteralPath $sourceRegistry -Destination $targetRegistry -Force
    foreach ($entry in $entries) { Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force }
    if ((Get-Sha256 $targetRegistry) -ne $backupManifest.TestRegistryHash) {
        throw "Verification du registre installe echouee."
    }
    foreach ($entry in $entries) {
        if ((Get-Sha256 $entry.Target) -ne $entry.TestHash) {
            throw "Verification apres copie echouee : $($entry.Target)"
        }
    }
} catch {
    $failure = $_
    Copy-Item -LiteralPath (Join-Path $backupDirectory "AreaAnimations-X4.registry") -Destination $targetRegistry -Force
    foreach ($entry in $entries) {
        if ($entry.WasPresent) {
            Copy-Item -LiteralPath (Join-Path $backupDirectory $entry.Name) -Destination $entry.Target -Force
        } elseif (Test-Path -LiteralPath $entry.Target -PathType Leaf) {
            if ((Get-Sha256 $entry.Target) -eq $entry.TestHash) { Remove-Item -LiteralPath $entry.Target -Force }
        }
    }
    throw "Installation annulee et etat initial restaure : $failure"
}

Write-Host "Patch interpolation installe : $($manifest.resref), $($manifest.frame_count) frames, $($manifest.playback_fps) FPS."
Write-Host "Sauvegarde reversible : $backupDirectory"
Write-Host "Le jeu reste ferme. Lancez-le vous-meme pour la QA."
