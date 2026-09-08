[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$GameRoot,
    [Parameter(Mandatory = $true)][string]$Dll,
    [string]$RuntimeBatch = 'icons/batches/item-inventory-xbr2x-aa-runtime-v3'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path.TrimEnd('\')

function Resolve-WorkspacePath([string]$Value) {
    if ([System.IO.Path]::IsPathRooted($Value)) { return [System.IO.Path]::GetFullPath($Value) }
    return [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $Value))
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Assert-GameChildPath([string]$Path, [string]$Root) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($Root + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors du dossier du jeu : $full"
    }
    return $full
}

function Set-IniBoolean([string[]]$Lines, [string]$Section, [string]$Key, [bool]$Value) {
    $rendered = if ($Value) { 'true' } else { 'false' }
    $sectionStart = -1
    $sectionEnd = $Lines.Count
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^\s*\[(.+)\]\s*$') {
            if ($sectionStart -ge 0) { $sectionEnd = $i; break }
            if ([string]::Equals($Matches[1].Trim(), $Section, [System.StringComparison]::OrdinalIgnoreCase)) {
                $sectionStart = $i
            }
        }
    }
    $list = [System.Collections.Generic.List[string]]::new()
    $list.AddRange([string[]]$Lines)
    if ($sectionStart -lt 0) {
        if ($list.Count -gt 0 -and $list[$list.Count - 1] -ne '') { $list.Add('') }
        $list.Add("[$Section]")
        $list.Add("$Key = $rendered")
        return $list.ToArray()
    }
    for ($i = $sectionStart + 1; $i -lt $sectionEnd; $i++) {
        if ($list[$i] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) {
            $list[$i] = "$Key = $rendered"
            return $list.ToArray()
        }
    }
    $list.Insert($sectionEnd, "$Key = $rendered")
    return $list.ToArray()
}

$gameFull = (Resolve-Path -LiteralPath (Resolve-WorkspacePath $GameRoot)).Path.TrimEnd('\')
$dllFull = (Resolve-Path -LiteralPath (Resolve-WorkspacePath $Dll)).Path
$runRoot = (Resolve-Path -LiteralPath (Resolve-WorkspacePath $RuntimeBatch)).Path
$manifestPath = Join-Path $runRoot 'build-manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'bg2-upscale-item-icon-x2-runtime-pack-v2' -or
    [int]$manifest.scale -ne 2 -or [int]$manifest.asset_count -ne 1484 -or
    [int]$manifest.frame_count -ne 1917 -or [int]$manifest.mapping_count -ne 1922) {
    throw 'Manifeste runtime des icônes non supporté ou incomplet.'
}
$pack = Join-Path $runRoot ([string]$manifest.registry)
if ((Get-Sha256 $pack) -ne [string]$manifest.registry_sha256) {
    throw 'Le registre runtime diffère de son manifeste scellé.'
}
if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw 'Le jeu ou InfinityLoader est actif. Ferme-le avant installation.'
}
$exe = Join-Path $gameFull 'BaldurReal.exe'
$supportedExe = 'B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57'
if ((Get-Sha256 $exe) -ne $supportedExe) { throw 'BaldurReal.exe ne correspond pas à BG2EE 2.7.3 supporté.' }

$activeState = Join-Path $runRoot 'ingame-test\active-test.json'
if (Test-Path -LiteralPath $activeState -PathType Leaf) {
    $previous = Get-Content -LiteralPath $activeState -Raw | ConvertFrom-Json
    if ($previous.status -in @('installing', 'installed-pending-qa', 'validated-installed', 'qa-failed')) {
        throw "Un test icones est deja actif : $($previous.status)"
    }
}

$mutexKey = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
    [Text.Encoding]::UTF8.GetBytes($gameFull.ToUpperInvariant())))
