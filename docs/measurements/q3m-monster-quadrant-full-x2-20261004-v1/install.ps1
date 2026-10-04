$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$creatures=Read-JsonFile (Join-Path $PSScriptRoot 'creatures.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$dllSource=Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$dllTarget=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$backupCatalog=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
$backupDll=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $backupCatalog)){throw 'Installation already attempted.'}
if($generation.scale -ne 2 -or $generation.SDF -or ($generation.animation_ids -join ',') -ne '0x1000,0x1003,0x1004,0x1100,0x1102,0x1103,0x1104' -or $generation.resources -ne 132){throw 'Unexpected Quadrant scope.'}
if(-not $verification.passed -or -not $verification.native_composite.passed -or $verification.native_composite.missing_layers -ne 0){throw 'Verification failed.'}
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Assert-Preserved{
    foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
Assert-GameClosed;Assert-Preserved
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256;Assert-Identity $dllTarget $baseline.dll_sha256
Assert-Identity $catalogSource $generation.catalog.sha256;Assert-Identity $dllSource $generation.dll.sha256
foreach($shard in $pack.new_shards){Assert-Identity (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $shard.sha256}
foreach($fixture in $creatures.fixtures){
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $fixture.target)){throw "Fixture target already exists: $($fixture.target)"}
    Assert-Identity (Resolve-WorkspaceInput $fixture.path -RequireExisting) $fixture.sha256
}
Copy-FileAtomic $catalogTarget $backupCatalog;Copy-FileAtomic $dllTarget $backupDll
$receipt=[ordered]@{schema='bg2-quadrant-Q3m-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$false;catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;parent_dll_sha256=$baseline.dll_sha256;new_shards=$pack.new_shards;fixtures=$creatures.fixtures;preserved_files=$baseline.preserved;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try{
    foreach($shard in $pack.new_shards){
        $target=Resolve-ChildPath $game $shard.registry
        if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target}
        Assert-Identity $target $shard.sha256
    }
    foreach($fixture in $creatures.fixtures){Copy-FileAtomic (Resolve-WorkspaceInput $fixture.path -RequireExisting) (Resolve-ChildPath $game $fixture.target);Assert-Identity (Resolve-ChildPath $game $fixture.target -RequireExisting) $fixture.sha256}
    Assert-GameClosed;Assert-Preserved
    Assert-Identity $catalogTarget $baseline.parent_catalog_sha256;Assert-Identity $dllTarget $baseline.dll_sha256
    $published=$true;Copy-FileAtomic $dllSource $dllTarget;Copy-FileAtomic $catalogSource $catalogTarget
    Assert-Identity $catalogTarget $generation.catalog.sha256;Assert-Identity $dllTarget $generation.dll.sha256;Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;animation_ids=$generation.animation_ids;scale=2;SDF=$false;catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;new_leaf_sha256_verified=$pack.new_shards.Count;fixtures_sha256_verified=$creatures.fixtures.Count;unchanged_files_sha256_verified=$baseline.preserved.Count;native_composite=$verification.native_composite;catalog_proof=$pack.proof;ingame_QA=$false;release=$false})
    Write-Output 'Installed complete native Monster_quadrant Q3m V7 x2 enhanced palettes, no SDF; seven IDs, four parts, native empty parts preserved.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backupDll $dllTarget;Copy-FileAtomic $backupCatalog $catalogTarget;Assert-Identity $catalogTarget $baseline.parent_catalog_sha256;Assert-Identity $dllTarget $baseline.dll_sha256}
    foreach($fixture in $creatures.fixtures){$target=Resolve-ChildPath $game $fixture.target;if(Test-Path -LiteralPath $target){Assert-Identity $target $fixture.sha256;Remove-Item -LiteralPath $target}}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt;throw $failure
}
