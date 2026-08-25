param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile,
    [switch]$RecoverInterrupted,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($VerifyOnly -and $RecoverInterrupted) {
    throw '-VerifyOnly et -RecoverInterrupted sont incompatibles.'
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Write-JsonAtomic($Value, [string]$Path) {
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $temporary = Join-Path $directory ('.' + [IO.Path]::GetFileName($Path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Resolve-ProjectPath([string]$Value, [string]$ProjectRoot) {
    if ([IO.Path]::IsPathRooted($Value)) { return [IO.Path]::GetFullPath($Value) }
    return [IO.Path]::GetFullPath((Join-Path $ProjectRoot $Value))
}

function Assert-GameChild([string]$GameRoot, [string]$RelativePath) {
    if ([IO.Path]::IsPathRooted($RelativePath)) { throw "Cible x4 absolue interdite : $RelativePath" }
    $full = [IO.Path]::GetFullPath((Join-Path $GameRoot $RelativePath))
    if (-not $full.StartsWith($GameRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible x4 hors du jeu : $full"
    }
    return $full
}

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$jobFull = [IO.Path]::GetFullPath($JobFile)
$job = Get-Content -LiteralPath $jobFull -Raw | ConvertFrom-Json
if ($job.schema -ne 'bg2-upscale-creature-sprite-xbr2x-job-v1' -or
    $job.job_id -ne 'dwarf-male-fighter-cdmb1-xbr4x' -or
    [int]$job.upscale.scale -ne 4 -or [string]$job.upscale.algorithm -ne 'XBR/xbr4X' -or
    [bool]$job.upscale.antialias -or [bool]$job.upscale.xbr_blend) {
    throw 'Job x4 CDMB1 inattendu.'
}
$gameRoot = [IO.Path]::GetFullPath([string]$job.paths.game_root).TrimEnd('\')
$runRoot = Resolve-ProjectPath ([string]$job.paths.run_dir) $projectRoot
$statePath = Join-Path $runRoot 'ingame-test\active-test.json'
if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { throw 'Aucun état x4 actif à restaurer.' }
if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw 'Le jeu ou InfinityLoader est actif. Ferme-le avant la restauration x4.'
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.schema -ne 'bg2-upscale-creature-sprite-x4-variant-test-v1' -or
    $state.job_id -ne $job.job_id -or
    -not [string]::Equals([string]$state.game_root, $gameRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'État x4 incompatible avec le job ou le jeu.'
}
$interrupted = $state.status -in @('installing', 'restoring')
if ($interrupted -and -not $RecoverInterrupted) {
    throw "Transaction x4 interrompue ($($state.status)); relance avec -RecoverInterrupted."
}
if (-not $interrupted -and $state.status -notin @('installed-pending-qa', 'qa-failed')) {
    throw "État x4 non restaurable : $($state.status)"
}
$backupRoot = [IO.Path]::GetFullPath([string]$state.backup_root).TrimEnd('\')
$backupBase = [IO.Path]::GetFullPath((Join-Path $runRoot 'ingame-test\backups')).TrimEnd('\') + '\'
if (-not ($backupRoot + '\').StartsWith($backupBase, [StringComparison]::OrdinalIgnoreCase)) {
    throw "backup_root x4 hors du job : $backupRoot"
}
$backupStatePath = Join-Path $backupRoot 'install-state.json'
if (-not (Test-Path -LiteralPath $backupStatePath -PathType Leaf)) { throw 'État de sauvegarde x4 absent.' }
$targets = @($state.targets)
if ($targets.Count -lt 5 -or $targets.Count -gt 69) { throw 'Liste de cibles x4 hors contrat.' }
$seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($targetState in $targets) {
    $relative = ([string]$targetState.relative_path).Replace('/', '\')
    $allowed = $relative -in @(
        'InfinityEngine-Enhancer.dll',
        'InfinityEngine-Enhancer.ini',
        'iee-assets\creature-sprites\CreatureSprites-X2.registry',
        'iee-assets\creature-sprites\CreatureSprites-XN.registry',
        'iee-assets\creature-sprites\CreatureSprites-XN.set'
    ) -or $relative -match '^iee-assets\\creature-sprites\\CreatureSprites-XN-[0-9]{4}\.registry$'
    if (-not $allowed -or -not $seen.Add($relative)) { throw "Cible x4 invalide : $relative" }
    $target = Assert-GameChild $gameRoot $relative
    if (-not $interrupted) {
        $present = Test-Path -LiteralPath $target -PathType Leaf
        if ([bool]$targetState.installed_present -ne $present) {
            throw "Présence modifiée depuis le test x4 : $relative"
        }
        if ($present -and (Get-Sha256 $target) -ne [string]$targetState.installed_sha256) {
            throw "Cible modifiée depuis le test x4 : $relative"
        }
    }
    if ([bool]$targetState.existed_before) {
        $backup = [IO.Path]::GetFullPath([string]$targetState.backup_path)
        $expected = [IO.Path]::GetFullPath((Join-Path $backupRoot $relative))
        if (-not [string]::Equals($backup, $expected, [StringComparison]::OrdinalIgnoreCase) -or
            -not (Test-Path -LiteralPath $backup -PathType Leaf) -or
            (Get-Sha256 $backup) -ne [string]$targetState.original_sha256) {
            throw "Sauvegarde x4 absente ou altérée : $relative"
        }
    }
}

if ($VerifyOnly) {
    [pscustomobject]@{
        Status = 'restore-preflight-verified'
        Job = $state.job_id
        ActiveStateUnchanged = $true
        VerifiedTargets = $targets.Count
        Backup = $backupRoot
    } | ConvertTo-Json
    exit 0
}

$state.status = 'restoring'
$state | Add-Member -NotePropertyName 'restore_started_at_utc' `
    -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
Write-JsonAtomic $state $statePath
Write-JsonAtomic $state $backupStatePath

foreach ($targetState in $targets) {
    $target = Assert-GameChild $gameRoot ([string]$targetState.relative_path)
    if ([bool]$targetState.existed_before) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath ([string]$targetState.backup_path) -Destination $target -Force
    }
    elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
    }
}
foreach ($targetState in $targets) {
    $target = Assert-GameChild $gameRoot ([string]$targetState.relative_path)
    if ([bool]$targetState.existed_before) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
            (Get-Sha256 $target) -ne [string]$targetState.original_sha256) {
            throw "Restauration x4 non fidèle : $($targetState.relative_path)"
        }
    }
    elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        throw "Fichier x4 ajouté encore présent : $($targetState.relative_path)"
    }
}
$state.status = 'restored'
$state | Add-Member -NotePropertyName 'recovered_interrupted_transaction' `
    -NotePropertyValue ([bool]$interrupted) -Force
$state | Add-Member -NotePropertyName 'restored_at_utc' `
    -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
Write-JsonAtomic $state $statePath
Write-JsonAtomic $state $backupStatePath

[pscustomobject]@{
    Status = $state.status
    Job = $state.job_id
    RestoredParentTests = @($state.parent_active_tests).Count
    Backup = $backupRoot
} | ConvertTo-Json
