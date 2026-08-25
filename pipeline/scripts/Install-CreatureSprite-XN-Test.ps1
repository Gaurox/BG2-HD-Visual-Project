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

function Get-RequiredProperty($Object, [string]$Name, [string]$Label) {
    if ($null -eq $Object) {
        throw "$Label absent."
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        throw "$Label.$Name absent."
    }
    return $property.Value
}

function Assert-OrdinalEqual([string]$Actual, [string]$Expected, [string]$Label) {
    if (-not [string]::Equals($Actual, $Expected, [System.StringComparison]::Ordinal)) {
        throw "$Label incompatible : '$Actual', attendu '$Expected'."
    }
}

function Resolve-JobPath([string]$Value) {
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot $Value))
}

function Resolve-ManifestChild([string]$Root, [string]$Relative, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or [System.IO.Path]::IsPathRooted($Relative)) {
        throw "$Label doit être un chemin relatif."
    }
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $full = [System.IO.Path]::GetFullPath((Join-Path $rootFull ($Relative.Replace('/', '\'))))
    if (-not $full.StartsWith($rootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label sort de sa racine déclarée : $Relative"
    }
    return $full
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

function Assert-ExpectedHash([string]$Path, [string]$Expected, [string]$Label) {
    if ($Expected -notmatch '^[0-9A-Fa-f]{64}$') {
        throw "$Label : SHA-256 manifeste invalide."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label absent : $Path"
    }
    $actual = Get-Sha256 $Path
    if (-not [string]::Equals($actual, $Expected, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label incompatible : SHA-256 $actual, attendu $Expected"
    }
}

function Assert-UpscaleContract($Contract, [int]$Scale, [string]$Label) {
    $expectedAlgorithm = if ($Scale -eq 2) { 'XBR/xbr2X' } else { 'XBR/xbr4X' }
    Assert-OrdinalEqual ([string](Get-RequiredProperty $Contract 'algorithm' $Label)) $expectedAlgorithm "$Label.algorithm"
    if ([int](Get-RequiredProperty $Contract 'scale' $Label) -ne $Scale) {
        throw "$Label.scale incompatible."
    }
    if ([int](Get-RequiredProperty $Contract 'passes' $Label) -ne 1) {
        throw "$Label.passes doit valoir 1."
    }
    $antialias = Get-RequiredProperty $Contract 'antialias' $Label
    $blend = Get-RequiredProperty $Contract 'xbr_blend' $Label
    if ($antialias -isnot [bool] -or $antialias) {
        throw "$Label.antialias doit être le booléen false."
    }
    if ($blend -isnot [bool] -or $blend) {
        throw "$Label.xbr_blend doit être le booléen false."
    }
}

function Read-ExactBytes($Stream, [int]$Count, [string]$Label) {
    [byte[]]$buffer = New-Object byte[] $Count
    $read = 0
    while ($read -lt $Count) {
        $chunk = $Stream.Read($buffer, $read, $Count - $read)
        if ($chunk -eq 0) { throw "$Label tronqué." }
        $read += $chunk
    }
    return ,$buffer
}

function Skip-RegistryBytes($Stream, [uint64]$Count, [string]$Label) {
    if ($Count -gt [uint64][long]::MaxValue -or
        [uint64]$Stream.Position + $Count -gt [uint64]$Stream.Length) {
        throw "$Label tronqué."
    }
    [void]$Stream.Seek([long]$Count, [System.IO.SeekOrigin]::Current)
}

function Read-RegistryHeader([string]$Path) {
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        if ($stream.Length -lt 24 -or $stream.Length -gt (128MB)) {
            throw "Taille de registre hors contrat 24 octets..128 Mio : $($stream.Length)"
        }
        [byte[]]$header = Read-ExactBytes $stream 24 'En-tête de registre'
        $magic = [System.Text.Encoding]::ASCII.GetString($header, 0, 7)
        if ($header[7] -ne 0) { $magic += '<non-nul>' }
        $version = [System.BitConverter]::ToUInt32($header, 8)
        $scale = [System.BitConverter]::ToUInt32($header, 12)
        $resourceCount = [System.BitConverter]::ToUInt32($header, 16)
        if ($magic -ne 'IEECSXN' -or $version -ne 3 -or $scale -notin @(2, 4) -or
            $resourceCount -lt 1 -or $resourceCount -gt 128) {
            throw 'En-tête de registre XN invalide.'
        }
        [uint64]$indexBytesTotal = 0
        for ($resourceIndex = 0; $resourceIndex -lt $resourceCount; $resourceIndex++) {
            [byte[]]$resourceHeader = Read-ExactBytes $stream 48 'Ressource registre'
            $frameCount = [System.BitConverter]::ToUInt32($resourceHeader, 40)
            $cycleCount = [System.BitConverter]::ToUInt32($resourceHeader, 44)
            if ($frameCount -lt 1 -or $frameCount -gt 4096 -or
                $cycleCount -lt 1 -or $cycleCount -gt 256) {
                throw 'Compteurs ressource registre invalides.'
            }
            for ($frameIndex = 0; $frameIndex -lt $frameCount; $frameIndex++) {
                [byte[]]$frameHeader = Read-ExactBytes $stream 528 'Frame registre'
                $width = [System.BitConverter]::ToUInt16($frameHeader, 0)
                $height = [System.BitConverter]::ToUInt16($frameHeader, 2)
                $frameBytes = [System.BitConverter]::ToUInt32($frameHeader, 12)
                $expected = [uint64]$width * [uint64]$height * [uint64]$scale * [uint64]$scale
                if ($width -eq 0 -or $height -eq 0 -or
                    $frameHeader[9] -ne 0 -or $frameHeader[10] -ne 0 -or
                    $frameHeader[11] -ne 0 -or [uint64]$frameBytes -ne $expected) {
                    throw 'Frame registre incompatible avec son échelle.'
                }
                Skip-RegistryBytes $stream ([uint64]$frameBytes) 'Payload frame registre'
                $indexBytesTotal += [uint64]$frameBytes
            }
            for ($cycleIndex = 0; $cycleIndex -lt $cycleCount; $cycleIndex++) {
                [byte[]]$cycleHeader = Read-ExactBytes $stream 4 'Cycle registre'
                $slots = [System.BitConverter]::ToUInt32($cycleHeader, 0)
                if ($slots -lt 1 -or $slots -gt 65536) { throw 'Cycle registre invalide.' }
                Skip-RegistryBytes $stream ([uint64]$slots * 4) 'Lookup cycle registre'
            }
        }
        if ($stream.Position -ne $stream.Length) { throw 'Octets résiduels dans le registre.' }
        return [pscustomobject]@{
            magic = $magic
            version = $version
            scale = $scale
            resource_count = $resourceCount
            animation_id = [System.BitConverter]::ToUInt32($header, 20)
            bytes = [uint64]$stream.Length
            index_bytes = $indexBytesTotal
        }
    }
    finally {
        $stream.Dispose()
    }
}

$jobSchema = [string](Get-RequiredProperty $job 'schema' 'job')
$isArmorSet = $jobSchema -eq 'bg2-upscale-creature-sprite-xbr2x-armor-set-v1'
if ($jobSchema -notin @(
    'bg2-upscale-creature-sprite-xbr2x-job-v1',
    'bg2-upscale-creature-sprite-xbr2x-armor-set-v1'
)) {
    throw "Schéma de job non supporté : $jobSchema"
}

$upscale = Get-RequiredProperty $job 'upscale' 'job'
$scale = [int](Get-RequiredProperty $upscale 'scale' 'job.upscale')
if ($scale -notin @(2, 4)) {
    throw "job.upscale.scale non supporté : $scale"
}
Assert-UpscaleContract $upscale $scale 'job.upscale'

$runtimeProfile = [string](Get-RequiredProperty $job.animation 'runtime_profile' 'job.animation')
if ($runtimeProfile -notin @('monster-icewind-bg2ee-2.7.3.0', 'character-bg2ee-2.7.3.0')) {
    throw "unsupported-runtime-profile : $runtimeProfile"
}
if ($isArmorSet -and $runtimeProfile -ne 'character-bg2ee-2.7.3.0') {
    throw 'Un set Character exige le profil Character.'
}

$runRoot = Resolve-JobPath ([string](Get-RequiredProperty $job.paths 'run_dir' 'job.paths'))
if (-not $runRoot.StartsWith($workspaceRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "job.paths.run_dir sort du workspace : $runRoot"
}
$buildRoot = Join-Path $runRoot 'build'
$runtimeRoot = Join-Path $runRoot 'runtime'
$buildManifestPath = Join-Path $buildRoot 'build-manifest.json'
$runtimeManifestPath = Join-Path $runtimeRoot 'runtime-manifest.json'
if (-not (Test-Path -LiteralPath $buildManifestPath -PathType Leaf)) {
    throw "Manifeste de build absent : $buildManifestPath"
}
if (-not (Test-Path -LiteralPath $runtimeManifestPath -PathType Leaf)) {
    throw "Manifeste runtime absent : $runtimeManifestPath"
}
$buildManifest = Get-Content -LiteralPath $buildManifestPath -Raw | ConvertFrom-Json
$runtimeManifest = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json

$expectedBuildSchema = if ($isArmorSet) {
    'bg2-upscale-creature-sprite-xbr2x-armor-set-pack-v1'
} else {
    'bg2-upscale-creature-sprite-xbr2x-pack-v1'
}
Assert-OrdinalEqual ([string](Get-RequiredProperty $buildManifest 'schema' 'build')) $expectedBuildSchema 'build.schema'
Assert-OrdinalEqual ([string](Get-RequiredProperty $buildManifest 'status' 'build')) 'built-pending-ingame-qa' 'build.status'
Assert-OrdinalEqual ([string](Get-RequiredProperty $buildManifest 'job_id' 'build')) ([string]$job.job_id) 'build.job_id'
Assert-OrdinalEqual ([string](Get-RequiredProperty $buildManifest 'runtime_profile' 'build')) $runtimeProfile 'build.runtime_profile'
if (-not [string]::Equals([string](Get-RequiredProperty $buildManifest 'animation_id' 'build'),
        [string](Get-RequiredProperty $job.animation 'id' 'job.animation'),
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'build.animation_id diffère du job.'
}
if ([int](Get-RequiredProperty $buildManifest 'registry_version' 'build') -ne 3) {
    throw 'build.registry_version doit valoir 3.'
}
Assert-OrdinalEqual ([string](Get-RequiredProperty $buildManifest 'registry_magic' 'build')) 'IEECSXN' 'build.registry_magic'
if ([int](Get-RequiredProperty $buildManifest 'registry_scale' 'build') -ne $scale) {
    throw 'build.registry_scale diffère du job.'
}
Assert-UpscaleContract (Get-RequiredProperty $buildManifest 'method' 'build') $scale 'build.method'

Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'schema' 'runtime')) 'bg2-upscale-creature-sprite-runtime-v1' 'runtime.schema'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'status' 'runtime')) 'built-tested' 'runtime.status'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'tests_status' 'runtime')) 'passed' 'runtime.tests_status'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'job_id' 'runtime')) ([string]$job.job_id) 'runtime.job_id'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'runtime_profile' 'runtime')) $runtimeProfile 'runtime.runtime_profile'

