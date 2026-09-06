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

function Get-RelativeFiles([string]$Root) {
    @(Get-ChildItem -LiteralPath $Root -File -Recurse |
        ForEach-Object { [IO.Path]::GetRelativePath($Root, $_.FullName).Replace('\', '/') } |
        Sort-Object)
}

function Write-BytesAtomic([string]$Path, [byte[]]$Bytes) {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary = Join-Path $parent ('.' + [IO.Path]::GetFileName($Path) + '.' + [Guid]::NewGuid().ToString('N') + '.partial')
    $backup = Join-Path $parent ('.' + [IO.Path]::GetFileName($Path) + '.' + [Guid]::NewGuid().ToString('N') + '.backup')
    try {
        [IO.File]::WriteAllBytes($temporary, $Bytes)
        if (Test-Path -LiteralPath $Path) {
            [IO.File]::Replace($temporary, $Path, $backup, $true)
            Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
        }
        else {
            [IO.File]::Move($temporary, $Path)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue }
    }
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
$targetParent = Split-Path -Parent $targetRoot
$officialManifestPath = Join-Path $release 'manifests\renderer-bundle.json'
$packageManifestPath = Join-Path $release 'bg2hd\manifests\renderer-bundle.json'
Require (Test-Path -LiteralPath $sourceRoot -PathType Container) "Source renderer candidate absente : $sourceRoot"
Require (Test-Path -LiteralPath $targetRoot -PathType Container) "Destination renderer absente : $targetRoot"
Require (Test-Path -LiteralPath $officialManifestPath -PathType Leaf) 'Manifeste renderer officiel absent.'
Require (Test-Path -LiteralPath $packageManifestPath -PathType Leaf) 'Miroir package du manifeste renderer absent.'

$officialBefore = [IO.File]::ReadAllBytes($officialManifestPath)
$packageBefore = [IO.File]::ReadAllBytes($packageManifestPath)
Require ([Linq.Enumerable]::SequenceEqual[byte]($officialBefore, $packageBefore)) 'Miroir package renderer deja divergent ; promotion refusee.'

$candidateDll = Join-Path $sourceRoot 'InfinityEngine-Enhancer.dll'
Require (Test-Path -LiteralPath $candidateDll -PathType Leaf) 'DLL renderer candidate absente.'
$candidateBinaryText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($candidateDll))
foreach ($marker in @('AreaAnimations-X4.registry', 'TimedTimeline', 'EnableAreaAnimationX4', 'EnableNativeOcclusionBridge', 'FXRenderClippingPolys', 'LoadArea')) {
    Require ($candidateBinaryText.IndexOf($marker, [StringComparison]::Ordinal) -ge 0) "Marqueur renderer alpha.7 absent : $marker"
}

$expected = @($candidate.files | ForEach-Object { [string]$_.path } | Sort-Object)
Require (-not (Compare-Object (Get-RelativeFiles $targetRoot) $expected)) 'Le renderer officiel contient un fichier non declare ; promotion refusee.'
foreach ($file in @($candidate.files)) {
    $relative = [string]$file.path
    $source = Join-Path $sourceRoot $relative.Replace('/', '\')
    Require (Test-Path -LiteralPath $source -PathType Leaf) "Fichier renderer candidat absent : $relative"
    Require ((Get-Item -LiteralPath $source).Length -eq [int64]$file.bytes -and (Get-Hash $source) -eq $file.sha256) "Fichier renderer candidat invalide : $relative"
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
$officialJson = $official | ConvertTo-Json -Depth 8
$validationPath = Join-Path (Split-Path -Parent $officialManifestPath) ('.renderer-bundle-' + [Guid]::NewGuid().ToString('N') + '.partial')
try {
    [IO.File]::WriteAllText($validationPath, $officialJson, [Text.UTF8Encoding]::new($false))
    Require (Test-Json -Path $validationPath -SchemaFile $schema) 'Manifeste renderer promu invalide.'
}
finally {
    if (Test-Path -LiteralPath $validationPath) { Remove-Item -LiteralPath $validationPath -Force }
}
$officialBytes = [Text.UTF8Encoding]::new($false).GetBytes($officialJson)

$transactionId = [Guid]::NewGuid().ToString('N')
$stagingRoot = Join-Path $targetParent ('.renderer-' + $transactionId + '.partial')
$backupRoot = Join-Path $targetParent ('.renderer-' + $transactionId + '.backup')
$targetMoved = $false
$candidatePublished = $false
$officialManifestPublished = $false
$packageManifestPublished = $false

try {
    New-Item -ItemType Directory -Path $stagingRoot | Out-Null
    foreach ($file in @($candidate.files)) {
        $relative = [string]$file.path
        $source = Join-Path $sourceRoot $relative.Replace('/', '\')
        $target = Join-Path $stagingRoot $relative.Replace('/', '\')
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -ErrorAction Stop
        Require ((Get-Item -LiteralPath $target).Length -eq [int64]$file.bytes -and (Get-Hash $target) -eq $file.sha256) "Copie renderer invalide : $relative"
    }
    Require (-not (Compare-Object (Get-RelativeFiles $stagingRoot) $expected)) 'Staging renderer incomplet ou surplus detecte.'

    Move-Item -LiteralPath $targetRoot -Destination $backupRoot -ErrorAction Stop
    $targetMoved = $true
    Move-Item -LiteralPath $stagingRoot -Destination $targetRoot -ErrorAction Stop
    $candidatePublished = $true

    Write-BytesAtomic $officialManifestPath $officialBytes
    $officialManifestPublished = $true
    Write-BytesAtomic $packageManifestPath $officialBytes
    $packageManifestPublished = $true

    Remove-Item -LiteralPath $backupRoot -Recurse -Force
    Write-Output "Promoted renderer $($candidate.bundle_id) to bg2hd/renderer with synchronized renderer manifests."
}
catch {
    $failure = $_
    try {
        if ($candidatePublished -and (Test-Path -LiteralPath $targetRoot)) {
            Remove-Item -LiteralPath $targetRoot -Recurse -Force
        }
        if ($targetMoved -and (Test-Path -LiteralPath $backupRoot)) {
            Move-Item -LiteralPath $backupRoot -Destination $targetRoot -ErrorAction Stop
        }
        if ($officialManifestPublished) { Write-BytesAtomic $officialManifestPath $officialBefore }
        if ($packageManifestPublished) { Write-BytesAtomic $packageManifestPath $packageBefore }
    }
    catch {
        throw "Promotion renderer interrompue et restauration incomplete : $($_.Exception.Message)"
    }
    throw $failure
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
    if ((Test-Path -LiteralPath $backupRoot) -and (Test-Path -LiteralPath $targetRoot)) { Remove-Item -LiteralPath $backupRoot -Recurse -Force }
}
