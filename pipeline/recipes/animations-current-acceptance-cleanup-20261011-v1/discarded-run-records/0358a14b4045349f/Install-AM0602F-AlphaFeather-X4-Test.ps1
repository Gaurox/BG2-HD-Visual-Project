param(
    [string]$GameRoot = "G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition",
    [string]$PrototypeRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) {
    throw 'Quittez completement BG2EE et InfinityLoader avant le test AM0602F.'
}

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$prototypeRootPath = (Resolve-Path -LiteralPath $PrototypeRoot).Path
$manifestPath = Join-Path $prototypeRootPath 'manifest.json'
$sourceDirectory = Join-Path $prototypeRootPath 'raw_rgba'
$targetDirectory = Join-Path $gameRootPath 'iee-assets'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifest de test absent : $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema -ne 'bg2-upscale-animation-alpha-feather-test-v1' -or
    $manifest.status -ne 'completed' -or
    $manifest.resref -ne 'AM0602F' -or
    [int]$manifest.frame_count -ne 9 -or
    [double]$manifest.alpha_operation.radius_physical_x4 -ne 8.0) {
    throw 'Manifest AM0602F incomplet ou incompatible.'
}

$entries = @()
foreach ($frame in @($manifest.frames)) {
    $name = [IO.Path]::GetFileName([string]$frame.runtime_asset)
    if ($name -ne ('AAX4-AM0602F-frame{0:D3}.rgba' -f [int]$frame.frame)) {
        throw "Nom runtime inattendu : $name"
    }
    $source = Join-Path $sourceDirectory $name
    $target = Join-Path $targetDirectory $name
    foreach ($required in @($source, $target)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Asset requis absent : $required"
        }
    }
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
    if ($sourceHash -ne [string]$frame.runtime_sha256 -or
        (Get-Item -LiteralPath $source).Length -ne [int64]$frame.runtime_bytes) {
        throw "Asset experimental corrompu : $source"
    }
    $entries += [PSCustomObject]@{
        Name = $name
        Source = $source
        Target = $target
        OriginalHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
        TestHash = $sourceHash
        Bytes = [int64]$frame.runtime_bytes
    }
}

$backupDirectory = Join-Path $prototypeRootPath ('install-backups\alpha-feather-x4-8px-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $backupDirectory) {
    throw "Sauvegarde deja presente : $backupDirectory"
}
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
foreach ($entry in $entries) {
    Copy-Item -LiteralPath $entry.Target -Destination (Join-Path $backupDirectory $entry.Name)
}

$backupManifest = [ordered]@{
    Schema = 'bg2-upscale-animation-alpha-feather-install-backup-v1'
    CreatedUtc = [DateTime]::UtcNow.ToString('o')
    GameRoot = $gameRootPath
    RadiusPhysicalX4 = 8.0
    Files = @($entries | ForEach-Object {
        [ordered]@{
            Name = $_.Name
            OriginalHash = $_.OriginalHash
            TestHash = $_.TestHash
            Bytes = $_.Bytes
        }
    })
}
$backupManifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backupDirectory 'install-backup.json') -Encoding UTF8

try {
    foreach ($entry in $entries) {
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force
        $installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Target).Hash.ToLowerInvariant()
        if ($installedHash -ne $entry.TestHash) {
            throw "Verification apres copie echouee : $($entry.Target)"
        }
    }
} catch {
    $failure = $_
    foreach ($entry in $entries) {
        Copy-Item -LiteralPath (Join-Path $backupDirectory $entry.Name) -Destination $entry.Target -Force
    }
    throw "Installation annulee et assets initiaux restaures : $failure"
}

Write-Host ("AM0602F x4 installee : fondu objet {0} px x4, bord canvas {1} px x4." -f `
    $manifest.alpha_operation.radius_physical_x4, $manifest.alpha_operation.canvas_edge_radius_physical_x4)
Write-Host "Sauvegarde reversible : $backupDirectory"
Write-Host 'Le jeu reste ferme. Lancez-le vous-meme et testez la lanterne dans AR0602.'
