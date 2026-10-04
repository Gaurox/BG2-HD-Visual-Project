$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$production=Read-JsonFile (Join-Path $PSScriptRoot 'production.json')
$verified=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$runtime=Read-JsonFile (Join-Path $PSScriptRoot 'runtime.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$work=Resolve-WorkspaceInput $production.work_dir -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$snapshotPath=Join-Path $PSScriptRoot 'installation-verification.json'
$backupRoot=Join-Path $PSScriptRoot 'work/before'
if ((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $snapshotPath) -or (Test-Path -LiteralPath $backupRoot)) { throw 'Installation already attempted; inspect state.' }
if (-not $verified.passed -or -not $verified.core_passed -or -not $verified.Character_SDF.passed -or
    $verified.Character_SDF.cold_misses -ne 0 -or $verified.Character_SDF.frames -ne 10323 -or
    -not $verified.Ankheg_SDF.passed -or $verified.malformed.Count -ne 3 -or
    ($generation.animation_ids -join ',') -ne '0x6110' -or $production.new_shards.Count -ne 23) { throw 'Incomplete scoped verification.' }
function Assert-Identity([string]$Path,[string]$Expected) {
    if ((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()) { throw "Identity differs: $Path" }
}
$catalogRelative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
$replaced=@('InfinityEngine-Enhancer.dll',$catalogRelative)+@($runtime.shaders | ForEach-Object target)
$preserved=@($baseline.unchanged_assets | Where-Object { $_.relative_path -notin $replaced })
function Assert-Preserved { foreach($item in $preserved) { Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256 } }
Assert-GameClosed
Assert-Preserved
foreach($sealed in @($generation.runtime,$generation.dll,$generation.catalog,$generation.production,$generation.verification,$verified.GPU,$verified.writer)+@($verified.source_provenance)+@($runtime.shaders)) {
    Assert-Identity (Resolve-WorkspaceInput $sealed.path -RequireExisting) $sealed.sha256
}
$parents=@([pscustomobject]@{relative_path='InfinityEngine-Enhancer.dll';sha256=$baseline.dll_sha256},
           [pscustomobject]@{relative_path=$catalogRelative;sha256=$baseline.catalog_sha256})+
         @($baseline.replaced_shaders | ForEach-Object { [pscustomobject]@{relative_path=$_.target;sha256=$_.sha256} })
foreach($item in $parents) {
    $target=Resolve-ChildPath $game $item.relative_path -RequireExisting
    Assert-Identity $target $item.sha256
    Copy-FileAtomic $target (Resolve-ChildPath $backupRoot $item.relative_path)
}
foreach($shard in $production.new_shards) {
    if($shard.version -ne 10 -or $shard.class_profile_id -ne 1 -or $shard.decode_rule_id -ne 1) { throw 'Unexpected leaf contract.' }
    Assert-Identity (Resolve-ChildPath $work ('isolated/'+[IO.Path]::GetFileName($shard.registry)) -RequireExisting) $shard.sha256
}
$receipt=[ordered]@{
    schema='bg2-character-SDF-install-v1';status='installing';game_root=$baseline.game_root
    animation_ids=@('0x6110');body='CHFB1';resources=23;frames=10323;scale=2;registry_version=10
    generation='docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/current-generation.json'
    backup_root='docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/work/before'
    parent_files=$parents;catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256
    shaders=$runtime.shaders;new_shards=$production.new_shards;preserved_files=$preserved
    filter='CatmullRom';ingame_QA=$false;installed_at_utc=$null;failure=$null
}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try {
    foreach($shard in $production.new_shards) {
        $target=Resolve-ChildPath $game $shard.registry
        if(-not (Test-Path -LiteralPath $target)) {
            Copy-FileAtomic (Resolve-ChildPath $work ('isolated/'+[IO.Path]::GetFileName($shard.registry))) $target
        }
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed
    Assert-Preserved
    foreach($item in $parents) { Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256 }
    $published=$true
    Copy-FileAtomic (Resolve-WorkspaceInput $generation.dll.path) (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll')
    foreach($shader in $runtime.shaders) {
        Copy-FileAtomic (Resolve-WorkspaceInput $shader.path) (Resolve-ChildPath $game $shader.target)
        Assert-Identity (Resolve-ChildPath $game $shader.target -RequireExisting) $shader.sha256
    }
    Copy-FileAtomic (Resolve-WorkspaceInput $generation.catalog.path) (Resolve-ChildPath $game $catalogRelative)
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll') $generation.dll.sha256
    Assert-Identity (Resolve-ChildPath $game $catalogRelative) $generation.catalog.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic $snapshotPath ([ordered]@{
        schema='bg2-character-SDF-installed-verification-v1';role='installation-not-ingame-QA-or-release'
        status=$receipt.status;installed_at_utc=$receipt.installed_at_utc;animation_ids=@('0x6110');body='CHFB1';resources=23;frames=10323
        dll_sha256=$generation.dll.sha256;catalog_sha256=$generation.catalog.sha256;shaders=$runtime.shaders
        new_leaves_sha256_verified=23;preserved_files_sha256_verified=$preserved.Count
        directory_entries_outside_6110_CHFB1_unchanged=$production.inherited_directory_entries_unchanged
        armour_equipment_UI_other_consumers_unchanged=$true;INI_byte_identical=$true
        verification=$generation.verification;installation_receipt_sha256=(Get-FileSha256 $receiptPath);ingame_QA=$false;release=$false
    })
    Write-Output 'Installed Character SDF trial: 0x6110 CHFB1 body, 23 resources / 10323 frames; ingame QA pending.'
} catch {
    $failure=$_
    if($published) {
        Assert-GameClosed
        foreach($item in $parents) {
            Copy-FileAtomic (Resolve-ChildPath $backupRoot $item.relative_path -RequireExisting) (Resolve-ChildPath $game $item.relative_path)
            Assert-Identity (Resolve-ChildPath $game $item.relative_path) $item.sha256
        }
    }
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure
    Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
