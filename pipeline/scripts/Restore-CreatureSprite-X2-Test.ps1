[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile
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
    throw "Schéma de job non supporté : $($job.schema)"
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
        finally {
            $sha.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Enter-GameMutationMutex([string]$GameRoot) {
    $normalized = [System.IO.Path]::GetFullPath($GameRoot).TrimEnd('\').ToUpperInvariant()
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $key = ([System.BitConverter]::ToString(
            $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($normalized)))).Replace('-', '')
    }
    finally { $sha.Dispose() }
    $mutex = New-Object System.Threading.Mutex($false, "Global\BG2UpscaleCreatureSpriteMutation_$key")
    $owned = $false
    try { $owned = $mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $owned = $true }
    if (-not $owned) {
        $mutex.Dispose()
        throw "Une installation ou restauration sprite modifie déjà ce GameRoot : $GameRoot"
    }
    return $mutex
}

function Exit-GameMutationMutex($Mutex) {
    if ($null -eq $Mutex) { return }
    try { $Mutex.ReleaseMutex() }
    finally { $Mutex.Dispose() }
}

if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw "Le jeu ou InfinityLoader est en cours d'exécution. Ferme-le avant la restauration."
}

$runRoot = Resolve-JobPath $job.paths.run_dir
$gameFull = (Resolve-Path -LiteralPath (Resolve-JobPath $job.paths.game_root)).Path.TrimEnd('\')
$gameMutationMutex = Enter-GameMutationMutex $gameFull
try {
$stateFile = Join-Path $runRoot 'ingame-test\active-test.json'
if (-not (Test-Path -LiteralPath $stateFile -PathType Leaf)) {
    throw "État de test absent : $stateFile"
}
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
if ($state.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
    throw "État non restaurable : $($state.status)"
}

if (-not [string]::Equals([string]$state.game_root, $gameFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Le GameRoot diffère de l'état actif : $($state.game_root)"
}

function Assert-GameChildPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $gamePrefix = $gameFull + '\'
    if (-not $full.StartsWith($gamePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors du dossier du jeu : $full"
    }
    return $full
}

# Refuser d'écraser un fichier que le joueur ou un autre outil a modifié depuis
# l'installation de ce test.
foreach ($targetState in $state.targets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "Cible installée absente : $($targetState.relative_path)"
    }
    $installedHashProperty = $targetState.PSObject.Properties['installed_sha256']
    if ($null -ne $installedHashProperty -and $null -ne $installedHashProperty.Value -and
        (Get-Sha256 $target) -ne [string]$installedHashProperty.Value) {
        throw "Cible modifiée depuis l'installation : $($targetState.relative_path)"
    }
    if ($targetState.existed_before) {
        $backup = [string]$targetState.backup_path
        if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
            throw "Sauvegarde absente : $backup"
        }
        if ((Get-Sha256 $backup) -ne [string]$targetState.original_sha256) {
            throw "Sauvegarde altérée : $backup"
        }
    }
}

foreach ($targetState in $state.targets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
    if ($targetState.existed_before) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $targetState.backup_path -Destination $target -Force
    }
    elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        Remove-Item -LiteralPath $target -Force
    }
}

foreach ($targetState in $state.targets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
    if ($targetState.existed_before) {
        if ((Get-Sha256 $target) -ne [string]$targetState.original_sha256) {
            throw "Restauration non fidèle : $($targetState.relative_path)"
        }
    }
    elseif (Test-Path -LiteralPath $target -PathType Leaf) {
        throw "Le fichier ajouté subsiste : $($targetState.relative_path)"
    }
}

$state.status = 'restored'
$state | Add-Member -MemberType NoteProperty -Name restored_at_utc -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
$state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $stateFile -Encoding utf8
$backupStatePath = Join-Path ([string]$state.backup_root) 'install-state.json'
$state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $backupStatePath -Encoding utf8

$result = [pscustomobject]@{
    Status = $state.status
    GameRoot = $gameFull
    Backup = $state.backup_root
    State = $stateFile
}
$result
}
finally {
    Exit-GameMutationMutex $gameMutationMutex
}
