[CmdletBinding()]
param(
    [ValidateSet('Install','Verify','Restore')][string]$Mode = 'Install',
    [string]$GameRoot = 'config://bg2ee_game_root',
    [string]$StateRoot
)
$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) {
    $workspace = Split-Path -Parent $workspace
    if (-not $workspace) { throw 'Workspace introuvable.' }
}
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$game = Resolve-WorkspaceInput $GameRoot -RequireExisting
$stateDirectory = if ($StateRoot) { Resolve-WorkspaceInput $StateRoot } else { Join-Path $PSScriptRoot 'ingame-installation' }
$statePath = Join-Path $stateDirectory 'active-test.json'
$manifestPath = Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-sprite-p7-chff2inv-q3m-20261002-v1.json' -RequireExisting
$runtime = Read-JsonFile $manifestPath
if ($runtime.schema -ne 'bg2-upscale-runtime-capabilities-v1' -or $runtime.runtime_id -ne 'iee-sprite-p7-chff2inv-q3m-20261002-v1' -or
    $runtime.paperdoll_pack.target -ne 'iee-assets/paperdolls/CHFF2INV-Q3m-X2.registry' -or $null -ne $runtime.baseline.pack) {
    throw 'Manifeste pilote P7 divergent.'
}
$sources = @{
    dll = Resolve-WorkspaceInput $runtime.dll.path -RequireExisting
    ini = Resolve-WorkspaceInput $runtime.ini.path -RequireExisting
    pack = Resolve-WorkspaceInput $runtime.paperdoll_pack.path -RequireExisting
}
$targets = @{
    dll = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
    ini = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
    pack = Resolve-ChildPath $game $runtime.paperdoll_pack.target
}
$expected = @{dll=$runtime.dll.sha256;ini=$runtime.ini.sha256;pack=$runtime.paperdoll_pack.sha256}
foreach ($key in $sources.Keys) {
    if ((Get-FileSha256 $sources[$key]) -ne $expected[$key]) { throw "Source $key divergente." }
}
function Assert-Context {
    if ((Get-FileSha256 (Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting)) -ne $runtime.game_profile.baldur_real_sha256) {
        throw 'Exécutable inconnu : aucune installation.'
    }
    if ((Get-FileSha256 (Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting)) -ne $runtime.baseline.catalog) {
        throw 'Catalogue divergent : aucun remplacement.'
    }
    foreach ($shader in $runtime.shaders) {
        if ((Get-FileSha256 (Resolve-ChildPath $game $shader.target -RequireExisting)) -ne $shader.sha256) { throw "Shader divergent : $($shader.target)" }
    }
    foreach ($preserved in $runtime.preserved_packs) {
        if ((Get-FileSha256 (Resolve-ChildPath $game $preserved.target -RequireExisting)) -ne $preserved.sha256) { throw 'Pack CHFF1INV préservé divergent.' }
    }
    $override = Resolve-ChildPath $game 'override' -RequireExisting
    if (@(Get-ChildItem -LiteralPath $override -File | Where-Object { $_.BaseName -ieq 'CHFF1INV' -or $_.BaseName -ieq 'CHFF2INV' -or $_.Name -ieq 'UI.MENU' }).Count) {
        throw 'CHFF2INV ou UI.MENU override : contrat natif non garanti.'
    }
}
function Assert-Targets($hashes) {
    foreach ($key in $targets.Keys) {
        if ($null -eq $hashes[$key]) {
            if (Test-Path -LiteralPath $targets[$key]) { throw "Dérive $key ; cible attendue absente." }
        } elseif (-not (Test-Path -LiteralPath $targets[$key]) -or (Get-FileSha256 $targets[$key]) -ne $hashes[$key]) {
            throw "Dérive $key ; aucun remplacement."
        }
    }
}
function Restore-Baseline {
    if ((Test-Path -LiteralPath $targets.pack) -and (Get-FileSha256 $targets.pack) -ne $expected.pack) {
        throw 'Dérive pack : suppression refusée.'
    }
    foreach ($key in @('dll','ini')) {
        $backup = Resolve-ChildPath $stateDirectory ('previous-InfinityEngine-Enhancer.'+$key) -RequireExisting
        if ((Get-FileSha256 $backup) -ne $runtime.baseline.$key) { throw "Sauvegarde $key divergente." }
    }
    foreach ($key in @('dll','ini')) { Copy-FileAtomic (Join-Path $stateDirectory ('previous-InfinityEngine-Enhancer.'+$key)) $targets[$key] }
    if (Test-Path -LiteralPath $targets.pack) {
        if ((Get-FileSha256 $targets.pack) -ne $expected.pack) { throw 'Dérive pack : suppression refusée.' }
        Remove-Item -LiteralPath $targets.pack
    }
    Assert-Targets @{dll=$runtime.baseline.dll;ini=$runtime.baseline.ini;pack=$null}
}
Assert-Context
if ($Mode -ne 'Install') {
    $state = Read-JsonFile $statePath
    if ($state.schema -ne 'bg2-p7-paperdoll-install-v1' -or $state.status -ne 'installed' -or
        $state.game_root -ne $game -or $state.manifest -ne $manifestPath) { throw 'Transaction P7 divergente.' }
    Assert-Targets $expected
    if ($Mode -eq 'Verify') {
        [pscustomobject]@{Status='verified';RuntimeId=$runtime.runtime_id;Body='CHFF2INV';HDPaperdoll=$true;UISampler='Nearest';WorldScale=2;WorldFilter='Box';GameRoot=$game}
        return
    }
    Assert-GameClosed
    try { Restore-Baseline } catch {
        foreach ($key in $targets.Keys) { Copy-FileAtomic $sources[$key] $targets[$key] }
        throw
    }
    $state.status = 'restored'
    $state | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
    Write-JsonAtomic (Join-Path $stateDirectory 'restoration.json') $state
    Remove-Item -LiteralPath $statePath
    [pscustomobject]@{Status='restored';Baseline='accepted CHFF1INV pilot';ExactDLLAndINI=$true;UIPackRemoved=$true}
    return
}
Assert-GameClosed
if (Test-Path -LiteralPath $stateDirectory) { throw 'Transaction déjà utilisée : Verify/Restore ou nouveau StateRoot.' }
Assert-Targets @{dll=$runtime.baseline.dll;ini=$runtime.baseline.ini;pack=$null}
New-Item -ItemType Directory -Path $stateDirectory | Out-Null
foreach ($key in @('dll','ini')) { Copy-Item -LiteralPath $targets[$key] -Destination (Join-Path $stateDirectory ('previous-InfinityEngine-Enhancer.'+$key)) }
$state = [ordered]@{
    schema='bg2-p7-paperdoll-install-v1';status='installing';game_root=$game;manifest=$manifestPath
    before=@{dll=$runtime.baseline.dll;ini=$runtime.baseline.ini;pack=$null};after=$expected
    body='CHFF2INV';hd_paperdoll=$true;ui_sampler='Nearest';world_scale=2;world_filter='Box'
    controls_pc_input=$false;ingame_qa=$false;release_changed=$false
}
Write-JsonAtomic $statePath $state
try {
    foreach ($key in $targets.Keys) { Copy-FileAtomic $sources[$key] $targets[$key] }
    Assert-Targets $expected
    Assert-Context
    $state.status='installed';$state.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
    Write-JsonAtomic (Join-Path $stateDirectory 'installation-verification.json') $state
} catch {
    $failure = $_
    Restore-Baseline
    $state.status='rolled-back';Write-JsonAtomic $statePath $state
    throw $failure
}
[pscustomobject]@{Status='installed';Body='CHFF2INV';HDPaperdoll=$true;UISampler='Nearest';WorldScale=2;WorldFilter='Box';GameRoot=$game;State=$statePath}
