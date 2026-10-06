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
$catalogTarget=Resolve-ChildPath $game $baseline.catalog_relative -RequireExisting
$receiptPath=Join-Path $PSScriptRoot 'ingame-installation/active-test.json'
$catalogBackup=Join-Path $PSScriptRoot 'work/before/CreatureSprites-XN.catalog'
function Check([string]$Path,[string]$Sha){if((Get-FileSha256 $Path) -ne $Sha.ToUpperInvariant()){throw "Identity differs: $Path"}}
function Preserved{
    foreach($r in $baseline.preserved){Check (Resolve-ChildPath $game $r.relative_path -RequireExisting) $r.sha256}
    foreach($name in $baseline.source_names){if(Test-Path -LiteralPath (Resolve-ChildPath $game "override/$name")){throw "Source override appeared: $name"}}
}
if((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $catalogBackup)){throw 'Fresh installation attempt required.'}
if($generation.family -ne 'monster' -or $generation.scale -ne 2 -or $generation.SDF -or $generation.animation_ids.Count -ne 77 -or $generation.resources -ne 1037 -or $generation.frames -ne 496816 -or $creatures.fixtures.Count -ne 77 -or $pack.monster_shards.Count -ne 1037){throw 'Unexpected Monster scope.'}
if(-not $verification.passed -or -not $verification.native_routing.passed -or $verification.native_routing_animation_ids.Count -ne 77 -or $verification.exhaustive_proven_bound_frames -ne 496822 -or -not $pack.proof.passed){throw 'Verification failed.'}
Assert-GameClosed;Preserved
Check $catalogTarget $baseline.parent_catalog_sha256;Check $catalogSource $generation.catalog.sha256
$planned=[System.Collections.Generic.List[object]]::new()
foreach($s in $pack.monster_shards){
    Check (Resolve-ChildPath $packRoot $s.registry -RequireExisting) $s.sha256
    $target=Resolve-ChildPath $game $s.registry
    if(Test-Path -LiteralPath $target){Check $target $s.sha256}else{$planned.Add([ordered]@{relative_path=$s.registry;sha256=$s.sha256})}
}
foreach($f in $creatures.fixtures){
    Check (Resolve-WorkspaceInput $f.path -RequireExisting) $f.sha256
    if(Test-Path -LiteralPath (Resolve-ChildPath $game $f.target)){throw "Fixture exists: $($f.target)"}
    $planned.Add([ordered]@{relative_path=$f.target;sha256=$f.sha256})
}
if($DryRun){Write-Output "Ready: 77 IDs/1037 leaves/77 neutral CRE; $($planned.Count) new files; runtime/Nearest and 254 inherited IDs preserved.";return}
Copy-FileAtomic $catalogTarget $catalogBackup;Check $catalogBackup $baseline.parent_catalog_sha256
$receipt=[ordered]@{schema='bg2-monster-Q3m-install-v1';status='installing';game_root=$baseline.game_root;animation_ids=$generation.animation_ids;scale=2;SDF=$false;
    catalog_relative=$baseline.catalog_relative;catalog_sha256=$generation.catalog.sha256;parent_catalog_sha256=$baseline.parent_catalog_sha256;
    dll_sha256=$generation.dll.sha256;runtime_changed=$false;monster_shards=$pack.monster_shards;fixtures=$creatures.fixtures;
    preserved_files=$baseline.preserved;planned_new_files=@($planned.ToArray());created_files=@();ingame_QA=$false;release=$false}
Write-JsonAtomic $receiptPath $receipt
$catalogPublished=$false;$created=[System.Collections.Generic.List[object]]::new()
try{
    foreach($s in $pack.monster_shards){
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
    Assert-GameClosed;Preserved;Check $catalogTarget $baseline.parent_catalog_sha256
    $catalogPublished=$true;Copy-FileAtomic $catalogSource $catalogTarget;Check $catalogTarget $generation.catalog.sha256
    Preserved
    $receipt.status='installed-pending-ingame-qa';$receipt.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $receiptPath $receipt
    Write-JsonAtomic (Join-Path $PSScriptRoot 'installation-verification.json') ([ordered]@{status=$receipt.status;animation_ids=$generation.animation_ids;
        catalog_sha256=$generation.catalog.sha256;dll_sha256=$generation.dll.sha256;monster_leaves_sha256_verified=1037;
        fixtures_sha256_verified=77;preserved_files_sha256_verified=$baseline.preserved.Count;created_files=$created.Count;
        retained_animations_unchanged=254;retained_bindings_unchanged=$pack.proof.retained_bindings_unchanged;replaced_pilot_ids=$pack.proof.replaced_pilot_ids;
        scale=2;filter='Nearest';SDF=$false;runtime_changed=$false;ingame_QA=$false;release=$false})
    Write-Output 'Installed Monster: 62 models/77 IDs, 1037 leaves, 77 neutral QMON CRE; runtime unchanged, ingame QA pending.'
}catch{
    $failure=$_;Assert-GameClosed
    if($catalogPublished){Copy-FileAtomic $catalogBackup $catalogTarget;Check $catalogTarget $baseline.parent_catalog_sha256}
    foreach($f in $created){$target=Resolve-ChildPath $game $f.relative_path;if(Test-Path -LiteralPath $target){Check $target $f.sha256;Remove-Item -LiteralPath $target}}
    $receipt.created_files=@($created.ToArray());$receipt.status='failed-restored-parent';$receipt.failure=[string]$failure
    Write-JsonAtomic $receiptPath $receipt;throw $failure
}
