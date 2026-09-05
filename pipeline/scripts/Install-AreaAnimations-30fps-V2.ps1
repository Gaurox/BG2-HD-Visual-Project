param(
    [Parameter(Mandatory = $true)]
    [string]$RunRoot,
    [string]$DllPath,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$BackupRoot,
    [switch]$VerifyOnly
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

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
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
        if ($currentSection -eq $Section -and
            $line -match ('^\s*' + [regex]::Escape($Key) + '\s*=\s*' + [regex]::Escape($ExpectedValue) + '\s*$')) {
            ++$count
        }
    }
    return $count
}

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant la verification ou installation V2.' }

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$runRootPath = (Resolve-Path -LiteralPath $RunRoot).Path
$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
if (-not $DllPath) {
    $DllPath = Join-Path $projectRoot 'engine\InfinityEngine-Enhancer\source-patchee\build-filter-diagnostic-v142\Release\InfinityEngine-Enhancer.dll'
}
$sourceDll = (Resolve-Path -LiteralPath $DllPath).Path
$runManifestPath = Join-Path $runRootPath 'manifest.json'
$approvalPath = Join-Path $runRootPath 'qa-approval.json'
$packRootPath = Join-Path $runRootPath '03_runtime_pack'
$packManifestPath = Join-Path $packRootPath 'manifest.json'
foreach ($required in @($runManifestPath, $approvalPath, $packManifestPath, $sourceDll)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier requis absent : $required" }
}

$runManifest = Get-Content -LiteralPath $runManifestPath -Raw | ConvertFrom-Json
$approval = Get-Content -LiteralPath $approvalPath -Raw | ConvertFrom-Json
$packManifest = Get-Content -LiteralPath $packManifestPath -Raw | ConvertFrom-Json
if ($runManifest.schema -ne 'bg2-upscale-area-animation-30fps-run-v2' -or
    $runManifest.status -ne 'completed' -or $runManifest.qa_status -ne 'pending-explicit-user-approval' -or
    $runManifest.pack -ne '03_runtime_pack') {
    throw 'Run temporel V2 incomplet ou incompatible.'
}
if ($approval.schema -ne 'bg2-upscale-area-animation-30fps-approval-v2' -or
    $approval.status -ne 'accepted' -or
    [string]$approval.run_manifest_sha256 -ne (Get-Sha256 $runManifestPath) -or
    [string]$approval.pack_manifest_sha256 -ne (Get-Sha256 $packManifestPath) -or
    [string]$approval.pack_manifest_sha256 -ne [string]$runManifest.pack_manifest_sha256 -or
    [string]$approval.registry_sha256 -ne [string]$runManifest.registry_sha256) {
    throw 'Approbation visuelle V2 absente, obsolete ou incoherente.'
}
if ($packManifest.schema -ne 'bg2-upscale-area-animation-runtime-pack-v2' -or
    $packManifest.status -ne 'completed' -or [int]$packManifest.scale -ne 4 -or
    [int]$packManifest.registry_version -notin @(2, 3) -or
    $packManifest.runtime_contract.feature -ne 'TimedTimeline' -or
    $packManifest.runtime_contract.clock -ne 'QPC-pause-aware' -or
    $packManifest.registry -ne 'AreaAnimations-X4.registry' -or
    [int]$packManifest.resource_count -le 0 -or [int]$packManifest.frame_count -le 0) {
    throw 'Pack runtime temporel V2 incomplet ou incompatible.'
}

$accepted = @($approval.accepted_resrefs | ForEach-Object { ([string]$_).ToUpperInvariant() } | Sort-Object)
$timed = @($runManifest.timed_resources | ForEach-Object { ([string]$_).ToUpperInvariant() } | Sort-Object)
if (($accepted -join ',') -ne ($timed -join ',') -or $accepted.Count -eq 0) {
    throw 'Approbation visuelle partielle : toutes les ressources temporisees doivent etre acceptees.'
}

$assetsRoot = Join-Path $gameRootPath 'iee-assets'
$targetDll = Join-Path $gameRootPath 'InfinityEngine-Enhancer.dll'
$iniPath = Join-Path $gameRootPath 'InfinityEngine-Enhancer.ini'
$targetRegistry = Join-Path $assetsRoot 'AreaAnimations-X4.registry'
$sourceRegistry = Join-Path $packRootPath 'AreaAnimations-X4.registry'
foreach ($required in @($targetDll, $iniPath, $targetRegistry, $sourceRegistry)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Fichier runtime requis absent : $required" }
}
if ((Get-Sha256 $sourceRegistry) -ne [string]$packManifest.registry_sha256 -or
    (Get-Item -LiteralPath $sourceRegistry).Length -ne [int64]$packManifest.registry_bytes) {
    throw 'Registre V2 source corrompu.'
}
if ((Get-Sha256 $targetRegistry) -ne [string]$packManifest.base_registry_sha256 -or
    (Get-Item -LiteralPath $targetRegistry).Length -ne [int64]$packManifest.base_registry_bytes) {
    throw 'Le registre actif ne correspond pas exactement au pack de base approuve.'
}

