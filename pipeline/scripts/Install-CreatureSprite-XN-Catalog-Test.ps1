[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$JobFile,
    [string]$RuntimeManifest = 'pipeline/runtime/manifests/iee-water-ar1000n-creature-catalog-v2-v1.json',
    [ValidateSet('Nearest', 'CatmullRom')][string]$CreatureSpriteFilter = 'Nearest',
    [switch]$EnableDerivedInstall,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$jobPath = Resolve-WorkspaceInput $JobFile -RequireExisting
$job = Read-JsonFile $jobPath
$catalogJob = $job
$environmentJob = $job
$supportedCatalogJobs = @(
        'bg2-upscale-creature-sprite-xn-catalog-job-v1',
        'bg2-upscale-creature-sprite-xn-catalog-delta-job-v1'
)
$derivedCatalogJob = 'bg2-upscale-reboutcx-derived-catalog-job-v1'
if ($job.schema -notin @($supportedCatalogJobs + $derivedCatalogJob)) {
    throw 'Job catalogue non supporté.'
}
$isDerivedCatalog = $job.schema -eq $derivedCatalogJob
if ($isDerivedCatalog -and -not $VerifyOnly -and -not $EnableDerivedInstall) {
    throw 'Installation ReboutCX exige -EnableDerivedInstall.'
}
$run = Resolve-WorkspaceInput ([string]$job.paths.run_dir) -RequireExisting
$stateRun = $run
$pointerPath = Join-Path $run 'current-generation.json'
$pointer = Read-JsonFile $pointerPath
$generation = Resolve-WorkspaceInput ([string]$pointer.generation_dir) -RequireExisting
$buildPath = Resolve-ChildPath $generation ([string]$pointer.build_manifest) -RequireExisting
$build = Read-JsonFile $buildPath

if ($catalogJob.schema -in $supportedCatalogJobs) {
    if ($pointer.schema -ne 'bg2-upscale-creature-sprite-xn-catalog-current-generation-v1' -or
        $build.schema -ne 'bg2-upscale-creature-sprite-xn-catalog-pack-v1' -or
        $build.generation_id -ne $pointer.generation_id -or $build.registry_layout -ne 'catalog') {
        throw 'Identité de génération catalogue incohérente.'
    }
} else {
    if ($pointer.schema -ne 'bg2-upscale-reboutcx-derived-catalog-current-v1' -or
        $build.schema -ne 'bg2-upscale-reboutcx-derived-catalog-build-v1' -or
        $build.status -ne 'built-offline-verified' -or [bool]$build.installable -or
        $build.generation_id -ne $pointer.generation_id -or [int]$build.registry_scale -ne 2 -or
        (Get-FileSha256 $jobPath) -ne ([string]$pointer.job_sha256).ToUpperInvariant() -or
        (Get-FileSha256 $buildPath) -ne ([string]$pointer.build_manifest_sha256).ToUpperInvariant() -or
        ([string]$build.registry_catalog_sha256).ToUpperInvariant() -ne
        ([string]$pointer.catalog_sha256).ToUpperInvariant()) {
        throw 'Identité de génération ReboutCX incohérente.'
    }
    $parentBuildPath = Resolve-WorkspaceInput ([string]$build.parent.build_manifest) -RequireExisting
    if ((Get-FileSha256 $parentBuildPath) -ne ([string]$build.parent.build_manifest_sha256).ToUpperInvariant()) {
        throw 'Manifeste xBR parent du catalogue ReboutCX incohérent.'
    }
    $parentBuild = Read-JsonFile $parentBuildPath
    if ($parentBuild.schema -ne 'bg2-upscale-creature-sprite-xn-catalog-pack-v1' -or
        $parentBuild.generation_id -ne $build.parent.generation_id -or
        ([string]$parentBuild.registry_catalog_sha256).ToUpperInvariant() -ne
        ([string]$build.parent.catalog_sha256).ToUpperInvariant() -or
        [int]$parentBuild.registry_catalog_version -ne 2 -or
        [int]$parentBuild.registry_catalog_shard_version -ne 5) {
        throw 'Génération xBR parente du catalogue ReboutCX incohérente.'
    }
    $parentPointerPath = Resolve-WorkspaceInput ([string]$catalogJob.paths.parent_pointer) -RequireExisting
    $manifestParentPointerPath = Resolve-WorkspaceInput ([string]$build.parent.pointer) -RequireExisting
    $parentPointerSha256 = Get-FileSha256 $parentPointerPath
    if (-not [string]::Equals(
            [IO.Path]::GetFullPath($parentPointerPath),
            [IO.Path]::GetFullPath($manifestParentPointerPath),
            [StringComparison]::OrdinalIgnoreCase
        ) -or
        $parentPointerSha256 -ne ([string]$catalogJob.parent.pointer_sha256).ToUpperInvariant() -or
        $parentPointerSha256 -ne ([string]$build.parent.pointer_sha256).ToUpperInvariant()) {
        throw 'Pointeur xBR parent du catalogue ReboutCX incohérent.'
    }
    $stateRun = Split-Path -Parent $parentPointerPath
    $environmentJobPath = Resolve-WorkspaceInput ([string]$parentBuild.job_file) -RequireExisting
    if ((Get-FileSha256 $environmentJobPath) -ne ([string]$parentBuild.job_sha256).ToUpperInvariant()) {
        throw 'Job xBR parent du catalogue ReboutCX incohérent.'
    }
    $environmentJob = Read-JsonFile $environmentJobPath
    if ($environmentJob.schema -notin $supportedCatalogJobs) {
        throw 'Job xBR parent non supporté.'
    }
    $build = [pscustomobject]@{
        generation_id = [string]$build.generation_id
        registry_layout = 'catalog'
        registry_catalog = [string]$build.registry_catalog
        registry_catalog_version = 2
        registry_catalog_shard_version = [int]$build.storage.shard_registry_version
        registry_catalog_frame_storage = [string]$build.storage.frame_storage
        registry_catalog_sha256 = ([string]$build.registry_catalog_sha256).ToUpperInvariant()
        registry_catalog_bytes = [int64]$build.registry_catalog_bytes
        animation_ids = @($build.animations | ForEach-Object { [string]$_.animation_id })
        shards = @($build.shards)
    }
}
$game = Resolve-WorkspaceInput ([string]$environmentJob.paths.game_root) -RequireExisting
$buildRoot = Split-Path -Parent $buildPath
$catalogSource = Resolve-ChildPath $buildRoot ([string]$build.registry_catalog) -RequireExisting
if ((Get-Item -LiteralPath $catalogSource).Length -ne [int64]$build.registry_catalog_bytes) {
    throw 'Taille du catalogue source incohérente.'
}
if ((Get-FileSha256 $catalogSource) -ne ([string]$build.registry_catalog_sha256).ToUpperInvariant()) {
    throw 'Hash du catalogue source incohérent.'
}

$installRoot = Join-Path $stateRun 'ingame-installation'
$statePath = Join-Path $installRoot 'active-test.json'
$active = $null
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $active = Read-JsonFile $statePath
}
if ($active -and $active.schema -eq 'bg2-upscale-creature-sprite-catalog-install-v2' -and
    $active.status -eq 'installing') {
    if ($VerifyOnly) {
        throw 'Transaction catalogue inachevée ; relancer une installation ou restaurer jeu fermé.'
    }
    Assert-GameClosed
    if (-not [string]::Equals(
            [IO.Path]::GetFullPath([string]$active.game_root),
            [IO.Path]::GetFullPath($game),
            [StringComparison]::OrdinalIgnoreCase
        )) {
        throw 'Transaction catalogue inachevée liée à une autre installation.'
    }
    Restore-CatalogInstallTransactionV2 $statePath $active
    $active = if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        Read-JsonFile $statePath
    } else { $null }
}
$runtimeInput = $RuntimeManifest
if (-not $PSBoundParameters.ContainsKey('RuntimeManifest') -and
    $active -and $active.schema -eq 'bg2-upscale-creature-sprite-catalog-install-v2' -and
    -not [string]::IsNullOrWhiteSpace([string]$active.runtime_manifest)) {
    $runtimeInput = [string]$active.runtime_manifest
}
$runtimePath = Resolve-WorkspaceInput $runtimeInput -RequireExisting
$runtime = Read-JsonFile $runtimePath
if ($runtime.schema -ne 'bg2-upscale-runtime-capabilities-v1') { throw 'Manifeste runtime non supporté.' }
$expectedExe = ([string]$environmentJob.compatibility.baldur_real_sha256).ToUpperInvariant()
if ($expectedExe -ne ([string]$runtime.game_profile.baldur_real_sha256).ToUpperInvariant() -or
    (Get-FileSha256 (Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting)) -ne $expectedExe) {
    throw 'Profil de jeu incompatible.'
}
$liveDll = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
if ((Get-FileSha256 $liveDll) -ne ([string]$runtime.dll.sha256).ToUpperInvariant()) {
    throw 'Installez le runtime stable déclaré par -RuntimeManifest avant le catalogue.'
}
$capability = $runtime.capabilities.creature_sprite_xn_catalog
if (@($capability.catalog_versions) -notcontains [int]$build.registry_catalog_version -or
    @($capability.shard_registry_versions) -notcontains [int]$build.registry_catalog_shard_version -or
    @($capability.frame_storage) -notcontains [string]$build.registry_catalog_frame_storage) {
    throw 'Le runtime stable ne supporte pas ce catalogue.'
}

