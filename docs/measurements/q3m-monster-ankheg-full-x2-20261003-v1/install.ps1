$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline = Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation = Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$game = Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot = Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack = Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource = Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$backupRoot = Join-Path $PSScriptRoot 'work/before'
$receiptPath = Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$snapshotPath = Join-Path $PSScriptRoot 'installation-verification.json'
if ((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $backupRoot) -or (Test-Path -LiteralPath $snapshotPath)) {
    throw 'Installation state already exists; inspect it before any retry.'
}
if ($pack.new_shards.Count -ne 12 -or $generation.family -ne 'monster_ankheg' -or
    $generation.resources -ne 12 -or $generation.frames -ne 516 -or $generation.scale -ne 2 -or
    ($generation.animation_ids -join ',') -ne '0x3000') { throw 'Unexpected scope.' }
$selection = Read-JsonFile (Join-Path $PSScriptRoot 'selection.json')
function Assert-Identity([string]$Path, [string]$Expected) {
    if ((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()) { throw "Identity differs: $Path" }
}
function Assert-Preserved {
    Assert-Identity (Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting) $baseline.executable_sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting) $baseline.dll_sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting) $baseline.ini_sha256
    foreach ($item in $baseline.preserved) {
        Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256
    }
    foreach ($item in $baseline.inherited_accepted_leaves) {
        Assert-Identity (Resolve-ChildPath $game $item.registry -RequireExisting) $item.sha256
    }
    Assert-Identity (Resolve-WorkspaceInput $baseline.inherited_flying_qa.path -RequireExisting) $baseline.inherited_flying_qa.sha256
    foreach ($name in @('3000.INI') + @($selection.witnesses[0].refs | ForEach-Object { "$_.BAM" })) {
        if (Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")) { throw "Native source override appeared: $name" }
    }
}
Assert-GameClosed
Assert-Preserved
Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting) $baseline.parent_catalog_sha256
Assert-Identity $catalogSource $generation.catalog.sha256
foreach ($identity in @($generation.production,$generation.runtime)) {
    Assert-Identity (Resolve-WorkspaceInput $identity.path -RequireExisting) $identity.sha256
}
$nativeLog = Resolve-WorkspaceInput 'sprite/.work/q3m-monster-ankheg-full-x2-20261003-v1/native-combined-tests.log' -RequireExisting
$native = Get-Content -LiteralPath $nativeLog | Where-Object { $_.StartsWith('{') } | Select-Object -Last 1 | ConvertFrom-Json
if (-not $native.passed -or $native.resources -ne 12 -or $native.frames -ne 516) { throw 'Native binding test incomplete.' }
foreach ($shard in $pack.new_shards) {
    if ([IO.Path]::GetFileName([string]$shard.registry) -ne "CreatureSprites-XN-$($shard.sha256).registry") { throw 'Unexpected leaf name.' }
    $source = Resolve-ChildPath $packRoot $shard.registry -RequireExisting
    Assert-Identity $source $shard.sha256
    if ((Get-Item -LiteralPath $source).Length -ne $shard.registry_bytes) { throw 'Leaf size differs.' }
    $target = Resolve-ChildPath $game $shard.registry
    if (Test-Path -LiteralPath $target) { Assert-Identity $target $shard.sha256 }
}
$backup = Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog'
Copy-FileAtomic (Resolve-ChildPath $game $baseline.catalog_relative) $backup
Assert-Identity $backup $baseline.parent_catalog_sha256
$receipt = [ordered]@{
    schema='bg2-ankheg-install-v1'; status='installing'; game_root=$baseline.game_root
    family='monster_ankheg'; animation_ids=$generation.animation_ids; scale=2; resources=12; frames=516
    generation='docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1/current-generation.json'
    backup_root='docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1/work/before'
    catalog_relative=$baseline.catalog_relative; catalog_sha256=$generation.catalog.sha256
    parent_catalog_sha256=$baseline.parent_catalog_sha256; dll_sha256=$baseline.dll_sha256; ini_sha256=$baseline.ini_sha256
    new_shards=@($pack.new_shards); inherited_animations=87; active_animations=88
    active_resources=4572; active_frames=1586172; active_routes=50253
    inherited_flying_QA_unchanged=$true; ingame_QA=$false; installed_at_utc=$null
}
Write-JsonAtomic $receiptPath $receipt
$published=$false
try {
    foreach ($shard in $pack.new_shards) {
        $target=Resolve-ChildPath $game $shard.registry
        if (-not (Test-Path -LiteralPath $target)) {
            Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target
        }
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed
    Assert-Preserved
    Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative) $baseline.parent_catalog_sha256
    $published=$true
    Copy-FileAtomic $catalogSource (Resolve-ChildPath $game $baseline.catalog_relative)
    Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative) $generation.catalog.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa'; $receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic $snapshotPath ([ordered]@{
        schema='bg2-ankheg-installed-verification-v1'; role='installation-facts-not-ingame-QA-or-release'
        verified_at_utc=[DateTime]::UtcNow.ToString('o'); family='monster_ankheg'; animation_ids=$generation.animation_ids
        scale=2; resources=12; frames=516; inherited_animations_unchanged=87; inherited_routes_unchanged=50241
        active_animations=88; active_resources=4572; active_frames=1586172; active_routes=50253
        new_leaf_sha256_verified=12; unchanged_assets_sha256_verified=$baseline.preserved.Count
        inherited_accepted_flying_leaf_sha256_verified=4; inherited_flying_QA_unchanged=$true
        dll_byte_identical=$true; ini_byte_identical=$true; backup_sha256_verified=$true
        native_combined_test=$native; installation_receipt_sha256=(Get-FileSha256 $receiptPath)
        ingame_QA=$false; release=$false
    })
    Write-Output 'Installed complete Ankheg: 12 BAM / 516 frames / 1 ID, Q3m V7 x2; 87 inherited animations preserved.'
} catch {
    $failure=$_
    if ($published) {
        Assert-GameClosed
        Copy-FileAtomic $backup (Resolve-ChildPath $game $baseline.catalog_relative)
        Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative) $baseline.parent_catalog_sha256
    }
    $receipt.status='failed-restored-parent'; $receipt.failure=[string]$failure
    Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
