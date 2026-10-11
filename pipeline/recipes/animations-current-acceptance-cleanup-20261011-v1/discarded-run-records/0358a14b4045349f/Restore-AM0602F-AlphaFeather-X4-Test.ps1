param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$GameRoot = "G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition"
)

$ErrorActionPreference = 'Stop'

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) {
    throw 'Quittez completement BG2EE et InfinityLoader avant restauration de AM0602F.'
}

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$backupRoot = (Resolve-Path -LiteralPath $BackupPath).Path
$backupManifestPath = Join-Path $backupRoot 'install-backup.json'
if (-not (Test-Path -LiteralPath $backupManifestPath -PathType Leaf)) {
    throw "Manifest de sauvegarde absent : $backupManifestPath"
}
$manifest = Get-Content -LiteralPath $backupManifestPath -Raw | ConvertFrom-Json
if ($manifest.Schema -ne 'bg2-upscale-animation-alpha-feather-install-backup-v1' -or
    @($manifest.Files).Count -ne 9) {
    throw 'Sauvegarde AM0602F invalide.'
}
if (-not [string]::Equals([IO.Path]::GetFullPath([string]$manifest.GameRoot), $gameRootPath,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw "Cette sauvegarde appartient a un autre jeu : $($manifest.GameRoot)"
}

$targetDirectory = Join-Path $gameRootPath 'iee-assets'
foreach ($entry in @($manifest.Files)) {
    $name = [string]$entry.Name
    if ([IO.Path]::GetFileName($name) -ne $name) {
        throw "Nom d'asset non securise : $name"
    }
    $backup = Join-Path $backupRoot $name
    $target = Join-Path $targetDirectory $name
    foreach ($required in @($backup, $target)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Asset requis absent : $required"
        }
    }
    $backupHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash.ToLowerInvariant()
    if ($backupHash -ne [string]$entry.OriginalHash) {
        throw "Sauvegarde corrompue : $backup"
    }
    $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    if ($currentHash -ne [string]$entry.TestHash) {
        throw "Asset actif modifie depuis le test, restauration refusee : $target"
    }
}

foreach ($entry in @($manifest.Files)) {
    $backup = Join-Path $backupRoot ([string]$entry.Name)
    $target = Join-Path $targetDirectory ([string]$entry.Name)
    Copy-Item -LiteralPath $backup -Destination $target -Force
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant() -ne [string]$entry.OriginalHash) {
        throw "Verification de restauration echouee : $target"
    }
}

Write-Host "Les 9 frames AM0602F precedentes ont ete restaurees depuis : $backupRoot"
