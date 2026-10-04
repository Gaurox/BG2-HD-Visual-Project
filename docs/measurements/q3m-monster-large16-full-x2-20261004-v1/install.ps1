$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$creatures=Read-JsonFile (Join-Path $PSScriptRoot 'creatures.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$snapshotPath=Join-Path $PSScriptRoot 'installation-verification.json'
$backupRoot=Join-Path $PSScriptRoot 'work/before'
$backup=Resolve-ChildPath $backupRoot 'CreatureSprites-XN.catalog'
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $snapshotPath) -or (Test-Path -LiteralPath $backupRoot)){throw 'Installation already attempted; inspect state.'}
if($generation.family -ne 'monster_large16' -or $generation.scale -ne 2 -or $generation.registry_version -ne 7 -or $generation.SDF -or
   $generation.resources -ne 20 -or $generation.frames -ne 1692 -or $pack.new_shards.Count -ne 20 -or
   ($generation.animation_ids -join ',') -ne '0xA000,0xA100,0xA200'){throw 'Unexpected scope.'}
function Assert-Identity([string]$Path,[string]$Expected){if((Get-FileSha256 $Path) -ne $Expected.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Assert-Preserved{
    foreach($item in $baseline.preserved){Assert-Identity (Resolve-ChildPath $game $item.relative_path -RequireExisting) $item.sha256}
    foreach($item in $baseline.inherited_QA){Assert-Identity (Resolve-WorkspaceInput $item.path -RequireExisting) $item.sha256}
    foreach($name in @('A000.INI','A100.INI','A200.INI','MWYV_WS.BMP')+@($baseline.source_BAMs | ForEach-Object {"$_.BAM"})){
        if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}
    }
}
$fixture=$creatures.fixture
if(-not $fixture -or $fixture.target -ne 'override/QMWYVW01.cre' -or $fixture.parent_target_existed){throw 'Unexpected test creature.'}
$fixtureSource=Resolve-WorkspaceInput $fixture.path -RequireExisting
$fixtureTarget=Resolve-ChildPath $game $fixture.target
if(Test-Path -LiteralPath $fixtureTarget){throw 'Test creature target already exists.'}
Assert-GameClosed
Assert-Preserved
Assert-Identity $fixtureSource $fixture.sha256
Assert-Identity $catalogSource $generation.catalog.sha256
Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
foreach($item in @($generation.production,$generation.runtime)){Assert-Identity (Resolve-WorkspaceInput $item.path -RequireExisting) $item.sha256}
$native=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'native-combined.log') | Where-Object {$_.StartsWith('{')} | Select-Object -Last 1 | ConvertFrom-Json
if(-not $native.passed -or $native.resources -ne 20 -or $native.frames -ne 1692){throw 'Native binding check incomplete.'}
foreach($shard in $pack.new_shards){
    if([IO.Path]::GetFileName([string]$shard.registry) -ne "CreatureSprites-XN-$($shard.sha256).registry"){throw 'Unexpected leaf name.'}
    Assert-Identity (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $shard.sha256
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $shard.registry)){Assert-Identity (Resolve-ChildPath $game $shard.registry) $shard.sha256}
}
Copy-FileAtomic $catalogTarget $backup
Assert-Identity $backup $baseline.parent_catalog_sha256
$receipt=[ordered]@{
    schema='bg2-Large16-install-v1';status='installing';game_root=$baseline.game_root
    family='monster_large16';animation_ids=$generation.animation_ids;scale=2;resources=20;frames=1692;SDF=$false
    generation='docs/measurements/q3m-monster-large16-full-x2-20261004-v1/current-generation.json'
    backup_root='docs/measurements/q3m-monster-large16-full-x2-20261004-v1/work/before'
    catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256
    dll_sha256=$baseline.dll_sha256;ini_sha256=$baseline.ini_sha256;preserved_files=$baseline.preserved;new_shards=$pack.new_shards;fixture=$fixture
    inherited_animations=88;active_animations=91;ingame_QA=$false;release=$false;installed_at_utc=$null
}
Write-JsonAtomic $receiptPath $receipt
$published=$false;$fixtureCreated=$false
try{
    foreach($shard in $pack.new_shards){
        $target=Resolve-ChildPath $game $shard.registry
        if(-not (Test-Path -LiteralPath $target)){Copy-FileAtomic (Resolve-ChildPath $packRoot $shard.registry -RequireExisting) $target}
        Assert-Identity $target $shard.sha256
    }
    Assert-GameClosed
    Assert-Preserved
    Assert-Identity $catalogTarget $baseline.parent_catalog_sha256
    if(Test-Path -LiteralPath $fixtureTarget){throw 'Test creature target appeared.'}
    Copy-FileAtomic $fixtureSource $fixtureTarget;$fixtureCreated=$true
    Assert-Identity $fixtureTarget $fixture.sha256
    Assert-GameClosed
    $published=$true
    Copy-FileAtomic $catalogSource $catalogTarget
    Assert-Identity $catalogTarget $generation.catalog.sha256
    Assert-Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic $snapshotPath ([ordered]@{
        schema='bg2-Large16-installed-verification-v1';role='installation-not-ingame-QA-or-release';status=$receipt.status
        installed_at_utc=$receipt.installed_at_utc;family='monster_large16';animation_ids=$generation.animation_ids
        resources=20;frames=1692;original_world_BAMs=12;auxiliary_inventory_BAMs=1;UI_integration_claimed=$false;scale=2;registry_version=7;SDF=$false
        inherited_animations_unchanged=88;inherited_routes_unchanged=50253;active_animations=91;active_resources=4592;active_frames=1587864;active_routes=50273
        new_leaf_sha256_verified=20;unchanged_files_sha256_verified=$baseline.preserved.Count
        dll_byte_identical=$true;ini_byte_identical=$true;Ankheg_SDF_and_wait_unchanged=$true;Character_SDF_not_enabled=$true
        native_combined_test=$native;fixture=$fixture;backup_sha256_verified=$true
        installation_receipt_sha256=(Get-FileSha256 $receiptPath);ingame_QA=$false;release=$false
    })
    Write-Output 'Installed complete available Large16: 3 IDs / Q3m V7 x2 / no SDF; 20 colour-contract leaves; stable Ankheg and Character stock preserved.'
}catch{
    $failure=$_
    if($published -or $fixtureCreated){Assert-GameClosed}
    if($published){Copy-FileAtomic $backup $catalogTarget;Assert-Identity $catalogTarget $baseline.parent_catalog_sha256}
    if($fixtureCreated){Assert-Identity $fixtureTarget $fixture.sha256;Remove-Item -LiteralPath $fixtureTarget}
    $receipt.status='failed-restored-parent';$receipt.failure=[string]$failure;Write-JsonAtomic $receiptPath $receipt
    throw $failure
}
