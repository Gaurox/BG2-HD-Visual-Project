[CmdletBinding()]
param([ValidateSet('Install','Verify','Restore')][string]$Mode='Install')
$ErrorActionPreference='Stop'
$q3mRepo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $q3mRepo 'pipeline/scripts/ThinInstall.ps1')
$q3mPhase6=Join-Path $q3mRepo 'docs/measurements/q3m-monster-integration-x2-20261003-v1'
$q3mBaseline=Read-JsonFile (Join-Path $q3mPhase6 'baseline.json')
$q3mPointer=Read-JsonFile (Join-Path $q3mPhase6 'current-generation.json')
$q3mPackRoot=Join-Path $q3mRepo $q3mPointer.generation_dir
$q3mManifest=Join-Path $q3mPackRoot 'pack.json'
if ((Get-FileSha256 $q3mManifest) -ne $q3mPointer.manifest_sha256.ToUpperInvariant()) { throw 'Integrated manifest changed.' }
$q3mPack=Read-JsonFile $q3mManifest
$q3mGame=Resolve-WorkspaceInput 'config://bg2ee_game_root' -RequireExisting
$q3mRuntimePath=Join-Path $q3mRepo $q3mPack.runtime_manifest
$q3mRuntime=Read-JsonFile $q3mRuntimePath
if ((Get-FileSha256 $q3mRuntimePath) -ne $q3mPack.runtime_manifest_sha256.ToUpperInvariant()) { throw 'Runtime manifest changed.' }
$q3mDll=Resolve-ChildPath $q3mGame 'InfinityEngine-Enhancer.dll' -RequireExisting
$q3mCatalog=Resolve-ChildPath $q3mGame 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting
$q3mIni=Resolve-ChildPath $q3mGame 'InfinityEngine-Enhancer.ini' -RequireExisting
$q3mBackup=Join-Path $PSScriptRoot 'work/before'
$q3mRuntimeState='docs/measurements/q3m-monster-ingame-x2-20261003-v1/work/runtime-installation'
$q3mReceipt=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$q3mRuntimeInstaller=Join-Path $q3mRepo 'pipeline/scripts/Install-IEE-Runtime-Test.ps1'
$q3mSourceCatalog=Join-Path $q3mPackRoot 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
if ($q3mPack.catalog.animation_count -ne 81 -or $q3mPack.catalog.total_resources -ne 4549 -or
    @($q3mPack.new_shards).Count -ne 39 -or
    (Get-FileSha256 $q3mSourceCatalog) -ne $q3mPointer.catalog_sha256) { throw 'Installation scope/catalog differs.' }

function Assert-Q3mBox {
    $q3mText=Get-Content -LiteralPath $q3mIni -Raw
    foreach ($q3mEntry in $q3mBaseline.box_configuration.PSObject.Properties) {
        if ((Get-IniValue $q3mText 'Shaders' $q3mEntry.Name) -ne $q3mEntry.Value) { throw 'BOX configuration differs.' }
    }
}

function Verify-Q3mInstalled {
    if ((Get-FileSha256 $q3mCatalog) -ne $q3mPointer.catalog_sha256 -or
        (Get-FileSha256 $q3mDll) -ne $q3mRuntime.dll.sha256.ToUpperInvariant() -or
        (Get-FileSha256 $q3mIni) -ne $q3mBaseline.live_files[1].sha256.ToUpperInvariant()) { throw 'Installed binding or preserved INI differs.' }
    Assert-Q3mBox
    foreach ($q3mShard in $q3mPack.new_shards) {
        $q3mTarget=Resolve-ChildPath $q3mGame $q3mShard.registry -RequireExisting
        if ((Get-Item -LiteralPath $q3mTarget).Length -ne $q3mShard.registry_bytes -or
            (Get-FileSha256 $q3mTarget) -ne $q3mShard.sha256) { throw 'Installed new shard differs.' }
    }
}