$registryRelative = ([string](Get-RequiredProperty $buildManifest 'registry' 'build')).Replace('/', '\')
Assert-OrdinalEqual $registryRelative 'iee-assets\creature-sprites\CreatureSprites-XN.registry' 'build.registry'
$sourcePack = Resolve-ManifestChild $buildRoot $registryRelative 'build.registry'
$sourceDll = Resolve-ManifestChild $runtimeRoot ([string](Get-RequiredProperty $runtimeManifest 'dll' 'runtime')) 'runtime.dll'
$expectedPackSha256 = [string](Get-RequiredProperty $buildManifest 'registry_sha256' 'build')
$expectedDllSha256 = [string](Get-RequiredProperty $runtimeManifest 'dll_sha256' 'runtime')
$expectedExeSha256 = [string](Get-RequiredProperty $job.compatibility 'baldur_real_sha256' 'job.compatibility')

Assert-ExpectedHash $sourcePack $expectedPackSha256 'Registre sprite xN'
Assert-ExpectedHash $sourceDll $expectedDllSha256 'DLL construite et testée'
$header = Read-RegistryHeader $sourcePack
Assert-OrdinalEqual ([string]$header.magic) 'IEECSXN' 'registre.magic'
if ($header.version -ne 3 -or $header.scale -ne $scale) {
    throw "En-tête registre incompatible : version=$($header.version), scale=$($header.scale)."
}
$resourceCount = [int](Get-RequiredProperty $buildManifest 'resource_count' 'build')
$frameCount = [int](Get-RequiredProperty $buildManifest 'frame_count' 'build')
if ($resourceCount -lt 1 -or $resourceCount -gt 128 -or $header.resource_count -ne $resourceCount) {
    throw 'Le nombre de ressources du registre est invalide ou diffère du build.'
}
if ($frameCount -lt 1) { throw 'build.frame_count doit être positif.' }
if ([uint64](Get-RequiredProperty $buildManifest 'registry_bytes' 'build') -ne $header.bytes) {
    throw 'build.registry_bytes diffère du fichier.'
}
$animationIdText = [string](Get-RequiredProperty $job.animation 'id' 'job.animation')
if ($animationIdText -notmatch '^0x[0-9A-Fa-f]{4}$') { throw 'job.animation.id invalide.' }
$animationId = [Convert]::ToUInt32($animationIdText.Substring(2), 16)
if ($header.animation_id -ne $animationId) { throw "L'animation ID du registre diffère du job." }

$metricName = if ($isArmorSet) { "x${scale}_index_bytes" } else { "x${scale}_pixel_count" }
if ([uint64](Get-RequiredProperty $buildManifest $metricName 'build') -ne $header.index_bytes) {
    throw "build.$metricName diffère du payload indexé du registre."
}
if (-not $isArmorSet) {
    $keepName = "kept_individual_x${scale}_frames"
    $kept = Get-RequiredProperty $buildManifest $keepName 'build'
    if ($kept -isnot [bool]) { throw "build.$keepName doit être booléen." }
    $validation = Get-RequiredProperty $buildManifest 'validation' 'build'
    $dimensionName = "dimensions_exact_x${scale}"
    if ([int](Get-RequiredProperty $validation $dimensionName 'build.validation') -ne $frameCount) {
        throw "build.validation.$dimensionName diffère du nombre de frames."
    }
}

$gameFull = (Resolve-Path -LiteralPath (Resolve-JobPath ([string](Get-RequiredProperty $job.paths 'game_root' 'job.paths')))).Path.TrimEnd('\')
$exePath = Join-Path $gameFull 'BaldurReal.exe'
Assert-ExpectedHash $exePath $expectedExeSha256 'BaldurReal.exe'

$prefixes = @()
if ($isArmorSet) {
    if ($null -eq $buildManifest.PSObject.Properties['bam_prefixes']) {
        throw 'build.bam_prefixes absent.'
    }
    $prefixes = @($buildManifest.bam_prefixes | ForEach-Object { ([string]$_).ToUpperInvariant() })
}
else {
    $prefix = ([string](Get-RequiredProperty $job.animation 'bam_prefix' 'job.animation')).ToUpperInvariant()
    if (-not [string]::Equals([string](Get-RequiredProperty $buildManifest 'bam_prefix' 'build'),
            $prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'build.bam_prefix diffère du job.'
    }
    $prefixes = @($prefix)
}
if ($prefixes.Count -eq 0 -or @($prefixes | Select-Object -Unique).Count -ne $prefixes.Count) {
    throw 'Préfixes BAM absents ou dupliqués.'
}
foreach ($prefix in $prefixes) {
    if ($prefix -notmatch '^[A-Z0-9_]{1,8}$') { throw "Préfixe BAM invalide : $prefix" }
}

foreach ($scanRoot in @((Join-Path $workspaceRoot 'proto'), (Join-Path $workspaceRoot 'sprite'))) {
    if (-not (Test-Path -LiteralPath $scanRoot -PathType Container)) { continue }
    foreach ($candidate in Get-ChildItem -LiteralPath $scanRoot -Filter 'active-test.json' -File -Recurse -ErrorAction SilentlyContinue) {
        $candidateState = Get-Content -LiteralPath $candidate.FullName -Raw | ConvertFrom-Json
        if ($candidateState.status -in @('installing', 'installed-pending-qa', 'validated-installed', 'qa-failed')) {
            throw "Un test sprite est déjà actif : $($candidate.FullName) [$($candidateState.status)]"
        }
    }
}
if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw "Le jeu ou InfinityLoader est en cours d'exécution. Ferme-le avant l'installation."
}

$overridePath = Join-Path $gameFull 'override'
$collisions = @()
if (Test-Path -LiteralPath $overridePath -PathType Container) {
    foreach ($prefix in $prefixes) {
        $paperdoll = "${prefix}INV.BAM"
        $collisions += @(Get-ChildItem -LiteralPath $overridePath -Filter "$prefix*.BAM" -File -ErrorAction SilentlyContinue |
            Where-Object { -not [string]::Equals($_.Name, $paperdoll, [System.StringComparison]::OrdinalIgnoreCase) })
    }
}
if ($collisions.Count -ne 0) {
    throw "Collision override détectée : $(@($collisions.Name | Sort-Object -Unique) -join ', ')"
}

function Assert-GameChildPath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($gameFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Cible hors du dossier du jeu : $full"
    }
    return $full
}

$activeStatePath = Join-Path $runRoot 'ingame-test\active-test.json'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$backupRoot = Join-Path $runRoot "ingame-test\backups\$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

# Les deux noms de registre sont sauvegardés. XN est prioritaire au runtime ; X2
# reste intact pendant le test et demeure le fallback exact après restauration.
$relativeTargets = @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.ini',
    'iee-assets\creature-sprites\CreatureSprites-XN.registry',
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
        if ((Get-Sha256 $backup) -ne $originalHash) { throw "Sauvegarde non fidèle : $relative" }
    }
    $targets += [ordered]@{
        relative_path = $relative
        existed_before = $existed
        original_sha256 = $originalHash
        backup_path = $backup
        installed_present = $null
        installed_sha256 = $null
    }
}

