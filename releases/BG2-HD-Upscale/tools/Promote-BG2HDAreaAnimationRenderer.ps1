[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$CandidateManifestPath = (Join-Path $PSScriptRoot '..\manifests\renderer-animation-pilot.json')
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-Hash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$candidatePath = (Resolve-Path -LiteralPath $CandidateManifestPath).Path
$schema = Join-Path $release 'schemas\renderer-bundle.schema.json'
Require (Test-Json -Path $candidatePath -SchemaFile $schema) 'Schema du renderer candidat invalide.'
$candidate = Get-Content -LiteralPath $candidatePath -Raw -Encoding utf8 | ConvertFrom-Json
Require ($candidate.bundle_id -eq 'iee-0.1.0-alpha.7') 'Le renderer occlusion/v2/v3 doit utiliser le bundle alpha.7 fige.'
Require ($candidate.status -eq 'frozen-awaiting-clean-game-validation') 'Le renderer candidat doit etre fige avant promotion.'

$sourceRoot = Join-Path $release (Join-Path 'release-inputs\renderer' $candidate.bundle_id)
$targetRoot = Join-Path $release 'bg2hd\renderer'
Require (Test-Path -LiteralPath $sourceRoot -PathType Container) "Source renderer candidate absente : $sourceRoot"
Require (Test-Path -LiteralPath $targetRoot -PathType Container) "Destination renderer absente : $targetRoot"

$candidateDll = Join-Path $sourceRoot 'InfinityEngine-Enhancer.dll'
Require (Test-Path -LiteralPath $candidateDll -PathType Leaf) 'DLL renderer candidate absente.'
$candidateBinaryText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($candidateDll))
foreach ($marker in @('AreaAnimations-X4.registry', 'TimedTimeline', 'EnableAreaAnimationX4', 'EnableNativeOcclusionBridge', 'FXRenderClippingPolys', 'LoadArea')) {
    Require ($candidateBinaryText.IndexOf($marker, [StringComparison]::Ordinal) -ge 0) "Marqueur renderer alpha.7 absent : $marker"
}

$expected = @($candidate.files | ForEach-Object { [string]$_.path } | Sort-Object)
$actual = @(Get-ChildItem -LiteralPath $targetRoot -File -Recurse | ForEach-Object { [IO.Path]::GetRelativePath($targetRoot, $_.FullName).Replace('\', '/') } | Sort-Object)
Require (-not (Compare-Object $actual $expected)) 'Le renderer officiel contient un fichier non declare ; promotion refusee.'

foreach ($file in @($candidate.files)) {
    $relative = [string]$file.path
    $source = Join-Path $sourceRoot $relative.Replace('/', '\')
    $target = Join-Path $targetRoot $relative.Replace('/', '\')
    Require (Test-Path -LiteralPath $source -PathType Leaf) "Fichier renderer candidat absent : $relative"
    Require ((Get-Item -LiteralPath $source).Length -eq [int64]$file.bytes -and (Get-Hash $source) -eq $file.sha256) "Fichier renderer candidat invalide : $relative"
    Copy-Item -LiteralPath $source -Destination $target -Force
    Require ((Get-Item -LiteralPath $target).Length -eq [int64]$file.bytes -and (Get-Hash $target) -eq $file.sha256) "Copie renderer invalide : $relative"
}

$official = [ordered]@{
    '$schema' = $candidate.'$schema'
    schema_version = $candidate.schema_version
    bundle_id = $candidate.bundle_id
    status = 'integrated-in-place-awaiting-user-lifecycle-test'
    source_tree = $candidate.source_tree
    build_environment = $candidate.build_environment
    files = @($candidate.files)
    validation_required = @($candidate.validation_required)
}
$temporaryManifest = Join-Path $release ('manifests\.renderer-bundle-' + [Guid]::NewGuid().ToString('N') + '.tmp')
try {
    [IO.File]::WriteAllText($temporaryManifest, ($official | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    Require (Test-Json -Path $temporaryManifest -SchemaFile $schema) 'Manifeste renderer promu invalide.'
    Copy-Item -LiteralPath $temporaryManifest -Destination (Join-Path $release 'manifests\renderer-bundle.json') -Force
}
finally {
    if (Test-Path -LiteralPath $temporaryManifest) { Remove-Item -LiteralPath $temporaryManifest -Force }
}

Write-Output "Promoted renderer $($candidate.bundle_id) to bg2hd/renderer."
