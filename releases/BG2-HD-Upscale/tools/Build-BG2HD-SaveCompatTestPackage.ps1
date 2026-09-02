[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$WeiDUExecutable = (Join-Path $PSScriptRoot '..\release-inputs\weidu\setup-bg2hd.exe'),
    [string]$PayloadRoot = (Join-Path $PSScriptRoot '..\bg2hd\payload-allvalidated'),
    [string]$OutputName = 'BG2HD-Installer-Windows'
)

$ErrorActionPreference = 'Stop'

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-Hash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function Write-Utf8NoBom([string]$Path, [string[]]$Lines) {
    [IO.File]::WriteAllLines($Path, $Lines, [Text.UTF8Encoding]::new($false))
}

function Copy-TreeContents([string]$From, [string]$To) {
    New-Item -ItemType Directory -Path $To -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $From -Force) {
        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $To $item.Name) -Recurse -Force
    }
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
            try { $input.CopyTo($output) }
            finally { $output.Dispose(); $input.Dispose() }
        }
    }
    finally { $zip.Dispose() }
}

$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$workspace = (Resolve-Path -LiteralPath (Join-Path $release '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
try {
$weidu = (Resolve-Path -LiteralPath $WeiDUExecutable).Path
$stagedPayload = (Resolve-Path -LiteralPath $PayloadRoot -ErrorAction Stop).Path
$outputParent = $release
$package = Join-Path $outputParent $OutputName
$archive = "$package.zip"
$sidecar = "$archive.sha256"
$temporary = Join-Path $outputParent ('.' + $OutputName + '.' + [Guid]::NewGuid().ToString('N') + '.tmp')

Require (-not (Test-Path -LiteralPath $package)) "Sortie deja presente : $package"
Require (-not (Test-Path -LiteralPath $archive)) "Archive deja presente : $archive"
Require (-not (Test-Path -LiteralPath $sidecar)) "Checksum deja present : $sidecar"
Require (([IO.Path]::GetFullPath($temporary)).StartsWith(([IO.Path]::GetFullPath($outputParent).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) 'Dossier temporaire hors de la sortie autorisee.'

New-Item -ItemType Directory -Path $temporary -Force | Out-Null
$temporaryPayload = Join-Path $temporary 'bg2hd\payload'
Copy-TreeContents $stagedPayload $temporaryPayload

# Copy every current control-plane file, including content.json, while keeping
# build-only payload-allvalidated out of the distributable tree.
$canonicalMod = Join-Path $release 'bg2hd'
foreach ($file in Get-ChildItem -LiteralPath $canonicalMod -File -Recurse) {
    $relative = [IO.Path]::GetRelativePath($canonicalMod, $file.FullName)
    if ($relative.StartsWith('payload', [StringComparison]::OrdinalIgnoreCase)) { continue }
    $destination = Join-Path (Join-Path $temporary 'bg2hd') $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
}
Copy-Item -LiteralPath $weidu -Destination (Join-Path $temporary 'setup-bg2hd.exe') -Force

$publicDocuments = @(
    'README.md', 'README_FR.md', 'README_EN.md', 'CHANGELOG.md', 'KNOWN_ISSUES.md',
    'docs/ARCHITECTURE.md', 'docs/MANIFESTS.md', 'docs/MAINTENANCE.md',
    'docs/INSTALLER_AND_UPSCALE_WORKFLOW.md', 'docs/LOCALIZATION.md',
    'docs/DEPENDENCY_BOOTSTRAP.md', 'docs/STEAM_INTEGRATION.md', 'docs/TESTING.md',
    'docs/TEST_SAVE_COMPATIBILITY_FR.md', 'docs/RECOVERY.md', 'docs/COMPATIBILITY.md',
    'docs/LICENCES.md', 'docs/DISTRIBUTION_POLICY.md'
)
foreach ($document in $publicDocuments) {
    $source = Join-Path $release $document
    Require (Test-Path -LiteralPath $source -PathType Leaf) "Document public absent : $document"
    $destination = Join-Path $temporary $document
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}
New-Item -ItemType Directory -Path (Join-Path $temporary 'tools') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $release 'tools\Test-BG2HD-FutureSaveCompatibility.ps1') -Destination (Join-Path $temporary 'tools\Test-BG2HD-FutureSaveCompatibility.ps1') -Force
Copy-Item -LiteralPath (Join-Path $release 'tools\Test-BG2HD-AR0413Contract.ps1') -Destination (Join-Path $temporary 'tools\Test-BG2HD-AR0413Contract.ps1') -Force

& (Join-Path $release 'tools\Build-BG2HDBootstrapLauncher.ps1') -ReleaseRoot $release -OutputPath (Join-Path $temporary 'Install-BG2HD.exe') | Out-Null
Copy-Item -LiteralPath (Join-Path $temporary 'Install-BG2HD.exe') -Destination (Join-Path $temporary 'Uninstall-BG2HD.exe') -Force

# Prove that the current content manifest describes every staged payload file,
# that no stale base-payload file survives, and that the save-neutral renderer
# guard remains intact.
$contentPath = Join-Path $temporary 'bg2hd\manifests\content.json'
$content = Get-Content -LiteralPath $contentPath -Raw -Encoding utf8 | ConvertFrom-Json
$expectedPayload = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($item in @($content.entries)) {
    $name = [IO.Path]::GetFileName([string]$item.source)
    $payloadPath = Join-Path $temporary "bg2hd\payload\$($item.payload_group)\$name"
    [void]$expectedPayload.Add([IO.Path]::GetRelativePath((Join-Path $temporary 'bg2hd\payload'), $payloadPath).Replace('\', '/'))
    Require (Test-Path -LiteralPath $payloadPath -PathType Leaf) "Payload retenu absent : $($item.payload_group)/$name"
    $payloadFile = Get-Item -LiteralPath $payloadPath
    Require ($payloadFile.Length -eq [int64]$item.bytes) "Taille payload retenu invalide : $($item.payload_group)/$name"
    Require ((Get-Hash $payloadPath) -eq [string]$item.sha256) "Hash payload retenu invalide : $($item.payload_group)/$name"
}
$actualPayload = @(Get-ChildItem -LiteralPath (Join-Path $temporary 'bg2hd\payload') -File -Recurse | ForEach-Object { [IO.Path]::GetRelativePath((Join-Path $temporary 'bg2hd\payload'), $_.FullName).Replace('\', '/') })
Require ($actualPayload.Count -eq $expectedPayload.Count -and @($actualPayload | Where-Object { -not $expectedPayload.Contains($_) }).Count -eq 0) 'Le payload final contient un fichier absent du manifeste courant.'
Require (-not (Test-Path -LiteralPath (Join-Path $temporary 'bg2hd\payload-allvalidated'))) 'Le staging de build ne doit jamais etre embarque dans le paquet.'
$rendererPath = Join-Path $temporary 'bg2hd\manifests\renderer-bundle.json'
$renderer = Get-Content -LiteralPath $rendererPath -Raw -Encoding utf8 | ConvertFrom-Json
$rendererPayloadRoot = Join-Path $temporary 'bg2hd\renderer'
foreach ($file in @($renderer.files)) {
    $packagedRendererFile = Join-Path $rendererPayloadRoot ([string]$file.path).Replace('/', '\')
    Require (Test-Path -LiteralPath $packagedRendererFile -PathType Leaf) "Fichier renderer absent : $($file.path)"
    Require ((Get-Item -LiteralPath $packagedRendererFile).Length -eq [int64]$file.bytes) "Taille renderer invalide : $($file.path)"
    Require ((Get-Hash $packagedRendererFile) -eq [string]$file.sha256) "Hash renderer invalide : $($file.path)"
}
$rendererDllPath = Join-Path $rendererPayloadRoot 'InfinityEngine-Enhancer.dll'
$rendererBinaryText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($rendererDllPath))
foreach ($marker in @('WTSEW', 'WTOIL', 'AreaAnimations-X4.registry', 'TimedTimeline', 'EnableAreaAnimationX4', 'EnableNativeOcclusionBridge', 'FXRenderClippingPolys', 'LoadArea')) {
    Require ($rendererBinaryText.IndexOf($marker, [StringComparison]::Ordinal) -ge 0) "Classificateur liquide absent de la DLL renderer : $marker"
}
$guard = @($renderer.files | Where-Object { $_.path -eq 'override/M_IEEE.lua' })
Require ($guard.Count -eq 1) 'M_IEEE.lua absent du manifeste renderer.'
$guardPath = Join-Path $temporary 'bg2hd\renderer\override\M_IEEE.lua'
Require ((Get-Hash $guardPath) -eq [string]$guard[0].sha256) 'Hash du garde save-neutral invalide.'
$guardText = Get-Content -LiteralPath $guardPath -Raw -Encoding utf8
Require ($guardText -match '(?m)^EEex_Debug_DisableExtraCreatureMarshalling\s*=\s*true\s*$') 'Le garde save-neutral EEex est absent.'
Require ($guardText.IndexOf('EEex_Debug_DisableExtraCreatureMarshalling', [StringComparison]::Ordinal) -lt $guardText.IndexOf('EEex_InitLuaBindings', [StringComparison]::Ordinal)) 'Le garde save-neutral est initialise trop tard.'
& (Join-Path $release 'tools\Test-BG2HD-AR0413Contract.ps1') -ReleaseRoot $temporary

$releaseManifestPath = Join-Path $temporary 'bg2hd\manifests\release.json'
$releaseManifest = Get-Content -LiteralPath $releaseManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
Write-Utf8NoBom (Join-Path $temporary 'BUILD-STATUS.txt') @(
    'BG2 HD Windows in-place installer',
    "Version: $($releaseManifest.version)",
    'Variant: Windows in-place',
    'Distribution: LOCAL TEST ONLY. Do not publish or redistribute.',
    'Launch: BG2HD replaces the supported Steam launch path with a verified InfinityLoader shim.',
    'Uninstall: the confirmed full-vanilla path restores the verified official Baldur.exe.',
    'EEex lifecycle: normal WeiDU source residue is recognized as inactive and can be reinstalled.',
    'Renderer lifecycle: every reinstall starts a fresh transaction and recreates a missing renderer INI.',
    'AR0413: canonical 16-page build, 12-sentinel TIS delta and WTOIL Oil runtime classification.',
    'Save compatibility: future clean save chains disable EEex X-BIV1.0 marshalling.',
    "Content: all $(@($content.entries).Count) current manifest files staged from validated map/UI coverage and approved per-area animation packs.",
    'Legacy saves: no migration or repair is performed.'
)

$buildManifest = [ordered]@{
    schema_version = 1
    package_kind = 'local-alpha-not-public'
    test_variant = 'windows-in-place'
    version = $releaseManifest.version
    weidu_executable_sha256 = Get-Hash $weidu
    release_manifest_sha256 = Get-Hash $releaseManifestPath
    content_manifest_sha256 = Get-Hash $contentPath
    staged_payload_source = 'bg2hd/payload-allvalidated'
    staged_payload_files = @($actualPayload).Count
    renderer_manifest_sha256 = Get-Hash $rendererPath
    renderer_dll_sha256 = Get-Hash $rendererDllPath
    save_guard_sha256 = Get-Hash $guardPath
    bootstrap_launcher_sha256 = Get-Hash (Join-Path $temporary 'Install-BG2HD.exe')
    uninstall_launcher_sha256 = Get-Hash (Join-Path $temporary 'Uninstall-BG2HD.exe')
    fixed_zip_timestamp_utc = '1980-01-01T00:00:00Z'
    public_documents = $publicDocuments
    excluded = @('game executables', 'EEex', 'InfinityLoader', 'logs', 'saves', 'development backups', 'x2 assets')
}
[IO.File]::WriteAllText((Join-Path $temporary 'BUILD-MANIFEST.json'), ($buildManifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

$checksums = @(Get-ChildItem -LiteralPath $temporary -File -Recurse | Where-Object { $_.Name -ne 'checksums.sha256' } | Sort-Object FullName | ForEach-Object {
    "$(Get-Hash $_.FullName)  $([IO.Path]::GetRelativePath($temporary, $_.FullName).Replace('\', '/'))"
})
Write-Utf8NoBom (Join-Path $temporary 'checksums.sha256') $checksums

Move-Item -LiteralPath $temporary -Destination $package
New-DeterministicZip -Source $package -Archive $archive
Write-Utf8NoBom $sidecar @("$(Get-Hash $archive)  $([IO.Path]::GetFileName($archive))")

[ordered]@{
    package = $package
    archive = $archive
    archive_sha256 = Get-Hash $archive
    archive_bytes = (Get-Item -LiteralPath $archive).Length
    save_guard_sha256 = Get-Hash (Join-Path $package 'bg2hd\renderer\override\M_IEEE.lua')
    content_entries = @($content.entries).Count
    status = 'LOCAL_TEST_READY'
} | ConvertTo-Json
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
