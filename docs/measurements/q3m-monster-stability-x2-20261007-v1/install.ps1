[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'runtime-verification.json')
$palette=Read-JsonFile (Join-Path $PSScriptRoot 'short-palette-dependencies.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$source=Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}}
if((Test-Path -LiteralPath $backup) -or (Test-Path -LiteralPath $receiptPath)){throw 'Fresh installation attempt required.'}
if(-not $verification.passed -or -not $palette.passed -or -not $verification.icewind_regression.passed -or $verification.monster.resources -ne 1040 -or $verification.monster.missing_or_wrong_frames -ne 0 -or $generation.animation_ids.Count -ne 77 -or $generation.family -ne 'monster'){throw 'Unexpected scope or failed verification.'}
Assert-GameClosed;Check $target $baseline.parent_dll_sha256;Check $source $generation.dll.sha256;Preserved
if($DryRun){Write-Output "Ready: DLL only, 77 Monster IDs; $($baseline.preserved.Count) preserved files verified.";return}
Copy-FileAtomic $target $backup;Check $backup $baseline.parent_dll_sha256
$receipt=[ordered]@{schema='bg2-monster-runtime-successor-install-v1';status='installing';game_root=$baseline.game_root;
    generation_reference='docs/measurements/q3m-monster-stability-x2-20261007-v1/current-generation.json';animation_ids=$generation.animation_ids;
    parent_dll_sha256=$baseline.parent_dll_sha256;dll_sha256=$generation.dll.sha256;catalog_sha256=$generation.catalog.sha256;
    changed_files=@('InfinityEngine-Enhancer.dll');preserved_files_sha256_verified=$baseline.preserved.Count;
    prior_partial_QA=$generation.partial_visual_QA;runtime_changed=$true;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try{
    Assert-GameClosed;Check $target $baseline.parent_dll_sha256
    $published=$true;Copy-FileAtomic $source $target;Check $target $generation.dll.sha256;Preserved
    $receipt.status='installed-corrected-runtime-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') $receipt
    Write-Output 'Installed corrected Monster runtime; DLL only; assets/catalog/77 CRE preserved; ingame confirmation pending.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backup $target;Check $target $baseline.parent_dll_sha256}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
