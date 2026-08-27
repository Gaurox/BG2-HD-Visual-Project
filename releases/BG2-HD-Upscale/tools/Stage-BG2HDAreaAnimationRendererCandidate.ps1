[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$SourceBundle,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$BundleId = 'iee-0.1.0-alpha.5',
    [string]$OutputManifestPath = (Join-Path $PSScriptRoot '..\manifests\renderer-animation-pilot.json')
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-BundleFile([string]$Root, [string]$RelativePath) {
    $path = Join-Path $Root $RelativePath.Replace('/', '\')
    Require (Test-Path -LiteralPath $path -PathType Leaf) "Fichier du bundle renderer absent : $RelativePath"
    Get-Item -LiteralPath $path
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$source = (Resolve-Path -LiteralPath $SourceBundle).Path
$selectedFiles = @(
    'InfinityEngine-Enhancer.dll',
    'InfinityEngine-Enhancer.sample.ini',
    'iee-textures/iee_water_dudv.rgba',
    'iee-textures/iee_water_foam.rgba',
    'iee-textures/iee_water_normal.rgba',
    'iee-textures/README.md',
    'override/fpSEAM.glsl',
    'override/M_IEEE.lua'
)
$destination = Join-Path $release (Join-Path 'release-inputs\renderer' $BundleId)
if (Test-Path -LiteralPath $destination) { throw "Candidat renderer deja present : $destination" }

$rendererDll = Get-BundleFile $source 'InfinityEngine-Enhancer.dll'
$binaryText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($rendererDll.FullName))
foreach ($marker in @('AreaAnimations-X4.registry', 'TimedTimeline', 'EnableAreaAnimationX4', 'LoadArea')) {
    Require ($binaryText.IndexOf($marker, [StringComparison]::Ordinal) -ge 0) "DLL renderer incompatible avec les animations de zone : marqueur absent $marker"
}

try {
    foreach ($relative in $selectedFiles) {
        $file = Get-BundleFile $source $relative
        $target = Join-Path $destination $relative.Replace('/', '\')
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target
    }
    $files = foreach ($relative in $selectedFiles) {
        $file = Get-BundleFile $destination $relative
        [ordered]@{
            path = $relative
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
            generator = 'Visual Studio 16 2019, x64'
            compiler = 'MSVC 19.29.30133 (v142)'
            build_type = 'Release'
            command = 'cmake -S engine/InfinityEngine-Enhancer/source-patchee -B <build-dir> -G "Visual Studio 16 2019" -A x64 -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=ON; cmake --build <build-dir> --config Release --target release_bundle; ctest --test-dir <build-dir> -C Release --output-on-failure'
        }
        files = @($files)
        validation_required = @(
            'host tests from the same source tree, including registry v1/v2/v3 compatibility and per-occurrence routing',
            'renderer binary markers: AreaAnimations-X4.registry, TimedTimeline, EnableAreaAnimationX4 and LoadArea',
            'clean BG2EE Steam 2.7.3.0 game-hash gate',
            'EEex/InfinityLoader launch gate with AR0602 v2 and AR0900 v3 runtime packs',
            'AR0602/AR0900 -> no-pack area transition and renderer-log fallback gate',
            'in-place Steam shim lifecycle and verified full vanilla restoration'
        )
    }
    $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputManifestPath -Encoding utf8NoBOM
    Write-Output "Staged animation renderer candidate $BundleId in $destination"
}
catch {
    if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Recurse -Force }
    throw
}
