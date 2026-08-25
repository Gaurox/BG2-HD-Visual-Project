[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile,
    [switch]$RecoverInstalling
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path.TrimEnd('\')
$jobPath = (Resolve-Path -LiteralPath $JobFile).Path
$job = Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json
$jobSchema = [string]$job.schema
if ($jobSchema -notin @(
    'bg2-upscale-creature-sprite-xbr2x-job-v1',
    'bg2-upscale-creature-sprite-xbr2x-armor-set-v1'
)) {
    throw "Schéma de job non supporté : $jobSchema"
}
if ($null -eq $job.PSObject.Properties['upscale'] -or [int]$job.upscale.scale -notin @(2, 4)) {
    throw 'Le restore xN exige un job avec upscale.scale=2|4.'
}

function Resolve-JobPath([string]$Value) {
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $Value))
}

function Get-Sha256([string]$Path) {
    if ($null -ne (Get-Command Get-FileHash -ErrorAction SilentlyContinue)) {
        return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    }
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '')
        }
        finally { $sha.Dispose() }
    }
    finally { $stream.Dispose() }
}

if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw "Le jeu ou InfinityLoader est en cours d'exécution. Ferme-le avant la restauration."
}

$runRoot = Resolve-JobPath ([string]$job.paths.run_dir)
if (-not $runRoot.StartsWith($workspaceRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "job.paths.run_dir sort du workspace : $runRoot"
}
$stateFile = Join-Path $runRoot 'ingame-test\active-test.json'
if (-not (Test-Path -LiteralPath $stateFile -PathType Leaf)) {
    throw "État de test absent : $stateFile"
}
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
if ($state.schema -ne 'bg2-upscale-creature-sprite-xn-ingame-test-v1') {
    throw "Schéma d’état non supporté : $($state.schema)"
}
$recoveringInterruptedInstall = $state.status -eq 'installing'
if ($recoveringInterruptedInstall -and -not $RecoverInstalling) {
    throw 'État installing détecté : relance avec -RecoverInstalling après vérification du job.'
}
if (-not $recoveringInterruptedInstall -and
    $state.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
    throw "État non restaurable : $($state.status)"
}
if (-not [string]::Equals([string]$state.job_id, [string]$job.job_id,
        [System.StringComparison]::Ordinal)) {
    throw "Le job diffère de l'état actif."
}
if ([int]$state.registry_scale -ne [int]$job.upscale.scale -or
    [int]$state.registry_version -ne 3 -or $state.registry_magic -ne 'IEECSXN') {
    throw "Le contrat xN de l'état actif diffère du job."
}

$gameFull = (Resolve-Path -LiteralPath (Resolve-JobPath ([string]$job.paths.game_root))).Path.TrimEnd('\')
if (-not [string]::Equals([string]$state.game_root, $gameFull,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Le GameRoot diffère de l’état actif : $($state.game_root)"
}

function Assert-GameChildPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($gameFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors du dossier du jeu : $full"
    }
    return $full
}

$requiredTargets = @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.ini',
    'iee-assets\creature-sprites\CreatureSprites-XN.registry',
    'iee-assets\creature-sprites\CreatureSprites-X2.registry'
)
$stateTargets = @($state.targets)
if ($stateTargets.Count -ne $requiredTargets.Count) {
    throw 'La liste des cibles sauvegardées est incomplète.'
}
foreach ($required in $requiredTargets) {
    if (@($stateTargets | Where-Object {
        [string]::Equals([string]$_.relative_path, $required,
            [System.StringComparison]::OrdinalIgnoreCase)
    }).Count -ne 1) {
        throw "Cible sauvegardée absente ou dupliquée : $required"
    }
}

# Préflight complet : ne restaurer aucun fichier tant que toutes les cibles et
# toutes les sauvegardes n'ont pas été vérifiées.
foreach ($targetState in $stateTargets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
    if (-not $recoveringInterruptedInstall) {
        if ($null -eq $targetState.PSObject.Properties['installed_present']) {
            throw "installed_present absent : $($targetState.relative_path)"
        }
        $present = Test-Path -LiteralPath $target -PathType Leaf
        if ([bool]$targetState.installed_present -ne $present) {
            throw "Présence modifiée depuis l’installation : $($targetState.relative_path)"
        }
        if ($present) {
            if ($null -eq $targetState.installed_sha256 -or
                -not [string]::Equals((Get-Sha256 $target), [string]$targetState.installed_sha256,
                    [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Cible modifiée depuis l’installation : $($targetState.relative_path)"
            }
        }
    }
    if ([bool]$targetState.existed_before) {
        $backup = [string]$targetState.backup_path
        if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
            throw "Sauvegarde absente : $backup"
        }
        if (-not [string]::Equals((Get-Sha256 $backup), [string]$targetState.original_sha256,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Sauvegarde altérée : $backup"
        }
    }
}

foreach ($targetState in $stateTargets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
    if ([bool]$targetState.existed_before) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $targetState.backup_path -Destination $target -Force
    }
    elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
    }
}

foreach ($targetState in $stateTargets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
    if ([bool]$targetState.existed_before) {
        if (-not [string]::Equals((Get-Sha256 $target), [string]$targetState.original_sha256,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Restauration non fidèle : $($targetState.relative_path)"
        }
    }
    elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        throw "Le fichier ajouté subsiste : $($targetState.relative_path)"
    }
}

$state.status = 'restored'
$state | Add-Member -MemberType NoteProperty -Name recovered_interrupted_install `
    -Value ([bool]$recoveringInterruptedInstall) -Force
$state | Add-Member -MemberType NoteProperty -Name restored_at_utc `
    -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $stateFile -Encoding utf8
$backupStatePath = Join-Path ([string]$state.backup_root) 'install-state.json'
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $backupStatePath -Encoding utf8

[pscustomobject]@{
    Status = $state.status
    Scale = $state.registry_scale
    GameRoot = $gameFull
    Backup = $state.backup_root
    State = $stateFile
}
