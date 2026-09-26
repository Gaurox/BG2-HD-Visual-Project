[CmdletBinding()]
param(
    [ValidateSet('Install', 'Restore')]
    [string]$Mode = 'Install',
    [ValidateSet('set-v1', 'catalog-v2')]
    [string]$PackVersion = 'catalog-v2'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$runRoot = Join-Path $workspace 'sprite\families\playable-characters\6110-human-female-fighter\family-runs\reboutcx-x4-visual-v1'
if ($PackVersion -eq 'catalog-v2') {
    $runRoot = Join-Path (Split-Path -Parent $runRoot) 'reboutcx-x4-visual-catalog-v2'
}
$manifestPath = Join-Path $runRoot 'manifest.json'
$statePath = Join-Path $runRoot 'ingame-installation\active-test.json'
$config = Get-Content -LiteralPath (Join-Path $workspace 'config\workspace-paths.local.json') -Raw | ConvertFrom-Json
$game = [IO.Path]::GetFullPath([string]$config.paths.bg2ee_game_root).TrimEnd('\')
$gameSprites = [IO.Path]::GetFullPath((Join-Path $game 'iee-assets\creature-sprites'))

function Hash([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Assert-GameChild([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($game + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors GameRoot : $full"
    }
    $full
}

function Write-State($Value) {
    $parent = Split-Path -Parent $statePath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = Join-Path $parent ('.state-' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllText(
            $temporary,
            (($Value | ConvertTo-Json -Depth 10) + [Environment]::NewLine),
            (New-Object Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $temporary -Destination $statePath -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Assert-Closed {
    $running = @(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue)
    if ($running.Count) {
        throw 'Ferme Baldur Gate II et InfinityLoader avant la bascule.'
    }
}

function Enter-Mutex {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $key = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($game.ToUpperInvariant())))).Replace('-', '')
    }
    finally { $sha.Dispose() }
    $mutex = New-Object Threading.Mutex($false, "Global\BG2UpscaleCreatureSpriteMutation_$key")
    try { $owned = $mutex.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $owned = $true }
    if (-not $owned) {
        $mutex.Dispose()
        throw 'Une autre installation sprite modifie déjà ce GameRoot.'
    }
    $mutex
}

function Leave-Mutex($Mutex) {
    if ($null -ne $Mutex) {
        try { $Mutex.ReleaseMutex() }
        finally { $Mutex.Dispose() }
    }
}

Assert-Closed
$mutex = Enter-Mutex
try {
    if ($Mode -eq 'Restore') {
        if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
            throw 'Aucun état x4 actif à restaurer.'
        }
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.status -ne 'installed-pending-qa') {
            throw "État x4 non restaurable : $($state.status)"
        }
        foreach ($installed in @($state.installed)) {
            $target = Assert-GameChild (Join-Path $game ([string]$installed.relative_path))
            if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
                (Hash $target) -ne [string]$installed.sha256) {
                throw "Payload x4 installé modifié : $($installed.relative_path)"
            }
        }
        foreach ($targetState in @($state.targets)) {
            if ([bool]$targetState.existed_before -and
                (Hash ([string]$targetState.backup_path)) -ne [string]$targetState.original_sha256) {
                throw "Backup modifie : $($targetState.relative_path)"
            }
        }
        foreach ($targetState in @($state.targets)) {
            $target = Assert-GameChild (Join-Path $game ([string]$targetState.relative_path))
            if (Test-Path -LiteralPath $target -PathType Leaf) {
                Remove-Item -LiteralPath $target -Force
            }
        }
        foreach ($targetState in @($state.targets)) {
            if ([bool]$targetState.existed_before) {
                $target = Assert-GameChild (Join-Path $game ([string]$targetState.relative_path))
                New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
                Copy-Item -LiteralPath ([string]$targetState.backup_path) -Destination $target -Force
                if ((Hash $target) -ne [string]$targetState.original_sha256) {
                    throw "Restauration non fidèle : $($targetState.relative_path)"
                }
            }
        }
        $state.status = 'restored-to-previous-x2'
        $state | Add-Member -NotePropertyName restored_at_utc -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
        Write-State $state
        [pscustomobject]@{
            status = $state.status
            restored_catalog_sha256 = (Hash (Join-Path $gameSprites 'CreatureSprites-XN.catalog'))
            state = $statePath
        } | ConvertTo-Json
        return
    }

    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw 'Manifest x4 absent.'
    }
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        $previous = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($previous.status -eq 'installed-pending-qa') {
            throw 'Le test x4 est déjà installé.'
        }
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema -notin @('bg2-upscale-reboutcx-x4-visual-pack-v1', 'bg2-upscale-reboutcx-x4-visual-catalog-v2') -or
        [int]$manifest.target_scale -ne 4 -or $manifest.animation_id -ne '0x6110' -or
        $manifest.registry_layout -notin @('set', 'catalog')) {
        throw 'Contrat du pack x4 incompatible.'
    }
    $buildRoot = Join-Path $runRoot 'build'
    $isCatalog = $manifest.registry_layout -eq 'catalog'
    $indexRelative = if ($isCatalog) { [string]$manifest.registry_catalog } else { [string]$manifest.registry_set }
    $indexHash = if ($isCatalog) { [string]$manifest.registry_catalog_sha256 } else { [string]$manifest.registry_set_sha256 }
    $sourceSet = Join-Path $buildRoot $indexRelative
    if ((Hash $sourceSet) -ne $indexHash) {
        throw 'Hash du set x4 incompatible.'
    }
    $sources = @()
    foreach ($shard in @($manifest.shards)) {
        $source = Join-Path $buildRoot ([string]$shard.path)
        if ((Hash $source) -ne [string]$shard.sha256) {
            throw "Hash shard x4 incompatible : $($shard.path)"
        }
        $sources += [pscustomobject]@{
            relative_path = "iee-assets\creature-sprites\$([IO.Path]::GetFileName($source))"
            source = $source
            sha256 = [string]$shard.sha256
        }
    }
    $sources += [pscustomobject]@{
        relative_path = $indexRelative.Replace('/', '\')
        source = $sourceSet
        sha256 = $indexHash
    }

    $relativeTargets = [Collections.Generic.List[string]]::new()
    foreach ($relative in @(
        'iee-assets\creature-sprites\CreatureSprites-XN.catalog',
        'iee-assets\creature-sprites\CreatureSprites-XN.set',
        'iee-assets\creature-sprites\CreatureSprites-XN.registry',
        'iee-assets\creature-sprites\CreatureSprites-X2.registry'
    )) { [void]$relativeTargets.Add($relative) }
    if (Test-Path -LiteralPath $gameSprites -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $gameSprites -File) {
            if ($file.Name -match '^CreatureSprites-XN-[0-9]{4}\.registry$') {
                [void]$relativeTargets.Add("iee-assets\creature-sprites\$($file.Name)")
            }
        }
    }
    foreach ($source in $sources) { [void]$relativeTargets.Add([string]$source.relative_path) }
    $relativeTargets = @($relativeTargets | Sort-Object -Unique)

    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') + "-$PID"
    $backupRoot = Join-Path $runRoot "ingame-installation\backups\$stamp"
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $targets = @()
    foreach ($relative in $relativeTargets) {
        $target = Assert-GameChild (Join-Path $game $relative)
        $exists = Test-Path -LiteralPath $target -PathType Leaf
        $backup = $null
        $original = $null
        if ($exists) {
            $backup = Join-Path $backupRoot $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $backup -Force
            $original = Hash $target
            if ((Hash $backup) -ne $original) { throw "Backup non fidèle : $relative" }
        }
        $targets += [ordered]@{
            relative_path = $relative
            existed_before = $exists
            original_sha256 = $original
            backup_path = $backup
        }
    }
    $dllPath = Join-Path $game 'InfinityEngine-Enhancer.dll'
    $state = [ordered]@{
        schema = 'bg2-upscale-reboutcx-x4-visual-install-v1'
        status = 'installing'
        installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        game_root = $game
        manifest = $manifestPath
        manifest_sha256 = Hash $manifestPath
        target_scale = 4
        animation_id = '0x6110'
        previous_catalog_sha256 = Hash (Join-Path $gameSprites 'CreatureSprites-XN.catalog')
        runtime_dll_sha256 = Hash $dllPath
        runtime_dll_mutated = $false
        backup_root = $backupRoot
        targets = $targets
        installed = @()
    }
    Write-State $state

    try {
    foreach ($targetState in $targets) {
        $target = Assert-GameChild (Join-Path $game ([string]$targetState.relative_path))
        if (Test-Path -LiteralPath $target -PathType Leaf) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    $installed = @()
    foreach ($source in $sources | Where-Object { $_.relative_path -like '*.registry' }) {
        $target = Assert-GameChild (Join-Path $game ([string]$source.relative_path))
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath ([string]$source.source) -Destination $target -Force
        if ((Hash $target) -ne [string]$source.sha256) { throw "Copie x4 non fidèle : $($source.relative_path)" }
        $installed += [ordered]@{ relative_path = $source.relative_path; sha256 = $source.sha256 }
    }
    $setSource = $sources | Where-Object { $_.relative_path -notlike '*.registry' }
    $setTarget = Assert-GameChild (Join-Path $game ([string]$setSource.relative_path))
    Copy-Item -LiteralPath ([string]$setSource.source) -Destination $setTarget -Force
    if ((Hash $setTarget) -ne [string]$setSource.sha256) { throw 'Copie index x4 non fidele.' }
    $installed += [ordered]@{ relative_path = $setSource.relative_path; sha256 = $setSource.sha256 }
    if (-not $isCatalog -and (Test-Path -LiteralPath (Join-Path $gameSprites 'CreatureSprites-XN.catalog') -PathType Leaf)) {
        throw 'Le catalogue x2 masque encore le set x4.'
    }
    if ((Hash $dllPath) -ne [string]$state.runtime_dll_sha256) {
        throw 'Le DLL runtime a change pendant installation.'
    }
    $state.installed = $installed
    $state.status = 'installed-pending-qa'
    Write-State $state
    }
    catch {
        $installFailure = $_
        foreach ($targetState in $targets) {
            $target = Assert-GameChild (Join-Path $game ([string]$targetState.relative_path))
            if ([bool]$targetState.existed_before) {
                Copy-Item -LiteralPath ([string]$targetState.backup_path) -Destination $target -Force
                if ((Hash $target) -ne [string]$targetState.original_sha256) { throw 'Rollback hash mismatch.' }
            }
            elseif (Test-Path -LiteralPath $target -PathType Leaf) {
                Remove-Item -LiteralPath $target -Force
            }
        }
        $state.status = 'installation-failed-rolled-back'
        Write-State $state
        throw $installFailure
    }
    [pscustomobject]@{
        status = $state.status
        scale = 4
        animation_id = '0x6110'
        resources = [int]$manifest.coverage.resources
        frames = [int]$manifest.coverage.frames
        shards = @($manifest.shards).Count
        registry_bytes = [int64]$manifest.totals.registry_bytes
        previous_x2_catalog_sha256 = $state.previous_catalog_sha256
        runtime_dll_sha256 = $state.runtime_dll_sha256
        restore_command = "& '$PSCommandPath' -Mode Restore"
        state = $statePath
    } | ConvertTo-Json
}
finally {
    Leave-Mutex $mutex
}
