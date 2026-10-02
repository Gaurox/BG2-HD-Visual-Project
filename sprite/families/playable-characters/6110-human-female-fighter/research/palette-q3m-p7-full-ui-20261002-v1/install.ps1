[CmdletBinding()]
param([ValidateSet('Install','Verify','Restore')][string]$Mode='Install', [string]$GameRoot='config://bg2ee_game_root', [string]$StateRoot)
$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
while (-not (Test-Path -LiteralPath (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1'))) { $workspace = Split-Path -Parent $workspace }
. (Join-Path $workspace 'pipeline/scripts/ThinInstall.ps1')
$game = Resolve-WorkspaceInput $GameRoot -RequireExisting
$stateDirectory = if ($StateRoot) { Resolve-WorkspaceInput $StateRoot } else { Join-Path $PSScriptRoot 'ingame-installation' }
$statePath = Join-Path $stateDirectory 'active-test.json'
$manifestPath = Resolve-WorkspaceInput 'pipeline/runtime/manifests/iee-sprite-p7-full-ui-q3m-20261002-v1.json' -RequireExisting
$runtime = Read-JsonFile $manifestPath
if ($runtime.runtime_id -ne 'iee-sprite-p7-full-ui-q3m-20261002-v1' -or @($runtime.paperdoll_packs).Count -ne 79 -or @($runtime.preserved_packs).Count -ne 2) { throw 'Unexpected UI manifest.' }
$files = @(
    [pscustomobject]@{name='dll';source=Resolve-WorkspaceInput $runtime.dll.path -RequireExisting;target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll';sha=$runtime.dll.sha256;before=$runtime.baseline.dll},
    [pscustomobject]@{name='ini';source=Resolve-WorkspaceInput $runtime.ini.path -RequireExisting;target=Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini';sha=$runtime.ini.sha256;before=$runtime.baseline.ini}
)
foreach ($pack in $runtime.paperdoll_packs) {
    if ($pack.target -ne ('iee-assets/paperdolls/'+$pack.resref+'-Q3m-X2.registry') -or $pack.resref -notmatch '^(CHFF[34]INV|WPN[A-Z0-9]{2}(INV|OIN))$') { throw 'Unexpected target identity.' }
    $files += [pscustomobject]@{name=$pack.resref;source=Resolve-WorkspaceInput $pack.path -RequireExisting;target=Resolve-ChildPath $game $pack.target;sha=$pack.sha256;before=$null}
}
if (@($files.target | Select-Object -Unique).Count -ne $files.Count) { throw 'Duplicate target.' }
foreach ($file in $files) { if ((Get-FileSha256 $file.source) -ne $file.sha) { throw "Source differs: $($file.name)" } }
function Assert-Context {
    if ((Get-FileSha256 (Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting)) -ne $runtime.game_profile.baldur_real_sha256) { throw 'Unknown executable.' }
    if ((Get-FileSha256 (Resolve-ChildPath $game 'iee-assets/creature-sprites/CreatureSprites-XN.catalog' -RequireExisting)) -ne $runtime.baseline.catalog) { throw 'World catalog differs.' }
    foreach ($pack in $runtime.preserved_packs) { if ((Get-FileSha256 (Resolve-ChildPath $game $pack.target -RequireExisting)) -ne $pack.sha256) { throw 'Preserved pack differs.' } }
    foreach ($shader in $runtime.shaders) { if ((Get-FileSha256 (Resolve-ChildPath $game $shader.target -RequireExisting)) -ne $shader.sha256) { throw 'Shader differs.' } }
    $refs=@($runtime.capabilities.paperdoll_q3m_test.resrefs)
    if (@(Get-ChildItem -LiteralPath (Resolve-ChildPath $game 'override' -RequireExisting) -File | Where-Object { $_.BaseName -in $refs -or $_.Name -ieq 'UI.MENU' }).Count) { throw 'Native UI override differs.' }
}
function Assert-Files([bool]$Installed) {
    foreach ($file in $files) {
        $expected = if ($Installed) { $file.sha } else { $file.before }
        if ($null -eq $expected) {
            if (Test-Path -LiteralPath $file.target) { throw "Target drift: $($file.name) expected absent." }
        } elseif (-not (Test-Path -LiteralPath $file.target) -or (Get-FileSha256 $file.target) -ne $expected) { throw "Target drift: $($file.name)" }
    }
}
function Restore-Baseline {
    foreach ($file in $files | Where-Object before -ne $null) {
        $backup=Join-Path $stateDirectory ('previous-InfinityEngine-Enhancer.'+$file.name)
        if ((Get-FileSha256 $backup) -ne $file.before) { throw 'Backup differs.' }
    }
    # Precheck every pack before the first mutation, including partial-install rollback.
    foreach ($file in $files | Where-Object before -eq $null) {
        if ((Test-Path -LiteralPath $file.target) -and (Get-FileSha256 $file.target) -ne $file.sha) { throw "Target drift: $($file.name)" }
    }
    foreach ($file in $files) {
        if ($null -ne $file.before) { Copy-FileAtomic (Join-Path $stateDirectory ('previous-InfinityEngine-Enhancer.'+$file.name)) $file.target }
        elseif (Test-Path -LiteralPath $file.target) { Remove-Item -LiteralPath $file.target }
    }
    Assert-Files $false
    Assert-Context
}
Assert-Context
if ($Mode -ne 'Install') {
    $state=Read-JsonFile $statePath
    if ($state.status -ne 'installed' -or $state.game_root -ne $game -or $state.manifest -ne $manifestPath) { throw 'Transaction differs.' }
    Assert-Files $true
    if ($Mode -eq 'Verify') { [pscustomobject]@{Status='verified';Resources=81;UISampler='Nearest';WorldFilter='Box';GameRoot=$game}; return }
    Assert-GameClosed
    Restore-Baseline
    $state.status='restored';$state | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
    Write-JsonAtomic (Join-Path $stateDirectory 'restoration.json') $state
    Remove-Item -LiteralPath $statePath
    [pscustomobject]@{Status='restored';Baseline='accepted CHFF2INV pilot';PreservedPacks=2};return
}
Assert-GameClosed
if (Test-Path -LiteralPath $stateDirectory) { throw 'Transaction already used.' }
Assert-Files $false
New-Item -ItemType Directory -Path $stateDirectory | Out-Null
foreach ($file in $files | Where-Object before -ne $null) { Copy-Item -LiteralPath $file.target -Destination (Join-Path $stateDirectory ('previous-InfinityEngine-Enhancer.'+$file.name)) }
$state=[ordered]@{schema='bg2-p7-full-ui-install-v1';status='installing';game_root=$game;manifest=$manifestPath;files=@($files | Select-Object name,target,sha,before);preserved_packs=$runtime.preserved_packs;ingame_qa=$false;release_changed=$false;controls_pc_input=$false}
Write-JsonAtomic $statePath $state
try {
    foreach ($file in $files) { Copy-FileAtomic $file.source $file.target }
    Assert-Files $true;Assert-Context
    $state.status='installed';$state.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
    Write-JsonAtomic (Join-Path $stateDirectory 'installation-verification.json') $state
} catch {
    $failure=$_;Restore-Baseline;$state.status='rolled-back';Write-JsonAtomic $statePath $state;throw $failure
}
[pscustomobject]@{Status='installed';Resources=81;NewPacks=79;PreservedPacks=2;UISampler='Nearest';WorldFilter='Box';GameRoot=$game;State=$statePath}