$mutex = [Threading.Mutex]::new($false, "Global\BG2UpscaleGameMutation_$mutexKey")
$owned = $false
try {
    try { $owned = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $owned = $true }
    if (-not $owned) { throw 'Une autre installation modifie déjà ce dossier de jeu.' }

    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') + "-$PID"
    $backupRoot = Join-Path $runRoot "ingame-test\backups\$stamp"
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $relativeTargets = @(
        'InfinityEngine-Enhancer.dll',
        'InfinityEngine-Enhancer.ini',
        'iee-assets\icons\ItemIcons-X2.registry'
    )
    $targets = @()
    foreach ($relative in $relativeTargets) {
        $target = Assert-GameChildPath (Join-Path $gameFull $relative) $gameFull
        $existed = Test-Path -LiteralPath $target -PathType Leaf
        $backup = $null
        $originalHash = $null
        if ($existed) {
            $backup = Join-Path $backupRoot $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $backup -Force
            $originalHash = Get-Sha256 $target
            if ((Get-Sha256 $backup) -ne $originalHash) { throw "Sauvegarde non fidèle : $relative" }
        }
        $targets += [ordered]@{
            relative_path = $relative
            existed_before = $existed
            original_sha256 = $originalHash
            backup_path = $backup
            installed_sha256 = $null
        }
    }

    $state = [ordered]@{
        schema = 'bg2-upscale-item-icon-x2-ingame-test-v2'
        status = 'installing'
        installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        game_root = $gameFull
        baldureal_sha256 = $supportedExe
        source_run = [string]$manifest.source_run
        runtime_run = [string]$manifest.output_run
        method = [string]$manifest.method
        assets = [int]$manifest.asset_count
        frames = [int]$manifest.frame_count
        mappings = [int]$manifest.mapping_count
        source_dll_sha256 = Get-Sha256 $dllFull
        source_pack_sha256 = [string]$manifest.registry_sha256
        backup_root = $backupRoot
        targets = $targets
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $activeState) -Force | Out-Null
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $activeState -Encoding utf8

    try {
        Copy-Item -LiteralPath $dllFull -Destination (Join-Path $gameFull 'InfinityEngine-Enhancer.dll') -Force
        $packTarget = Join-Path $gameFull 'iee-assets\icons\ItemIcons-X2.registry'
        New-Item -ItemType Directory -Path (Split-Path -Parent $packTarget) -Force | Out-Null
        Copy-Item -LiteralPath $pack -Destination $packTarget -Force

        $iniTarget = Join-Path $gameFull 'InfinityEngine-Enhancer.ini'
        if (Test-Path -LiteralPath $iniTarget -PathType Leaf) {
            [string[]]$iniLines = Get-Content -LiteralPath $iniTarget
        } else {
            [string[]]$iniLines = Get-Content -LiteralPath (Join-Path $workspaceRoot 'engine\InfinityEngine-Enhancer\source-patchee\tools\InfinityEngine-Enhancer.sample.ini')
        }
        $iniLines = Set-IniBoolean $iniLines 'Shaders' 'EnableAM0205EAnimationX4Test' $false
        $iniLines = Set-IniBoolean $iniLines 'Shaders' 'EnableItemIconX2' $true
        Set-Content -LiteralPath $iniTarget -Value $iniLines -Encoding utf8

        foreach ($targetState in $state.targets) {
            $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path) $gameFull
            if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Cible installée absente : $($targetState.relative_path)" }
            $targetState.installed_sha256 = Get-Sha256 $target
        }
        if ((Get-Sha256 $packTarget) -ne [string]$manifest.registry_sha256) { throw 'Copie du registre non fidèle.' }
        $state.status = 'installed-pending-qa'
        $state | Add-Member -MemberType NoteProperty -Name receipt -Value ((Join-Path $runRoot 'ingame-test\install-receipt.json')) -Force
        $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $activeState -Encoding utf8
        $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $state.receipt -Encoding utf8
    } catch {
        foreach ($targetState in $state.targets) {
            $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path) $gameFull
            if ($targetState.existed_before) {
                New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
                Copy-Item -LiteralPath $targetState.backup_path -Destination $target -Force
            } elseif (Test-Path -LiteralPath $target -PathType Leaf) {
                Remove-Item -LiteralPath $target -Force
            }
        }
        $state.status = 'install-failed-restored'
        $state | Add-Member -MemberType NoteProperty -Name error -Value $_.Exception.Message -Force
        $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $activeState -Encoding utf8
        throw
    }

    [pscustomobject]@{ Status = $state.status; GameRoot = $gameFull; State = $activeState; Receipt = $state.receipt }
} finally {
    if ($owned) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
