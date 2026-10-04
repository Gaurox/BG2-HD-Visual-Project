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
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$backup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $backup)){throw 'Fresh installation attempt required.'}
if($generation.scale -ne 2 -or $generation.SDF -or ($generation.animation_ids -join ',') -ne '0x1000,0x1003,0x1004,0x1100,0x1102,0x1103,0x1104' -or $generation.resources -ne 132){throw 'Scope mismatch.'}
if(-not $verification.passed -or -not $verification.outside_band_encoded_pixels_unchanged -or $verification.changed_outside_band -ne 0 -or -not $verification.native_composite.passed -or $verification.native_composite.missing_layers -ne 0){throw 'Verification failed.'}
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{
    foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
Assert-GameClosed;Preserved;Check $catalogTarget $baseline.parent_catalog_sha256;Check $catalogSource $generation.catalog.sha256
foreach($s in $pack.new_shards){Check (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $s.sha256}
foreach($f in $creatures.fixtures){Check (Resolve-ChildPath $game $f.target -RequireExisting) $f.sha256}
Copy-FileAtomic $catalogTarget $backup
$receipt=[ordered]@{schema='bg2-quadrant-seam-Q3m-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$false;catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;dll_sha256=$baseline.dll_sha256;DLL_unchanged=$true;new_shards=$pack.new_shards;fixtures=$creatures.fixtures;fixtures_reused=$true;preserved_files=$baseline.preserved;changed_outside_band=0;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt;$published=$false;$newCopies=0
try{
    foreach($s in $pack.new_shards){$target=Resolve-ChildPath $game $s.registry;if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $target;$newCopies++};Check $target $s.sha256}
    Assert-GameClosed;Preserved;Check $catalogTarget $baseline.parent_catalog_sha256
    $published=$true;Copy-FileAtomic $catalogSource $catalogTarget
    Check $catalogTarget $generation.catalog.sha256;Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o');$receipt.new_files_copied=$newCopies;Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;animation_ids=$generation.animation_ids;catalog_sha256=$generation.catalog.sha256;dll_sha256=$baseline.dll_sha256;DLL_unchanged=$true;leaf_sha256_verified=$pack.new_shards.Count;new_files_copied=$newCopies;fixtures_sha256_verified=$creatures.fixtures.Count;unchanged_files_sha256_verified=$baseline.preserved.Count;changed_outside_band=0;native_composite=$verification.native_composite;SDF=$false;ingame_QA=$false;release=$false})
    Write-Output 'Installed complete Quadrant contextual seam repair; seven IDs, Q3m enhanced x2, no SDF; same DLL/shaders/INI/CLUA fixtures.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backup $catalogTarget;Check $catalogTarget $baseline.parent_catalog_sha256}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt;throw $failure
}
