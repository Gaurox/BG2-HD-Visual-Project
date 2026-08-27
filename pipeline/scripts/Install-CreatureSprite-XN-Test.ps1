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

function Get-EngineSourceContractSha256([string]$SourceRoot) {
    $relativeFiles = @(
        'CMakeLists.txt',
        'src/iee/hooks.cpp',
        'src/iee/native_occlusion_bridge.cpp',
        'src/iee/native_occlusion_bridge.h',
        'src/iee/dll_main.cpp',
        'src/iee/bridge_transition.cpp',
        'src/iee/bridge_transition.h',
        'src/iee/creature_sprite_x2.cpp',
        'src/iee/creature_sprite_x2.h',
        'src/iee/core/config.cpp',
        'src/iee/core/config.h',
        'src/iee/core/native_occlusion_probe.cpp',
        'src/iee/core/native_occlusion_probe.h',
        'src/iee/game/build_manifest.cpp',
        'src/iee/game/build_manifest.h',
        'tests/iee_tests.cpp',
        'tests/bridge_worker_lifecycle_tests.cpp'
    )
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        foreach ($relative in $relativeFiles) {
            $path = Join-Path $SourceRoot ($relative.Replace('/', '\'))
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "Contrat source runtime incomplet : $relative"
            }
            [byte[]]$prefix = [System.Text.Encoding]::UTF8.GetBytes($relative + [char]0)
            [void]$sha.TransformBlock($prefix, 0, $prefix.Length, $prefix, 0)
            $stream = [System.IO.File]::OpenRead($path)
            try {
                [byte[]]$buffer = New-Object byte[] (1024 * 1024)
                while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                    [void]$sha.TransformBlock($buffer, 0, $read, $buffer, 0)
                }
            }
            finally {
                $stream.Dispose()
            }
        }
        [void]$sha.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($sha.Hash)).Replace('-', '')
    }
    finally {
        $sha.Dispose()
    }
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

