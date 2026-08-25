[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile,
    [Alias('RecoverInterrupted')]
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

function Write-JsonAtomic($Value, [string]$Path, [int]$Depth = 8) {
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Path))
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Dossier d'état absent : $parent"
    }
    $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Path) +
        '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $replaceBackup = $temporary + '.replace-backup'
    try {
        $json = ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine
        [System.IO.File]::WriteAllText(
            $temporary, $json, (New-Object System.Text.UTF8Encoding($false)))
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            [System.IO.File]::Replace($temporary, $Path, $replaceBackup, $true)
        }
        else {
            [System.IO.File]::Move($temporary, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) {
            Remove-Item -LiteralPath $temporary -Force
        }
        if (Test-Path -LiteralPath $replaceBackup -PathType Leaf) {
            Remove-Item -LiteralPath $replaceBackup -Force
        }
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

$runRoot = Resolve-JobPath ([string]$job.paths.run_dir)
if (-not $runRoot.StartsWith($workspaceRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "job.paths.run_dir sort du workspace : $runRoot"
}
$gameFull = (Resolve-Path -LiteralPath (Resolve-JobPath ([string]$job.paths.game_root))).Path.TrimEnd('\')
$gameMutationMutex = Enter-GameMutationMutex $gameFull
try {
$stateFile = Join-Path $runRoot 'ingame-test\active-test.json'
if (-not (Test-Path -LiteralPath $stateFile -PathType Leaf)) {
    throw "État de test absent : $stateFile"
}
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
if ($state.schema -notin @(
        'bg2-upscale-creature-sprite-xn-ingame-test-v1',
        'bg2-upscale-creature-sprite-xn-ingame-test-v2'
    )) {
    throw "Schéma d’état non supporté : $($state.schema)"
}
$recoveringInterruptedInstall = $state.status -in @('installing', 'restoring')
if ($recoveringInterruptedInstall -and -not $RecoverInstalling) {
    throw "État $($state.status) détecté : relance avec -RecoverInstalling après vérification du job."
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
if ($state.schema -eq 'bg2-upscale-creature-sprite-xn-ingame-test-v2') {
    if ($state.registry_layout -notin @('monolith', 'set')) {
        throw "Layout xN de l'état actif invalide : $($state.registry_layout)"
    }
    if ($state.registry_layout -eq 'set' -and
        ($state.registry_set_magic -ne 'IEECSNS' -or [int]$state.registry_set_version -ne 1 -or
         [int]$state.registry_shard_count -lt 1 -or [int]$state.registry_shard_count -gt 64)) {
        throw "Contrat de registry-set invalide dans l'état actif."
    }
}

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
$isDynamicState = $state.schema -eq 'bg2-upscale-creature-sprite-xn-ingame-test-v2'
if ($isDynamicState) {
    $requiredTargets += 'iee-assets\creature-sprites\CreatureSprites-XN.set'
}
$stateTargets = @($state.targets)
if ($stateTargets.Count -lt $requiredTargets.Count -or $stateTargets.Count -gt 69) {
    throw 'La liste des cibles sauvegardées est hors contrat.'
}
$seenTargets = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase)
foreach ($targetState in $stateTargets) {
    if ($null -eq $targetState.PSObject.Properties['relative_path']) {
        throw 'Une cible sauvegardée ne contient pas relative_path.'
    }
    $relative = ([string]$targetState.relative_path).Replace('/', '\')
    if ([string]::IsNullOrWhiteSpace($relative) -or
        [System.IO.Path]::IsPathRooted($relative) -or
        -not $seenTargets.Add($relative)) {
        throw "Cible sauvegardée invalide ou dupliquée : $relative"
    }
    $isCoreTarget = @($requiredTargets | Where-Object {
        [string]::Equals($_, $relative, [System.StringComparison]::OrdinalIgnoreCase)
    }).Count -eq 1
    $isShardTarget = $relative -match '^iee-assets\\creature-sprites\\CreatureSprites-XN-[0-9]{4}\.registry$'
    if (-not $isCoreTarget -and (-not $isDynamicState -or -not $isShardTarget)) {
        throw "Cible sauvegardée hors namespace autorisé : $relative"
    }
    [void](Assert-GameChildPath (Join-Path $gameFull $relative))
}
foreach ($required in $requiredTargets) {
    if (@($stateTargets | Where-Object {
        [string]::Equals([string]$_.relative_path, $required,
            [System.StringComparison]::OrdinalIgnoreCase)
    }).Count -ne 1) {
        throw "Cible sauvegardée absente ou dupliquée : $required"
    }
}

if ($isDynamicState) {
    $stateRegistryRelative = ([string]$state.registry_relative_path).Replace('/', '\')
    $expectedRegistryRelative = if ($state.registry_layout -eq 'set') {
        'iee-assets\creature-sprites\CreatureSprites-XN.set'
    } else {
        'iee-assets\creature-sprites\CreatureSprites-XN.registry'
    }
    if (-not [string]::Equals($stateRegistryRelative, $expectedRegistryRelative,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "La cible principale du layout diffère de l'état actif."
    }
    $stateSourceShards = @($state.source_shards)
    $expectedSourceShardCount = if ($state.registry_layout -eq 'set') {
        [int]$state.registry_shard_count
    } else {
        0
    }
    if ($stateSourceShards.Count -ne $expectedSourceShardCount) {
        throw 'La liste source des shards diffère du layout actif.'
    }
    for ($index = 0; $index -lt $stateSourceShards.Count; $index++) {
        $sourceShard = $stateSourceShards[$index]
        $expectedRelative = 'iee-assets\creature-sprites\CreatureSprites-XN-{0:D4}.registry' -f $index
        if ([int]$sourceShard.index -ne $index -or
            -not [string]::Equals([string]$sourceShard.relative_path, $expectedRelative,
                [System.StringComparison]::OrdinalIgnoreCase) -or
            [string]$sourceShard.sha256 -notmatch '^[0-9A-Fa-f]{64}$' -or
            [uint64]$sourceShard.crc32 -gt [uint64][uint32]::MaxValue -or
            -not $seenTargets.Contains($expectedRelative)) {
            throw "Métadonnées source invalides pour le shard $index."
        }
    }
}
else {
    $untrackedSet = Assert-GameChildPath (Join-Path $gameFull 'iee-assets\creature-sprites\CreatureSprites-XN.set')
    if (Test-Path -LiteralPath $untrackedSet -PathType Leaf) {
        throw "Un registry-set absent de l'ancien état v1 est présent ; restaurer son état propriétaire."
    }
}

$backupBase = [System.IO.Path]::GetFullPath((Join-Path $runRoot 'ingame-test\backups')).TrimEnd('\')
$backupRoot = [System.IO.Path]::GetFullPath([string]$state.backup_root).TrimEnd('\')
if (-not $backupRoot.StartsWith($backupBase + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "backup_root sort du dossier de backups du job : $backupRoot"
}
$backupStatePath = Join-Path $backupRoot 'install-state.json'

# Refuser une apparition externe dans le namespace des shards : elle ne doit ni
# être supprimée silencieusement, ni survivre comme shard actif après rollback.
$gameSpriteRoot = Assert-GameChildPath (Join-Path $gameFull 'iee-assets\creature-sprites')
if (Test-Path -LiteralPath $gameSpriteRoot -PathType Container) {
    foreach ($existingShard in Get-ChildItem -LiteralPath $gameSpriteRoot -File -ErrorAction Stop) {
        if ($existingShard.Name -notmatch '^CreatureSprites-XN-[0-9]{4}\.registry$') { continue }
        $relative = "iee-assets\creature-sprites\$($existingShard.Name)"
        if (-not $seenTargets.Contains($relative)) {
            throw "Shard apparu depuis l'installation et absent de l'état : $relative"
        }
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
        $expectedBackup = [System.IO.Path]::GetFullPath((Join-Path $backupRoot $targetState.relative_path))
        if (-not [string]::Equals([System.IO.Path]::GetFullPath($backup), $expectedBackup,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Chemin de sauvegarde incompatible : $backup"
        }
        if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
            throw "Sauvegarde absente : $backup"
        }
        if (-not [string]::Equals((Get-Sha256 $backup), [string]$targetState.original_sha256,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Sauvegarde altérée : $backup"
        }
    }
    elseif ($null -ne $targetState.backup_path -or $null -ne $targetState.original_sha256) {
        throw "Métadonnées de sauvegarde inattendues : $($targetState.relative_path)"
    }
}

# Publier un état récupérable avant la première mutation de restauration. Une
# interruption laisse toutes les sauvegardes intactes et peut être reprise avec
# -RecoverInstalling (alias -RecoverInterrupted).
$state.status = 'restoring'
$state | Add-Member -MemberType NoteProperty -Name restore_started_at_utc `
    -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
Write-JsonAtomic $state $stateFile 8
Write-JsonAtomic $state $backupStatePath 8

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
Write-JsonAtomic $state $backupStatePath 8
Write-JsonAtomic $state $stateFile 8

$result = [pscustomobject]@{
    Status = $state.status
    Scale = $state.registry_scale
    GameRoot = $gameFull
    Backup = $state.backup_root
    State = $stateFile
}
$result
}
finally {
    Exit-GameMutationMutex $gameMutationMutex
}
