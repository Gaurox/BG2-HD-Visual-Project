$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$source=Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$backup=Join-Path $PSScriptRoot 'work/before/InfinityEngine-Enhancer.dll'
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Assert-Preserved{foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}}
if((Test-Path -LiteralPath $backup) -or (Test-Path -LiteralPath $receiptPath)){throw 'Already attempted; inspect receipt first.'}
if(-not $verification.passed -or $verification.fixed.cold_native_fallback_groups -ne 0 -or $generation.scale -ne 2 -or -not $generation.assets_unchanged){throw 'Unexpected correction scope or failed verification.'}
Assert-GameClosed;Assert-Preserved
Assert-Identity $target $baseline.dll_sha256;Assert-Identity $source $generation.dll.sha256
Copy-FileAtomic $target $backup;Assert-Identity $backup $baseline.dll_sha256
$receipt=[ordered]@{schema='bg2-multi-new-runtime-only-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$false;dll_sha256=$generation.dll.sha256;parent_dll_sha256=$baseline.dll_sha256;catalog_sha256=$generation.catalog.sha256;inherited_asset_installation=$baseline.inherited_asset_installation;only_replaced='InfinityEngine-Enhancer.dll';preserved_files=$baseline.preserved;ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
try{
    Assert-GameClosed;Assert-Preserved;Assert-Identity $target $baseline.dll_sha256
    Copy-FileAtomic $source $target
    Assert-Identity $target $generation.dll.sha256;Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;dll_sha256=$generation.dll.sha256;catalog_sha256=$generation.catalog.sha256;scale=2;assets_unchanged=$true;only_replaced=$receipt.only_replaced;preserved_files_verified=$baseline.preserved.Count;native_regression=$verification;ingame_QA=$false;release=$false})
    Write-Output 'Installed runtime-only MultiNew stability correction, Q3m x2 unchanged; ingame QA pending.'
}catch{
    $failure=$_;Assert-GameClosed
    Copy-FileAtomic $backup $target;Assert-Identity $target $baseline.dll_sha256
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
