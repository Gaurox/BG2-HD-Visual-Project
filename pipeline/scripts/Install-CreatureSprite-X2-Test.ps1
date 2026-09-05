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
$isArmorSet = $jobSchema -eq 'bg2-upscale-creature-sprite-xbr2x-armor-set-v1'
if ($jobSchema -notin @(
    'bg2-upscale-creature-sprite-xbr2x-job-v1',
    'bg2-upscale-creature-sprite-xbr2x-armor-set-v1'
)) {
    throw "Schéma de job non supporté : $($job.schema)"
}
$supportedRuntimeProfiles = @(
    'monster-icewind-bg2ee-2.7.3.0',
    'character-bg2ee-2.7.3.0'
)
if ($job.animation.runtime_profile -notin $supportedRuntimeProfiles) {
    throw "unsupported-runtime-profile : $($job.animation.runtime_profile)"
}
if ($isArmorSet -and $job.animation.runtime_profile -ne 'character-bg2ee-2.7.3.0') {
    throw 'Un set armor requires the Character profile.'
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

function Assert-ExpectedHash([string]$Path, [string]$Expected, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label absent : $Path"
    }
    $actual = Get-Sha256 $Path
    if ($actual -ne $Expected) {
        throw "$Label incompatible : SHA-256 $actual, attendu $Expected"
    }
}

