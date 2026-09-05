[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SourceBundle,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$BundleId = 'iee-0.1.0-alpha.7'
)

$ErrorActionPreference = 'Stop'

function Get-BundleFile([string]$Root, [string]$RelativePath) {
    $path = Join-Path $Root $RelativePath.Replace('/', '\')
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Fichier du bundle absent : $RelativePath" }
    return Get-Item -LiteralPath $path
}

$expectedFiles = @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.sample.ini',
    'iee-textures/iee_water_dudv.rgba',
    'iee-textures/iee_water_foam.rgba',
    'iee-textures/iee_water_normal.rgba',
    'iee-textures/README.md',
    'override/fpSEAM.glsl',
    'override/M_IEEE.lua'
)
$sourceRoot = (Resolve-Path -LiteralPath $SourceBundle).Path
$actualFiles = Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | ForEach-Object {
    [IO.Path]::GetRelativePath($sourceRoot, $_.FullName).Replace('\', '/')
} | Sort-Object
if (Compare-Object -ReferenceObject ($expectedFiles | Sort-Object) -DifferenceObject $actualFiles) {
    throw 'Le bundle source contient un inventaire different de celui approuve pour alpha.'
}

# AR0413 relies on runtime classification of its stock WTOIL overlay. A stale
# renderer binary can still pass the file inventory and hash generation steps,
# while silently disabling the oil mask in game. Keep the required classifiers
# as a freeze-time contract so that source/binary drift cannot recur.
$rendererDll = Get-BundleFile $sourceRoot 'InfinityEngine-Enhancer.dll'
$rendererBinaryText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($rendererDll.FullName))
foreach ($marker in @('WTSEW', 'WTOIL', 'AreaAnimations-X4.registry', 'TimedTimeline', 'EnableAreaAnimationX4', 'EnableNativeOcclusionBridge', 'FXRenderClippingPolys', 'LoadArea')) {
    if ($rendererBinaryText.IndexOf($marker, [StringComparison]::Ordinal) -lt 0) {
        throw "DLL renderer obsolete : classificateur liquide absent du binaire ($marker)."
    }
}

$destination = Join-Path $ReleaseRoot (Join-Path 'release-inputs/renderer' $BundleId)
if (Test-Path -LiteralPath $destination) { throw "Destination deja existante : $destination" }
New-Item -ItemType Directory -Path $destination | Out-Null
foreach ($relativePath in $expectedFiles) {
    $sourceFile = Get-BundleFile $sourceRoot $relativePath
    $destinationFile = Join-Path $destination $relativePath.Replace('/', '\')
    New-Item -ItemType Directory -Path (Split-Path -Parent $destinationFile) -Force | Out-Null
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $destinationFile
}

$files = foreach ($relativePath in $expectedFiles) {
    $file = Get-BundleFile $destination $relativePath
    [ordered]@{
        path = $relativePath
        bytes = $file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}
$record = [ordered]@{
    '$schema' = '../schemas/renderer-bundle.schema.json'
    schema_version = 1
    bundle_id = $BundleId
    status = 'frozen-awaiting-clean-game-validation'
    source_tree = 'engine/InfinityEngine-Enhancer/source-patchee'
    build_environment = [ordered]@{
        cmake = '4.0.2'
        generator = 'Ninja 1.13.0.git.kitware.jobserver-pipe-1'
        compiler = 'MSVC 19.29.30133 (v142, x64)'
        build_type = 'Release'
        command = 'cmake -S engine/InfinityEngine-Enhancer/source-patchee -B <build-dir> -G Ninja -DCMAKE_BUILD_TYPE=Release -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON; cmake --build <build-dir> --target release_bundle'
    }
    files = @($files)
    validation_required = @(
        'host tests from the same source tree',
        'clean BG2EE Steam 2.7.3.0 game-hash gate',
        'EEex/InfinityLoader launch gate',
        'x4 map and UI smoke gates',
        'AR0516 SPHINCT/SPHINCT2 native WED occlusion gate with bridge enabled',
        'AR0413 WTOIL overlay classified as Oil with liquidOverlayMask 0x02',
        'In-place Steam shim lifecycle and verified full vanilla restoration after Phase 3'
    )
}
$recordPath = Join-Path $ReleaseRoot 'manifests/renderer-bundle.json'
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $recordPath -Encoding utf8NoBOM
Write-Output "Frozen $BundleId in $destination"
Write-Output "Wrote $recordPath"
