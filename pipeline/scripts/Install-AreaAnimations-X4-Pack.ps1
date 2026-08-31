param(
    [Parameter(Mandatory = $true)]
    [string]$PackRoot,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$BackupRoot
)

$workspaceRoot = $PSScriptRoot
while ($workspaceRoot -and -not (Test-Path -LiteralPath (Join-Path $workspaceRoot 'config\workspace-paths.json') -PathType Leaf)) {
    $workspaceRoot = Split-Path -Parent $workspaceRoot
}
if ([string]::IsNullOrWhiteSpace($workspaceRoot)) { throw 'Racine du workspace BG2 Upscale introuvable.' }
. (Join-Path $workspaceRoot 'pipeline\scripts\WorkspacePaths.ps1')
if ((Get-Variable -Name GameRoot -ErrorAction SilentlyContinue) -and [string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Resolve-BG2WorkspacePath -Key 'bg2ee_game_root' -RequireExisting
}

$ErrorActionPreference = 'Stop'

function Assert-GameClosed {
    $running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
    if ($running) {
        throw 'Quittez completement BG2EE et InfinityLoader avant installation du pack x4.'
    }
}

function Set-IniValue {
    param([string]$Path, [string]$Key, [string]$Value)

    $lines = [Collections.Generic.List[string]]::new()
    foreach ($line in [IO.File]::ReadAllLines($Path)) { $lines.Add($line) }
    for ($index = $lines.Count - 1; $index -ge 0; --$index) {
        if ($lines[$index] -match ('^\s*' + [regex]::Escape($Key) + '\s*=')) {
            $lines.RemoveAt($index)
        }
    }
    $shadersIndex = -1
    for ($index = 0; $index -lt $lines.Count; ++$index) {
        if ($lines[$index] -match '^\s*\[Shaders\]\s*$') { $shadersIndex = $index; break }
    }
    if ($shadersIndex -lt 0) {
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -ne '') { $lines.Add('') }
        $lines.Add('[Shaders]')
        $shadersIndex = $lines.Count - 1
    }
    $insertAt = $lines.Count
    for ($index = $shadersIndex + 1; $index -lt $lines.Count; ++$index) {
        if ($lines[$index] -match '^\s*\[[^]]+\]\s*$') { $insertAt = $index; break }
    }
    $lines.Insert($insertAt, "$Key = $Value")
    [IO.File]::WriteAllLines($Path, $lines, [Text.UTF8Encoding]::new($false))
}

function Get-IniSectionKeyCount {
    param([string]$Path, [string]$Section, [string]$Key, [string]$ExpectedValue)

    $currentSection = ''
    $count = 0
    foreach ($line in [IO.File]::ReadAllLines($Path)) {
        if ($line -match '^\s*\[([^]]+)\]\s*$') { $currentSection = $Matches[1]; continue }
        if ($currentSection -eq $Section -and $line -match ('^\s*' + [regex]::Escape($Key) + '\s*=\s*' + [regex]::Escape($ExpectedValue) + '\s*$')) {
            ++$count
        }
    }
    return $count
}

Assert-GameClosed

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$packRootPath = (Resolve-Path -LiteralPath $PackRoot).Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$sourceDll = Join-Path $projectRoot 'engine\InfinityEngine-Enhancer\source-patchee\build-filter-diagnostic-v142\Release\InfinityEngine-Enhancer.dll'
$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$assetsDirectory = Join-Path $gameRootPath 'iee-assets'
$manifestPath = Join-Path $packRootPath 'manifest.json'

foreach ($required in @($sourceDll, $targetDll, $iniPath, $manifestPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier requis absent : $required" }
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'bg2-upscale-area-animation-runtime-pack-v1' -or
    $manifest.status -ne 'completed' -or [int]$manifest.scale -ne 4 -or
    [int]$manifest.resource_count -le 0 -or [int]$manifest.frame_count -le 0 -or
    $manifest.registry -ne 'AreaAnimations-X4.registry') {
    throw 'Manifest runtime incomplet ou incompatible.'
}

$sourceFiles = @([PSCustomObject]@{
    Name = [string]$manifest.registry
    Hash = [string]$manifest.registry_sha256
    Bytes = [int64]$manifest.registry_bytes
    AllowsReplacement = $true
})
foreach ($resource in @($manifest.resources)) {
    foreach ($frame in @($resource.frames)) {
        $sourceFiles += [PSCustomObject]@{
            Name = [string]$frame.asset
            Hash = [string]$frame.sha256
            Bytes = [int64]$frame.bytes
            AllowsReplacement = $false
        }
    }
}
if ($sourceFiles.Count -ne (1 + [int]$manifest.frame_count) -or
    (@($sourceFiles.Name | Select-Object -Unique)).Count -ne $sourceFiles.Count) {
    throw 'Inventaire runtime invalide ou duplique.'
}

$assetState = @()
foreach ($sourceFile in $sourceFiles) {
    if ([IO.Path]::GetFileName($sourceFile.Name) -ne $sourceFile.Name) {
        throw "Nom d'asset runtime non securise : $($sourceFile.Name)"
    }
    $sourcePath = Join-Path $packRootPath $sourceFile.Name
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Asset runtime absent : $sourcePath" }
    $sourceInfo = Get-Item -LiteralPath $sourcePath
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
    if ($sourceInfo.Length -ne $sourceFile.Bytes -or $sourceHash -ne $sourceFile.Hash.ToLowerInvariant()) {
        throw "Asset runtime corrompu : $sourcePath"
    }
    $targetPath = Join-Path $assetsDirectory $sourceFile.Name
    $wasPresent = Test-Path -LiteralPath $targetPath -PathType Leaf
    $originalHash = $null
    if ($wasPresent) {
        $originalHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetPath).Hash.ToLowerInvariant()
        if (-not $sourceFile.AllowsReplacement -and $originalHash -ne $sourceHash) {
            throw "Asset existant protege : $targetPath. Le pack ne l'ecrase pas sans restauration explicite."
        }
    }
    $assetState += [PSCustomObject]@{
        Name = $sourceFile.Name; Source = $sourcePath; Target = $targetPath
        WasPresent = $wasPresent; OriginalHash = $originalHash; InstalledHash = $sourceHash
    }
}

