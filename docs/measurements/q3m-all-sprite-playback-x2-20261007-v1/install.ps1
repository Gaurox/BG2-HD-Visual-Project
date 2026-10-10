[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$gen=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'runtime-verification.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$source=Resolve-WorkspaceInput $gen.dll.path -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{
    $i=0
    foreach($r in $baseline.preserved){
        Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256
        $i++;if(($i % 2500) -eq 0){Write-Output "Preserved SHA checks: $i/$($baseline.preserved.Count)"}
    }
}
if((Test-Path -LiteralPath $backup) -or (Test-Path -LiteralPath $receiptPath)){throw 'Fresh installation attempt required.'}
if(-not $verification.passed -or -not $verification.all_playback.observed_6110_fixed -or
    $verification.all_playback.animation_ids -ne 331 -or $verification.all_playback.missing_or_wrong_frames -ne 0 -or
    $gen.animation_ids.Count -ne 331 -or $gen.production_changed -or $gen.sprites_recalculated -ne 0){throw 'Unexpected scope or failed verification.'}
Assert-GameClosed;Check $target $baseline.parent_dll_sha256;Check $source $gen.dll.sha256;Preserved
if($DryRun){Write-Output 'Ready:331 IDs;DLL only;catalog/sprites unchanged.';return}
Copy-FileAtomic $target $backup;Check $backup $baseline.parent_dll_sha256
$receipt=[ordered]@{schema='bg2-common-sprite-runtime-install-v1';status='installing';game_root=$baseline.game_root;
    generation_reference='docs/measurements/q3m-all-sprite-playback-x2-20261007-v1/current-generation.json';
    animation_ids=$gen.animation_ids;parent_dll_sha256=$baseline.parent_dll_sha256;dll_sha256=$gen.dll.sha256;
    catalog_sha256=$gen.catalog_sha256;changed_files=@('InfinityEngine-Enhancer.dll');
    preserved_files_sha256_verified=$baseline.preserved.Count;sprites_recalculated=0;runtime_changed=$true;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try{
    Assert-GameClosed;Check $target $baseline.parent_dll_sha256
    $published=$true;Copy-FileAtomic $source $target;Check $target $gen.dll.sha256;Preserved
    $receipt.status='installed-common-playback-corrected-pending-ingame-confirmation';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt;Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') $receipt
    Write-Output 'Installed common sprite playback:331 IDs;DLL only;all14330 leaves preserved;ingame confirmation pending.'
}catch{
    $failure=$_;Assert-GameClosed
    if($published){Copy-FileAtomic $backup $target;Check $target $baseline.parent_dll_sha256}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
