$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$dllSource=Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$dllTarget=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$snapshotPath=Join-Path $PSScriptRoot 'installation-verification.json'
$backupRoot=Join-Path $PSScriptRoot 'work/before'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $snapshotPath) -or (Test-Path -LiteralPath $backupRoot)){throw 'Installation already attempted; inspect state.'}
if($generation.family -ne 'monster_large16' -or $generation.scale -ne 2 -or $generation.registry_version -ne 9 -or -not $generation.SDF -or
   $generation.resources -ne 18 -or $generation.frames -ne 1688 -or $pack.new_shards.Count -ne 18 -or
   ($generation.animation_ids -join ',') -ne '0xA000,0xA100,0xA200' -or -not $verification.passed -or
   $verification.cold_resolution.Large16_cold_HD -ne 18 -or $verification.cold_resolution.cold_misses -ne 0 -or
   -not $verification.Character_V10_not_in_build){throw 'Unexpected or unverified scope.'}
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
$preserved=@($baseline.preserved | Where-Object relative_path -ne 'InfinityEngine-Enhancer.dll')
$parentPack=Read-JsonFile (Resolve-WorkspaceInput 'sprite/.work/q3m-monster-large16-full-x2-20261004-v1/combined/pack.json' -RequireExisting)
$preserved+=@($parentPack.new_shards | ForEach-Object {[pscustomobject]@{relative_path=$_.registry;sha256=$_.sha256}})
if($preserved.Count -ne 119){throw 'Unexpected preserved scope.'}
function Assert-Preserved{
    foreach($item in $preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
    foreach($item in $baseline.inherited_QA){Assert-Identity (Resolve-WorkspaceInput $item.path -RequireExisting) $item.sha256}
    foreach($name in @('A000.INI','A100.INI','A200.INI','MWYV_WS.BMP')+@($baseline.source_BAMs | ForEach-Object {"$_.BAM"})){
        if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}
    }
}
Assert-GameClosed
Assert-Preserved
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
Assert-Identity $dllTarget $baseline.dll_sha256
Assert-Identity $catalogSource $generation.catalog.sha256
Assert-Identity $dllSource $generation.dll.sha256
foreach($item in @($generation.production,$generation.runtime,$generation.verification)){Assert-Identity (Resolve-WorkspaceInput $item.path -RequireExisting) $item.sha256}
foreach($shard in $pack.new_shards){
    if([IO.Path]::GetFileName([string]$shard.registry) -ne "CreatureSprites-XN-$($shard.sha256).registry"){throw 'Unexpected leaf name.'}
    Assert-Identity (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $shard.sha256
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $shard.registry)){Assert-Identity (Resolve-ChildPath $game $shard.registry) $shard.sha256}
}
$catalogBackup=Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog'
$dllBackup=Resolve-ChildPath $backupRoot 'InfinityEngine-Enhancer.dll'
Copy-FileAtomic $catalogTarget $catalogBackup
Copy-FileAtomic $dllTarget $dllBackup
Assert-Identity $catalogBackup $baseline.parent_catalog_sha256
Assert-Identity $dllBackup $baseline.dll_sha256
$receipt=[ordered]@{
    schema='bg2-Large16-SDF-install-v1';status='installing';game_root=$baseline.game_root
    family='monster_large16';animation_ids=$generation.animation_ids;scale=2;resources=18;frames=1688;SDF=$true
    generation='docs/measurements/q3m-large16-sdf-ingame-x2-20261004-v1/current-generation.json'
    backup_root='docs/measurements/q3m-large16-sdf-ingame-x2-20261004-v1/work/before'
    catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256
    dll_sha256=$generation.dll.sha256;parent_dll_sha256=$baseline.dll_sha256;ini_sha256=$baseline.ini_sha256
    preserved_files=$preserved;new_shards=$pack.new_shards;all_native_routes_unchanged=50273
    ingame_QA=$false;release=$false;installed_at_utc=$null
}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try{
    foreach($shard in $pack.new_shards){
        $target=Resolve-ChildPath $game $shard.registry
        if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target}
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed
    Assert-Preserved
    Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
    Assert-Identity $dllTarget $baseline.dll_sha256
    $published=$true
    Copy-FileAtomic $dllSource $dllTarget
    Copy-FileAtomic $catalogSource $catalogTarget
    Assert-Identity $catalogTarget $generation.catalog.sha256
    Assert-Identity $dllTarget $generation.dll.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic $snapshotPath ([ordered]@{
        schema='bg2-Large16-SDF-installed-verification-v1';role='installation-not-ingame-QA-or-release';status=$receipt.status
        installed_at_utc=$receipt.installed_at_utc;family='monster_large16';animation_ids=$generation.animation_ids
        resources=18;frames=1688;auxiliary_INV_V7_unchanged=2;scale=2;registry_version=9;SDF=$true
        all_native_routes_unchanged=50273;active_animations=91;active_resources=4592;active_frames=1587864
        new_leaf_sha256_verified=18;unchanged_files_sha256_verified=$preserved.Count
        ini_shaders_executable_UI_byte_identical=$true;Ankheg_SDF_and_wait_preserved=$true;Character_SDF_not_enabled=$true
        original_V7_colours_acquired=$true;new_neural_inference=0;new_Q3m_encoding=0
        catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256
        cold_resolution=$verification.cold_resolution;backup_sha256_verified=$true
        installation_receipt_sha256=(Get-FileSha256 $receiptPath);ingame_QA=$false;release=$false
    })
    Write-Output 'Installed Large16 SDF V9 x2: all three world variants; stable-derived DLL with scoped metadata wait; 119 files unchanged.'
}catch{
    $failure=$_
    if($published){
        Assert-GameClosed
        Copy-FileAtomic $dllBackup $dllTarget
        Copy-FileAtomic $catalogBackup $catalogTarget
        Assert-Identity $dllTarget $baseline.dll_sha256
        Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
    }
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
