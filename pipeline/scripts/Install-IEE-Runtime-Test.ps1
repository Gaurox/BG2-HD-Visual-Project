[CmdletBinding()]
param(
    [ValidateSet('Install', 'Restore', 'Verify')]
    [string]$Mode = 'Install',
    [string]$Manifest = 'pipeline/runtime/manifests/iee-water-ar1000n-creature-catalog-v2-v1.json',
    [string]$GameRoot,
    [string]$StateRoot = '.tmp/iee-runtime-install'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$game = if ($GameRoot) { Resolve-WorkspaceInput $GameRoot -RequireExisting } else {
    Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
}
$dllTarget = Resolve-ChildPath $game 'InfinityEngine-Enhancer.dll'
$stateDirectory = Resolve-WorkspaceInput $StateRoot
$statePath = Join-Path $stateDirectory 'active-test.json'

if ($Mode -eq 'Restore') {
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { throw 'Aucune transaction runtime active.' }
    $state = Read-JsonFile $statePath
    if ($state.schema -ne 'bg2-upscale-iee-runtime-install-v1') { throw 'Etat runtime non supporté.' }
    if ([IO.Path]::GetFullPath([string]$state.game_root) -ne [IO.Path]::GetFullPath($game)) {
        throw 'Le jeu demandé diffère de la transaction runtime.'
    }
    Assert-GameClosed
    if ([bool]$state.dll_existed_before) {
        Copy-FileAtomic (Resolve-ChildPath $stateDirectory ([string]$state.backup) -RequireExisting) $dllTarget
    } elseif (Test-Path -LiteralPath $dllTarget) {
        Remove-Item -LiteralPath $dllTarget -Force
    }
    Remove-Item -LiteralPath $statePath -Force
    [pscustomobject]@{ Status = 'restored'; GameRoot = $game; RuntimeUntouchedByAssets = $true }
    return
}

$manifestPath = Resolve-WorkspaceInput $Manifest -RequireExisting
$runtime = Read-JsonFile $manifestPath
if ($runtime.schema -ne 'bg2-upscale-runtime-capabilities-v1') { throw 'Manifeste runtime non supporté.' }
$sourceDll = Resolve-WorkspaceInput ([string]$runtime.dll.path) -RequireExisting
$expectedDll = ([string]$runtime.dll.sha256).ToUpperInvariant()
if ((Get-FileSha256 $sourceDll) -ne $expectedDll) { throw 'La DLL source diffère du manifeste runtime.' }
$exe = Resolve-ChildPath $game 'BaldurReal.exe' -RequireExisting
if ((Get-FileSha256 $exe) -ne ([string]$runtime.game_profile.baldur_real_sha256).ToUpperInvariant()) {
    throw 'BaldurReal.exe est incompatible avec le runtime.'
}

if ($Mode -eq 'Verify') {
    if (-not (Test-Path -LiteralPath $dllTarget -PathType Leaf) -or (Get-FileSha256 $dllTarget) -ne $expectedDll) {
        throw 'Le runtime live ne correspond pas au manifeste.'
    }
    [pscustomobject]@{ Status = 'verified'; RuntimeId = $runtime.runtime_id; GameRoot = $game }
    return
}

if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $active = Read-JsonFile $statePath
    if ($active.runtime_id -eq $runtime.runtime_id -and (Test-Path -LiteralPath $dllTarget) -and
        (Get-FileSha256 $dllTarget) -eq $expectedDll) {
        [pscustomobject]@{ Status = 'already-installed'; RuntimeId = $runtime.runtime_id; GameRoot = $game }
        return
    }
    throw 'Une autre transaction runtime est active ; restaurez-la avant remplacement.'
}

Assert-GameClosed
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$backupName = 'previous-InfinityEngine-Enhancer.dll'
$existed = Test-Path -LiteralPath $dllTarget -PathType Leaf
if ($existed) { Copy-Item -LiteralPath $dllTarget -Destination (Join-Path $stateDirectory $backupName) -Force }
$state = [ordered]@{
    schema = 'bg2-upscale-iee-runtime-install-v1'; status = 'installing'
    runtime_id = [string]$runtime.runtime_id; manifest = $manifestPath; game_root = $game
    dll_sha256 = $expectedDll; dll_existed_before = [bool]$existed
    backup = if ($existed) { $backupName } else { $null }
}
Write-JsonAtomic $statePath $state
try {
    Copy-FileAtomic $sourceDll $dllTarget
    $state.status = 'installed'
    $state.installed_at_utc = [DateTime]::UtcNow.ToString('o')
    Write-JsonAtomic $statePath $state
} catch {
    if ($existed) { Copy-FileAtomic (Join-Path $stateDirectory $backupName) $dllTarget }
    elseif (Test-Path -LiteralPath $dllTarget) { Remove-Item -LiteralPath $dllTarget -Force }
    Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
    throw
}
[pscustomobject]@{ Status = 'installed'; RuntimeId = $runtime.runtime_id; GameRoot = $game }
