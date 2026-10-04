$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verified=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$snapshotPath=Join-Path $PSScriptRoot 'installation-verification.json'
$backupRoot=Join-Path $PSScriptRoot 'work/before'
if ((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $snapshotPath) -or (Test-Path -LiteralPath $backupRoot)) {
    throw 'Installation already attempted; inspect state before retry.'
}
if (-not $verified.passed -or $verified.core.exit_code -ne 0 -or
    $verified.cold_lookup.cold_misses -ne 0 -or $verified.cold_lookup.warm_hits -ne 12 -or
    -not $verified.SDF.passed -or $verified.SDF.composite_cases -ne 48 -or
    $generation.family -ne 'monster_ankheg' -or ($generation.animation_ids -join ',') -ne '0x3000' -or
    $generation.resources -ne 12 -or $generation.frames -ne 516 -or
    $generation.metadata_wait.owner -ne 9 -or $generation.metadata_wait.maximum_wait_ms -ne 5000) {
    throw 'Unexpected runtime scope or incomplete native verification.'
}
function Assert-Identity([string]$Path,[string]$Expected) {
    if ((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()) { throw "Identity differs: $Path" }
}
function Assert-Preserved {
    foreach ($item in $baseline.unchanged_assets) {
        Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256
    }
}
Assert-GameClosed
Assert-Preserved
foreach ($sealed in @($generation.runtime,$generation.dll,$generation.catalog,$generation.production,
                      $generation.host_verification,$generation.parent_generation,
                      $verified.original_GPU_verification,$verified.original_SDF_verification) + @($verified.source_provenance)) {
    Assert-Identity (Resolve-WorkspaceInput $sealed.path -RequireExisting) $sealed.sha256
}
$dllSource=Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$dllTarget=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$dllBackup=Resolve-ChildPath $backupRoot 'InfinityEngine-Enhancer.dll'
Assert-Identity $dllTarget $baseline.dll_sha256
Copy-FileAtomic $dllTarget $dllBackup
Assert-Identity $dllBackup $baseline.dll_sha256
$receipt=[ordered]@{
    schema='bg2-ankheg-sdf-runtime-patch-install-v1';status='installing';game_root=$baseline.game_root
    family='monster_ankheg';animation_ids=@('0x3000');resources=12;frames=516;scale=2;registry_version=9
    generation='docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1/current-generation.json'
    backup_root='docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1/work/before'
    replaced_files=@('InfinityEngine-Enhancer.dll');dll_sha256=$generation.dll.sha256;parent_dll_sha256=$baseline.dll_sha256
    preserved_files=$baseline.unchanged_assets;metadata_wait=$generation.metadata_wait
    world_filter='CatmullRom';ingame_QA=$false;installed_at_utc=$null;failure=$null
}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try {
    Assert-GameClosed
    Assert-Preserved
    Assert-Identity $dllTarget $baseline.dll_sha256
    $published=$true
    Copy-FileAtomic $dllSource $dllTarget
    Assert-Identity $dllTarget $generation.dll.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic $snapshotPath ([ordered]@{
        schema='bg2-ankheg-sdf-runtime-patch-installed-verification-v1';role='installation-not-ingame-QA-or-release'
        status=$receipt.status;installed_at_utc=$receipt.installed_at_utc;family='monster_ankheg';resources=12;frames=516
        replaced_files=$receipt.replaced_files;dll_sha256=$generation.dll.sha256;parent_dll_sha256=$baseline.dll_sha256
        catalog_sha256=$generation.catalog.sha256;unchanged_files_sha256_verified=$baseline.unchanged_assets.Count
        shaders_catalog_INI_sprites_unchanged=$true;backup_sha256_verified=$true
        verification=$generation.host_verification;generation=$receipt.generation;metadata_wait=$generation.metadata_wait
        installation_receipt_sha256=(Get-FileSha256 $receiptPath);ingame_QA=$false;release=$false
    })
    Write-Output "Installed metadata-wait patch: 12 Ankheg resources; only DLL replaced; $($baseline.unchanged_assets.Count) preserved files verified."
} catch {
    $failure=$_
    if ($published) {
        Assert-GameClosed
        Copy-FileAtomic $dllBackup $dllTarget
        Assert-Identity $dllTarget $baseline.dll_sha256
    }
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure
    Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
