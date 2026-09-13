[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$JobFile,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$job = Read-JsonFile (Resolve-WorkspaceInput $JobFile -RequireExisting)
$run = Resolve-WorkspaceInput ([string]$job.paths.run_dir) -RequireExisting
$statePath = Join-Path $run 'ingame-installation/active-test.json'
if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
    [pscustomobject]@{ Status = 'not-installed'; State = $statePath }
    return
}
$state = Read-JsonFile $statePath
$game = Resolve-WorkspaceInput ([string]$state.game_root) -RequireExisting
$backupRoot = Resolve-WorkspaceInput ([string]$state.backup_root) -RequireExisting
$previousState = Join-Path $backupRoot 'previous-active-test.json'
if (-not $VerifyOnly) { Assert-GameClosed }

if ($state.schema -eq 'bg2-upscale-creature-sprite-catalog-install-v2') {
    $iniTarget = Resolve-ChildPath $game 'InfinityEngine-Enhancer.ini'
    $iniBackup = Resolve-ChildPath $backupRoot ([string]$state.ini_backup) -RequireExisting
    $catalogTarget = Resolve-ChildPath $game ([string]$state.catalog_relative_path)
    $catalogBackup = if ([bool]$state.catalog_existed_before) {
        Resolve-ChildPath $backupRoot ([string]$state.catalog_backup) -RequireExisting
    } else { $null }
    if (-not $VerifyOnly) {
        Copy-FileAtomic $iniBackup $iniTarget
        if ($catalogBackup) { Copy-FileAtomic $catalogBackup $catalogTarget }
        elseif (Test-Path -LiteralPath $catalogTarget) { Remove-Item -LiteralPath $catalogTarget -Force }
    }
} elseif ($state.schema -eq 'bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1') {
    foreach ($targetState in @($state.targets)) {
        if ($targetState.role -notin @('runtime-ini', 'catalog-owner', 'catalog')) { continue }
        $target = Resolve-ChildPath $game ([string]$targetState.relative_path)
        if ([bool]$targetState.existed_before) {
            $backup = Resolve-WorkspaceInput ([string]$targetState.backup_path) -RequireExisting
            if (-not $VerifyOnly) { Copy-FileAtomic $backup $target }
        } elseif (-not $VerifyOnly -and (Test-Path -LiteralPath $target)) {
            Remove-Item -LiteralPath $target -Force
        }
    }
} else {
    throw "Etat d'installation non supporté : $($state.schema)"
}

if ($VerifyOnly) {
    [pscustomobject]@{ Status = 'verified'; GenerationId = $state.generation_id; RuntimeMode = 'untouched' }
    return
}
if (Test-Path -LiteralPath $previousState -PathType Leaf) {
    Copy-FileAtomic $previousState $statePath
} else {
    Remove-Item -LiteralPath $statePath -Force
}
[pscustomobject]@{
    Status = 'restored'; GenerationId = $state.generation_id
    RuntimeMode = 'untouched'; InertShardsKept = $true
}