$baseAssets = @($packManifest.base_assets)
$newAssets = @($packManifest.new_assets)
$replacementAssets = if ($null -ne $packManifest.PSObject.Properties['replacement_assets']) { @($packManifest.replacement_assets) } else { @() }
if ($baseAssets.Count + $newAssets.Count + $replacementAssets.Count -ne [int]$packManifest.frame_count -or
    @($baseAssets + $newAssets + $replacementAssets | Select-Object -ExpandProperty name -Unique).Count -ne [int]$packManifest.frame_count) {
    throw 'Inventaire base/nouvelles phases V2 invalide ou duplique.'
}
foreach ($asset in $baseAssets) {
    $name = [string]$asset.name
    $target = Join-Path $assetsRoot $name
    if ([IO.Path]::GetFileName($name) -ne $name -or
        -not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Item -LiteralPath $target).Length -ne [int64]$asset.bytes -or
        (Get-Sha256 $target) -ne [string]$asset.sha256) {
        throw "Asset du pack de base actif absent ou modifie : $name"
    }
}

$replacementEntries = @()
foreach ($asset in $replacementAssets) {
    $name = [string]$asset.name
    $source = Join-Path $packRootPath $name
    $target = Join-Path $assetsRoot $name
    if ([IO.Path]::GetFileName($name) -ne $name -or
        -not (Test-Path -LiteralPath $source -PathType Leaf) -or
        (Get-Item -LiteralPath $source).Length -ne [int64]$asset.bytes -or
        (Get-Sha256 $source) -ne [string]$asset.sha256 -or
        -not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Item -LiteralPath $target).Length -ne [int64]$asset.expected_base_bytes -or
        (Get-Sha256 $target) -ne [string]$asset.expected_base_sha256) {
        throw "Asset V2 a remplacer absent, modifie ou incompatible : $name"
    }
    $replacementEntries += [PSCustomObject]@{
        Name = $name; Source = $source; Target = $target
        Hash = [string]$asset.sha256; Bytes = [int64]$asset.bytes
        OriginalHash = [string]$asset.expected_base_sha256; OriginalBytes = [int64]$asset.expected_base_bytes
    }
}

$newEntries = @()
foreach ($asset in $newAssets) {
    $name = [string]$asset.name
    $source = Join-Path $packRootPath $name
    $target = Join-Path $assetsRoot $name
    if ([IO.Path]::GetFileName($name) -ne $name -or
        -not (Test-Path -LiteralPath $source -PathType Leaf) -or
        (Get-Item -LiteralPath $source).Length -ne [int64]$asset.bytes -or
        (Get-Sha256 $source) -ne [string]$asset.sha256) {
        throw "Phase V2 source absente ou corrompue : $name"
    }
    if (Test-Path -LiteralPath $target) {
        throw "Phase V2 deja presente dans le jeu ; restaurez d'abord l'etat de base : $name"
    }
    $newEntries += [PSCustomObject]@{
        Name = $name; Source = $source; Target = $target
        Hash = [string]$asset.sha256; Bytes = [int64]$asset.bytes
    }
}

if ($VerifyOnly) {
    Write-Host "Verification V2 OK : $($accepted.Count) BAM approuvees, $($newEntries.Count) phases nouvelles et $($replacementEntries.Count) assets a remplacer."
    Write-Host 'Aucun fichier modifie.'
    exit 0
}