function Write-TextAtomic([string]$Text, [string]$Path) {
    $parent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($Path))
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Dossier de destination absent : $parent"
    }
    $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Path) +
        '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $replaceBackup = $temporary + '.replace-backup'
    try {
        [System.IO.File]::WriteAllText(
            $temporary, $Text, (New-Object System.Text.UTF8Encoding($false)))
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
    finally {
        $sha.Dispose()
    }
    $mutex = New-Object System.Threading.Mutex($false, "Global\BG2UpscaleCreatureSpriteMutation_$key")
    $owned = $false
    try {
        $owned = $mutex.WaitOne(0)
    }
    catch [System.Threading.AbandonedMutexException] {
        $owned = $true
    }
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

function Get-Crc32([string]$Path) {
    if ($null -eq ('Bg2CreatureSpriteCrc32' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.IO;

public static class Bg2CreatureSpriteCrc32
{
    private static readonly uint[] Table = BuildTable();

    private static uint[] BuildTable()
    {
        uint[] table = new uint[256];
        for (uint index = 0; index < table.Length; ++index)
        {
            uint value = index;
            for (int bit = 0; bit < 8; ++bit)
                value = (value & 1U) != 0U ? (value >> 1) ^ 0xEDB88320U : value >> 1;
            table[index] = value;
        }
        return table;
    }

    public static uint Compute(string path)
    {
        uint crc = UInt32.MaxValue;
        byte[] buffer = new byte[1024 * 1024];
        using (FileStream stream = new FileStream(
            path, FileMode.Open, FileAccess.Read, FileShare.Read, buffer.Length,
            FileOptions.SequentialScan))
        {
            int read;
            while ((read = stream.Read(buffer, 0, buffer.Length)) > 0)
                for (int index = 0; index < read; ++index)
                    crc = (crc >> 8) ^ Table[(crc ^ buffer[index]) & 0xFFU];
        }
        return crc ^ UInt32.MaxValue;
    }
}
'@
    }
    return [Bg2CreatureSpriteCrc32]::Compute($Path)
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

function Get-MaxRegistryBytes([int]$Scale) {
    if ($Scale -eq 2) { return [uint64](128MB) }
    if ($Scale -eq 4) { return [uint64](512MB) }
    throw "Échelle sans plafond de registre : $Scale"
}

function Get-MaxLazyFrameIndexBytes() {
    return [uint64](128MB)
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
        $absoluteMaximum = Get-MaxRegistryBytes 4
        if ($stream.Length -lt 24 -or [uint64]$stream.Length -gt $absoluteMaximum) {
            throw "Taille de registre hors borne absolue 24 octets..512 Mio : $($stream.Length)"
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
        $maximumRegistryBytes = Get-MaxRegistryBytes ([int]$scale)
        if ([uint64]$stream.Length -gt $maximumRegistryBytes) {
            throw "Registre x$scale supérieur au plafond de $maximumRegistryBytes octets."
        }
        [uint64]$indexBytesTotal = 0
        [uint64]$frameCountTotal = 0
        $resourceNames = @()
        for ($resourceIndex = 0; $resourceIndex -lt $resourceCount; $resourceIndex++) {
            [byte[]]$resourceHeader = Read-ExactBytes $stream 48 'Ressource registre'
            $nameEnd = [System.Array]::IndexOf($resourceHeader, [byte]0, 0, 8)
            if ($nameEnd -eq -1) { $nameEnd = 8 }
            if ($nameEnd -lt 1) { throw 'Nom de ressource registre invalide.' }
            $resourceName = [System.Text.Encoding]::ASCII.GetString($resourceHeader, 0, $nameEnd)
            if ($resourceName -notmatch '^[A-Z0-9_]{1,8}$') {
                throw "Nom de ressource registre invalide : $resourceName"
            }
            for ($paddingIndex = $nameEnd; $paddingIndex -lt 8; $paddingIndex++) {
                if ($resourceHeader[$paddingIndex] -ne 0) {
                    throw "Padding de ressource registre invalide : $resourceName"
                }
            }
            if ($resourceNames -contains $resourceName) {
                throw "Ressource dupliquée dans le registre : $resourceName"
            }
            $resourceNames += $resourceName
            $frameCount = [System.BitConverter]::ToUInt32($resourceHeader, 40)
            $cycleCount = [System.BitConverter]::ToUInt32($resourceHeader, 44)
            if ($frameCount -lt 1 -or $frameCount -gt 4096 -or
                $cycleCount -lt 1 -or $cycleCount -gt 256) {
                throw 'Compteurs ressource registre invalides.'
            }
            $frameCountTotal += [uint64]$frameCount
            for ($frameIndex = 0; $frameIndex -lt $frameCount; $frameIndex++) {
                [byte[]]$frameHeader = Read-ExactBytes $stream 528 'Frame registre'
                $width = [System.BitConverter]::ToUInt16($frameHeader, 0)
                $height = [System.BitConverter]::ToUInt16($frameHeader, 2)
                $frameBytes = [System.BitConverter]::ToUInt32($frameHeader, 12)
                $expected = [uint64]$width * [uint64]$height * [uint64]$scale * [uint64]$scale
                if ($width -eq 0 -or $height -eq 0 -or
                    $frameHeader[9] -ne 0 -or $frameHeader[10] -ne 0 -or
                    $frameHeader[11] -ne 0 -or [uint64]$frameBytes -ne $expected -or
                    [uint64]$frameBytes -gt (Get-MaxLazyFrameIndexBytes)) {
                    throw 'Frame registre incompatible avec son échelle.'
                }
                Skip-RegistryBytes $stream ([uint64]$frameBytes) 'Payload frame registre'
                $indexBytesTotal += [uint64]$frameBytes
            }
            for ($cycleIndex = 0; $cycleIndex -lt $cycleCount; $cycleIndex++) {
                [byte[]]$cycleHeader = Read-ExactBytes $stream 4 'Cycle registre'
                $slots = [System.BitConverter]::ToUInt32($cycleHeader, 0)
                if ($slots -gt 65536) { throw 'Cycle registre invalide.' }
                Skip-RegistryBytes $stream ([uint64]$slots * 4) 'Lookup cycle registre'
            }
        }
        if ($stream.Position -ne $stream.Length) { throw 'Octets résiduels dans le registre.' }
        return [pscustomobject]@{
            magic = $magic
            version = $version
            scale = $scale
            resource_count = $resourceCount
            frame_count = $frameCountTotal
            animation_id = [System.BitConverter]::ToUInt32($header, 20)
            bytes = [uint64]$stream.Length
            index_bytes = $indexBytesTotal
            resources = $resourceNames
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Read-RegistrySet([string]$Path) {
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        if ($stream.Length -lt 120) { throw 'Index de registry-set tronqué.' }
        [byte[]]$header = Read-ExactBytes $stream 56 'En-tête registry-set'
        $magic = [System.Text.Encoding]::ASCII.GetString($header, 0, 7)
        if ($header[7] -ne 0) { $magic += '<non-nul>' }
        $version = [System.BitConverter]::ToUInt32($header, 8)
        $scale = [System.BitConverter]::ToUInt32($header, 12)
        $shardCount = [System.BitConverter]::ToUInt32($header, 16)
        $totalResources = [System.BitConverter]::ToUInt32($header, 20)
        $animationId = [System.BitConverter]::ToUInt32($header, 24)
        $reserved = [System.BitConverter]::ToUInt32($header, 28)
        $totalFrames = [System.BitConverter]::ToUInt64($header, 32)
        $totalIndexBytes = [System.BitConverter]::ToUInt64($header, 40)
        $totalRegistryBytes = [System.BitConverter]::ToUInt64($header, 48)
        if ($magic -ne 'IEECSNS' -or $version -ne 1 -or $scale -notin @(2, 4) -or
            $shardCount -lt 1 -or $shardCount -gt 64 -or
            $totalResources -lt 1 -or $totalResources -gt 8192 -or
            [uint64]$totalResources -gt [uint64]$shardCount * [uint64]128 -or
            $animationId -lt 1 -or $animationId -gt 65535 -or $reserved -ne 0 -or
            $totalFrames -lt 1 -or $totalFrames -gt [uint64]1048576 -or
            $totalIndexBytes -lt 1 -or $totalIndexBytes -gt [uint64](8GB) -or
            $totalRegistryBytes -lt 24 -or $totalRegistryBytes -gt [uint64](8GB) -or
            $totalIndexBytes -gt $totalRegistryBytes) {
            throw 'En-tête de registry-set invalide.'
        }
        $expectedLength = [uint64]56 + [uint64]64 * [uint64]$shardCount
        if ([uint64]$stream.Length -ne $expectedLength) {
            throw "Taille de registry-set invalide : $($stream.Length), attendu $expectedLength."
        }

        $entries = @()
        [uint64]$summedResources = 0
        [uint64]$summedFrames = 0
        [uint64]$summedIndexBytes = 0
        [uint64]$summedRegistryBytes = 0
        for ($index = 0; $index -lt $shardCount; $index++) {
            [byte[]]$entry = Read-ExactBytes $stream 64 "Entrée shard $index"
            [byte[]]$shaBytes = New-Object byte[] 32
            [System.Array]::Copy($entry, 0, $shaBytes, 0, 32)
            if (@($shaBytes | Where-Object { $_ -ne 0 }).Count -eq 0) {
                throw "SHA-256 nul pour le shard $index."
            }
            $sha256 = ([System.BitConverter]::ToString($shaBytes)).Replace('-', '')
            $crc32 = [System.BitConverter]::ToUInt32($entry, 32)
            $resourceCount = [System.BitConverter]::ToUInt32($entry, 36)
            $frameCount = [System.BitConverter]::ToUInt64($entry, 40)
            $indexBytes = [System.BitConverter]::ToUInt64($entry, 48)
            $registryBytes = [System.BitConverter]::ToUInt64($entry, 56)
            if ($resourceCount -lt 1 -or $resourceCount -gt 128 -or
                $frameCount -lt 1 -or
                $frameCount -gt [uint64]$resourceCount * [uint64]4096 -or
                $indexBytes -lt 1 -or
                $indexBytes -gt (Get-MaxRegistryBytes ([int]$scale)) -or
                $registryBytes -lt 24 -or
                $registryBytes -gt (Get-MaxRegistryBytes ([int]$scale)) -or
                $indexBytes -gt $registryBytes) {
                throw "Compteurs invalides pour le shard $index."
            }
            $entries += [pscustomobject]@{
                index = $index
                sha256 = $sha256
                crc32 = [uint32]$crc32
                resource_count = $resourceCount
                frame_count = $frameCount
                index_bytes = $indexBytes
                registry_bytes = $registryBytes
            }
            $summedResources += [uint64]$resourceCount
            $summedFrames += $frameCount
            $summedIndexBytes += $indexBytes
            $summedRegistryBytes += $registryBytes
        }
        if ($summedResources -ne [uint64]$totalResources -or
            $summedFrames -ne $totalFrames -or
            $summedIndexBytes -ne $totalIndexBytes -or
            $summedRegistryBytes -ne $totalRegistryBytes) {
            throw 'Les totaux du registry-set diffèrent de la somme de ses shards.'
        }
        return [pscustomobject]@{
            magic = $magic
            version = $version
            scale = $scale
            shard_count = $shardCount
            total_resources = $totalResources
            animation_id = $animationId
            total_frames = $totalFrames
            total_index_bytes = $totalIndexBytes
            total_registry_bytes = $totalRegistryBytes
            bytes = [uint64]$stream.Length
            entries = $entries
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

$currentAdapterPath = Join-Path $workspaceRoot 'pipeline\scripts\xbr2x_batch.js'
$currentAdapterSha256 = Get-Sha256 $currentAdapterPath
if (-not $isArmorSet) {
    $sourceManifestPath = Resolve-JobPath ([string](Get-RequiredProperty $buildManifest 'source_manifest' 'build'))
    $sourceRoot = Resolve-JobPath ([string](Get-RequiredProperty $job.paths 'source_dir' 'job.paths'))
    if (-not $sourceRoot.StartsWith($workspaceRoot + '\',
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Source du job hors workspace : $sourceRoot"
    }
    $expectedSourceManifestPath = [System.IO.Path]::GetFullPath(
        (Join-Path $sourceRoot 'manifest.json'))
    if (-not [string]::Equals([System.IO.Path]::GetFullPath($sourceManifestPath),
            $expectedSourceManifestPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'build.source_manifest ne désigne pas le manifeste source canonique du job.'
    }
    Assert-ExpectedHash $sourceManifestPath `
        ([string](Get-RequiredProperty $buildManifest 'source_manifest_sha256' 'build')) `
        'Manifeste source du build'
    $scalepixPath = Resolve-JobPath ([string](Get-RequiredProperty $job.paths 'scalepix' 'job.paths'))
    Assert-ExpectedHash $scalepixPath `
        ([string](Get-RequiredProperty $buildManifest 'scalepix_sha256' 'build')) `
        'Scalepix du build'
    $expectedAdapterSha256 = [string](Get-RequiredProperty $buildManifest 'xbr_adapter_sha256' 'build')
    if (-not [string]::Equals($currentAdapterSha256, $expectedAdapterSha256,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Le contrat de l'adaptateur xBR diffère du build."
    }
}
else {
    $members = @(Get-RequiredProperty $buildManifest 'members' 'build')
    if ($members.Count -lt 1 -or $members.Count -gt 8192) {
        throw 'build.members est hors contrat.'
    }
    $seenMemberJobs = @{}
    foreach ($member in $members) {
        $memberJobPath = Resolve-JobPath ([string](Get-RequiredProperty $member 'job_file' 'build.members[]'))
        if (-not $memberJobPath.StartsWith($workspaceRoot + '\',
                [System.StringComparison]::OrdinalIgnoreCase) -or
            -not (Test-Path -LiteralPath $memberJobPath -PathType Leaf)) {
            throw "Job membre absent ou hors workspace : $memberJobPath"
        }
        $memberJobKey = [System.IO.Path]::GetFullPath($memberJobPath).ToUpperInvariant()
        if ($seenMemberJobs.ContainsKey($memberJobKey)) {
            throw "Job membre dupliqué : $memberJobPath"
        }
        $seenMemberJobs[$memberJobKey] = $true
        $memberJob = Get-Content -LiteralPath $memberJobPath -Raw | ConvertFrom-Json
        Assert-OrdinalEqual ([string](Get-RequiredProperty $memberJob 'job_id' 'member job')) `
            ([string](Get-RequiredProperty $member 'job_id' 'build.members[]')) 'member job_id'
        if (-not [string]::Equals(
                [string](Get-RequiredProperty $memberJob.animation 'bam_prefix' 'member job.animation'),
                [string](Get-RequiredProperty $member 'bam_prefix' 'build.members[]'),
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Le préfixe BAM d'un job membre diffère du build."
        }
        $memberRunRoot = Resolve-JobPath ([string](Get-RequiredProperty $memberJob.paths 'run_dir' 'member job.paths'))
        if (-not $memberRunRoot.StartsWith($workspaceRoot + '\',
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Run membre hors workspace : $memberRunRoot"
        }
        $memberSourceRoot = Resolve-JobPath `
            ([string](Get-RequiredProperty $memberJob.paths 'source_dir' 'member job.paths'))
        if (-not $memberSourceRoot.StartsWith($workspaceRoot + '\',
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Source membre hors workspace : $memberSourceRoot"
        }
        $memberSourceManifest = Join-Path $memberSourceRoot 'manifest.json'
        $memberBuildManifestPath = Join-Path $memberRunRoot 'build\build-manifest.json'
        $memberSourceSha256 = [string](Get-RequiredProperty $member 'source_manifest_sha256' 'build.members[]')
        Assert-ExpectedHash $memberSourceManifest $memberSourceSha256 'Manifeste source membre'
        Assert-ExpectedHash $memberBuildManifestPath `
            ([string](Get-RequiredProperty $member 'build_manifest_sha256' 'build.members[]')) `
            'Manifeste build membre'
        $memberBuildManifest = Get-Content -LiteralPath $memberBuildManifestPath -Raw | ConvertFrom-Json
        $declaredMemberSourceManifest = Resolve-JobPath `
            ([string](Get-RequiredProperty $memberBuildManifest 'source_manifest' 'member build'))
        if (-not [string]::Equals([System.IO.Path]::GetFullPath($declaredMemberSourceManifest),
                [System.IO.Path]::GetFullPath($memberSourceManifest),
                [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Le manifeste build membre ne désigne pas sa source canonique."
        }
        if (-not [string]::Equals(
                [string](Get-RequiredProperty $memberBuildManifest 'source_manifest_sha256' 'member build'),
                $memberSourceSha256, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'Le manifeste build membre ne correspond pas à sa source courante.'
        }
        $memberScalepixPath = Resolve-JobPath `
            ([string](Get-RequiredProperty $memberJob.paths 'scalepix' 'member job.paths'))
        Assert-ExpectedHash $memberScalepixPath `
            ([string](Get-RequiredProperty $memberBuildManifest 'scalepix_sha256' 'member build')) `
            'Scalepix membre'
        $memberAdapterSha256 = [string](Get-RequiredProperty $memberBuildManifest 'xbr_adapter_sha256' 'member build')
        $memberExplicit = $null -ne $memberJob.PSObject.Properties['upscale']
        $legacyAdapterSha256 = '11FE3B2F1ACAAA0F141E282D86FFE28D7A8DB0B86AFFCEDB8A16741F141FC1D4'
        if (-not [string]::Equals($memberAdapterSha256, $currentAdapterSha256,
                [System.StringComparison]::OrdinalIgnoreCase) -and
            ($memberExplicit -or -not [string]::Equals($memberAdapterSha256,
                    $legacyAdapterSha256, [System.StringComparison]::OrdinalIgnoreCase))) {
            throw "Le contrat de l'adaptateur xBR d'un membre diffère du pipeline."
        }
    }
}

Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'schema' 'runtime')) 'bg2-upscale-creature-sprite-runtime-v1' 'runtime.schema'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'status' 'runtime')) 'built-tested' 'runtime.status'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'tests_status' 'runtime')) 'passed' 'runtime.tests_status'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'bridge_worker_tests_status' 'runtime')) 'passed' 'runtime.bridge_worker_tests_status'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'job_id' 'runtime')) ([string]$job.job_id) 'runtime.job_id'
Assert-OrdinalEqual ([string](Get-RequiredProperty $runtimeManifest 'runtime_profile' 'runtime')) $runtimeProfile 'runtime.runtime_profile'
$engineSource = Resolve-JobPath ([string](Get-RequiredProperty $job.paths 'engine_source' 'job.paths'))
$manifestEngineSource = Resolve-JobPath ([string](Get-RequiredProperty $runtimeManifest 'engine_source' 'runtime'))
if (-not [string]::Equals([System.IO.Path]::GetFullPath($engineSource).TrimEnd('\'),
        [System.IO.Path]::GetFullPath($manifestEngineSource).TrimEnd('\'),
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'runtime.engine_source diffère du job.'
}
$expectedSourceContract = [string](Get-RequiredProperty $runtimeManifest 'engine_source_contract_sha256' 'runtime')
if ($expectedSourceContract -notmatch '^[0-9A-Fa-f]{64}$') {
    throw 'runtime.engine_source_contract_sha256 invalide.'
}
$actualSourceContract = Get-EngineSourceContractSha256 $engineSource
if (-not [string]::Equals($actualSourceContract, $expectedSourceContract,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Le contrat source runtime a changé : $actualSourceContract, attendu $expectedSourceContract"
}

$sourceDll = Resolve-ManifestChild $runtimeRoot ([string](Get-RequiredProperty $runtimeManifest 'dll' 'runtime')) 'runtime.dll'
$expectedDllSha256 = [string](Get-RequiredProperty $runtimeManifest 'dll_sha256' 'runtime')
$expectedExeSha256 = [string](Get-RequiredProperty $job.compatibility 'baldur_real_sha256' 'job.compatibility')
Assert-ExpectedHash $sourceDll $expectedDllSha256 'DLL construite et testée'

$registryLayoutDeclared = $null -ne $buildManifest.PSObject.Properties['registry_layout']
$registryLayout = 'monolith'
if ($registryLayoutDeclared) {
    $registryLayout = [string]$buildManifest.registry_layout
}
if ($registryLayout -notin @('monolith', 'set')) {
    throw "build.registry_layout non supporté : $registryLayout"
}

$animationIdText = [string](Get-RequiredProperty $job.animation 'id' 'job.animation')
if ($animationIdText -notmatch '^0x[0-9A-Fa-f]{4}$') { throw 'job.animation.id invalide.' }
$animationId = [Convert]::ToUInt32($animationIdText.Substring(2), 16)
$resourceCount = [uint64](Get-RequiredProperty $buildManifest 'resource_count' 'build')
$frameCount = [uint64](Get-RequiredProperty $buildManifest 'frame_count' 'build')
$registryBytes = [uint64](Get-RequiredProperty $buildManifest 'registry_bytes' 'build')
if ($resourceCount -lt 1 -or $resourceCount -gt 8192) {
    throw 'build.resource_count est hors contrat.'
}
if ($frameCount -lt 1 -or $frameCount -gt [uint64]1048576 -or
    $registryBytes -lt 24 -or $registryBytes -gt [uint64](8GB)) {
    throw 'Les compteurs globaux du build sont hors contrat.'
}

$registryRelative = $null
$sourcePack = $null
$expectedPackSha256 = $null
$registrySetRelative = $null
$sourceRegistrySet = $null
$expectedRegistrySetSha256 = $null
$registrySetInfo = $null
$sourceShards = @()
$globalResourceNames = @()

if ($registryLayout -eq 'monolith') {
    $registryRelative = ([string](Get-RequiredProperty $buildManifest 'registry' 'build')).Replace('/', '\')
    Assert-OrdinalEqual $registryRelative 'iee-assets\creature-sprites\CreatureSprites-XN.registry' 'build.registry'
    $sourcePack = Resolve-ManifestChild $buildRoot $registryRelative 'build.registry'
    $expectedPackSha256 = [string](Get-RequiredProperty $buildManifest 'registry_sha256' 'build')
    Assert-ExpectedHash $sourcePack $expectedPackSha256 'Registre sprite xN'
    $header = Read-RegistryHeader $sourcePack
    if ($header.magic -ne 'IEECSXN' -or $header.version -ne 3 -or
        $header.scale -ne $scale -or $header.animation_id -ne $animationId) {
        throw 'En-tête du registre monolithique incompatible avec le job.'
    }
    if ($resourceCount -gt 128 -or [uint64]$header.resource_count -ne $resourceCount -or
        [uint64]$header.frame_count -ne $frameCount -or
        [uint64]$header.bytes -ne $registryBytes) {
        throw 'Les compteurs du registre monolithique diffèrent du build.'
    }
    if ($registryLayoutDeclared) {
        if ($null -eq $buildManifest.PSObject.Properties['registry_set'] -or
            $null -ne $buildManifest.registry_set -or
            $null -eq $buildManifest.PSObject.Properties['registry_set_sha256'] -or
            $null -ne $buildManifest.registry_set_sha256 -or
            $null -eq $buildManifest.PSObject.Properties['registry_set_bytes'] -or
            $null -ne $buildManifest.registry_set_bytes -or
            @(Get-RequiredProperty $buildManifest 'shards' 'build').Count -ne 0 -or
            [uint64](Get-RequiredProperty $buildManifest 'total_resources' 'build') -ne $resourceCount -or
            [uint64](Get-RequiredProperty $buildManifest 'total_frames' 'build') -ne $frameCount -or
            [uint64](Get-RequiredProperty $buildManifest 'total_index_bytes' 'build') -ne [uint64]$header.index_bytes -or
            [uint64](Get-RequiredProperty $buildManifest 'total_registry_bytes' 'build') -ne $registryBytes) {
            throw 'Les champs de layout monolithique du build sont incompatibles.'
        }
    }
    $globalResourceNames = @($header.resources)
}
else {
    if ($null -eq $buildManifest.PSObject.Properties['registry'] -or
        $null -ne $buildManifest.registry -or
        $null -eq $buildManifest.PSObject.Properties['registry_sha256'] -or
        $null -ne $buildManifest.registry_sha256) {
        throw 'Un registry-set exige build.registry=null et build.registry_sha256=null.'
    }
    $registrySetRelative = ([string](Get-RequiredProperty $buildManifest 'registry_set' 'build')).Replace('/', '\')
    Assert-OrdinalEqual $registrySetRelative 'iee-assets\creature-sprites\CreatureSprites-XN.set' 'build.registry_set'
    $sourceRegistrySet = Resolve-ManifestChild $buildRoot $registrySetRelative 'build.registry_set'
    $expectedRegistrySetSha256 = [string](Get-RequiredProperty $buildManifest 'registry_set_sha256' 'build')
    Assert-ExpectedHash $sourceRegistrySet $expectedRegistrySetSha256 'Index registry-set xN'
    $registrySetInfo = Read-RegistrySet $sourceRegistrySet
    if ($registrySetInfo.scale -ne $scale -or $registrySetInfo.animation_id -ne $animationId) {
        throw 'En-tête du registry-set incompatible avec le job.'
    }

    $manifestShards = @(Get-RequiredProperty $buildManifest 'shards' 'build')
    if ($manifestShards.Count -ne $registrySetInfo.shard_count) {
        throw 'build.shards diffère du nombre de shards indexés.'
    }
    for ($index = 0; $index -lt $manifestShards.Count; $index++) {
        $manifestShard = $manifestShards[$index]
        if ([int](Get-RequiredProperty $manifestShard 'index' "build.shards[$index]") -ne $index) {
            throw "Index de shard non contigu à la position $index."
        }
        $expectedRelative = 'iee-assets\creature-sprites\CreatureSprites-XN-{0:D4}.registry' -f $index
        $shardRelative = ([string](Get-RequiredProperty $manifestShard 'registry' "build.shards[$index]")).Replace('/', '\')
        Assert-OrdinalEqual $shardRelative $expectedRelative "build.shards[$index].registry"
        $sourceShard = Resolve-ManifestChild $buildRoot $shardRelative "build.shards[$index].registry"
        $expectedSha256 = [string](Get-RequiredProperty $manifestShard 'sha256' "build.shards[$index]")
        Assert-ExpectedHash $sourceShard $expectedSha256 "Shard xN $index"
        [uint64]$manifestCrc64 = [uint64](Get-RequiredProperty $manifestShard 'crc32' "build.shards[$index]")
        if ($manifestCrc64 -gt [uint64][uint32]::MaxValue) {
            throw "CRC32 manifeste hors contrat pour le shard $index."
        }
        [uint32]$actualCrc32 = Get-Crc32 $sourceShard
        $shardHeader = Read-RegistryHeader $sourceShard
        $setEntry = $registrySetInfo.entries[$index]
        if ($shardHeader.magic -ne 'IEECSXN' -or $shardHeader.version -ne 3 -or
            $shardHeader.scale -ne $scale -or $shardHeader.animation_id -ne $animationId) {
            throw "En-tête incompatible pour le shard $index."
        }
        if (-not [string]::Equals($expectedSha256, [string]$setEntry.sha256,
                [System.StringComparison]::OrdinalIgnoreCase) -or
            $actualCrc32 -ne [uint32]$setEntry.crc32 -or
            $manifestCrc64 -ne [uint64]$setEntry.crc32 -or
            [uint64](Get-RequiredProperty $manifestShard 'resource_count' "build.shards[$index]") -ne [uint64]$setEntry.resource_count -or
            [uint64](Get-RequiredProperty $manifestShard 'frame_count' "build.shards[$index]") -ne [uint64]$setEntry.frame_count -or
            [uint64](Get-RequiredProperty $manifestShard 'index_bytes' "build.shards[$index]") -ne [uint64]$setEntry.index_bytes -or
            [uint64](Get-RequiredProperty $manifestShard 'registry_bytes' "build.shards[$index]") -ne [uint64]$setEntry.registry_bytes -or
            [uint64]$shardHeader.resource_count -ne [uint64]$setEntry.resource_count -or
            [uint64]$shardHeader.frame_count -ne [uint64]$setEntry.frame_count -or
            [uint64]$shardHeader.index_bytes -ne [uint64]$setEntry.index_bytes -or
            [uint64]$shardHeader.bytes -ne [uint64]$setEntry.registry_bytes) {
            throw "Manifeste, index et contenu diffèrent pour le shard $index."
        }
        foreach ($resourceName in @($shardHeader.resources)) {
            if ($globalResourceNames -contains $resourceName) {
                throw "Ressource dupliquée entre shards : $resourceName"
            }
            $globalResourceNames += $resourceName
        }
        $sourceShards += [pscustomobject]@{
            index = $index
            relative_path = $shardRelative
            source_path = $sourceShard
            sha256 = $expectedSha256
            crc32 = [uint32]$actualCrc32
            header = $shardHeader
        }
    }
    $sourceShardNames = @(Get-ChildItem -LiteralPath (Split-Path -Parent $sourceRegistrySet) -File -ErrorAction Stop |
        Where-Object { $_.Name -match '^CreatureSprites-XN-[0-9]{4}\.registry$' } |
        ForEach-Object { $_.Name } | Sort-Object)
    $expectedSourceShardNames = @($sourceShards |
        ForEach-Object { Split-Path -Leaf $_.relative_path } | Sort-Object)
    if (($sourceShardNames -join '|') -cne ($expectedSourceShardNames -join '|')) {
        throw 'Les noms des shards source ne sont pas contigus et exacts.'
    }
    if ([uint64]$registrySetInfo.total_resources -ne $resourceCount -or
        [uint64]$registrySetInfo.total_frames -ne $frameCount -or
        [uint64]$registrySetInfo.total_registry_bytes -ne $registryBytes -or
        [uint64](Get-RequiredProperty $buildManifest 'registry_set_bytes' 'build') -ne [uint64]$registrySetInfo.bytes -or
        [uint64](Get-RequiredProperty $buildManifest 'total_resources' 'build') -ne $resourceCount -or
        [uint64](Get-RequiredProperty $buildManifest 'total_frames' 'build') -ne $frameCount -or
        [uint64](Get-RequiredProperty $buildManifest 'total_index_bytes' 'build') -ne [uint64]$registrySetInfo.total_index_bytes -or
        [uint64](Get-RequiredProperty $buildManifest 'total_registry_bytes' 'build') -ne $registryBytes) {
        throw "Les totaux du build, de l'index et des shards diffèrent."
    }
}

if ($registryLayoutDeclared -or $isArmorSet) {
    $layoutValidation = Get-RequiredProperty $buildManifest 'validation' 'build'
    $expectedShardCount = if ($registryLayout -eq 'set') { $sourceShards.Count } else { 1 }
    if ([int](Get-RequiredProperty $layoutValidation 'shard_count' 'build.validation') -ne $expectedShardCount -or
        [int](Get-RequiredProperty $layoutValidation 'maximum_shard_resources' 'build.validation') -ne 128 -or
        [uint64](Get-RequiredProperty $layoutValidation 'maximum_shard_bytes' 'build.validation') -ne (Get-MaxRegistryBytes $scale) -or
        [int](Get-RequiredProperty $layoutValidation 'maximum_set_shards' 'build.validation') -ne 64 -or
        [int](Get-RequiredProperty $layoutValidation 'maximum_set_resources' 'build.validation') -ne 8192 -or
        [uint64](Get-RequiredProperty $layoutValidation 'maximum_set_frames' 'build.validation') -ne [uint64]1048576 -or
        [uint64](Get-RequiredProperty $layoutValidation 'maximum_set_registry_bytes' 'build.validation') -ne [uint64](8GB)) {
        throw 'Les limites déclarées dans build.validation diffèrent du contrat xN.'
    }
}

if ($isArmorSet) {
    $sourceFormats = @(Get-RequiredProperty $buildManifest 'source_registry_formats' 'build')
    if ($sourceFormats.Count -lt 1) { throw 'build.source_registry_formats est vide.' }
    $promotionRequired = $false
    foreach ($format in $sourceFormats) {
        $formatMagic = [string](Get-RequiredProperty $format 'registry_magic' 'build.source_registry_formats')
        $formatVersion = [int](Get-RequiredProperty $format 'registry_version' 'build.source_registry_formats')
        $formatScale = [int](Get-RequiredProperty $format 'scale' 'build.source_registry_formats')
        $isLegacyX2 = $formatMagic -eq 'IEECSX2' -and $formatVersion -eq 2 -and $formatScale -eq 2
        $isXn = $formatMagic -eq 'IEECSXN' -and $formatVersion -eq 3 -and $formatScale -eq $scale
        if (($scale -eq 4 -and -not $isXn) -or ($scale -eq 2 -and -not ($isLegacyX2 -or $isXn))) {
            throw 'build.source_registry_formats contient un contrat incompatible.'
        }
        if ($isLegacyX2) { $promotionRequired = $true }
    }
    $promotedToXn = Get-RequiredProperty $buildManifest 'promoted_to_xn' 'build'
    if ($promotedToXn -isnot [bool] -or [bool]$promotedToXn -ne $promotionRequired) {
        throw 'build.promoted_to_xn diffère des formats sources.'
    }
}

$metricName = if ($isArmorSet) { "x${scale}_index_bytes" } else { "x${scale}_pixel_count" }
$expectedIndexBytes = if ($registryLayout -eq 'set') {
    [uint64]$registrySetInfo.total_index_bytes
} else {
    [uint64]$header.index_bytes
}
if ([uint64](Get-RequiredProperty $buildManifest $metricName 'build') -ne $expectedIndexBytes) {
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
$gameMutationMutex = Enter-GameMutationMutex $gameFull
try {
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
        if ($candidateState.status -in @('installing', 'restoring', 'installed-pending-qa', 'validated-installed', 'qa-failed')) {
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
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss.fffffffZ') +
    "-$PID-$([Guid]::NewGuid().ToString('N'))"
$backupRoot = Join-Path $runRoot "ingame-test\backups\$stamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

# Sauvegarder l'ensemble du namespace actif avant toute mutation : index, monolithe,
# fallback V2, shards cibles et tous les shards préexistants au nom canonique. Cela
# permet de retirer les shards obsolètes sans perdre leur présence initiale.
$relativeTargets = [System.Collections.Generic.List[string]]::new()
foreach ($relative in @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.ini',
    'iee-assets\creature-sprites\CreatureSprites-XN.registry',
    'iee-assets\creature-sprites\CreatureSprites-X2.registry',
    'iee-assets\creature-sprites\CreatureSprites-XN.set'
)) {
    [void]$relativeTargets.Add($relative)
}
foreach ($shard in $sourceShards) {
    [void]$relativeTargets.Add([string]$shard.relative_path)
}
$gameSpriteRoot = Assert-GameChildPath (Join-Path $gameFull 'iee-assets\creature-sprites')
if (Test-Path -LiteralPath $gameSpriteRoot -PathType Container) {
    foreach ($existingShard in Get-ChildItem -LiteralPath $gameSpriteRoot -File -ErrorAction Stop) {
        if ($existingShard.Name -match '^CreatureSprites-XN-[0-9]{4}\.registry$') {
            [void]$relativeTargets.Add("iee-assets\creature-sprites\$($existingShard.Name)")
        }
    }
}
$relativeTargets = @($relativeTargets | Sort-Object -Unique)
if ($relativeTargets.Count -gt 69) {
    throw 'Plus de 64 shards canoniques sont présents ou ciblés ; nettoyer via leur état propriétaire.'
}
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
    schema = 'bg2-upscale-creature-sprite-xn-ingame-test-v2'
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
    registry_layout = $registryLayout
    registry_relative_path = if ($registryLayout -eq 'set') { $registrySetRelative } else { $registryRelative }
    registry_magic = 'IEECSXN'
    registry_version = 3
    registry_scale = $scale
    registry_set_magic = if ($registryLayout -eq 'set') { 'IEECSNS' } else { $null }
    registry_set_version = if ($registryLayout -eq 'set') { 1 } else { $null }
    registry_shard_count = if ($registryLayout -eq 'set') { $sourceShards.Count } else { 0 }
    resource_family = ($prefixes -join ',')
    animation_id = $animationIdText
    runtime_profile = $runtimeProfile
    resources = $resourceCount
    frames = $frameCount
    source_dll_sha256 = $expectedDllSha256
    source_pack_sha256 = if ($registryLayout -eq 'set') { $expectedRegistrySetSha256 } else { $expectedPackSha256 }
    source_shards = @($sourceShards | ForEach-Object {
        [ordered]@{
            index = $_.index
            relative_path = $_.relative_path
            sha256 = $_.sha256
            crc32 = $_.crc32
        }
    })
    backup_root = $backupRoot
    targets = $targets
}
$statePath = Join-Path $backupRoot 'install-state.json'
Write-JsonAtomic $state $statePath 8
# Publier l'état récupérable avant la première mutation du jeu. En cas d'arrêt
# brutal, Restore-CreatureSprite-XN-Test.ps1 -RecoverInstalling retrouve les
# sauvegardes validées via ce pointeur stable.
New-Item -ItemType Directory -Path (Split-Path -Parent $activeStatePath) -Force | Out-Null
Write-JsonAtomic $state $activeStatePath 8

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
    $keyPattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    $keyIndexes = @()
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
        # Le parseur runtime conserve la valeur au fil des sections répétées.
        # Une seule insertion dans la première occurrence est donc suffisante et
        # préserve intégralement les autres blocs [Section].
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
    $packRelative = if ($registryLayout -eq 'set') { $registrySetRelative } else { $registryRelative }
    $packTarget = Assert-GameChildPath (Join-Path $gameFull $packRelative)
    if (-not (Test-Path -LiteralPath $iniTarget -PathType Leaf)) {
        throw 'InfinityEngine-Enhancer.ini est absent.'
    }

    Copy-Item -LiteralPath $sourceDll -Destination $dllTarget -Force

    # Désactiver d'abord tout layout XN antérieur. Pour un set, les shards sont
    # copiés et validés avant que l'index soit publié en dernier.
    foreach ($targetState in $targets) {
        $relative = [string]$targetState.relative_path
        if ($relative -in @(
                'iee-assets\creature-sprites\CreatureSprites-XN.registry',
                'iee-assets\creature-sprites\CreatureSprites-XN.set'
            ) -or $relative -match '^iee-assets\\creature-sprites\\CreatureSprites-XN-[0-9]{4}\.registry$') {
            $target = Assert-GameChildPath (Join-Path $gameFull $relative)
            if (Test-Path -LiteralPath $target -PathType Leaf) {
                Remove-Item -LiteralPath $target -Force
            }
        }
    }

    if ($registryLayout -eq 'set') {
        foreach ($shard in $sourceShards) {
            $shardTarget = Assert-GameChildPath (Join-Path $gameFull $shard.relative_path)
            New-Item -ItemType Directory -Path (Split-Path -Parent $shardTarget) -Force | Out-Null
            Copy-Item -LiteralPath $shard.source_path -Destination $shardTarget -Force
            Assert-ExpectedHash $shardTarget $shard.sha256 "Shard installé $($shard.index)"
            if ((Get-Crc32 $shardTarget) -ne [uint32]$shard.crc32) {
                throw "CRC32 du shard installé $($shard.index) incompatible."
            }
            $installedShardHeader = Read-RegistryHeader $shardTarget
            if ($installedShardHeader.magic -ne 'IEECSXN' -or
                $installedShardHeader.version -ne 3 -or
                $installedShardHeader.scale -ne $scale -or
                $installedShardHeader.animation_id -ne $animationId) {
                throw "En-tête du shard installé $($shard.index) incompatible."
            }
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $packTarget) -Force | Out-Null
        Copy-Item -LiteralPath $sourceRegistrySet -Destination $packTarget -Force
    }
    else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $packTarget) -Force | Out-Null
        Copy-Item -LiteralPath $sourcePack -Destination $packTarget -Force
    }

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
    Write-TextAtomic $iniText $iniTarget

    Assert-ExpectedHash $dllTarget $expectedDllSha256 'DLL installée'
    $installedPackSha256 = if ($registryLayout -eq 'set') {
        $expectedRegistrySetSha256
    } else {
        $expectedPackSha256
    }
    Assert-ExpectedHash $packTarget $installedPackSha256 'Layout XN installé'
    if ($registryLayout -eq 'set') {
        $installedSet = Read-RegistrySet $packTarget
        if ($installedSet.scale -ne $scale -or $installedSet.animation_id -ne $animationId -or
            $installedSet.shard_count -ne $sourceShards.Count) {
            throw 'Index du registry-set installé incompatible.'
        }
    }
    else {
        $installedHeader = Read-RegistryHeader $packTarget
        if ($installedHeader.magic -ne 'IEECSXN' -or $installedHeader.version -ne 3 -or
            $installedHeader.scale -ne $scale -or $installedHeader.animation_id -ne $animationId) {
            throw 'En-tête du registre installé incompatible.'
        }
    }
    $installedShardNames = @()
    if (Test-Path -LiteralPath $gameSpriteRoot -PathType Container) {
        $installedShardNames = @(Get-ChildItem -LiteralPath $gameSpriteRoot -File -ErrorAction Stop |
            Where-Object { $_.Name -match '^CreatureSprites-XN-[0-9]{4}\.registry$' } |
            ForEach-Object { $_.Name } | Sort-Object)
    }
    $expectedShardNames = if ($registryLayout -eq 'set') {
        @($sourceShards | ForEach-Object { Split-Path -Leaf $_.relative_path } | Sort-Object)
    } else {
        @()
    }
    if (($installedShardNames -join '|') -cne ($expectedShardNames -join '|')) {
        throw 'La liste des shards installés contient un shard absent ou obsolète.'
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
    Write-JsonAtomic $state $statePath 8
    Write-JsonAtomic $state $activeStatePath 8
}
catch {
    $installError = $_.Exception.Message
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
    foreach ($targetState in $targets) {
        $target = Assert-GameChildPath (Join-Path $gameFull $targetState.relative_path)
        if ($targetState.existed_before) {
            if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
                -not [string]::Equals((Get-Sha256 $target), [string]$targetState.original_sha256,
                    [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Rollback d'installation non fidèle : $($targetState.relative_path)"
            }
        }
        elseif (Test-Path -LiteralPath $target -PathType Leaf) {
            throw "Fichier ajouté subsistant après rollback : $($targetState.relative_path)"
        }
    }
    $state.status = 'rolled-back-after-install-error'
    $state.error = $installError
    Write-JsonAtomic $state $statePath 8
    Write-JsonAtomic $state $activeStatePath 8
    throw
}

$result = [pscustomobject]@{
    Status = $state.status
    Scale = $scale
    GameRoot = $gameFull
    DllSha256 = $state.installed_dll_sha256
    PackSha256 = $state.installed_pack_sha256
    RegistryLayout = $registryLayout
    Backup = $backupRoot
    State = $activeStatePath
}
$result
}
finally {
    Exit-GameMutationMutex $gameMutationMutex
}
