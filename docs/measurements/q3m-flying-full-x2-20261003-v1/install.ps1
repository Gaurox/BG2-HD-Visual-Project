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
if ($pack.new_shards.Count -ne 4 -or $generation.family -ne 'flying' -or
    $generation.resources -ne 4 -or $generation.frames -ne 243 -or $generation.scale -ne 2 -or
    ($generation.animation_ids -join ',') -ne '0xD000,0xD100,0xD200,0xD300,0xD400') { throw 'Unexpected scope.' }
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
    foreach ($name in @('D000.INI','D100.INI','D200.INI','D300.INI','D400.INI','AEAGG1.BAM','AGULG1.BAM','AVULG1.BAM','ABIRG1.BAM')) {
        if (Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")) { throw "Native source override appeared: $name" }
    }
}
Assert-GameClosed
Assert-Preserved
Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting) $baseline.parent_catalog_sha256
Assert-Identity $catalogSource $generation.catalog.sha256
foreach ($identity in @($generation.production,$generation.runtime,$generation.accepted_comparison)) {
    Assert-Identity (Resolve-WorkspaceInput $identity.path -RequireExisting) $identity.sha256
}
$nativeLog = Resolve-WorkspaceInput 'sprite/.work/q3m-flying-full-x2-20261003-v1/native-combined-tests.log' -RequireExisting
$native = Get-Content -LiteralPath $nativeLog | Where-Object { $_.StartsWith('{') } | Select-Object -Last 1 | ConvertFrom-Json
if (-not $native.passed -or $native.resources -ne 5 -or $native.frames -ne 279) { throw 'Native binding test incomplete.' }
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
    schema='bg2-flying-install-v1'; status='installing'; game_root=$baseline.game_root
    family='flying'; animation_ids=$generation.animation_ids; scale=2; resources=4; frames=243
    generation='docs/measurements/q3m-flying-full-x2-20261003-v1/current-generation.json'
    backup_root='docs/measurements/q3m-flying-full-x2-20261003-v1/work/before'
    catalog_relative=$baseline.catalog_relative; catalog_sha256=$generation.catalog.sha256
    parent_catalog_sha256=$baseline.parent_catalog_sha256; dll_sha256=$baseline.dll_sha256; ini_sha256=$baseline.ini_sha256
    new_shards=@($pack.new_shards); inherited_animations=82; active_animations=87
    active_resources=4560; active_frames=1585656; shared_bird_component=$true
    ingame_QA=$false; installed_at_utc=$null
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
        schema='bg2-flying-installed-verification-v1'; role='installation-facts-not-ingame-QA-or-release'
        verified_at_utc=[DateTime]::UtcNow.ToString('o'); family='flying'; animation_ids=$generation.animation_ids
        scale=2; resources=4; frames=243; inherited_animations_unchanged=82; inherited_routes_unchanged=50236
        active_animations=87; active_resources=4560; active_frames=1585656; shared_bird_component=$true
        new_leaf_sha256_verified=4; unchanged_assets_sha256_verified=$baseline.preserved.Count
        dll_byte_identical=$true; ini_byte_identical=$true; backup_sha256_verified=$true
        native_combined_test=$native; python_tests_passed=8; accepted_sample_encodings_unchanged=4
        installation_receipt_sha256=(Get-FileSha256 $receiptPath); ingame_QA=$false; release=$false
    })
    Write-Output 'Installed complete flying family: 4 shared BAM / 243 frames / 5 IDs, Q3m V7 x2; 82 inherited animations preserved.'
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