if (-not $BackupRoot) { $BackupRoot = Join-Path $packRootPath 'install-backups' }
$backupRootPath = [IO.Path]::GetFullPath($BackupRoot)
$backupDirectory = Join-Path $backupRootPath ('x4-animation-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $backupDirectory) { throw "Dossier de sauvegarde deja present : $backupDirectory" }
$backupAssets = Join-Path $backupDirectory 'iee-assets'
New-Item -ItemType Directory -Path $backupAssets -Force | Out-Null
Copy-Item -LiteralPath $targetDll -Destination (Join-Path $backupDirectory 'InfinityEngine-Enhancer.dll')
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $backupDirectory 'InfinityEngine-Enhancer.ini')
foreach ($entry in $assetState) {
    if ($entry.WasPresent) { Copy-Item -LiteralPath $entry.Target -Destination (Join-Path $backupAssets $entry.Name) }
}

$backupManifest = [ordered]@{
    Schema = 'bg2-upscale-area-animation-install-backup-v2'
    CreatedUtc = [DateTime]::UtcNow.ToString('o')
    GameRoot = $gameRootPath
    OriginalDllHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetDll).Hash.ToLowerInvariant()
    InstalledDllHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceDll).Hash.ToLowerInvariant()
    OriginalIniHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $iniPath).Hash.ToLowerInvariant()
    PackManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
    Files = @($assetState | ForEach-Object {
        [ordered]@{ Name = $_.Name; WasPresent = [bool]$_.WasPresent; OriginalHash = $_.OriginalHash; InstalledHash = $_.InstalledHash }
    })
}
$backupManifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backupDirectory 'install-backup.json') -Encoding UTF8

try {
    New-Item -ItemType Directory -Path $assetsDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourceDll -Destination $targetDll -Force
    foreach ($entry in $assetState) { Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force }
    Set-IniValue -Path $iniPath -Key 'EnableAreaAnimationX4' -Value 'true'
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $targetDll).Hash.ToLowerInvariant() -ne $backupManifest.InstalledDllHash) {
        throw 'La DLL installee ne correspond pas a la compilation validee.'
    }
    foreach ($entry in $assetState) {
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Target).Hash.ToLowerInvariant() -ne $entry.InstalledHash) {
            throw "Verification apres copie echouee : $($entry.Target)"
        }
    }
    if ((Get-IniSectionKeyCount -Path $iniPath -Section 'Shaders' -Key 'EnableAreaAnimationX4' -ExpectedValue 'true') -ne 1) {
        throw 'La cle EnableAreaAnimationX4 doit apparaitre exactement une fois sous [Shaders].'
    }
} catch {
    $failure = $_
    foreach ($entry in $assetState) {
        if ($entry.WasPresent) {
            Copy-Item -LiteralPath (Join-Path $backupAssets $entry.Name) -Destination $entry.Target -Force
        } elseif (Test-Path -LiteralPath $entry.Target -PathType Leaf) {
            $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Target).Hash.ToLowerInvariant()
            if ($currentHash -eq $entry.InstalledHash) { Remove-Item -LiteralPath $entry.Target -Force }
        }
    }
    Copy-Item -LiteralPath (Join-Path $backupDirectory 'InfinityEngine-Enhancer.dll') -Destination $targetDll -Force
    Copy-Item -LiteralPath (Join-Path $backupDirectory 'InfinityEngine-Enhancer.ini') -Destination $iniPath -Force
    throw "Installation annulee et etat initial restaure : $failure"
}

Write-Host "Pack runtime installe : $($manifest.resource_count) BAM, $($manifest.frame_count) frames x4."
Write-Host "Sauvegarde reversible : $backupDirectory"
Write-Host 'Le jeu reste ferme. Lancez-le vous-meme pour le test.'