$gameFull = (Resolve-Path -LiteralPath (Resolve-JobPath $job.paths.game_root)).Path.TrimEnd('\')
$gameMutationMutex = Enter-GameMutationMutex $gameFull
try {
$runRoot = Resolve-JobPath $job.paths.run_dir
$buildRoot = Join-Path $runRoot 'build'
$runtimeRoot = Join-Path $runRoot 'runtime'
$buildManifestPath = Join-Path $buildRoot 'build-manifest.json'
$runtimeManifestPath = Join-Path $runtimeRoot 'runtime-manifest.json'
$buildManifest = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
$runtimeManifest = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json
if ($buildManifest.schema -notin @(
    'bg2-upscale-creature-sprite-xbr2x-pack-v1',
    'bg2-upscale-creature-sprite-xbr2x-armor-set-pack-v1'
)) {
    throw 'Manifeste de build sprite non supporté.'
}
if ($isArmorSet -and $buildManifest.schema -ne 'bg2-upscale-creature-sprite-xbr2x-armor-set-pack-v1') {
    throw 'Armor set requires an aggregate build manifest.'
}
if (-not $isArmorSet -and $buildManifest.schema -ne 'bg2-upscale-creature-sprite-xbr2x-pack-v1') {
    throw 'Le job sprite exige un manifeste de build individuel.'
}
if ($runtimeManifest.schema -ne 'bg2-upscale-creature-sprite-runtime-v1' -or
    $runtimeManifest.tests_status -ne 'passed') {
    throw 'Runtime non construit ou tests natifs absents.'
}

$sourcePack = Join-Path $buildRoot ([string]$buildManifest.registry)
$sourceDll = Join-Path $runtimeRoot ([string]$runtimeManifest.dll)
$expectedPackSha256 = [string]$buildManifest.registry_sha256
$expectedDllSha256 = [string]$runtimeManifest.dll_sha256
$expectedExeSha256 = [string]$job.compatibility.baldur_real_sha256
$exePath = Join-Path $gameFull 'BaldurReal.exe'
$activeStatePath = Join-Path $runRoot 'ingame-test\active-test.json'
$prefixes = @()
if ($isArmorSet) {
    $prefixes = @($buildManifest.bam_prefixes | ForEach-Object { ([string]$_).ToUpperInvariant() })
}
else {
    $prefixes = @(([string]$job.animation.bam_prefix).ToUpperInvariant())
}
if ($prefixes.Count -eq 0 -or @($prefixes | Select-Object -Unique).Count -ne $prefixes.Count) {
    throw 'Préfixes BAM absents ou dupliqués.'
}
foreach ($prefix in $prefixes) {
    if ($prefix -notmatch '^[A-Z0-9_]{1,8}$') {
        throw "Préfixe BAM invalide : $prefix"
    }
}

function Assert-GameChildPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    $gamePrefix = $gameFull + '\'
    if (-not $full.StartsWith($gamePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors du dossier du jeu : $full"
    }
    return $full
}

foreach ($scanRoot in @((Join-Path $workspaceRoot 'proto'), (Join-Path $workspaceRoot 'sprite'))) {
    if (-not (Test-Path -LiteralPath $scanRoot -PathType Container)) { continue }
    foreach ($candidate in Get-ChildItem -LiteralPath $scanRoot -Filter 'active-test.json' -File -Recurse -ErrorAction SilentlyContinue) {
        $candidateState = Get-Content -LiteralPath $candidate.FullName -Raw | ConvertFrom-Json
        if ($candidateState.status -in @('installing', 'restoring', 'installed-pending-qa', 'validated-installed', 'qa-failed')) {
            throw "Un test sprite est déjà actif : $($candidate.FullName) [$($candidateState.status)]"
        }
    }
}

if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw "Le jeu ou InfinityLoader est en cours d'exécution. Ferme-le avant l'installation."
}

Assert-ExpectedHash $exePath $expectedExeSha256 'BaldurReal.exe'
Assert-ExpectedHash $sourceDll $expectedDllSha256 'DLL construite et testée'
Assert-ExpectedHash $sourcePack $expectedPackSha256 'Registre sprite x2'

# Le runtime donne volontairement priorité au registre XN. Un test legacy ne
# peut donc prouver son propre pack si un XN résiduel est présent.
$xnPriorityFiles = @(
    'iee-assets\creature-sprites\CreatureSprites-XN.set',
    'iee-assets\creature-sprites\CreatureSprites-XN.registry'
)
foreach ($relative in $xnPriorityFiles) {
    $xnPriorityFile = Assert-GameChildPath (Join-Path $gameFull $relative)
    if (Test-Path -LiteralPath $xnPriorityFile) {
        throw "$([System.IO.Path]::GetFileName($xnPriorityFile)) est présent : restaure le test xN avant tout test legacy x2."
    }
}

$overridePath = Join-Path $gameFull 'override'
$characterBodySuffixes = @(
    'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'CA',
    'G1', 'G11', 'G12', 'G13', 'G14', 'G15', 'G16', 'G17', 'G18', 'G19',
    'SA', 'SS', 'SX'
)
if ($job.animation.runtime_profile -eq 'character-bg2ee-2.7.3.0') {
    $collisions = @(
        foreach ($prefix in $prefixes) {
            foreach ($suffix in $characterBodySuffixes) {
                $candidate = Join-Path $overridePath "$prefix$suffix.BAM"
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    Get-Item -LiteralPath $candidate
                }
            }
        }
    )
}
else {
    $collisions = @(Get-ChildItem -LiteralPath $overridePath -Filter "$($prefixes[0])*.BAM" -File -ErrorAction SilentlyContinue)
}
if ($collisions.Count -ne 0) {
    throw "Collision override détectée : $($collisions.Name -join ', ')"
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') +
    "-$PID-$([Guid]::NewGuid().ToString('N'))"
$backupRoot = Join-Path $runRoot "ingame-test\backups\$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

$relativeTargets = @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.ini',
    'iee-assets\creature-sprites\CreatureSprites-X2.registry'
)
$targets = @()
foreach ($relative in $relativeTargets) {
    $target = Assert-GameChildPath (Join-Path $gameFull $relative)
    $existed = Test-Path -LiteralPath $target -PathType Leaf
    $backup = $null
    $originalHash = $null
    if ($existed) {
        $backup = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backup -Force
        $originalHash = Get-Sha256 $target
        if ((Get-Sha256 $backup) -ne $originalHash) {
            throw "Sauvegarde non fidèle : $relative"
        }
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
    schema = 'bg2-upscale-creature-sprite-x2-ingame-test-v1'
    status = 'installing'
    installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    job_file = $jobPath
    job_id = [string]$job.job_id
    game_root = $gameFull
    baldureal_sha256 = $expectedExeSha256
    method = 'XBR/xbr2X; x2; one pass; antialias off; NEAREST'
    resource_family = ($prefixes -join ',')
    animation_id = [string]$job.animation.id
    runtime_profile = [string]$job.animation.runtime_profile
    resources = [int]$buildManifest.resource_count
    frames = [int]$buildManifest.frame_count
    source_dll_sha256 = $expectedDllSha256
    source_pack_sha256 = $expectedPackSha256
    backup_root = $backupRoot
    targets = $targets
}
$statePath = Join-Path $backupRoot 'install-state.json'
$state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding utf8

function Set-IniKey([string]$Text, [string]$Section, [string]$Key, [string]$Value) {
    $newline = if ($Text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [regex]::Split($Text, '\r?\n')) { [void]$lines.Add($line) }
    $sectionRanges = @()
    $sectionStart = -1
    $sectionMatches = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[([^\]]+)\]\s*$') {
            if ($sectionMatches) {
                $sectionRanges += [pscustomobject]@{ Start = $sectionStart; End = $index }
            }
            $sectionStart = $index
            $sectionMatches = [string]::Equals($Matches[1].Trim(), $Section,
                [System.StringComparison]::OrdinalIgnoreCase)
        }
    }
    if ($sectionMatches) {
        $sectionRanges += [pscustomobject]@{ Start = $sectionStart; End = $lines.Count }
    }
    if ($sectionRanges.Count -eq 0) {
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') { [void]$lines.Add('') }
        [void]$lines.Add("[$Section]")
        [void]$lines.Add("$Key = $Value")
        return [string]::Join($newline, $lines)
    }
    $keyIndexes = @()
    $keyPattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    foreach ($range in $sectionRanges) {
        for ($index = [int]$range.Start + 1; $index -lt [int]$range.End; $index++) {
            if ($lines[$index] -match $keyPattern) { $keyIndexes += $index }
        }
    }
    if ($keyIndexes.Count -gt 1) { throw "Clé INI dupliquée dans [$Section] : $Key" }
    if ($keyIndexes.Count -eq 1) {
        $lines[[int]$keyIndexes[0]] = "$Key = $Value"
    }
    else {
        $lines.Insert([int]$sectionRanges[0].End, "$Key = $Value")
    }
    return [string]::Join($newline, $lines)
}

