[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WeiDUExecutable,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$PayloadRoot = (Join-Path $PSScriptRoot '..\bg2hd\payload-allvalidated'),
    [string]$OutputRoot = (Join-Path $PSScriptRoot '..\dist-local\phase6b-candidate')
)

$ErrorActionPreference = 'Stop'
function Get-Hash([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-', '') }
    finally { $sha.Dispose() }
}
function Require([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Write-Utf8NoBom([string]$Path, [string[]]$Lines) {
    [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
}
function New-DeterministicZip([string]$Source, [string]$Archive) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $epoch = [DateTimeOffset]::new(1980, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
    $zip = [IO.Compression.ZipFile]::Open($Archive, [IO.Compression.ZipArchiveMode]::Create)
    try {
        Get-ChildItem -LiteralPath $Source -File -Recurse | Sort-Object FullName | ForEach-Object {
            $relative = [IO.Path]::GetRelativePath($Source, $_.FullName).Replace('\', '/')
            $entry = $zip.CreateEntry($relative, [IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $epoch
            $input = [IO.File]::OpenRead($_.FullName)
            $output = $entry.Open()
            try { $input.CopyTo($output) } finally { $output.Dispose(); $input.Dispose() }
        }
    } finally { $zip.Dispose() }
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$workspace = (Resolve-Path -LiteralPath (Join-Path $release '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
$weidu = (Resolve-Path -LiteralPath $WeiDUExecutable).Path
$stagedPayload = (Resolve-Path -LiteralPath $PayloadRoot -ErrorAction Stop).Path
$output = [IO.Path]::GetFullPath($OutputRoot)
& (Join-Path $release 'tools\Test-BG2HD-Phase4.ps1') -ReleaseRoot $release
$releaseManifestPath = Join-Path $release 'manifests\release.json'
$contentManifestPath = Join-Path $release 'manifests\content.json'
$manifest = Get-Content -LiteralPath $releaseManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
Require ($manifest.release_status -eq 'blocked') 'Le build reproductible local exige un manifeste non publiable.'

$name = "BG2HD-$($manifest.version)-windows-local-alpha"
$package = Join-Path $output $name
$archive = Join-Path $output "$name.zip"
$sidecar = "$archive.sha256"
Require (-not (Test-Path -LiteralPath $package)) "Sortie deja presente : $package"
Require (-not (Test-Path -LiteralPath $archive)) "Sortie deja presente : $archive"
Require (-not (Test-Path -LiteralPath $sidecar)) "Checksum deja present : $sidecar"
$temporary = Join-Path $output ('.' + $name + '.' + [Guid]::NewGuid().ToString('N') + '.tmp')
$publicDocuments = @(
    'README.md', 'README_FR.md', 'README_EN.md', 'CHANGELOG.md', 'KNOWN_ISSUES.md',
    'docs/ARCHITECTURE.md', 'docs/MANIFESTS.md', 'docs/MAINTENANCE.md',
    'docs/INSTALLER_AND_UPSCALE_WORKFLOW.md', 'docs/LOCALIZATION.md',
    'docs/DEPENDENCY_BOOTSTRAP.md',
    'docs/STEAM_INTEGRATION.md', 'docs/TESTING.md', 'docs/RECOVERY.md',
    'docs/COMPATIBILITY.md', 'docs/LICENCES.md', 'docs/DISTRIBUTION_POLICY.md'
)
try {
    New-Item -ItemType Directory -Path $temporary -Force | Out-Null
    $temporaryMod = Join-Path $temporary 'bg2hd'
    New-Item -ItemType Directory -Path $temporaryMod -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath (Join-Path $release 'bg2hd') -Force) {
        if ($item.Name -in @('payload', 'payload-allvalidated')) { continue }
        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $temporaryMod $item.Name) -Recurse
    }
    Copy-Item -LiteralPath $stagedPayload -Destination (Join-Path $temporaryMod 'payload') -Recurse
    Copy-Item -LiteralPath $weidu -Destination (Join-Path $temporary 'setup-bg2hd.exe')
    & (Join-Path $release 'tools\Build-BG2HDBootstrapLauncher.ps1') -ReleaseRoot $release -OutputPath (Join-Path $temporary 'Install-BG2HD.exe') | Out-Null
    Copy-Item -LiteralPath (Join-Path $temporary 'Install-BG2HD.exe') -Destination (Join-Path $temporary 'Uninstall-BG2HD.exe')
    foreach ($document in $publicDocuments) {
        $source = Join-Path $release $document
        Require (Test-Path -LiteralPath $source -PathType Leaf) "Document public absent : $document"
        $destination = Join-Path $temporary $document
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
    }
    New-Item -ItemType Directory -Path (Join-Path $temporary 'tools') -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $release 'tools\Test-BG2HD-FutureSaveCompatibility.ps1') -Destination (Join-Path $temporary 'tools\Test-BG2HD-FutureSaveCompatibility.ps1')
    Write-Utf8NoBom (Join-Path $temporary 'BUILD-STATUS.txt') @(
        'BG2 HD local reproducible alpha build',
        "Version: $($manifest.version)",
        'Distribution: LOCAL TEST ONLY. Do not publish or redistribute.',
        'Launch: BG2HD installs in place; Steam launches through the verified InfinityLoader shim.',
        'Save compatibility: future save chains disable EEex X-BIV1.0 marshalling.',
        'EEex: guided external prerequisite; never redistributed by BG2HD.',
        'Renderer: bundled BG2HD local-alpha payload; clean lifecycle validation remains required.',
        'Content: validated x4 SeedVR2 7B maps and approved x4 UI only.'
    )
    $buildManifest = [ordered]@{
        schema_version = 1
        package_kind = 'local-alpha-not-public'
        version = $manifest.version
        release_manifest_sha256 = Get-Hash $releaseManifestPath
        content_manifest_sha256 = Get-Hash $contentManifestPath
        bootstrap_launcher_sha256 = Get-Hash (Join-Path $temporary 'Install-BG2HD.exe')
        uninstall_launcher_sha256 = Get-Hash (Join-Path $temporary 'Uninstall-BG2HD.exe')
        fixed_zip_timestamp_utc = '1980-01-01T00:00:00Z'
        public_documents = $publicDocuments
        excluded = @('game executables', 'EEex', 'InfinityLoader', 'logs', 'saves', 'development backups', 'x2 assets')
    }
    [IO.File]::WriteAllText((Join-Path $temporary 'BUILD-MANIFEST.json'), ($buildManifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    $checksums = @(Get-ChildItem -LiteralPath $temporary -File -Recurse | Sort-Object FullName | ForEach-Object {
        "$(Get-Hash $_.FullName)  $([IO.Path]::GetRelativePath($temporary, $_.FullName).Replace('\', '/'))"
    })
    Write-Utf8NoBom (Join-Path $temporary 'checksums.sha256') $checksums
    New-Item -ItemType Directory -Path $output -Force | Out-Null
    Move-Item -LiteralPath $temporary -Destination $package
    New-DeterministicZip -Source $package -Archive $archive
    Write-Utf8NoBom $sidecar @("$(Get-Hash $archive)  $([IO.Path]::GetFileName($archive))")
    [ordered]@{
        package = $package
        archive = $archive
        archive_sha256 = Get-Hash $archive
        archive_bytes = (Get-Item -LiteralPath $archive).Length
        checksum_file = $sidecar
        status = 'local-alpha-not-public'
    } | ConvertTo-Json
} catch {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    throw
}
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
