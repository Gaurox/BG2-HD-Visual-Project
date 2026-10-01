[CmdletBinding()]
param(
    [ValidateSet('Install', 'Verify', 'Restore')][string]$Mode = 'Install',
    [string]$Run = $PSScriptRoot,
    [string]$Manifest = 'pipeline/runtime/manifests/iee-sprite-p4-box-x2-20261001-v1.json'
)
$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) {
    $workspace = Split-Path -Parent $workspace
    if (-not $workspace) { throw 'Workspace introuvable.' }
}
$scripts = Join-Path $workspace 'pipeline/scripts'
. (Join-Path $scripts 'ThinInstall.ps1')
$runRoot = Resolve-WorkspaceInput $Run -RequireExisting
$jobPath = Resolve-ChildPath $runRoot 'x2-box.job.json' -RequireExisting
$job = Read-JsonFile $jobPath
$game = Resolve-WorkspaceInput $job.paths.game_root -RequireExisting
if ((Resolve-WorkspaceInput $job.paths.run_dir -RequireExisting) -ne $runRoot) { throw 'Run/job divergent.' }
$manifestPath = Resolve-WorkspaceInput $Manifest -RequireExisting
$runtime = Read-JsonFile $manifestPath
if ($runtime.runtime_id -ne 'iee-sprite-p4-box-x2-20261001-v1') { throw 'Runtime BOX x2 divergent.' }
$stateRoot = Join-Path $runRoot 'ingame-installation'
$runtimeState = Join-Path $stateRoot 'runtime'
$statePath = Join-Path $stateRoot 'box-state.json'
$catalogStatePath = Join-Path $stateRoot 'active-test.json'
$catalogTarget = Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting
$iniTarget = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
$dllTarget = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
$targets = @{dll = $dllTarget; ini = $iniTarget; catalog = $catalogTarget}
$captures = Join-Path $runRoot 'captures/box-x2'

function Assert-Shaders {
    if (@($runtime.shaders).Count -ne 3) { throw 'Trois shaders BOX requis.' }
    foreach ($shader in $runtime.shaders) {
        if ((Get-FileSha256 (Resolve-ChildPath $game $shader.target -RequireExisting)) -ne $shader.sha256) {
            throw "Shader divergent : $($shader.target)"
        }
    }
}

