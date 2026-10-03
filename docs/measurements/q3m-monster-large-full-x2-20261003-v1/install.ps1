$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline = Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation = Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$game = Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot = Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack = Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource = Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$dllSource = Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$backupRoot = Join-Path $PSScriptRoot 'work/before'
$receiptPath = Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
if (Test-Path -LiteralPath $receiptPath) { throw 'Installation receipt exists; inspect it before any retry.' }
if (Test-Path -LiteralPath $backupRoot) { throw 'Backup exists; inspect it before any retry.' }
if ($pack.new_shards.Count -ne 7 -or $generation.family -ne 'monster_large' -or
    $generation.resources -ne 7 -or $generation.frames -ne 434 -or $generation.scale -ne 2) {
    throw 'Unexpected family scope.'
}
function Assert-Identity([string]$Path, [string]$Expected) {
    if ((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()) { throw "Identity differs: $Path" }
}
function Assert-Preserved {
    foreach ($item in $baseline.preserved) {
        Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256
    }
}
function Assert-Baseline {
    Assert-GameClosed
    Assert-Identity (Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting) $baseline.executable_sha256
    Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting) $baseline.parent_catalog_sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting) $baseline.dll_sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting) $baseline.ini_sha256
    Assert-Preserved
    foreach ($name in @('9000.INI', 'MOGRG1.BAM', 'MOGRG1E.BAM', 'MOGRG2.BAM', 'MOGRG2E.BAM', 'MOGRG3.BAM', 'MOGRG3E.BAM', 'MOGRINV.BAM')) {
        if (Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")) { throw "Native source override appeared: $name" }
    }
}
Assert-Baseline
Assert-Identity $catalogSource $generation.catalog.sha256
Assert-Identity $dllSource $generation.dll.sha256
Assert-Identity (Resolve-WorkspaceInput $generation.runtime.path -RequireExisting) $generation.runtime.sha256
Assert-Identity (Resolve-WorkspaceInput $generation.production.path -RequireExisting) $generation.production.sha256
foreach ($shard in $pack.new_shards) {
    $name = [IO.Path]::GetFileName([string]$shard.registry)
    if ($name -ne "CreatureSprites-XN-$($shard.sha256).registry") { throw 'Unexpected leaf name.' }
    $source = Resolve-ChildPath $packRoot $shard.registry -RequireExisting
    if ((Get-Item -LiteralPath $source).Length -ne $shard.registry_bytes) { throw 'Leaf size differs.' }
    Assert-Identity $source $shard.sha256
    $target = Resolve-ChildPath $game $shard.registry
    if (Test-Path -LiteralPath $target) { Assert-Identity $target $shard.sha256 }
}
$backups = @(
    @{ relative_path = $baseline.catalog_relative; file = 'CreatureSprites-XN.catalog'; sha256 = $baseline.parent_catalog_sha256 },
    @{ relative_path = 'InfinityEngine-Enhancer.dll'; file = 'InfinityEngine-Enhancer.dll'; sha256 = $baseline.dll_sha256 },
    @{ relative_path = 'InfinityEngine-Enhancer.ini'; file = 'InfinityEngine-Enhancer.ini'; sha256 = $baseline.ini_sha256 }
)
foreach ($item in $backups) {
    $backup = Resolve-ChildPath $backupRoot $item.file
    Copy-FileAtomic (Resolve-ChildPath $game $item.relative_path -RequireExisting) $backup
    Assert-Identity $backup $item.sha256
}
$receipt = [ordered]@{
    schema = 'bg2-monster-large-install-v1'; status = 'installing'; game_root = $baseline.game_root
    family = 'monster_large'; animation_ids = @('0x9000'); scale = 2; resources = 7; frames = 434
    generation = 'docs/measurements/q3m-monster-large-full-x2-20261003-v1/current-generation.json'
    backup_root = 'docs/measurements/q3m-monster-large-full-x2-20261003-v1/work/before'
    backups = $backups; new_shards = @($pack.new_shards)
    catalog_relative = $baseline.catalog_relative; catalog_sha256 = $generation.catalog.sha256
    dll_sha256 = $generation.dll.sha256; ini_sha256 = $baseline.ini_sha256
    preserved_assets = $baseline.preserved.Count; inherited_animations = 81
    active_animations = 82; active_resources = 4556; active_frames = 1585413
    ingame_QA = $false; installed_at_utc = $null
}
Write-JsonAtomic $receiptPath $receipt
$published = $false
try {
    foreach ($shard in $pack.new_shards) {
        $target = Resolve-ChildPath $game $shard.registry
        if (-not (Test-Path -LiteralPath $target)) {
            Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target
        }
        Assert-Identity $target $shard.sha256
    }
    Assert-Baseline
    $published = $true
    Copy-FileAtomic $dllSource (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll')
    Assert-GameClosed
    Copy-FileAtomic $catalogSource (Resolve-ChildPath $game $baseline.catalog_relative)
    Assert-Identity (Resolve-ChildPath $game $baseline.catalog_relative) $generation.catalog.sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll') $generation.dll.sha256
    Assert-Identity (Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini') $baseline.ini_sha256
    Assert-Preserved
    $receipt.status = 'installed-pending-ingame-qa'
    $receipt.installed_at_utc = [DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-Output 'Installed monster_large 0x9000: 7 BAM / 434 frames, Q3m V7 x2; 81 inherited animations preserved.'
} catch {
    $failure = $_
    if ($published) {
        Assert-GameClosed
        foreach ($item in $backups) {
            Copy-FileAtomic (Resolve-ChildPath $backupRoot $item.file -RequireExisting) (Resolve-ChildPath $game $item.relative_path)
            Assert-Identity (Resolve-ChildPath $game $item.relative_path) $item.sha256
        }
    }
    $receipt.status = 'failed-restored-parent'
    $receipt.failure = [string]$failure
    Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
