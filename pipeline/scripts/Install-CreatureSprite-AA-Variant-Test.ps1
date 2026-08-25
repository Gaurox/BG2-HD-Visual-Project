param(
    [Parameter(Mandatory = $true)]
    [string]$JobFile
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

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
    if ([IO.Path]::IsPathRooted($Value)) {
        return [IO.Path]::GetFullPath($Value)
    }
    return [IO.Path]::GetFullPath((Join-Path $ProjectRoot $Value))
}

function Assert-GameChild([string]$GameRoot, [string]$RelativePath) {
    if ([IO.Path]::IsPathRooted($RelativePath)) {
        throw "Cible AA absolue interdite : $RelativePath"
    }
    $full = [IO.Path]::GetFullPath((Join-Path $GameRoot $RelativePath))
    $prefix = $GameRoot.TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible AA hors du jeu : $full"
    }
    return $full
}

function Set-IniBoolean([Collections.Generic.List[string]]$Lines, [string]$Section, [string]$Key, [bool]$Value) {
    $sectionStart = -1
    $sectionEnd = $Lines.Count
    for ($index = 0; $index -lt $Lines.Count; $index++) {
        if ($Lines[$index].Trim() -match '^\[(.+)\]$') {
            if ($sectionStart -ge 0) {
                $sectionEnd = $index
                break
            }
            if ([string]::Equals($Matches[1], $Section, [StringComparison]::OrdinalIgnoreCase)) {
                $sectionStart = $index
            }
        }
    }
    if ($sectionStart -lt 0) {
        if ($Lines.Count -gt 0 -and $Lines[$Lines.Count - 1] -ne '') { $Lines.Add('') }
        $Lines.Add("[$Section]")
        $Lines.Add("$Key = $($Value.ToString().ToLowerInvariant())")
        return
    }
    for ($index = $sectionStart + 1; $index -lt $sectionEnd; $index++) {
        if ($Lines[$index] -match '^\s*([^;#][^=]*?)\s*=') {
            if ([string]::Equals($Matches[1].Trim(), $Key, [StringComparison]::OrdinalIgnoreCase)) {
                $Lines[$index] = "$Key = $($Value.ToString().ToLowerInvariant())"
                return
            }
        }
    }
    $Lines.Insert($sectionEnd, "$Key = $($Value.ToString().ToLowerInvariant())")
}

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$jobFull = [IO.Path]::GetFullPath($JobFile)
$jobsRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'sprite\jobs')).TrimEnd('\') + '\'
if (-not $jobFull.StartsWith($jobsRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Le job AA doit rester sous sprite/jobs : $jobFull"
}
$job = Get-Content -LiteralPath $jobFull -Raw | ConvertFrom-Json
if ($job.schema -ne 'bg2-upscale-creature-sprite-xbr2x-aa-job-v1' -or
    $job.job_id -ne 'dwarf-male-fighter-cdmb1-aa-xbr2x') {
    throw 'Job AA inattendu.'
}
$gameRoot = [IO.Path]::GetFullPath([string]$job.paths.game_root).TrimEnd('\')
$runRoot = Resolve-ProjectPath ([string]$job.paths.run_dir) $projectRoot
$runPrefix = [IO.Path]::GetFullPath((Join-Path $projectRoot 'sprite')).TrimEnd('\') + '\'
if (-not ($runRoot.TrimEnd('\') + '\').StartsWith($runPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "run_dir AA hors de sprite : $runRoot"
}
$buildRoot = Join-Path $runRoot 'build'
$runtimeRoot = Join-Path $runRoot 'runtime'
$buildManifestPath = Join-Path $buildRoot 'build-manifest.json'
$runtimeManifestPath = Join-Path $runtimeRoot 'runtime-manifest.json'
$registrySource = Join-Path $buildRoot 'iee-assets\creature-sprites\CreatureSprites-XN.registry'
$dllSource = Join-Path $runtimeRoot 'InfinityEngine-Enhancer.dll'
foreach ($required in @($buildManifestPath, $runtimeManifestPath, $registrySource, $dllSource)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Artefact AA absent : $required" }
}
$build = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
$runtime = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json
if ($build.schema -ne 'bg2-upscale-creature-sprite-xbr2x-aa-pack-v1' -or
    $build.status -ne 'built-pending-ingame-qa' -or
    [int]$build.registry_version -ne 4 -or [int]$build.registry_scale -ne 2 -or
    $build.registry_layout -ne 'monolith' -or $build.sampling -ne 'NEAREST' -or
    $build.registry_sha256 -ne (Get-Sha256 $registrySource)) {
    throw 'Build AA non vérifiable.'
}
if ($runtime.schema -ne 'bg2-upscale-creature-sprite-runtime-v1' -or
    $runtime.status -ne 'built-tested' -or $runtime.tests_status -ne 'passed' -or
    $runtime.dll_sha256 -ne (Get-Sha256 $dllSource)) {
    throw 'Runtime AA non vérifiable.'
}
$exe = Join-Path $gameRoot 'BaldurReal.exe'
if ((Get-Sha256 $exe) -ne ([string]$job.compatibility.baldur_real_sha256).ToUpperInvariant()) {
    throw 'BaldurReal.exe diffère du job AA.'
}
if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw "Le jeu ou InfinityLoader est actif. Ferme-le avant l'installation AA."
}

$activeStatePath = Join-Path $runRoot 'ingame-test\active-test.json'
if (Test-Path -LiteralPath $activeStatePath -PathType Leaf) {
    $existing = Get-Content -LiteralPath $activeStatePath -Raw | ConvertFrom-Json
    if ($existing.status -in @('installing', 'restoring', 'installed-pending-qa', 'qa-failed')) {
        throw "La variante AA est déjà active ou interrompue : $($existing.status)"
    }
}

$parentStates = @()
$spriteRoot = Join-Path $projectRoot 'sprite'
foreach ($candidate in Get-ChildItem -LiteralPath $spriteRoot -Filter 'active-test.json' -File -Recurse -ErrorAction SilentlyContinue) {
    if ([string]::Equals($candidate.FullName, $activeStatePath, [StringComparison]::OrdinalIgnoreCase)) { continue }
    try { $candidateState = Get-Content -LiteralPath $candidate.FullName -Raw | ConvertFrom-Json } catch { continue }
    if ($candidateState.status -in @('installing', 'restoring', 'installed-pending-qa', 'validated-installed', 'qa-failed')) {
        $parentStates += [ordered]@{
            state_path = $candidate.FullName
            job_id = [string]$candidateState.job_id
            status = [string]$candidateState.status
        }
    }
}
if ($parentStates.Count -gt 1) {
    throw "Plusieurs tests sprite parents sont actifs ; état ambigu : $($parentStates.state_path -join ', ')"
}

$relativeTargets = [Collections.Generic.List[string]]::new()
foreach ($relative in @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.ini',
    'iee-assets\creature-sprites\CreatureSprites-X2.registry',
    'iee-assets\creature-sprites\CreatureSprites-XN.registry',
    'iee-assets\creature-sprites\CreatureSprites-XN.set'
)) { $relativeTargets.Add($relative) }
$gameSpriteRoot = Assert-GameChild $gameRoot 'iee-assets\creature-sprites'
if (Test-Path -LiteralPath $gameSpriteRoot -PathType Container) {
    foreach ($shard in Get-ChildItem -LiteralPath $gameSpriteRoot -File -ErrorAction SilentlyContinue |
        Where-Object Name -match '^CreatureSprites-XN-[0-9]{4}\.registry$' | Sort-Object Name) {
        $relativeTargets.Add('iee-assets\creature-sprites\' + $shard.Name)
    }
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') + '-' + [guid]::NewGuid().ToString('N')
$backupRoot = Join-Path $runRoot "ingame-test\backups\$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$targets = @()
foreach ($relative in $relativeTargets) {
    $target = Assert-GameChild $gameRoot $relative
    $existed = Test-Path -LiteralPath $target -PathType Leaf
    $backup = $null
    $hash = $null
    if ($existed) {
        $hash = Get-Sha256 $target
        $backup = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $backup -Force
        if ((Get-Sha256 $backup) -ne $hash) { throw "Sauvegarde AA non fidèle : $relative" }
    }
    $targets += [ordered]@{
        relative_path = $relative
        existed_before = [bool]$existed
        original_sha256 = $hash
        backup_path = $backup
        installed_present = $null
        installed_sha256 = $null
    }
}

$state = [ordered]@{
    schema = 'bg2-upscale-creature-sprite-aa-variant-test-v1'
    status = 'installing'
    created_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    job_file = $jobFull
    job_id = [string]$job.job_id
    game_root = $gameRoot
    animation_id = '0x6102'
    bam_prefix = 'CDMB1'
    scope = 'body-only; armor-code-1; no equipped overlays'
    method = [ordered]@{
        algorithm = 'XBR/xbr2X'
        scale = 2
        passes = 1
        antialias = $true
        xbr_blend = $true
        sampling = 'NEAREST'
    }
    registry_magic = 'IEECSXN'
    registry_version = 4
    source_registry_sha256 = Get-Sha256 $registrySource
    source_dll_sha256 = Get-Sha256 $dllSource
    parent_active_tests = $parentStates
    backup_root = $backupRoot
    targets = $targets
    game_launch_automatic = $false
    release_manifest_modified = $false
}
$backupStatePath = Join-Path $backupRoot 'install-state.json'
Write-JsonAtomic $state $activeStatePath
Write-JsonAtomic $state $backupStatePath

try {
    foreach ($targetState in $targets) {
        if ([string]$targetState.relative_path -match '^iee-assets\\creature-sprites\\CreatureSprites-X(?:2|N)') {
            $target = Assert-GameChild $gameRoot ([string]$targetState.relative_path)
            if (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target -Force }
        }
    }
    $registryTarget = Assert-GameChild $gameRoot 'iee-assets\creature-sprites\CreatureSprites-XN.registry'
    New-Item -ItemType Directory -Path (Split-Path -Parent $registryTarget) -Force | Out-Null
    Copy-Item -LiteralPath $registrySource -Destination $registryTarget -Force
    Copy-Item -LiteralPath $dllSource -Destination (Assert-GameChild $gameRoot 'InfinityEngine-Enhancer.dll') -Force

    $iniTarget = Assert-GameChild $gameRoot 'InfinityEngine-Enhancer.ini'
    if (-not (Test-Path -LiteralPath $iniTarget -PathType Leaf)) {
        throw 'InfinityEngine-Enhancer.ini doit exister avant le test AA.'
    }
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in [IO.File]::ReadAllLines($iniTarget)) { $lines.Add($line) }
    Set-IniBoolean $lines 'Shaders' 'EnableCreatureSpriteUpscaleTest' $true
    Set-IniBoolean $lines 'Shaders' 'EnableCreatureSpriteX2Test' $false
    Set-IniBoolean $lines 'Shaders' 'EnableCreatureSpriteLinearFiltering' $false
    [IO.File]::WriteAllLines($iniTarget, $lines, [Text.UTF8Encoding]::new($false))

    foreach ($targetState in $targets) {
        $target = Assert-GameChild $gameRoot ([string]$targetState.relative_path)
        $present = Test-Path -LiteralPath $target -PathType Leaf
        $targetState.installed_present = [bool]$present
        $targetState.installed_sha256 = if ($present) { Get-Sha256 $target } else { $null }
    }
    if ((Get-Sha256 $registryTarget) -ne (Get-Sha256 $registrySource)) { throw 'Registre AA installé non fidèle.' }
    $state.status = 'installed-pending-qa'
    $state.installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    $state.installed_registry_sha256 = Get-Sha256 $registryTarget
    $state.installed_dll_sha256 = Get-Sha256 (Assert-GameChild $gameRoot 'InfinityEngine-Enhancer.dll')
    $state.installed_ini_sha256 = Get-Sha256 $iniTarget
    Write-JsonAtomic $state $activeStatePath
    Write-JsonAtomic $state $backupStatePath
}
catch {
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
    $state.status = 'rolled-back-after-install-error'
    $state.error = $_.Exception.Message
    $state.rolled_back_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    Write-JsonAtomic $state $activeStatePath
    Write-JsonAtomic $state $backupStatePath
    throw
}

[pscustomobject]@{
    Status = $state.status
    Job = $state.job_id
    Scope = $state.scope
    Registry = $state.installed_registry_sha256
    Sampling = $state.method.sampling
    Backup = $backupRoot
} | ConvertTo-Json
