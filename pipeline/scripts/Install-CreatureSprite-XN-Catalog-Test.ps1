[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$JobFile,
    [string]$RuntimeManifest = 'pipeline/runtime/manifests/iee-water-ar1000n-creature-catalog-v2-v1.json',
    [ValidateSet('Nearest', 'CatmullRom')][string]$CreatureSpriteFilter = 'Nearest',
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$jobPath = Resolve-WorkspaceInput $JobFile -RequireExisting
$job = Read-JsonFile $jobPath
if ($job.schema -ne 'bg2-upscale-creature-sprite-xn-catalog-job-v1') { throw 'Job catalogue non supporté.' }
$game = Resolve-WorkspaceInput ([string]$job.paths.game_root) -RequireExisting
$run = Resolve-WorkspaceInput ([string]$job.paths.run_dir) -RequireExisting
$pointerPath = Join-Path $run 'current-generation.json'
$pointer = Read-JsonFile $pointerPath
if ($pointer.schema -ne 'bg2-upscale-creature-sprite-xn-catalog-current-generation-v1') {
    throw 'Pointeur de génération non supporté.'
}
$generation = Resolve-WorkspaceInput ([string]$pointer.generation_dir) -RequireExisting
$buildPath = Resolve-ChildPath $generation ([string]$pointer.build_manifest) -RequireExisting
$build = Read-JsonFile $buildPath
if ($build.schema -ne 'bg2-upscale-creature-sprite-xn-catalog-pack-v1' -or
    $build.generation_id -ne $pointer.generation_id -or $build.registry_layout -ne 'catalog') {
    throw 'Identité de génération catalogue incohérente.'
}
$buildRoot = Split-Path -Parent $buildPath
$catalogSource = Resolve-ChildPath $buildRoot ([string]$build.registry_catalog) -RequireExisting
if ((Get-Item -LiteralPath $catalogSource).Length -ne [int64]$build.registry_catalog_bytes) {
    throw 'Taille du catalogue source incohérente.'
}

$runtimePath = Resolve-WorkspaceInput $RuntimeManifest -RequireExisting
$runtime = Read-JsonFile $runtimePath
if ($runtime.schema -ne 'bg2-upscale-runtime-capabilities-v1') { throw 'Manifeste runtime non supporté.' }
$expectedExe = ([string]$job.compatibility.baldur_real_sha256).ToUpperInvariant()
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
    if ($relative -notmatch '^iee-assets/creature-sprites/CreatureSprites-XN-[0-9A-F]{64}\.registry$') {
        throw "Nom de shard invalide : $relative"
    }
    $shards.Add([pscustomobject]@{
            source = Resolve-ChildPath $buildRoot $relative -RequireExisting
            target = Resolve-ChildPath $game $relative
        })
}
if (-not $shards.Count) { throw 'Le catalogue ne référence aucun shard.' }

$installRoot = Join-Path $run 'ingame-installation'
$statePath = Join-Path $installRoot 'active-test.json'
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $active = Read-JsonFile $statePath
    if ($active.schema -eq 'bg2-upscale-creature-sprite-catalog-install-v2' -and
        $active.generation_id -eq $pointer.generation_id -and
        $active.status -in @('installed-pending-qa', 'validated-installed', 'qa-failed') -and
        (Test-Path -LiteralPath $catalogTarget -PathType Leaf)) {
        [pscustomobject]@{ Status = 'already-installed'; GenerationId = $pointer.generation_id; Shards = $shards.Count }
        return
    }
}
if ($VerifyOnly) {
    [pscustomobject]@{ Status = 'verified'; GenerationId = $pointer.generation_id; Shards = $shards.Count }
    return
}

Assert-GameClosed
$transaction = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmss.fffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$backupRoot = Join-Path $installRoot "backups/$transaction"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$previousState = Test-Path -LiteralPath $statePath -PathType Leaf
if ($previousState) { Copy-Item -LiteralPath $statePath -Destination (Join-Path $backupRoot 'previous-active-test.json') }
$iniTarget = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
$iniBackup = Join-Path $backupRoot 'InfinityEngine-Enhancer.ini'
Copy-Item -LiteralPath $iniTarget -Destination $iniBackup
$catalogExisted = Test-Path -LiteralPath $catalogTarget -PathType Leaf
$catalogBackup = Join-Path $backupRoot 'CreatureSprites-XN.catalog'
if ($catalogExisted) { Copy-Item -LiteralPath $catalogTarget -Destination $catalogBackup }

$copied = 0
foreach ($shard in $shards) {
    if (-not (Test-Path -LiteralPath $shard.target -PathType Leaf)) {
        Copy-FileAtomic $shard.source $shard.target
        $copied++
    }
}
$state = [ordered]@{
    schema = 'bg2-upscale-creature-sprite-catalog-install-v2'; status = 'installing'
    transaction_id = $transaction; job_file = $jobPath; job_id = [string]$job.job_id
    generation_id = [string]$pointer.generation_id; game_root = $game
    runtime_id = [string]$runtime.runtime_id; runtime_manifest = $runtimePath
    installation_mode = 'thin-catalog'; creature_sprite_filter = $CreatureSpriteFilter
    build_manifest = $buildPath; catalog_relative_path = [string]$build.registry_catalog
    catalog_sha256 = ([string]$build.registry_catalog_sha256).ToUpperInvariant()
    catalog_existed_before = [bool]$catalogExisted
    catalog_backup = if ($catalogExisted) { 'CreatureSprites-XN.catalog' } else { $null }
    ini_backup = 'InfinityEngine-Enhancer.ini'; backup_root = $backupRoot
    previous_active_state = if ($previousState) { 'previous-active-test.json' } else { $null }
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
    $state.status = 'installed-pending-qa'
    $state.installed_at_utc = [DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
} catch {
    Copy-FileAtomic $iniBackup $iniTarget
    if ($catalogExisted) { Copy-FileAtomic $catalogBackup $catalogTarget }
    elseif (Test-Path -LiteralPath $catalogTarget) { Remove-Item -LiteralPath $catalogTarget -Force }
    if ($previousState) { Copy-FileAtomic (Join-Path $backupRoot 'previous-active-test.json') $statePath }
    else { Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue }
    throw
}
[pscustomobject]@{
    Status = 'installed-pending-qa'; GenerationId = $pointer.generation_id
    Shards = $shards.Count; CopiedShards = $copied; RuntimeMode = 'independent'
}
