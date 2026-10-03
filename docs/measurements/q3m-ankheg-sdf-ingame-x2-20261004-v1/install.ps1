$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verified=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$snapshotPath=Join-Path $PSScriptRoot 'installation-verification.json'
$backupRoot=Join-Path $PSScriptRoot 'work/before'
if ((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $snapshotPath) -or (Test-Path -LiteralPath $backupRoot)) { throw 'Installation already attempted; inspect state before retry.' }
if ($generation.family -ne 'monster_ankheg' -or ($generation.animation_ids -join ',') -ne '0x3000' -or
    $generation.resources -ne 12 -or $generation.frames -ne 516 -or $generation.scale -ne 2 -or
    $generation.registry_version -ne 9 -or $pack.new_shards.Count -ne 12) { throw 'Unexpected SDF scope.' }
if (-not $verified.V9_SDF.passed -or -not $verified.V7_original_unchanged.passed -or
    -not $verified.V7_flying_unchanged.passed -or -not $verified.core_native_suite_passed -or
    $verified.native_malformed_catalogs.Count -ne 2) { throw 'Native verification incomplete.' }
function Assert-Identity([string]$Path,[string]$Expected) {
    if ((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()) { throw "Identity differs: $Path" }
}
function Assert-Preserved {
    Assert-Identity (Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting) $baseline.executable_sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting) $baseline.ini_sha256
    foreach ($item in $baseline.unchanged_assets) { Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256 }
    $settings=Get-Content -LiteralPath (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini') -Raw
    if ((Get-IniValue $settings 'Shaders' 'CreatureSpriteFilter') -ne 'CatmullRom' -or
        (Get-IniValue $settings 'Shaders' 'CreatureSpriteFilterAnimation') -ne '0x0') { throw 'Comparison filter changed.' }
}
if (-not (Read-JsonFile (Join-Path $PSScriptRoot 'composition-verification.json')).passed) { throw 'Native layering incomplete.' }
Assert-GameClosed
Assert-Preserved
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$dllTarget=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
Assert-Identity $dllTarget $baseline.dll_sha256
$runtime=Read-JsonFile (Resolve-WorkspaceInput $generation.runtime.path -RequireExisting)
foreach ($shader in $baseline.replaced_shaders) { Assert-Identity (Resolve-ChildPath $game $shader.relative_path -RequireExisting) $shader.sha256 }
foreach ($shader in $runtime.shaders) { Assert-Identity (Resolve-WorkspaceInput $shader.path -RequireExisting) $shader.sha256 }
foreach ($sealed in @($generation.production,$generation.runtime,$generation.dll,$generation.catalog,$generation.host_verification,$verified.source,$verified.SDF_encoder,$verified.leaf_writer,$generation.composition_verification,$verified.GPU)) {
    Assert-Identity (Resolve-WorkspaceInput $sealed.path -RequireExisting) $sealed.sha256
}
foreach ($shard in $pack.new_shards) {
    if ($shard.version -ne 9 -or [IO.Path]::GetFileName([string]$shard.registry) -ne "CreatureSprites-XN-$($shard.sha256).registry") { throw 'Unexpected contour leaf.' }
    $source=Resolve-ChildPath $packRoot $shard.registry -RequireExisting
    Assert-Identity $source $shard.sha256
    if ((Get-Item -LiteralPath $source).Length -ne $shard.registry_bytes) { throw 'Contour leaf length differs.' }
    $target=Resolve-ChildPath $game $shard.registry
    if (Test-Path -LiteralPath $target) { Assert-Identity $target $shard.sha256 }
}
$catalogBackup=Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog'
$dllBackup=Resolve-ChildPath $backupRoot 'InfinityEngine-Enhancer.dll'
Copy-FileAtomic $catalogTarget $catalogBackup
Copy-FileAtomic $dllTarget $dllBackup
Assert-Identity $catalogBackup $baseline.parent_catalog_sha256
Assert-Identity $dllBackup $baseline.dll_sha256
foreach ($shader in $baseline.replaced_shaders) {
    $target=Resolve-ChildPath $game $shader.relative_path -RequireExisting
    $backup=Resolve-ChildPath $backupRoot $shader.relative_path
    Copy-FileAtomic $target $backup
    Assert-Identity $backup $shader.sha256
}
$receipt=[ordered]@{
 schema='bg2-ankheg-sdf-install-v1'; status='installing'; game_root=$baseline.game_root; family='monster_ankheg'
 animation_ids=@('0x3000'); scale=2; resources=12; frames=516; registry_version=9; world_filter='CatmullRom'
 generation='docs/measurements/q3m-ankheg-sdf-ingame-x2-20261004-v1/current-generation.json'
 backup_root='docs/measurements/q3m-ankheg-sdf-ingame-x2-20261004-v1/work/before'
 catalog_relative=$baseline.catalog_relative; catalog_sha256=$generation.catalog.sha256; parent_catalog_sha256=$baseline.parent_catalog_sha256
 dll_sha256=$generation.dll.sha256; parent_dll_sha256=$baseline.dll_sha256; ini_sha256=$baseline.ini_sha256
 shaders=@($runtime.shaders); parent_shaders=@($baseline.replaced_shaders)
 new_shards=@($pack.new_shards); inherited_animations=87; active_animations=88; active_resources=4572; active_frames=1586172
 ingame_QA=$false; installed_at_utc=$null
}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try {
    foreach ($shard in $pack.new_shards) {
        $target=Resolve-ChildPath $game $shard.registry
        if (-not (Test-Path -LiteralPath $target)) { Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry) $target }
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed
    Assert-Preserved
    Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
    Assert-Identity $dllTarget $baseline.dll_sha256
    foreach ($shader in $baseline.replaced_shaders) { Assert-Identity (Resolve-ChildPath $game $shader.relative_path -RequireExisting) $shader.sha256 }
    $published=$true
    Copy-FileAtomic (Resolve-WorkspaceInput $generation.dll.path -RequireExisting) $dllTarget
    foreach ($shader in $runtime.shaders) {
        Copy-FileAtomic (Resolve-WorkspaceInput $shader.path -RequireExisting) (Resolve-ChildPath $game $shader.target)
        Assert-Identity (Resolve-ChildPath $game $shader.target -RequireExisting) $shader.sha256
    }
    Copy-FileAtomic (Resolve-WorkspaceInput $generation.catalog.path -RequireExisting) $catalogTarget
    Assert-Identity $dllTarget $generation.dll.sha256
    Assert-Identity $catalogTarget $generation.catalog.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic $snapshotPath ([ordered]@{
        schema='bg2-ankheg-sdf-installed-verification-v1';role='installation-not-ingame-QA-or-release';verified_at_utc=[DateTime]::UtcNow.ToString('o')
        family='monster_ankheg';resources=12;frames=516;registry_version=9;scale=2;world_filter='CatmullRom'
        contour_recipe=$generation.mask_recipe;new_leaf_sha256_verified=12;inherited_animations_unchanged=87
        catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;ini_byte_identical=$true
        unchanged_assets_sha256_verified=$baseline.unchanged_assets.Count;backup_sha256_verified=$true
        native_SDF=$verified.V9_SDF;native_original=$verified.V7_original_unchanged;native_flying=$verified.V7_flying_unchanged
        installation_receipt_sha256=(Get-FileSha256 $receiptPath);ingame_QA=$false;release=$false
    })
    Write-Output 'Installed Ankheg adaptive SDF: complete 12 BAM / 516 frames, Q3m colours retained, CatmullRom active.'
} catch {
    $failure=$_
    if ($published) {
        Assert-GameClosed
        Copy-FileAtomic $catalogBackup $catalogTarget
        Copy-FileAtomic $dllBackup $dllTarget
        foreach ($shader in $baseline.replaced_shaders) {
            Copy-FileAtomic (Resolve-ChildPath $backupRoot $shader.relative_path -RequireExisting) (Resolve-ChildPath $game $shader.relative_path)
            Assert-Identity (Resolve-ChildPath $game $shader.relative_path -RequireExisting) $shader.sha256
        }
        Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
        Assert-Identity $dllTarget $baseline.dll_sha256
    }
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure
    Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