if ($Mode -eq 'Verify') { Verify-Q3mInstalled; [pscustomobject]@{Status='verified';Animations=81;NewResources=39;Filter='Box'}; return }
if ($Mode -eq 'Restore') {
    Assert-GameClosed
    $q3mState=Read-JsonFile $q3mReceipt
    if ($q3mState.schema -ne 'bg2-q3m-monster-catalog-install-v1' -or $q3mState.game_root -ne $q3mGame) { throw 'Restoration receipt differs.' }
    Verify-Q3mInstalled
    Copy-FileAtomic (Join-Path $q3mBackup 'CreatureSprites-XN.catalog') $q3mCatalog
    Copy-FileAtomic (Join-Path $q3mBackup 'InfinityEngine-Enhancer.ini') $q3mIni
    & $q3mRuntimeInstaller -Mode Restore -Manifest $q3mPack.runtime_manifest -StateRoot $q3mRuntimeState
    $q3mState.status='restored';$q3mState.restored_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $q3mReceipt $q3mState
    return
}
if (Test-Path -LiteralPath $q3mReceipt) { throw 'Preserve existing receipt; create a new installation version.' }
Assert-GameClosed
if ($q3mGame -ne $q3mBaseline.game_root) { throw 'Game root changed.' }
foreach ($q3mFile in $q3mBaseline.live_files) {
    if ((Get-FileSha256 (Resolve-ChildPath $q3mGame $q3mFile.relative_path -RequireExisting)) -ne $q3mFile.sha256.ToUpperInvariant()) {
        throw "Live baseline changed: $($q3mFile.relative_path)"
    }
}
Assert-Q3mBox
New-Item -ItemType Directory -Path $q3mBackup -Force | Out-Null
Copy-Item -LiteralPath $q3mCatalog -Destination (Join-Path $q3mBackup 'CreatureSprites-XN.catalog')
Copy-Item -LiteralPath $q3mIni -Destination (Join-Path $q3mBackup 'InfinityEngine-Enhancer.ini')
$q3mState=[ordered]@{schema='bg2-q3m-monster-catalog-install-v1';status='installing';game_root=$q3mGame
    source_manifest=$q3mManifest;source_manifest_sha256=$q3mPointer.manifest_sha256;catalog_sha256=$q3mPointer.catalog_sha256
    runtime_manifest=$q3mRuntimePath;runtime_manifest_sha256=$q3mPack.runtime_manifest_sha256;runtime_dll_sha256=$q3mRuntime.dll.sha256
    baseline=(Join-Path $q3mPhase6 'baseline.json');backup_root=$q3mBackup;runtime_state_root=$q3mRuntimeState
    animations=81;character_animations_preserved=78;paperdolls_preserved=81;new_resources=39
    monster_animation_ids=@('0x7F02','0x7F07','0x7F30');native_frames=1584979;world_filter='Box';world_scope='0x0';UI_sampler='Nearest'
    character_shards_written=0;paperdolls_written=0;shaders_written=0;source_BAM_written=0
    new_shards=@();installed_shards_verified=0;ingame_validated=$false;QA_registry_written=$false;release_written=$false}
Write-JsonAtomic $q3mReceipt $q3mState
$q3mRuntimeInstalled=$false;$q3mPublished=$false;$q3mCopied=[Collections.Generic.List[string]]::new()
try {
    # Runtime owns only its DLL and rollback; the asset transaction never writes the DLL.
    & $q3mRuntimeInstaller -Mode Install -Manifest $q3mPack.runtime_manifest -StateRoot $q3mRuntimeState
    $q3mRuntimeInstalled=$true
    foreach ($q3mShard in $q3mPack.new_shards) {
        if ($q3mShard.registry -notmatch '^iee-assets/creature-sprites/CreatureSprites-XN-([A-F0-9]{64})\.registry$' -or
            $Matches[1] -ne $q3mShard.sha256) { throw 'New shard name/hash differs.' }
        $q3mSource=Resolve-ChildPath $q3mPackRoot $q3mShard.registry -RequireExisting
        $q3mTarget=Resolve-ChildPath $q3mGame $q3mShard.registry
        if ((Get-FileSha256 $q3mSource) -ne $q3mShard.sha256) { throw 'New source shard changed.' }
        if (-not (Test-Path -LiteralPath $q3mTarget)) { Copy-FileAtomic $q3mSource $q3mTarget;$q3mCopied.Add($q3mTarget) }
        if ((Get-Item -LiteralPath $q3mTarget).Length -ne $q3mShard.registry_bytes -or
            (Get-FileSha256 $q3mTarget) -ne $q3mShard.sha256) { throw 'New installed shard differs.' }
        $q3mState.installed_shards_verified++
    }
    Assert-GameClosed
    if ((Get-FileSha256 $q3mCatalog) -ne $q3mBaseline.character_catalog_sha256 -or
        (Get-FileSha256 $q3mIni) -ne $q3mBaseline.live_files[1].sha256.ToUpperInvariant()) { throw 'Catalog/INI baseline changed before publication.' }
    $q3mPublished=$true;Copy-FileAtomic $q3mSourceCatalog $q3mCatalog
    Verify-Q3mInstalled
    $q3mState.status='installed-verified-pending-ingame';$q3mState.new_shards=@($q3mCopied)
    $q3mState.installed_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $q3mReceipt $q3mState
} catch {
    if ($q3mPublished) { Copy-FileAtomic (Join-Path $q3mBackup 'CreatureSprites-XN.catalog') $q3mCatalog;Copy-FileAtomic (Join-Path $q3mBackup 'InfinityEngine-Enhancer.ini') $q3mIni }
    if ($q3mRuntimeInstalled) { & $q3mRuntimeInstaller -Mode Restore -Manifest $q3mPack.runtime_manifest -StateRoot $q3mRuntimeState }
    $q3mState.status='rolled-back';$q3mState.error=$_.Exception.Message;$q3mState.new_shards=@($q3mCopied)
    Write-JsonAtomic $q3mReceipt $q3mState;throw
}
[pscustomobject]@{Status=$q3mState.status;Animations=81;NewShardsVerified=39;Copied=$q3mCopied.Count;IniWritten=$false;Filter='Box'}
