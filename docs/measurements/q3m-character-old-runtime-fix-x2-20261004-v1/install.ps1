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
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $backup)){throw 'Installation already attempted.'}
if($generation.family -ne 'character_old' -or $generation.scale -ne 2 -or $generation.SDF -or $generation.animation_ids.Count -ne 7 -or $generation.additional_resources -ne 967){throw 'Unexpected correction scope.'}
if(-not $verification.passed -or $verification.resources -ne 967 -or $verification.frames -ne 44669 -or -not $verification.native_composite.passed -or $verification.native_composite.missing_layers -ne 0){throw 'Native complete composition verification failed.'}
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Assert-Preserved{
    foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
Assert-GameClosed
Assert-Preserved
Assert-Identity $catalogSource $generation.catalog.sha256
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
foreach($shard in $pack.new_shards){Assert-Identity (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $shard.sha256}
Copy-FileAtomic $catalogTarget $backup
Assert-Identity $backup $baseline.parent_catalog_sha256
$receipt=[ordered]@{schema='bg2-character-old-native-dependencies-install-v1';status='installing';game_root=$baseline.game_root;family='character_old';animation_ids=$generation.animation_ids;scale=2;SDF=$false;catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;preserved_files=$baseline.preserved;new_shards=$pack.new_shards;body_resources_unchanged=99;body_frames_unchanged=4725;additional_resources=967;additional_frames=44669;ingame_QA=$false;release=$false}
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
    $published=$true
    Copy-FileAtomic $catalogSource $catalogTarget
    Assert-Identity $catalogTarget $generation.catalog.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;family='character_old';scale=2;SDF=$false;catalog_sha256=$generation.catalog.sha256;backup_sha256_verified=$true;new_leaf_sha256_verified=967;unchanged_files_sha256_verified=$baseline.preserved.Count;native_composite=$verification.native_composite;catalog_proof=$pack.proof;ingame_QA=$false;release=$false})
    Write-Output 'Installed Character_old native dependencies: 7 IDs / 967 additional BAM / 44669 frames / Q3m V7 x2 / no SDF.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backup $catalogTarget;Assert-Identity $catalogTarget $baseline.parent_catalog_sha256}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt;throw $failure
}