if ($Mode -ne 'Install') {
    $state = Read-JsonFile $statePath
    if ($state.schema -ne 'bg2-p4-box-x2-install-v1' -or $state.status -ne 'installed' -or
        $state.game_root -ne $game -or $state.manifest -ne $manifestPath) { throw 'Transaction BOX x2 divergente.' }
    foreach ($key in $targets.Keys) {
        if ((Get-FileSha256 $targets[$key]) -ne $state.after.$key) { throw "Dérive utilisateur $key ; aucun remplacement." }
    }
    if ((Get-FileSha256 $catalogStatePath) -ne $state.catalog_receipt_sha256) { throw 'Reçu catalogue divergent.' }
    Assert-Shaders
    $verified = & (Join-Path $scripts 'Install-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $jobPath -RuntimeManifest $manifestPath -CreatureSpriteFilter Box -VerifyOnly
    if (-not $verified.TargetActive) { throw 'Catalogue BOX x2 inactif.' }
    if ($Mode -eq 'Verify') {
        [pscustomobject]@{Status='verified'; Scale=2; Filter='Box'; Animation='0x6110'; Mipmaps=$false;
            RuntimeId=$runtime.runtime_id; Shards=$verified.InstalledShardsVerified; Captures=$captures; State=$statePath}
        return
    }
    Assert-GameClosed
    $catalogState = Read-JsonFile $catalogStatePath
    if ((Get-FileSha256 (Resolve-ChildPath $runtimeState 'previous-InfinityEngine-Enhancer.dll' -RequireExisting)) -ne $state.before.dll -or
        (Get-FileSha256 (Resolve-ChildPath $catalogState.backup_root $catalogState.ini_backup -RequireExisting)) -ne $state.before.ini -or
        (Get-FileSha256 (Resolve-ChildPath $catalogState.backup_root $catalogState.catalog_backup -RequireExisting)) -ne $state.before.catalog) {
        throw 'Sauvegardes BOX x2 divergentes ; aucune restauration.'
    }
    & (Join-Path $scripts 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $jobPath | Out-Null
    & (Join-Path $scripts 'Install-IEE-Runtime-Test.ps1') -Mode Restore -GameRoot $game -StateRoot $runtimeState | Out-Null
    foreach ($key in $targets.Keys) {
        if ((Get-FileSha256 $targets[$key]) -ne $state.before.$key) { throw "Restauration $key non exacte." }
    }
    $state.status = 'restored'
    Write-JsonAtomic (Join-Path $stateRoot 'restoration.json') $state
    Remove-Item -LiteralPath $statePath
    [pscustomobject]@{Status='restored'; PreviousScale=4; PreviousFilter='Mipmaps'; CapturesPreserved=$true}
    return
}

Assert-GameClosed
if ((Test-Path -LiteralPath $stateRoot) -or (Test-Path -LiteralPath (Join-Path $runRoot 'installation-verification.json'))) {
    throw 'Run déjà utilisé ; Verify/Restore ou nouveau run requis.'
}
Assert-Shaders
$before = @{dll=Get-FileSha256 $dllTarget; ini=Get-FileSha256 $iniTarget; catalog=Get-FileSha256 $catalogTarget}
foreach ($key in $targets.Keys) {
    if ($before[$key] -ne $runtime.baseline.$key) { throw "Baseline $key divergente ; aucune installation." }
}
try {
    & (Join-Path $scripts 'Install-IEE-Runtime-Test.ps1') -Mode Install -Manifest $manifestPath -GameRoot $game -StateRoot $runtimeState | Out-Null
    & (Join-Path $scripts 'Install-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $jobPath -RuntimeManifest $manifestPath -CreatureSpriteFilter Box | Out-Null
    New-Item -ItemType Directory -Path $captures -Force | Out-Null
    $ini = [IO.File]::ReadAllText($iniTarget)
    $ini = Set-IniValue $ini 'Shaders' 'EnableCreatureSpriteP4Probe' 'true'
    $ini = Set-IniValue $ini 'Shaders' 'CreatureSpriteP4Output' $captures
    Write-TextAtomic $iniTarget $ini
    $state = [ordered]@{
        schema='bg2-p4-box-x2-install-v1'; status='installed'; game_root=$game; manifest=$manifestPath
        installed_at_utc=[DateTime]::UtcNow.ToString('o'); before=$before
        after=@{dll=Get-FileSha256 $dllTarget; ini=Get-FileSha256 $iniTarget; catalog=Get-FileSha256 $catalogTarget}
        catalog_receipt_sha256=Get-FileSha256 $catalogStatePath; filter='Box'; scale=2; animation='0x6110'; captures=$captures
    }
    Write-JsonAtomic $statePath $state
    $verified = & $PSCommandPath -Mode Verify -Run $runRoot -Manifest $manifestPath
    Write-JsonAtomic (Join-Path $runRoot 'installation-verification.json') ([ordered]@{
        schema='bg2-p4-box-x2-installation-verification-v1'; status='installed-ingame-pending'
        verified_at_utc=[DateTime]::UtcNow.ToString('o'); verification=$verified; state=$state
        catalog_animation_ids=@('0x6100','0x6110'); filter_animation='0x6110'; mipmaps=$false
        shader_bytes_unchanged=$true; payload_bytes_unchanged=$true; controls_pc_input=$false; release_changed=$false
    })
    $verified
} catch {
    $failure = $_
    if (Test-Path -LiteralPath $catalogStatePath) {
        & (Join-Path $scripts 'Restore-CreatureSprite-XN-Catalog-Test.ps1') -JobFile $jobPath | Out-Null
    }
    if (Test-Path -LiteralPath (Join-Path $runtimeState 'active-test.json')) {
        & (Join-Path $scripts 'Install-IEE-Runtime-Test.ps1') -Mode Restore -GameRoot $game -StateRoot $runtimeState | Out-Null
    }
    if (Test-Path -LiteralPath $statePath) {
        $state.status='rolled-back'; Write-JsonAtomic $statePath $state
    }
    throw $failure
}