$state = [ordered]@{
    schema = 'bg2-upscale-creature-sprite-xn-ingame-test-v1'
    status = 'installing'
    installed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    job_file = $jobPath
    job_id = [string]$job.job_id
    game_root = $gameFull
    baldureal_sha256 = $expectedExeSha256
    method = [ordered]@{
        algorithm = [string]$upscale.algorithm
        scale = $scale
        passes = 1
        antialias = $false
        xbr_blend = $false
        sampling = 'NEAREST'
    }
    registry_relative_path = $registryRelative
    registry_magic = 'IEECSXN'
    registry_version = 3
    registry_scale = $scale
    resource_family = ($prefixes -join ',')
    animation_id = $animationIdText
    runtime_profile = $runtimeProfile
    resources = $resourceCount
    frames = $frameCount
    source_dll_sha256 = $expectedDllSha256
    source_pack_sha256 = $expectedPackSha256
    backup_root = $backupRoot
    targets = $targets
}
$statePath = Join-Path $backupRoot 'install-state.json'
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8
# Publier l'état récupérable avant la première mutation du jeu. En cas d'arrêt
# brutal, Restore-CreatureSprite-XN-Test.ps1 -RecoverInstalling retrouve les
# sauvegardes validées via ce pointeur stable.
New-Item -ItemType Directory -Path (Split-Path -Parent $activeStatePath) -Force | Out-Null
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $activeStatePath -Encoding utf8

