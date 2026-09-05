[CmdletBinding()]
param([string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)
$ErrorActionPreference='Stop'

function Test-BG2HDRegularFilePath([string]$Path, [string]$Label) {
    try {
        $attributes = [IO.File]::GetAttributes($Path)
    } catch {
        $exception = $_.Exception
        while ($null -ne $exception.InnerException) { $exception = $exception.InnerException }
        if (
            $exception -is [System.IO.FileNotFoundException] -or
            $exception -is [System.IO.DirectoryNotFoundException]
        ) {
            return $false
        }
        throw
    }
    if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label ReparsePoint interdit : $Path"
    }
    if (
        ($attributes -band [IO.FileAttributes]::Directory) -ne 0 -or
        ($attributes -band [IO.FileAttributes]::Device) -ne 0 -or
        -not [IO.File]::Exists($Path)
    ) {
        throw "$Label non regulier : $Path"
    }
    return $true
}

function Write-BG2HDAtomicUtf8NoBomFile([string]$Path, [string]$Text) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    $directory = [IO.Path]::GetDirectoryName($fullPath)
    if ([string]::IsNullOrWhiteSpace($directory)) { throw "Dossier de sortie introuvable : $Path" }
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $temporaryPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullPath) + '.' + [Guid]::NewGuid().ToString('N') + '.partial')
    $backupPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullPath) + '.' + [Guid]::NewGuid().ToString('N') + '.replace-backup.partial')
    $stream = $null
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text)
        $stream = [IO.FileStream]::new(
            $temporaryPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None,
            65536,
            [IO.FileOptions]::WriteThrough
        )
        if ($bytes.Length -gt 0) { $stream.Write($bytes, 0, $bytes.Length) }
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        $targetExists = Test-BG2HDRegularFilePath -Path $fullPath -Label 'Cible de publication'
        if ($targetExists) {
            [IO.File]::Replace($temporaryPath, $fullPath, $backupPath, $true)
        } else {
            [IO.File]::Move($temporaryPath, $fullPath)
        }
    }
    finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ([IO.File]::Exists($temporaryPath)) { [IO.File]::Delete($temporaryPath) }
        if ([IO.File]::Exists($backupPath)) { [IO.File]::Delete($backupPath) }
    }
}

