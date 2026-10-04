$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$creatures=Read-JsonFile (Join-Path $PSScriptRoot 'creatures.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $backup)){throw 'Installation already attempted.'}
if($generation.family -ne 'ambient_static' -or $generation.scale -ne 2 -or $generation.registry_version -ne 7 -or $generation.SDF -or $generation.resources -ne 2 -or $generation.frames -ne 44 -or $generation.animation_ids.Count -ne 1){throw 'Unexpected scope.'}
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Assert-Preserved{
    foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
Assert-GameClosed
Assert-Preserved
Assert-Identity (Resolve-WorkspaceInput $baseline.accepted_QA.path -RequireExisting) $baseline.accepted_QA.sha256
Assert-Identity $catalogSource $generation.catalog.sha256
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
$native=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'native-combined.log') | Where-Object {$_.StartsWith('{')} | Select-Object -Last 1 | ConvertFrom-Json
if(-not $native.passed -or $native.resources -ne 2 -or $native.frames -ne 44){throw 'Native binding check incomplete.'}
foreach($item in $creatures.fixtures){
    Assert-Identity (Resolve-WorkspaceInput $item.path -RequireExisting) $item.sha256
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $item.target)){throw 'Test CRE already exists.'}
}
foreach($shard in $pack.new_shards){
    Assert-Identity (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $shard.sha256
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $shard.registry)){Assert-Identity (Resolve-ChildPath $game $shard.registry) $shard.sha256}
}
Copy-FileAtomic $catalogTarget $backup
Assert-Identity $backup $baseline.parent_catalog_sha256
$receipt=[ordered]@{schema='bg2-horse-eye-install-v1';status='installing';game_root=$baseline.game_root;family=$generation.family;animation_ids=$generation.animation_ids;resources=2;frames=44;scale=2;SDF=$false;catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;preserved_files=$baseline.preserved;new_shards=$pack.new_shards;fixtures=$creatures.fixtures;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$published=$false;$created=@()
try{
    foreach($shard in $pack.new_shards){
        $target=Resolve-ChildPath $game $shard.registry
        if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target}
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed
    Assert-Preserved
    foreach($item in $creatures.fixtures){
        $target=Resolve-ChildPath $game $item.target
        if(Test-Path -LiteralPath $target){throw 'Test CRE target appeared.'}
        Copy-FileAtomic (Resolve-WorkspaceInput $item.path -RequireExisting) $target
        $created+=,$item
        Assert-Identity $target $item.sha256
    }
    Assert-GameClosed
    Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
    $published=$true
    Copy-FileAtomic $catalogSource $catalogTarget
    Assert-Identity $catalogTarget $generation.catalog.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;family='ambient_static';resources=2;frames=44;scale=2;SDF=$false;catalog_sha256=$generation.catalog.sha256;backup_sha256_verified=$true;new_leaf_sha256_verified=1;unchanged_files_sha256_verified=$baseline.preserved.Count;native_combined_test=$native;catalog_proof=$pack.proof;fixtures=$creatures.fixtures;ingame_QA=$false;release=$false})
    Write-Output 'Installed reviewed horse eye: 1 changed leaf / 5 frames / 134 x2 pixels / Q3m V7 / no SDF.'
}catch{
    $failure=$_
    Assert-GameClosed
    if($published){Copy-FileAtomic $backup $catalogTarget;Assert-Identity $catalogTarget $baseline.parent_catalog_sha256}
    foreach($item in $created){$target=Resolve-ChildPath $game $item.target;Assert-Identity $target $item.sha256;Remove-Item -LiteralPath $target}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