function Set-IniKey([string]$Text, [string]$Section, [string]$Key, [string]$Value) {
    $newline = if ($Text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [regex]::Split($Text, '\r?\n')) { [void]$lines.Add($line) }
    $sectionStarts = @()
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[([^\]]+)\]\s*$' -and
            [string]::Equals($Matches[1].Trim(), $Section,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            $sectionStarts += $index
        }
    }
    if ($sectionStarts.Count -gt 1) { throw "Section INI dupliquée : [$Section]" }
    if ($sectionStarts.Count -eq 0) {
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') { [void]$lines.Add('') }
        [void]$lines.Add("[$Section]")
        [void]$lines.Add("$Key = $Value")
        return [string]::Join($newline, $lines)
    }
    $sectionStart = [int]$sectionStarts[0]
    $sectionEnd = $lines.Count
    for ($index = $sectionStart + 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*\[[^\]]+\]\s*$') { $sectionEnd = $index; break }
    }
    $keyIndexes = @()
    $keyPattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    for ($index = $sectionStart + 1; $index -lt $sectionEnd; $index++) {
        if ($lines[$index] -match $keyPattern) { $keyIndexes += $index }
    }
    if ($keyIndexes.Count -gt 1) { throw "Clé INI dupliquée dans [$Section] : $Key" }
    if ($keyIndexes.Count -eq 1) {
        $lines[[int]$keyIndexes[0]] = "$Key = $Value"
    }
    else {
        $lines.Insert($sectionEnd, "$Key = $Value")
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
    $packTarget = Assert-GameChildPath (Join-Path $gameFull $registryRelative)
    if (-not (Test-Path -LiteralPath $iniTarget -PathType Leaf)) {
        throw 'InfinityEngine-Enhancer.ini est absent.'
    }

    Copy-Item -LiteralPath $sourceDll -Destination $dllTarget -Force
    New-Item -ItemType Directory -Path (Split-Path -Parent $packTarget) -Force | Out-Null
    Copy-Item -LiteralPath $sourcePack -Destination $packTarget -Force

    $iniText = Get-Content -LiteralPath $iniTarget -Raw
    $iniText = Set-IniKey $iniText 'Shaders' 'EnableCreatureSpriteUpscaleTest' 'true'
    $iniText = Set-IniKey $iniText 'Shaders' 'EnableCreatureSpriteX2Test' 'false'
    $noFilter = $true
    if ($null -ne $job.PSObject.Properties['runtime'] -and
        $null -ne $job.runtime.PSObject.Properties['no_filter_comparison']) {
        $noFilter = [bool]$job.runtime.no_filter_comparison
    }
    if ($noFilter) {
        $iniText = Set-IniKey $iniText 'Rendering' 'EnableAnisotropicFiltering' 'false'
        $iniText = Set-IniKey $iniText 'Rendering' 'EnableFullFrameFXAA' 'false'
        $iniText = Set-IniKey $iniText 'Rendering' 'EnableFullFrameSSAA2x' 'false'
    }
    Set-Content -LiteralPath $iniTarget -Value $iniText -Encoding utf8 -NoNewline

    Assert-ExpectedHash $dllTarget $expectedDllSha256 'DLL installée'
    Assert-ExpectedHash $packTarget $expectedPackSha256 'Registre installé'
    $installedHeader = Read-RegistryHeader $packTarget
    if ($installedHeader.magic -ne 'IEECSXN' -or $installedHeader.version -ne 3 -or
        $installedHeader.scale -ne $scale) {
        throw 'En-tête du registre installé incompatible.'
    }
    $installedIni = Get-Content -LiteralPath $iniTarget -Raw
    if ((Get-IniKey $installedIni 'Shaders' 'EnableCreatureSpriteUpscaleTest') -ne 'true' -or
        (Get-IniKey $installedIni 'Shaders' 'EnableCreatureSpriteX2Test') -ne 'false') {
        throw 'Les flags xN/alias x2 ne correspondent pas au test xN.'
    }

    foreach ($targetState in $targets) {
        $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
        $present = Test-Path -LiteralPath $target -PathType Leaf
        $targetState.installed_present = $present
        $targetState.installed_sha256 = if ($present) { Get-Sha256 $target } else { $null }
    }
    $state.status = 'installed-pending-qa'
    $state.installed_dll_sha256 = Get-Sha256 $dllTarget
    $state.installed_ini_sha256 = Get-Sha256 $iniTarget
    $state.installed_pack_sha256 = Get-Sha256 $packTarget
    $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8
    $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $activeStatePath -Encoding utf8
}
catch {
    foreach ($targetState in $targets) {
        $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
        if ($targetState.existed_before) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-Item -LiteralPath $targetState.backup_path -Destination $target -Force
        }
        elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    $state.status = 'rolled-back-after-install-error'
    $state.error = $_.Exception.Message
    $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding utf8
    $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $activeStatePath -Encoding utf8
    throw
}

[pscustomobject]@{
    Status = $state.status
    Scale = $scale
    GameRoot = $gameFull
    DllSha256 = $state.installed_dll_sha256
    PackSha256 = $state.installed_pack_sha256
    Backup = $backupRoot
    State = $activeStatePath
}