function Copy-BG2HDFileAtomic([string]$SourcePath, [string]$DestinationPath, [string]$ExpectedSha256) {
    $fullSourcePath = [IO.Path]::GetFullPath($SourcePath)
    $fullDestinationPath = [IO.Path]::GetFullPath($DestinationPath)
    if (-not (Test-BG2HDRegularFilePath -Path $fullSourcePath -Label 'Manifeste source')) {
        throw "Manifeste source absent : $fullSourcePath"
    }
    $directory = [IO.Path]::GetDirectoryName($fullDestinationPath)
    if ([string]::IsNullOrWhiteSpace($directory)) { throw "Dossier de miroir introuvable : $DestinationPath" }
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $temporaryPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullDestinationPath) + '.' + [Guid]::NewGuid().ToString('N') + '.partial')
    $backupPath = Join-Path $directory ('.' + [IO.Path]::GetFileName($fullDestinationPath) + '.' + [Guid]::NewGuid().ToString('N') + '.replace-backup.partial')
    $inputStream = $null
    $outputStream = $null
    try {
        $inputStream = [IO.FileStream]::new($fullSourcePath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $outputStream = [IO.FileStream]::new(
            $temporaryPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None,
            65536,
            [IO.FileOptions]::WriteThrough
        )
        $inputStream.CopyTo($outputStream)
        $outputStream.Flush($true)
        $outputStream.Dispose()
        $outputStream = $null
        $inputStream.Dispose()
        $inputStream = $null
        $temporaryHash = (Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash
        if ($temporaryHash -cne $ExpectedSha256) {
            throw "Le manifeste source a change pendant la synchronisation : $fullSourcePath"
        }
        $destinationExists = Test-BG2HDRegularFilePath -Path $fullDestinationPath -Label 'Miroir package'
        if ($destinationExists) {
            [IO.File]::Replace($temporaryPath, $fullDestinationPath, $backupPath, $true)
        } else {
            [IO.File]::Move($temporaryPath, $fullDestinationPath)
        }
    }
    finally {
        if ($null -ne $outputStream) { $outputStream.Dispose() }
        if ($null -ne $inputStream) { $inputStream.Dispose() }
        if ([IO.File]::Exists($temporaryPath)) { [IO.File]::Delete($temporaryPath) }
        if ([IO.File]::Exists($backupPath)) { [IO.File]::Delete($backupPath) }
    }
}

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $ReleaseRoot '..\..')).Path
. (Join-Path $PSScriptRoot 'Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspaceRoot -AllowPackageMetadataSyncRecovery
try {
$source = Join-Path $ReleaseRoot 'manifests'
$destination = Join-Path $ReleaseRoot 'bg2hd/manifests'
[IO.Directory]::CreateDirectory([IO.Path]::GetFullPath($destination)) | Out-Null
$names = @(
    'runtime-compatibility.json',
    'dependency-bootstrap.json',
    'components.json',
    'content.json',
    'animation-release-candidates.json',
    'overlay-sources.json',
    'renderer-bundle.json',
    'languages.json',
    'licenses-and-exclusions.json',
    'release.json'
)
$mirrorPlan = foreach ($name in $names) {
    $sourcePath = Join-Path $source $name
    $fullSourcePath = [IO.Path]::GetFullPath($sourcePath)
    $fullDestinationPath = [IO.Path]::GetFullPath((Join-Path $destination $name))
    if (-not (Test-BG2HDRegularFilePath -Path $fullSourcePath -Label 'Manifeste source')) {
        throw "Manifeste source absent : $fullSourcePath"
    }
    [void](Test-BG2HDRegularFilePath -Path $fullDestinationPath -Label 'Miroir package')
    [pscustomobject]@{
        Name = $name
        SourcePath = $fullSourcePath
        DestinationPath = $fullDestinationPath
        Sha256 = (Get-FileHash -LiteralPath $fullSourcePath -Algorithm SHA256).Hash
    }
}
$syncMarkerPath = Join-Path $destination '.package-metadata-sync.partial'
$syncMarker = [ordered]@{
    schema_version = 1
    state = 'in-progress'
    files = @($mirrorPlan | ForEach-Object {
        [ordered]@{ name = $_.Name; sha256 = $_.Sha256 }
    })
}
Write-BG2HDAtomicUtf8NoBomFile -Path $syncMarkerPath -Text (($syncMarker | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
foreach ($item in $mirrorPlan) {
    Copy-BG2HDFileAtomic -SourcePath $item.SourcePath -DestinationPath $item.DestinationPath -ExpectedSha256 $item.Sha256
}
foreach ($item in $mirrorPlan) {
    if (-not (Test-BG2HDRegularFilePath -Path $item.SourcePath -Label 'Manifeste source')) {
        throw "Manifeste source absent : $($item.SourcePath)"
    }
    if (-not (Test-BG2HDRegularFilePath -Path $item.DestinationPath -Label 'Miroir package')) {
        throw "Miroir package absent apres synchronisation : $($item.Name)"
    }
    $currentSourceHash = (Get-FileHash -LiteralPath $item.SourcePath -Algorithm SHA256).Hash
    $currentDestinationHash = (Get-FileHash -LiteralPath $item.DestinationPath -Algorithm SHA256).Hash
    if ($currentSourceHash -cne $item.Sha256 -or $currentDestinationHash -cne $item.Sha256) {
        throw "Miroir package divergent apres synchronisation : $($item.Name)"
    }
}
[IO.File]::Delete([IO.Path]::GetFullPath($syncMarkerPath))
Write-Output "Synced package metadata to $destination"
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
}