if (-not $BackupRoot) { $BackupRoot = Join-Path $runRootPath 'install-backups' }
$backupRootPath = [IO.Path]::GetFullPath($BackupRoot)
$backupDirectory = Join-Path $backupRootPath ('30fps-v2-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $backupDirectory) { throw "Dossier de sauvegarde deja present : $backupDirectory" }
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
Copy-Item -LiteralPath $targetDll -Destination (Join-Path $backupDirectory 'InfinityEngine-Enhancer.dll')
Copy-Item -LiteralPath $iniPath -Destination (Join-Path $backupDirectory 'InfinityEngine-Enhancer.ini')
Copy-Item -LiteralPath $targetRegistry -Destination (Join-Path $backupDirectory 'AreaAnimations-X4.registry')
$backupAssets = Join-Path $backupDirectory 'iee-assets'
if ($replacementEntries.Count -gt 0) {
    New-Item -ItemType Directory -Path $backupAssets -Force | Out-Null
    foreach ($entry in $replacementEntries) {
        Copy-Item -LiteralPath $entry.Target -Destination (Join-Path $backupAssets $entry.Name)
    }
}

$backupManifest = [ordered]@{
    Schema = 'bg2-upscale-area-animation-30fps-install-backup-v2'
    Status = 'prepared'
    CreatedUtc = [DateTime]::UtcNow.ToString('o')
    GameRoot = $gameRootPath
    RunManifestHash = Get-Sha256 $runManifestPath
    ApprovalHash = Get-Sha256 $approvalPath
    OriginalDllHash = Get-Sha256 $targetDll
    InstalledDllHash = Get-Sha256 $sourceDll
    OriginalIniHash = Get-Sha256 $iniPath
    InstalledIniHash = $null
    OriginalRegistryHash = Get-Sha256 $targetRegistry
    InstalledRegistryHash = Get-Sha256 $sourceRegistry
    NewAssets = @($newEntries | ForEach-Object {
        [ordered]@{ Name = $_.Name; Hash = $_.Hash; Bytes = $_.Bytes }
    })
    ReplacedAssets = @($replacementEntries | ForEach-Object {
        [ordered]@{ Name = $_.Name; OriginalHash = $_.OriginalHash; OriginalBytes = $_.OriginalBytes; Hash = $_.Hash; Bytes = $_.Bytes }
    })
}
$backupManifestPath = Join-Path $backupDirectory 'install-backup.json'
$backupManifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $backupManifestPath -Encoding UTF8

try {
    Copy-Item -LiteralPath $sourceDll -Destination $targetDll -Force
    Copy-Item -LiteralPath $sourceRegistry -Destination $targetRegistry -Force
    foreach ($entry in $replacementEntries) { Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force }
    foreach ($entry in $newEntries) { Copy-Item -LiteralPath $entry.Source -Destination $entry.Target }
    Set-IniValue -Path $iniPath -Key 'EnableAreaAnimationX4' -Value 'true'
    if ((Get-Sha256 $targetDll) -ne [string]$backupManifest.InstalledDllHash -or
        (Get-Sha256 $targetRegistry) -ne [string]$backupManifest.InstalledRegistryHash) {
        throw 'Verification DLL/registre V2 apres copie echouee.'
    }
    foreach ($entry in $newEntries) {
        if ((Get-Sha256 $entry.Target) -ne $entry.Hash) {
            throw "Verification apres copie echouee : $($entry.Target)"
        }
    }
    foreach ($entry in $replacementEntries) {
        if ((Get-Sha256 $entry.Target) -ne $entry.Hash) {
            throw "Verification apres remplacement echouee : $($entry.Target)"
        }
    }
    if ((Get-IniSectionKeyCount -Path $iniPath -Section 'Shaders' -Key 'EnableAreaAnimationX4' -ExpectedValue 'true') -ne 1) {
        throw 'La cle EnableAreaAnimationX4 doit apparaitre exactement une fois sous [Shaders].'
    }
    $backupManifest.InstalledIniHash = Get-Sha256 $iniPath
    $backupManifest.Status = 'installed'
    $backupManifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $backupManifestPath -Encoding UTF8
} catch {
    $failure = $_
    Copy-Item -LiteralPath (Join-Path $backupDirectory 'InfinityEngine-Enhancer.dll') -Destination $targetDll -Force
    Copy-Item -LiteralPath (Join-Path $backupDirectory 'InfinityEngine-Enhancer.ini') -Destination $iniPath -Force
    Copy-Item -LiteralPath (Join-Path $backupDirectory 'AreaAnimations-X4.registry') -Destination $targetRegistry -Force
    foreach ($entry in $replacementEntries) {
        Copy-Item -LiteralPath (Join-Path $backupAssets $entry.Name) -Destination $entry.Target -Force
    }
    foreach ($entry in $newEntries) {
        if (Test-Path -LiteralPath $entry.Target -PathType Leaf) {
            if ((Get-Sha256 $entry.Target) -eq $entry.Hash) { Remove-Item -LiteralPath $entry.Target -Force }
        }
    }
    throw "Installation V2 annulee et etat initial restaure : $failure"
}

Write-Host "Pack 30 fps V2 installe : $($accepted.Count) BAM, $($newEntries.Count) phases nouvelles, $($replacementEntries.Count) assets remplaces."
Write-Host "Sauvegarde reversible : $backupDirectory"
Write-Host 'Le jeu reste ferme. Lancez-le vous-meme pour la QA ingame.'
