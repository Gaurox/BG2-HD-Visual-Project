[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$JobFile,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ThinInstall.ps1')

$jobPath = Resolve-WorkspaceInput $JobFile -RequireExisting
$job = Read-JsonFile $jobPath
$run = Resolve-WorkspaceInput ([string]$job.paths.run_dir) -RequireExisting
$stateRun = if ($job.schema -eq 'bg2-upscale-reboutcx-derived-catalog-job-v1') {
    Split-Path -Parent (Resolve-WorkspaceInput ([string]$job.paths.parent_pointer) -RequireExisting)
} else { $run }
$pointer = Read-JsonFile (Join-Path $run 'current-generation.json')
$statePath = Join-Path $stateRun 'ingame-installation/active-test.json'
if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
    [pscustomobject]@{ Status = 'not-installed'; State = $statePath }
    return
}
$state = Read-JsonFile $statePath

if ($state.schema -eq 'bg2-upscale-creature-sprite-catalog-install-v2') {
    $stateJobPath = Resolve-WorkspaceInput ([string]$state.job_file) -RequireExisting
    if (-not [string]::Equals(
            [IO.Path]::GetFullPath($stateJobPath),
            [IO.Path]::GetFullPath($jobPath),
            [StringComparison]::OrdinalIgnoreCase
        ) -or [string]$state.generation_id -ne [string]$pointer.generation_id) {
        [pscustomobject]@{
            Status = 'not-active'; GenerationId = $pointer.generation_id
            ActiveGenerationId = $state.generation_id; State = $statePath
        }
        return
    }
    $game = Resolve-WorkspaceInput ([string]$state.game_root) -RequireExisting
    $catalogTarget = Resolve-ChildPath $game ([string]$state.catalog_relative_path)
    if ($state.status -ne 'installing') {
        if ($state.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed') -or
            -not (Test-Path -LiteralPath $catalogTarget -PathType Leaf) -or
            (Get-FileSha256 $catalogTarget) -ne ([string]$state.catalog_sha256).ToUpperInvariant()) {
            throw 'Etat actif divergent avant restauration.'
        }
    }
    if ($VerifyOnly) {
        [pscustomobject]@{
            Status = 'verified'; GenerationId = $state.generation_id
            RuntimeMode = 'untouched'; State = $statePath
        }
        return
    }
    Assert-GameClosed
    Restore-CatalogInstallTransactionV2 $statePath $state
    [pscustomobject]@{
        Status = 'restored'; GenerationId = $state.generation_id
        RuntimeMode = 'untouched'; InertShardsKept = $true
    }
    return
} elseif ($state.schema -eq 'bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1') {
    $game = Resolve-WorkspaceInput ([string]$state.game_root) -RequireExisting
    $backupRoot = Resolve-WorkspaceInput ([string]$state.backup_root) -RequireExisting
    $previousState = Join-Path $backupRoot 'previous-active-test.json'
    if (-not $VerifyOnly) { Assert-GameClosed }
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