$catalogTarget = Resolve-ChildPath $game ([string]$build.registry_catalog)
$shards = [Collections.Generic.List[object]]::new()
foreach ($shard in @($build.shards)) {
    $relative = ([string]$shard.registry).Replace('\', '/')
    if ($relative -notmatch '^iee-assets/creature-sprites/CreatureSprites-XN-([0-9A-F]{64})\.registry$') {
        throw "Nom de shard invalide : $relative"
    }
    $expectedShardSha256 = ([string]$shard.sha256).ToUpperInvariant()
    if ($expectedShardSha256 -ne $Matches[1]) {
        throw "Hash et nom de shard divergents : $relative"
    }
    $source = Resolve-ChildPath $buildRoot $relative -RequireExisting
    if ((Get-FileSha256 $source) -ne $expectedShardSha256) {
        throw "Hash du shard source incohérent : $relative"
    }
    $target = Resolve-ChildPath $game $relative
    $targetPresent = Test-Path -LiteralPath $target -PathType Leaf
    if ($targetPresent -and (Get-FileSha256 $target) -ne $expectedShardSha256) {
        throw "Shard installé corrompu ou concurrent : $relative"
    }
    $shards.Add([pscustomobject]@{
            source = $source
            target = $target
            sha256 = $expectedShardSha256
            present = [bool]$targetPresent
        })
}
if (-not $shards.Count) { throw 'Le catalogue ne référence aucun shard.' }

$iniTarget = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
$activeCatalogSha256 = $null
$targetActive = $false
$runtimeAdoption = $false
if ($active) {
    if ($active.schema -ne 'bg2-upscale-creature-sprite-catalog-install-v2' -or
        $active.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
        throw 'Reçu catalogue actif invalide ou transaction inachevée.'
    }
    if (-not [string]::Equals(
            [IO.Path]::GetFullPath([string]$active.game_root),
            [IO.Path]::GetFullPath($game),
            [StringComparison]::OrdinalIgnoreCase
        )) {
        throw 'Reçu catalogue actif lié à une autre installation.'
    }
    $activeCatalogTarget = Resolve-ChildPath $game ([string]$active.catalog_relative_path) -RequireExisting
    $activeCatalogSha256 = Get-FileSha256 $activeCatalogTarget
    if ($activeCatalogSha256 -ne ([string]$active.catalog_sha256).ToUpperInvariant()) {
        throw 'Catalogue actif divergent du reçu.'
    }
    if ([string]$active.runtime_id -ne [string]$runtime.runtime_id) {
        if (-not $PSBoundParameters.ContainsKey('RuntimeManifest')) {
            throw 'Runtime actif divergent du reçu catalogue.'
        }
        $runtimeAdoption = $true
    }
    $activeFilter = [string]$active.creature_sprite_filter
    if ($activeFilter -notin @('Nearest', 'CatmullRom')) {
        throw 'Filtre sprites du reçu actif invalide.'
    }
    $ini = Get-Content -LiteralPath $iniTarget -Raw
    $expectedIni = [ordered]@{
        EnableCreatureSpriteUpscaleTest = 'true'
        EnableCreatureSpriteX2Test = 'false'
        EnableCreatureSpriteLinearFiltering = 'false'
        CreatureSpriteFilter = $activeFilter
    }
    foreach ($entry in $expectedIni.GetEnumerator()) {
        $actual = Get-IniValue $ini 'Shaders' $entry.Key
        if (-not [string]::Equals($actual, [string]$entry.Value, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Configuration sprites active divergente : $($entry.Key)"
        }
    }
    $targetActive = (
        -not $runtimeAdoption -and
        [string]$active.generation_id -eq [string]$pointer.generation_id -and
        ([string]$active.catalog_sha256).ToUpperInvariant() -eq
        ([string]$build.registry_catalog_sha256).ToUpperInvariant() -and
        $activeFilter -eq $CreatureSpriteFilter
    )
    if ($targetActive) {
        $missing = @($shards | Where-Object { -not $_.present })
        if ($missing.Count) {
            throw 'Catalogue actif incomplet : shard référencé absent.'
        }
        [pscustomobject]@{
            Status = 'already-installed'; GenerationId = $pointer.generation_id
            Shards = $shards.Count; SourceShardsVerified = $shards.Count
            InstalledShardsVerified = $shards.Count; CatalogSha256 = $activeCatalogSha256
            State = $statePath; TargetActive = $true
        }
        return
    }
}
if ($VerifyOnly) {
    [pscustomobject]@{
        Status = 'verified'; GenerationId = $pointer.generation_id
        Shards = $shards.Count; SourceShardsVerified = $shards.Count
        ActiveGenerationId = if ($active) { [string]$active.generation_id } else { $null }
        ActiveCatalogSha256 = $activeCatalogSha256; State = $statePath
        TargetActive = $false; RuntimeAdoption = $runtimeAdoption
        RuntimeId = [string]$runtime.runtime_id
    }
    return
}

Assert-GameClosed
$transaction = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmss.fffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$backupRoot = Join-Path $installRoot "backups/$transaction"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$previousState = Test-Path -LiteralPath $statePath -PathType Leaf
if ($previousState) { Copy-Item -LiteralPath $statePath -Destination (Join-Path $backupRoot 'previous-active-test.json') }
$iniBackup = Join-Path $backupRoot 'InfinityEngine-Enhancer.ini'
Copy-Item -LiteralPath $iniTarget -Destination $iniBackup
$catalogExisted = Test-Path -LiteralPath $catalogTarget -PathType Leaf
$catalogBackup = Join-Path $backupRoot 'CreatureSprites-XN.catalog'
if ($catalogExisted) { Copy-Item -LiteralPath $catalogTarget -Destination $catalogBackup }
$iniBackupSha256 = Get-FileSha256 $iniBackup
$catalogBackupSha256 = if ($catalogExisted) { Get-FileSha256 $catalogBackup } else { $null }
$previousStateSha256 = if ($previousState) {
    Get-FileSha256 (Join-Path $backupRoot 'previous-active-test.json')
} else { $null }

$copied = 0
foreach ($shard in $shards) {
    if (-not (Test-Path -LiteralPath $shard.target -PathType Leaf)) {
        Copy-FileAtomic $shard.source $shard.target
        if ((Get-FileSha256 $shard.target) -ne [string]$shard.sha256) {
            throw "Copie de shard incohérente : $($shard.target)"
        }
        $copied++
    }
}
$state = [ordered]@{
    schema = 'bg2-upscale-creature-sprite-catalog-install-v2'; status = 'installing'
    transaction_id = $transaction; job_file = $jobPath; job_id = [string]$catalogJob.job_id
    generation_id = [string]$pointer.generation_id; game_root = $game
    runtime_id = [string]$runtime.runtime_id; runtime_manifest = $runtimePath
    installation_mode = 'thin-catalog'; creature_sprite_filter = $CreatureSpriteFilter
    build_manifest = $buildPath; catalog_relative_path = [string]$build.registry_catalog
    catalog_sha256 = ([string]$build.registry_catalog_sha256).ToUpperInvariant()
    catalog_existed_before = [bool]$catalogExisted
    catalog_backup = if ($catalogExisted) { 'CreatureSprites-XN.catalog' } else { $null }
    catalog_backup_sha256 = $catalogBackupSha256
    ini_backup = 'InfinityEngine-Enhancer.ini'; ini_backup_sha256 = $iniBackupSha256
    backup_root = $backupRoot
    previous_active_state = if ($previousState) { 'previous-active-test.json' } else { $null }
    previous_active_state_sha256 = $previousStateSha256
    animation_ids = @($build.animation_ids); shards_total = $shards.Count; shards_copied = $copied
}
Write-JsonAtomic $statePath $state
try {
    $ini = Get-Content -LiteralPath $iniTarget -Raw
    $ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpriteUpscaleTest' 'true'
    $ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpriteX2Test' 'false'
    $ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpriteLinearFiltering' 'false'
    $ini = Set-IniValue $ini 'Shaders' 'CreatureSpriteFilter' $CreatureSpriteFilter
    Write-TextAtomic $iniTarget $ini
    Copy-FileAtomic $catalogSource $catalogTarget
    if ((Get-FileSha256 $catalogTarget) -ne ([string]$build.registry_catalog_sha256).ToUpperInvariant()) {
        throw 'Catalogue actif incorrect après publication.'
    }
    $installedIni = Get-Content -LiteralPath $iniTarget -Raw
    foreach ($entry in ([ordered]@{
                EnableCreatureSpriteUpscaleTest = 'true'
                EnableCreatureSpriteX2Test = 'false'
                EnableCreatureSpriteLinearFiltering = 'false'
                CreatureSpriteFilter = $CreatureSpriteFilter
            }).GetEnumerator()) {
        if (-not [string]::Equals(
                (Get-IniValue $installedIni 'Shaders' $entry.Key),
                [string]$entry.Value,
                [StringComparison]::OrdinalIgnoreCase
            )) {
            throw "Configuration sprites incorrecte après publication : $($entry.Key)"
        }
    }
    $state.status = 'installed-pending-qa'
    $state.installed_at_utc = [DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
} catch {
    Restore-CatalogInstallTransactionV2 $statePath $state
    throw
}
[pscustomobject]@{
    Status = 'installed-pending-qa'; GenerationId = $pointer.generation_id
    Shards = $shards.Count; CopiedShards = $copied
    RuntimeMode = if ($runtimeAdoption) { 'adopted-existing' } else { 'independent' }
}
