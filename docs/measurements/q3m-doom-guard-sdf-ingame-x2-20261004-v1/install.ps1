$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$gpu=Read-JsonFile (Join-Path $PSScriptRoot 'gpu-verification.json')
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
if($generation.scale -ne 2 -or -not $generation.SDF -or ($generation.animation_ids -join ',') -ne '0x6405,0x6406' -or $generation.resources -ne 974){throw 'Unexpected scope.'}
if(-not $verification.passed -or -not $gpu.passed -or -not $verification.native_composite.passed -or $verification.native_composite.missing_layers -ne 0){throw 'Verification failed.'}
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Assert-Preserved{
    foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
Assert-GameClosed
Assert-Preserved
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
Assert-Identity $dllTarget $baseline.dll_sha256
Assert-Identity $catalogSource $generation.catalog.sha256
Assert-Identity $dllSource $generation.dll.sha256
foreach($shard in $pack.new_shards){Assert-Identity (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $shard.sha256}
Copy-FileAtomic $catalogTarget $backupCatalog
Copy-FileAtomic $dllTarget $backupDll
$receipt=[ordered]@{schema='bg2-doom-guard-SDF-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$true;catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;parent_dll_sha256=$baseline.dll_sha256;new_shards=$pack.new_shards;preserved_files=$baseline.preserved;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try{
    foreach($shard in $pack.new_shards){
        $target=Resolve-ChildPath $game $shard.registry
        if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target}
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed;Assert-Preserved
    Assert-Identity $catalogTarget $baseline.parent_catalog_sha256;Assert-Identity $dllTarget $baseline.dll_sha256
    $published=$true
    Copy-FileAtomic $dllSource $dllTarget
    Copy-FileAtomic $catalogSource $catalogTarget
    Assert-Identity $catalogTarget $generation.catalog.sha256;Assert-Identity $dllTarget $generation.dll.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o');Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;animation_ids=$generation.animation_ids;scale=2;SDF=$true;catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;new_leaf_sha256_verified=$pack.new_shards.Count;unchanged_files_sha256_verified=$baseline.preserved.Count;native_composite=$verification.native_composite;GPU=$gpu.passed;catalog_proof=$pack.proof;ingame_QA=$false;release=$false})
    Write-Output 'Installed QCOL6405/QCOL6406 Q3m V9 x2 + SDF; native bodies remain transparent.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backupDll $dllTarget;Copy-FileAtomic $backupCatalog $catalogTarget;Assert-Identity $catalogTarget $baseline.parent_catalog_sha256;Assert-Identity $dllTarget $baseline.dll_sha256}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt;throw $failure
}