function Get-IniKey([string]$Text, [string]$Section, [string]$Key) {
    $currentSection = ''
    $values = @()
    foreach ($line in [regex]::Split($Text, '\r?\n')) {
        if ($line -match '^\s*\[([^\]]+)\]\s*$') {
            $currentSection = $Matches[1].Trim()
            continue
        }
        if ([string]::Equals($currentSection, $Section,
                [System.StringComparison]::OrdinalIgnoreCase) -and
            $line -match ('^\s*' + [regex]::Escape($Key) + '\s*=\s*(.*?)\s*$')) {
            $values += $Matches[1]
        }
    }
    if ($values.Count -ne 1) { throw "Clé INI absente ou dupliquée dans [$Section] : $Key" }
    return [string]$values[0]
}

try {
    $dllTarget = Assert-GameChildPath (Join-Path $gameFull 'InfinityEngine-Enhancer.dll')
    $iniTarget = Assert-GameChildPath (Join-Path $gameFull 'InfinityEngine-Enhancer.ini')
    $packTarget = Assert-GameChildPath (Join-Path $gameFull 'iee-assets\creature-sprites\CreatureSprites-X2.registry')
    if (-not (Test-Path -LiteralPath $iniTarget -PathType Leaf)) {
        throw 'InfinityEngine-Enhancer.ini est absent.'
    }

    Copy-Item -LiteralPath $sourceDll -Destination $dllTarget -Force
    New-Item -ItemType Directory -Path (Split-Path -Parent $packTarget) -Force | Out-Null
    Copy-Item -LiteralPath $sourcePack -Destination $packTarget -Force

    $iniText = Get-Content -LiteralPath $iniTarget -Raw
    $iniText = Set-IniKey $iniText 'Shaders' 'EnableCreatureSpriteX2Test' 'true'
    $noFilter = $true
    if ($null -ne $job.runtime -and $null -ne $job.runtime.no_filter_comparison) {
        $noFilter = [bool]$job.runtime.no_filter_comparison
    }
    if ($noFilter) {
        $iniText = Set-IniKey $iniText 'Rendering' 'EnableAnisotropicFiltering' 'false'
        $iniText = Set-IniKey $iniText 'Shaders' 'EnableFullFrameFXAA' 'false'
        $iniText = Set-IniKey $iniText 'Shaders' 'EnableFullFrameSSAA2x' 'false'
    }
    Set-Content -LiteralPath $iniTarget -Value $iniText -Encoding utf8 -NoNewline

    Assert-ExpectedHash $dllTarget $expectedDllSha256 'DLL installée'
    Assert-ExpectedHash $packTarget $expectedPackSha256 'Registre installé'
    $installedIni = Get-Content -LiteralPath $iniTarget -Raw
    if ((Get-IniKey $installedIni 'Shaders' 'EnableCreatureSpriteX2Test') -ne 'true') {
        throw "EnableCreatureSpriteX2Test n'est pas actif."
    }

    foreach ($targetState in $targets) {
        $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
        $targetState.installed_sha256 = Get-Sha256 $target
    }
    $state.status = 'installed-pending-qa'
    $state.installed_dll_sha256 = Get-Sha256 $dllTarget
    $state.installed_ini_sha256 = Get-Sha256 $iniTarget
    $state.installed_pack_sha256 = Get-Sha256 $packTarget
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding utf8
    New-Item -ItemType Directory -Path (Split-Path -Parent $activeStatePath) -Force | Out-Null
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $activeStatePath -Encoding utf8
}
catch {
    foreach ($targetState in $targets) {
        $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
        if ($targetState.existed_before) {
            Copy-Item -LiteralPath $targetState.backup_path -Destination $target -Force
        }
        elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    $state.status = 'rolled-back-after-install-error'
    $state.error = $_.Exception.Message
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding utf8
    throw
}

$result = [pscustomobject]@{
    Status = $state.status
    GameRoot = $gameFull
    DllSha256 = $state.installed_dll_sha256
    PackSha256 = $state.installed_pack_sha256
    Backup = $backupRoot
    State = $activeStatePath
}
$result
}
finally {
    Exit-GameMutationMutex $gameMutationMutex
}
