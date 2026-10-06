[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$proof=Read-JsonFile (Join-Path $PSScriptRoot 'catalog-proof.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$targetCatalog=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$sourceCatalog=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$sourceAssets=Split-Path -Parent $sourceCatalog
$backupCatalog=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}}
if((Test-Path -LiteralPath $backupCatalog) -or (Test-Path -LiteralPath $receiptPath)){throw 'Fresh installation attempt required.'}
if(-not $verification.passed -or -not $verification.native_pixels.passed -or -not $verification.native_palette_guards.native_palettes_correct -or
   -not $proof.passed -or $proof.retained_ids -ne 329 -or $proof.changed_bindings.Count -ne 14 -or $generation.runtime_changed -or
   $verification.native_pixels.frames -ne 11774 -or ($generation.correction_animation_ids -join ',') -ne '0x7312,0x7313' -or
   $baseline.candidate_shards.Count -ne 27){throw 'Unexpected scope or failed verification.'}
Assert-GameClosed;Check $targetCatalog $baseline.parent_catalog_sha256;Check $sourceCatalog $generation.catalog.sha256;Preserved
$missing=@()
foreach($s in $baseline.candidate_shards){
    $src=Resolve-ChildPath $sourceAssets ([IO.Path]::GetFileName($s.registry)) -RequireExisting
    $dst=Resolve-ChildPath $game $s.registry;Check $src $s.sha256
    if(Test-Path -LiteralPath $dst){Check $dst $s.sha256}else{$missing+= $s}
}
if($missing.Count -ne 14){throw "Expected fourteen new G2 leaves; found $($missing.Count)."}
if($DryRun){Write-Output "Ready:7312/7313 G2 only;14 new leaves/catalog;329 IDs and $($baseline.preserved.Count) files preserved, DLL unchanged.";return}
Copy-FileAtomic $targetCatalog $backupCatalog;Check $backupCatalog $baseline.parent_catalog_sha256
$receipt=[ordered]@{schema='bg2-monster-G2-native-palette-install-v1';status='installing';game_root=$baseline.game_root;
    generation_reference='docs/measurements/q3m-monster-g2-palettes-x2-20261007-v1/current-generation.json';animation_ids=$generation.animation_ids;
    correction_animation_ids=$generation.correction_animation_ids;parent_catalog_sha256=$baseline.parent_catalog_sha256;
    dll_sha256=$generation.dll.sha256;catalog_sha256=$generation.catalog.sha256;changed_existing_files=$baseline.changed_files;
    created_leaves=@();preserved_files_sha256_verified=$baseline.preserved.Count;retained_ids=329;retained_routes=$proof.retained_routes;
    inherited_QA_decisions=$generation.inherited_QA_decisions;retained_Monster_user_QA_ids=$generation.retained_Monster_user_QA_ids;
    runtime_changed=$false;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$publishing=$false
try{
    foreach($s in $missing){
        Assert-GameClosed;$dst=Resolve-ChildPath $game $s.registry
        if(Test-Path -LiteralPath $dst){throw "Unexpected new target: $dst"}
        $receipt.created_leaves+= [ordered]@{relative_path=$s.registry;sha256=$s.sha256};Write-JsonAtomic $receiptPath $receipt
        Copy-FileAtomic (Resolve-ChildPath $sourceAssets ([IO.Path]::GetFileName($s.registry)) -RequireExisting) $dst;Check $dst $s.sha256
    }
    Assert-GameClosed;Check $targetCatalog $baseline.parent_catalog_sha256;Preserved
    $publishing=$true;Copy-FileAtomic $sourceCatalog $targetCatalog;Check $targetCatalog $generation.catalog.sha256
    Preserved
    foreach($s in $baseline.candidate_shards){Check (Resolve-ChildPath $game $s.registry -RequireExisting) $s.sha256}
    $receipt.status='installed-G2-native-palettes-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt;Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') $receipt
    Write-Output 'Installed G2 fixes7312/7313:14 new leaves/catalog;DLL and329 IDs preserved;two ingame retests pending.'
}catch{
    $failure=$_;Assert-GameClosed
    if($publishing){Copy-FileAtomic $backupCatalog $targetCatalog}
    foreach($r in $receipt.created_leaves){$p=Resolve-ChildPath $game $r.relative_path;if(Test-Path -LiteralPath $p){Check $p $r.sha256;Remove-Item -LiteralPath $p -Force}}
    Check $targetCatalog $baseline.parent_catalog_sha256;Preserved
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
