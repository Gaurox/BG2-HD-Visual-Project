[CmdletBinding()]param([switch]$DryRun)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../../pipeline/scripts/ThinInstall.ps1')
$baseline=Read-JsonFile (Join-Path $PSScriptRoot 'baseline.json')
$generation=Read-JsonFile (Join-Path $PSScriptRoot 'current-generation.json')
$verification=Read-JsonFile (Join-Path $PSScriptRoot 'verification.json')
$creatures=Read-JsonFile (Join-Path $PSScriptRoot 'creatures.json')
$game=Resolve-WorkspaceInput $baseline.game_root -RequireExisting
$packRoot=Resolve-WorkspaceInput $generation.generation_dir -RequireExisting
$pack=Read-JsonFile (Resolve-ChildPath $packRoot 'pack.json' -RequireExisting)
$catalogSource=Resolve-WorkspaceInput $generation.catalog.path -RequireExisting
$dllSource=Resolve-WorkspaceInput $generation.dll.path -RequireExisting
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$dllTarget=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$backupRoot=Join-Path $PSScriptRoot 'work/before'
$catalogBackup=Join-Path $backupRoot 'CreatureSprites-XN.catalog'
$dllBackup=Join-Path $backupRoot 'InfinityEngine-Enhancer.dll'
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{
    foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $catalogBackup) -or (Test-Path -LiteralPath $dllBackup)){throw 'Fresh installation attempt required; inspect receipt.'}
if($generation.family -ne 'monster_icewind' -or $generation.scale -ne 2 -or $generation.SDF -or $generation.animation_ids.Count -ne 40 -or $generation.resources -ne 1115 -or $generation.frames -ne 75176 -or $creatures.fixtures.Count -ne 40 -or $pack.new_shards.Count -ne 1115){throw 'Unexpected Icewind scope.'}
if(-not $verification.passed -or -not $verification.native_world.passed -or $verification.native_world.frames -ne 76955 -or -not $verification.playback.passed -or $verification.playback.missing_or_wrong_frames -ne 0){throw 'Combined native verification failed.'}
Check (Resolve-WorkspaceInput $generation.runtime.path -RequireExisting) $generation.runtime.sha256
Assert-GameClosed;Preserved
Check $catalogTarget $baseline.parent_catalog_sha256;Check $dllTarget $baseline.parent_dll_sha256
Check $catalogSource $generation.catalog.sha256;Check $dllSource $generation.dll.sha256
foreach($s in $pack.new_shards){
    Check (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $s.sha256
    $target=Resolve-ChildPath $game $s.registry
    if(Test-Path -LiteralPath $target){Check $target $s.sha256}
}
foreach($f in $creatures.fixtures){
    Check (Resolve-WorkspaceInput $f.path -RequireExisting) $f.sha256
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $f.target)){throw "Fixture exists: $($f.target)"}
}
if($DryRun){Write-Output 'Ready: game/loader closed; 40 IDs, 1115 leaves, 40 fixtures, inherited assets preserved; candidate DLL/catalog verified.';return}
Copy-FileAtomic $catalogTarget $catalogBackup;Check $catalogBackup $baseline.parent_catalog_sha256
Copy-FileAtomic $dllTarget $dllBackup;Check $dllBackup $baseline.parent_dll_sha256
$receipt=[ordered]@{schema='bg2-icewind-Q3m-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$false;
    catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;
    dll_sha256=$generation.dll.sha256;parent_dll_sha256=$baseline.parent_dll_sha256;new_shards=$pack.new_shards;fixtures=$creatures.fixtures;
    preserved_files=$baseline.preserved;created_files=@();ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$catalogPublished=$false;$dllPublished=$false;$created=[System.Collections.Generic.List[object]]::new()
try{
    foreach($s in $pack.new_shards){
        Assert-GameClosed;$target=Resolve-ChildPath $game $s.registry
        if(-not(Test-Path -LiteralPath $target)){
            $created.Add([ordered]@{relative_path=$s.registry;sha256=$s.sha256})
            Copy-FileAtomic (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $target
        }
        Check $target $s.sha256
    }
    foreach($f in $creatures.fixtures){
        Assert-GameClosed;$target=Resolve-ChildPath $game $f.target
        if(Test-Path -LiteralPath $target){throw "Fixture appeared: $($f.target)"}
        $created.Add([ordered]@{relative_path=$f.target;sha256=$f.sha256})
        Copy-FileAtomic (Resolve-WorkspaceInput $f.path -RequireExisting) $target;Check $target $f.sha256
    }
    $receipt.created_files=@($created.ToArray());Write-JsonAtomic $receiptPath $receipt
    Assert-GameClosed;Preserved
    Check $catalogTarget $baseline.parent_catalog_sha256;Check $dllTarget $baseline.parent_dll_sha256
    $dllPublished=$true;Copy-FileAtomic $dllSource $dllTarget;Check $dllTarget $generation.dll.sha256
    $catalogPublished=$true;Copy-FileAtomic $catalogSource $catalogTarget;Check $catalogTarget $generation.catalog.sha256
    Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;animation_ids=$generation.animation_ids;
        catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;new_leaves_sha256_verified=$pack.new_shards.Count;
        fixtures_sha256_verified=$creatures.fixtures.Count;preserved_files_sha256_verified=$baseline.preserved.Count;
        inherited_animations_unchanged=217;inherited_routes_unchanged=60888;scale=2;filter='Nearest';SDF=$false;ingame_QA=$false;release=$false})
    Write-Output 'Installed Icewind: 40 IDs/1115 leaves/40 neutral CRE fixtures, candidate DLL; previous 217 animations retained, ingame QA pending.'
}catch{
    $failure=$_;Assert-GameClosed
    if($catalogPublished){Copy-FileAtomic $catalogBackup $catalogTarget;Check $catalogTarget $baseline.parent_catalog_sha256}
    if($dllPublished){Copy-FileAtomic $dllBackup $dllTarget;Check $dllTarget $baseline.parent_dll_sha256}
    foreach($f in $created){$target=Resolve-ChildPath $game $f.relative_path;if(Test-Path -LiteralPath $target){Check $target $f.sha256;Remove-Item -LiteralPath $target}}
    $receipt.created_files=@($created.ToArray());$receipt.status='failed-restored-parent';$receipt.failure=[string]$failure
    Write-JsonAtomic $receiptPath $receipt;throw $failure
}
