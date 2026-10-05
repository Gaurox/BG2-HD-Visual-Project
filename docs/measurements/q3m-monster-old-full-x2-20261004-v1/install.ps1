$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$creatures=Read-JsonFile (Join-Path $PSScriptRoot 'creatures.json')
$selection=Read-JsonFile (Join-Path $PSScriptRoot 'selection.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $backup)){throw 'Fresh installation attempt required.'}
if($generation.family -ne 'monster_old' -or $generation.scale -ne 2 -or $generation.SDF -or $generation.animation_ids.Count -ne 46 -or $generation.resources -ne 217 -or $generation.logical_resource_bindings -ne 218 -or $generation.bound_frames -ne 17754 -or $creatures.fixtures.Count -ne 46 -or ($generation.animation_ids -join ',') -ne ($selection.witnesses.animation_id -join ',')){throw 'Scope mismatch.'}
if(-not $verification.passed -or $verification.frames -ne 17754 -or -not $verification.native_world.combined.passed){throw 'Verification failed.'}
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{
    foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
Assert-GameClosed;Preserved;Check $catalogTarget $baseline.parent_catalog_sha256;Check $catalogSource $generation.catalog.sha256
foreach($s in $pack.new_shards){Check (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $s.sha256}
foreach($f in $creatures.fixtures){Check (Resolve-WorkspaceInput $f.path -RequireExisting) $f.sha256;if(Test-Path -LiteralPath (Resolve-ChildPath $game $f.target)){throw "Fixture already exists: $($f.target)"}}
Copy-FileAtomic $catalogTarget $backup
$receipt=[ordered]@{schema='bg2-monster-old-Q3m-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$false;catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;dll_sha256=$baseline.dll_sha256;DLL_unchanged=$true;new_shards=$pack.new_shards;fixtures=$creatures.fixtures;preserved_files=$baseline.preserved;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt;$published=$false;$newCopies=0;$createdFixtures=[System.Collections.Generic.List[object]]::new()
try{
    foreach($s in $pack.new_shards){$target=Resolve-ChildPath $game $s.registry;if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $target;$newCopies++};Check $target $s.sha256}
    foreach($f in $creatures.fixtures){Assert-GameClosed;$target=Resolve-ChildPath $game $f.target;if(Test-Path -LiteralPath $target){throw "Fixture appeared: $($f.target)"};$createdFixtures.Add($f);Copy-FileAtomic (Resolve-WorkspaceInput $f.path -RequireExisting) $target;Check $target $f.sha256}
    Assert-GameClosed;Preserved;Check $catalogTarget $baseline.parent_catalog_sha256
    $published=$true;Copy-FileAtomic $catalogSource $catalogTarget
    Check $catalogTarget $generation.catalog.sha256;Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o');$receipt.new_files_copied=$newCopies;Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;animation_ids=$generation.animation_ids;catalog_sha256=$generation.catalog.sha256;dll_sha256=$baseline.dll_sha256;DLL_unchanged=$true;leaf_sha256_verified=$pack.new_shards.Count;new_files_copied=$newCopies;fixtures_sha256_verified=$creatures.fixtures.Count;unchanged_files_sha256_verified=$baseline.preserved.Count;native_world=$verification.native_world.combined;SDF=$false;ingame_QA=$false;release=$false})
    Write-Output 'Installed complete MonsterOld; 46 IDs, Q3m enhanced x2, no SDF; acquired DLL/shaders/INI unchanged.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backup $catalogTarget;Check $catalogTarget $baseline.parent_catalog_sha256}
    foreach($f in $createdFixtures){$target=Resolve-ChildPath $game $f.target;if(Test-Path -LiteralPath $target){Check $target $f.sha256;Remove-Item -LiteralPath $target}}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt;throw $failure
}
