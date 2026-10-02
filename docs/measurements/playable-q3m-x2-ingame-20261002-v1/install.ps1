[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$q3mRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $q3mRepo 'pipeline/scripts/ThinInstall.ps1')
$q3mBaseline = Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$q3mPackRoot = Join-Path $q3mRepo 'sprite/.work/q3m-playable-all-x2-pack-20261002-v1'
$q3mPack = Read-JsonFile (Join-Path $q3mPackRoot 'pack.json')
$q3mRuntime = Read-JsonFile (Join-Path $q3mRepo $q3mBaseline.runtime_manifest)
$q3mGame = Resolve-WorkspaceInput 'config://bg2ee_game_root' -RequireExisting
$q3mCatalogRelative = 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
$q3mCatalog = Resolve-ChildPath $q3mGame $q3mCatalogRelative -RequireExisting
$q3mIni = Resolve-ChildPath $q3mGame 'InfinityEngine-Enhancer.ini' -RequireExisting
$q3mReceiptPath = Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
if (Test-Path -LiteralPath $q3mReceiptPath) { throw 'Installation receipt exists; preserve this run.' }
if ($q3mGame -ne $q3mBaseline.game_root -or $q3mPack.scale -ne 2 -or
    @($q3mPack.animations).Count -ne 78 -or $q3mPack.resources -ne 4510) { throw 'Installation scope differs.' }
if ((Get-FileSha256 $q3mCatalog) -ne $q3mBaseline.catalog_sha256 -or
    (Get-FileSha256 $q3mIni) -ne $q3mBaseline.ini_sha256) { throw 'Live baseline changed.' }
if ((Get-FileSha256 (Join-Path $q3mPackRoot 'CreatureSprites-XN.catalog')) -ne $q3mPack.catalog.sha256) {
    throw 'Source catalog differs.'
}
if (@($q3mRuntime.capabilities.creature_sprite_xn_catalog.shard_registry_versions) -notcontains 6 -or
    @($q3mRuntime.capabilities.sprite_minification.box_scales) -notcontains 2) { throw 'Runtime lacks Q3m x2 / BOX.' }
