[CmdletBinding()]
param(
    [ValidateSet('Install','Verify','Restore')][string]$Mode = 'Install',
    [string]$GameRoot = 'config://bg2ee_game_root',
    [string]$StateRoot,
    [string]$Manifest = 'pipeline/runtime/manifests/iee-sprite-p7-ui-probe-20261002-v2.json'
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
$manifestPath = Resolve-WorkspaceInput $Manifest -RequireExisting
$runtime = Read-JsonFile $manifestPath
if ($runtime.schema -ne 'bg2-upscale-runtime-capabilities-v1' -or $runtime.runtime_id -ne 'iee-sprite-p7-ui-probe-20261002-v2') {
    throw 'Manifeste sonde P7 divergent.'
}
$sources = @{
    dll = Resolve-WorkspaceInput $runtime.dll.path -RequireExisting
    ini = Resolve-WorkspaceInput $runtime.ini.path -RequireExisting
}
$targets = @{
    dll = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll' -RequireExisting
    ini = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini' -RequireExisting
}
$expected = @{dll=$runtime.dll.sha256; ini=$runtime.ini.sha256}
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
        if ((Get-FileSha256 (Resolve-ChildPath $game $shader.target -RequireExisting)) -ne $shader.sha256) {
            throw "Shader divergent : $($shader.target)"
        }
    }
}

function Assert-Targets($hashes) {
    foreach ($key in $targets.Keys) {
        if ((Get-FileSha256 $targets[$key]) -ne $hashes[$key]) { throw "Dérive $key ; aucun remplacement." }
    }
}

Assert-Context
if ($Mode -ne 'Install') {
    $state = Read-JsonFile $statePath
    if ($state.schema -ne 'bg2-p7-ui-probe-install-v1' -or $state.status -ne 'installed' -or
        $state.game_root -ne $game -or $state.manifest -ne $manifestPath) { throw 'Transaction P7 divergente.' }
    Assert-Targets $expected
    if ($Mode -eq 'Verify') {
        [pscustomobject]@{Status='verified'; RuntimeId=$runtime.runtime_id; Body='CHFF1INV'; HDPaperdoll=$false; WorldScale=2; WorldFilter='Box'; GameRoot=$game}
        return
    }
    Assert-GameClosed
    $backups = @{
        dll = Resolve-ChildPath $stateDirectory 'previous-InfinityEngine-Enhancer.dll' -RequireExisting
        ini = Resolve-ChildPath $stateDirectory 'previous-InfinityEngine-Enhancer.ini' -RequireExisting
    }
    foreach ($key in $backups.Keys) {
        if ((Get-FileSha256 $backups[$key]) -ne $runtime.baseline.$key) { throw "Sauvegarde $key divergente." }
    }
    try {
        foreach ($key in $targets.Keys) { Copy-FileAtomic $backups[$key] $targets[$key] }
        Assert-Targets @{dll=$runtime.baseline.dll; ini=$runtime.baseline.ini}
    } catch {
        foreach ($key in $targets.Keys) { Copy-FileAtomic $sources[$key] $targets[$key] }
        throw
    }
    $state.status = 'restored'
    $state | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
    Write-JsonAtomic (Join-Path $stateDirectory 'restoration.json') $state
    Remove-Item -LiteralPath $statePath
    [pscustomobject]@{Status='restored'; WorldScale=2; WorldFilter='Box'; ExactDLLAndINI=$true}
    return
}

Assert-GameClosed
if (Test-Path -LiteralPath $stateDirectory) { throw 'Transaction déjà utilisée : Verify/Restore ou nouveau StateRoot.' }
Assert-Targets @{dll=$runtime.baseline.dll; ini=$runtime.baseline.ini}
New-Item -ItemType Directory -Path $stateDirectory | Out-Null
Copy-Item -LiteralPath $targets.dll -Destination (Join-Path $stateDirectory 'previous-InfinityEngine-Enhancer.dll')
Copy-Item -LiteralPath $targets.ini -Destination (Join-Path $stateDirectory 'previous-InfinityEngine-Enhancer.ini')
$state = [ordered]@{
    schema='bg2-p7-ui-probe-install-v1'; status='installing'; game_root=$game; manifest=$manifestPath
    before=@{dll=$runtime.baseline.dll; ini=$runtime.baseline.ini}; after=$expected
    body='CHFF1INV'; hd_paperdoll=$false; controls_pc_input=$false; release_changed=$false
}
Write-JsonAtomic $statePath $state
try {
    foreach ($key in $targets.Keys) { Copy-FileAtomic $sources[$key] $targets[$key] }
    Assert-Targets $expected
    Assert-Context
    $state.status='installed'; $state.installed_at_utc=[DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
    Write-JsonAtomic (Join-Path $stateDirectory 'installation-verification.json') $state
} catch {
    $failure = $_
    foreach ($key in $targets.Keys) {
        Copy-FileAtomic (Join-Path $stateDirectory ('previous-InfinityEngine-Enhancer.' + $key)) $targets[$key]
    }
    $state.status='rolled-back'; Write-JsonAtomic $statePath $state
    throw $failure
}
[pscustomobject]@{Status='installed'; Body='CHFF1INV'; HDPaperdoll=$false; WorldScale=2; WorldFilter='Box'; GameRoot=$game; State=$statePath}
