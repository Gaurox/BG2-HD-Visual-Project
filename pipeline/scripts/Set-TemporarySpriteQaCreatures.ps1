[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Manifest,
    [Parameter(Mandatory = $true)]
    [string]$GameRoot,
    [ValidateSet('Install', 'Verify', 'Restore')]
    [string]$Action = 'Install'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Sha256([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Write-JsonAtomic($Value, [string]$Path) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $temporary = $Path + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    $replaceBackup = $temporary + '.replace-backup'
    try {
        [System.IO.File]::WriteAllText(
            $temporary,
            (($Value | ConvertTo-Json -Depth 12) + [Environment]::NewLine),
            (New-Object System.Text.UTF8Encoding($false)))
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            [System.IO.File]::Replace($temporary, $Path, $replaceBackup, $true)
        } else {
            [System.IO.File]::Move($temporary, $Path)
        }
    } finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) {
            Remove-Item -LiteralPath $temporary -Force
        }
        if (Test-Path -LiteralPath $replaceBackup -PathType Leaf) {
            Remove-Item -LiteralPath $replaceBackup -Force
        }
    }
}

function Copy-FileAtomic([string]$Source, [string]$Target, [string]$ExpectedSha256) {
    if ((Get-Sha256 $Source) -cne $ExpectedSha256) {
        throw "Source QA divergente : $Source"
    }
    $temporary = $Target + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    try {
        Copy-Item -LiteralPath $Source -Destination $temporary
        if ((Get-Sha256 $temporary) -cne $ExpectedSha256) {
            throw "Copie QA divergente : $Target"
        }
        [System.IO.File]::Move($temporary, $Target)
    } finally {
        if (Test-Path -LiteralPath $temporary -PathType Leaf) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path.TrimEnd('\')
$manifestPath = (Resolve-Path -LiteralPath $Manifest).Path
if (-not $manifestPath.StartsWith($workspace + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Manifest QA hors workspace.'
}
$game = (Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\')
$override = Join-Path $game 'override'
if (-not (Test-Path -LiteralPath $override -PathType Container)) {
    throw "Dossier override absent : $override"
}
if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count) {
    throw "Le jeu ou InfinityLoader est en cours d'execution."
}

$manifestValue = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ([string]$manifestValue.schema -cne 'bg2-upscale-temporary-sprite-qa-creatures-v1') {
    throw 'Manifest QA incompatible.'
}
$entries = @($manifestValue.entries)
if ($entries.Count -lt 1 -or $entries.Count -gt 256) { throw 'Nombre de CRE QA invalide.' }
$manifestRoot = Split-Path -Parent $manifestPath
$statePath = Join-Path $manifestRoot 'ingame-installation\active-test.json'
$targets = @()
$seen = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase)
foreach ($entry in $entries) {
    $resref = ([string]$entry.resref).ToUpperInvariant()
    if ($resref -notmatch '^[A-Z0-9_]{1,8}$' -or -not $seen.Add($resref)) {
        throw "Resref QA invalide ou dupliqué : $resref"
    }
    $sourceCandidate = [string]$entry.output
    $source = if ([System.IO.Path]::IsPathRooted($sourceCandidate)) {
        [System.IO.Path]::GetFullPath($sourceCandidate)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $workspace $sourceCandidate))
    }
    if (-not $source.StartsWith($workspace + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Source CRE QA absente ou hors workspace : $source"
    }
    $expected = ([string]$entry.output_sha256).ToUpperInvariant()
    if ($expected -notmatch '^[0-9A-F]{64}$' -or (Get-Sha256 $source) -cne $expected) {
        throw "Hash source CRE QA divergent : $resref"
    }
    $target = Join-Path $override ($resref + '.CRE')
    $targets += [pscustomobject]@{
        resref = $resref
        animation_id = [string]$entry.animation_id
        source = $source
        relative_path = 'override\' + $resref + '.CRE'
        target = $target
        sha256 = $expected
    }
}

$active = $null
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $active = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
}
if ($Action -eq 'Restore') {
    if ($null -eq $active -or [string]$active.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
        throw 'Aucune installation QA temporaire active à restaurer.'
    }
    foreach ($target in $targets) {
        if (-not (Test-Path -LiteralPath $target.target -PathType Leaf) -or
            (Get-Sha256 $target.target) -cne $target.sha256) {
            throw "CRE QA live absente ou altérée : $($target.resref)"
        }
    }
    if ($Action -eq 'Restore') {
        foreach ($target in $targets) { Remove-Item -LiteralPath $target.target -Force }
        $active.status = 'restored'
        $active | Add-Member -MemberType NoteProperty -Name restored_at_utc `
            -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
        Write-JsonAtomic $active $statePath
        [pscustomobject]@{ Status = 'restored'; Creatures = $targets.Count; State = $statePath }
        return
    }
}

if ($null -ne $active -and
    [string]$active.status -in @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
    foreach ($target in $targets) {
        if (-not (Test-Path -LiteralPath $target.target -PathType Leaf) -or
            (Get-Sha256 $target.target) -cne $target.sha256) {
            throw "Installation QA active divergente : $($target.resref)"
        }
    }
    [pscustomobject]@{ Status = if ($Action -eq 'Verify') { 'verified' } else { [string]$active.status }
        Mode = 'already-installed'; Creatures = $targets.Count; State = $statePath }
    return
}
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target.target) {
        throw "Collision CRE QA non propriétaire : $($target.relative_path)"
    }
}
if ($Action -eq 'Verify') {
    [pscustomobject]@{ Status = 'verified'; Mode = 'ready-to-install'; Creatures = $targets.Count
        State = $statePath }
    return
}

$transactionId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') +
    "-$PID-$([Guid]::NewGuid().ToString('N'))"
$state = [ordered]@{
    schema = 'bg2-upscale-temporary-sprite-qa-creatures-installation-v1'
    status = 'installing'
    transaction_id = $transactionId
    manifest = $manifestPath.Substring($workspace.Length + 1).Replace('\', '/')
    manifest_sha256 = Get-Sha256 $manifestPath
    game_root = $game
    installed_at_utc = $null
    targets = @($targets | ForEach-Object {
        [ordered]@{ resref = $_.resref; animation_id = $_.animation_id
            relative_path = $_.relative_path; sha256 = $_.sha256; existed_before = $false }
    })
}
Write-JsonAtomic $state $statePath
try {
    foreach ($target in $targets) {
        Copy-FileAtomic $target.source $target.target $target.sha256
    }
    $state.status = 'installed-pending-qa'
    $state.installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    Write-JsonAtomic $state $statePath
} catch {
    foreach ($target in $targets) {
        if ((Test-Path -LiteralPath $target.target -PathType Leaf) -and
            (Get-Sha256 $target.target) -ceq $target.sha256) {
            Remove-Item -LiteralPath $target.target -Force
        }
    }
    $state.status = 'rolled-back-after-install-error'
    $state | Add-Member -MemberType NoteProperty -Name error -Value $_.Exception.Message -Force
    Write-JsonAtomic $state $statePath
    throw
}
[pscustomobject]@{ Status = $state.status; Mode = 'installed'; Creatures = $targets.Count
    GameRoot = $game; State = $statePath }