foreach ($q3mPreserved in $q3mBaseline.preserved) {
    if ((Get-FileSha256 (Resolve-ChildPath $q3mGame $q3mPreserved.relative_path -RequireExisting)) -ne $q3mPreserved.sha256) {
        throw "Preserved runtime/UI asset changed: $($q3mPreserved.relative_path)"
    }
}
Assert-GameClosed
$q3mBackup = Join-Path $PSScriptRoot 'work/before'
New-Item -ItemType Directory -Path $q3mBackup -Force | Out-Null
Copy-Item -LiteralPath $q3mCatalog -Destination (Join-Path $q3mBackup 'CreatureSprites-XN.catalog')
Copy-Item -LiteralPath $q3mIni -Destination (Join-Path $q3mBackup 'InfinityEngine-Enhancer.ini')
$q3mState = [ordered]@{
    schema='bg2-playable-q3m-x2-install-v1'; status='installing'; game_root=$q3mGame
    catalog_sha256=$q3mPack.catalog.sha256; source_pack=(Join-Path $q3mPackRoot 'pack.json')
    baseline=(Join-Path $PSScriptRoot 'baseline.json'); backup_root=$q3mBackup
    scale=2; animation_ids=@($q3mPack.animations); resources=4510
    creature_sprite_filter='Box'; creature_sprite_filter_animation='0x0'
    new_shards=@(); installed_shards_verified=0; installed_at_utc=$null
}
Write-JsonAtomic $q3mReceiptPath $q3mState
$q3mCopied = [Collections.Generic.List[string]]::new()
$q3mPublicationStarted = $false
try {
    foreach ($q3mShard in $q3mPack.catalog.shards) {
        if ($q3mShard.registry -notmatch '^iee-assets/creature-sprites/CreatureSprites-XN-([A-F0-9]{64})\.registry$' -or
            $Matches[1] -ne $q3mShard.sha256) { throw 'Shard name/hash differs.' }
        $q3mSource = Join-Path $q3mPackRoot ([IO.Path]::GetFileName($q3mShard.registry))
        if ((Get-FileSha256 $q3mSource) -ne $q3mShard.sha256) { throw "Source shard differs: $q3mSource" }
        $q3mTarget = Resolve-ChildPath $q3mGame $q3mShard.registry
        if (-not (Test-Path -LiteralPath $q3mTarget)) {
            Copy-FileAtomic $q3mSource $q3mTarget
            $q3mCopied.Add($q3mTarget)
        }
        if ((Get-Item -LiteralPath $q3mTarget).Length -ne $q3mShard.registry_bytes -or
            (Get-FileSha256 $q3mTarget) -ne $q3mShard.sha256) { throw "Installed shard differs: $q3mTarget" }
        $q3mState.installed_shards_verified++
        if ($q3mState.installed_shards_verified % 500 -eq 0) { Write-Host "installed/verified $($q3mState.installed_shards_verified)/4510" }
    }
    Assert-GameClosed
    if ((Get-FileSha256 $q3mCatalog) -ne $q3mBaseline.catalog_sha256 -or
        (Get-FileSha256 $q3mIni) -ne $q3mBaseline.ini_sha256) { throw 'Live baseline changed during shard copying.' }
    $q3mIniText = Get-Content -LiteralPath $q3mIni -Raw
    $q3mExpected = [ordered]@{ EnableCreatureSpriteUpscaleTest='true'; EnableCreatureSpriteX2Test='false'
        EnableCreatureSpriteLinearFiltering='false'; CreatureSpriteFilter='Box'; CreatureSpriteFilterAnimation='0x0' }
    foreach ($q3mEntry in $q3mExpected.GetEnumerator()) {
        $q3mIniText = Set-IniValue $q3mIniText 'Shaders' $q3mEntry.Key $q3mEntry.Value
    }
    $q3mPublicationStarted = $true
    Write-TextAtomic $q3mIni $q3mIniText
    Copy-FileAtomic (Join-Path $q3mPackRoot 'CreatureSprites-XN.catalog') $q3mCatalog
    if ((Get-FileSha256 $q3mCatalog) -ne $q3mPack.catalog.sha256) { throw 'Published catalog differs.' }
    $q3mInstalledIni = Get-Content -LiteralPath $q3mIni -Raw
    foreach ($q3mEntry in $q3mExpected.GetEnumerator()) {
        if ((Get-IniValue $q3mInstalledIni 'Shaders' $q3mEntry.Key) -ne $q3mEntry.Value) { throw 'Installed filter/config differs.' }
    }
    foreach ($q3mPreserved in $q3mBaseline.preserved) {
        if ((Get-FileSha256 (Resolve-ChildPath $q3mGame $q3mPreserved.relative_path -RequireExisting)) -ne $q3mPreserved.sha256) {
            throw "Preserved asset differs: $($q3mPreserved.relative_path)"
        }
    }
    $q3mState.status='installed-pending-qa'
    $q3mState.new_shards=@($q3mCopied)
    $q3mState.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $q3mReceiptPath $q3mState
} catch {
    if ($q3mPublicationStarted) {
        Copy-FileAtomic (Join-Path $q3mBackup 'CreatureSprites-XN.catalog') $q3mCatalog
        Copy-FileAtomic (Join-Path $q3mBackup 'InfinityEngine-Enhancer.ini') $q3mIni
    }
    # Content-addressed leaves are harmless without catalog references; retain
    # copied leaves after rollback rather than deleting any installed assets.
    $q3mState.status='rolled-back'
    $q3mState.new_shards=@($q3mCopied)
    Write-JsonAtomic $q3mReceiptPath $q3mState
    throw
}
[pscustomobject]@{ Status=$q3mState.status; Animations=78; Resources=4510
    InstalledShardsVerified=$q3mState.installed_shards_verified; Copied=$q3mCopied.Count; Filter='Box'; Scope='all' }
