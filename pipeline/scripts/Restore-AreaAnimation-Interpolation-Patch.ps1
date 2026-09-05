param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT
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

$ErrorActionPreference = "Stop"

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw "Quittez completement BG2EE et InfinityLoader avant restauration." }

$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$backupRoot = (Resolve-Path -LiteralPath $BackupPath).Path
$backupManifestPath = Join-Path $backupRoot "install-backup.json"
$manifest = Get-Content -LiteralPath $backupManifestPath -Raw | ConvertFrom-Json
if ($manifest.Schema -ne "bg2-upscale-area-animation-interpolation-install-backup-v1" -or
    -not ([string]$manifest.Resref -match "^[A-Z0-9]{1,8}$") -or @($manifest.Files).Count -le 0) {
    throw "Sauvegarde interpolation incompatible."
}
if (-not [string]::Equals([IO.Path]::GetFullPath([string]$manifest.GameRoot), $gameRootPath,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw "Cette sauvegarde appartient a une autre installation du jeu."
}

$assetsRoot = Join-Path $gameRootPath "iee-assets"
$targetRegistry = Join-Path $assetsRoot "AreaAnimations-X4.registry"
$backupRegistry = Join-Path $backupRoot "AreaAnimations-X4.registry"
if ((Get-Sha256 $targetRegistry) -ne [string]$manifest.TestRegistryHash) {
    throw "Le registre actif a change depuis le test ; restauration refusee."
}
if ((Get-Sha256 $backupRegistry) -ne [string]$manifest.OriginalRegistryHash) {
    throw "Le registre de sauvegarde est corrompu."
}

foreach ($entry in @($manifest.Files)) {
    $name = [string]$entry.Name
    if ([IO.Path]::GetFileName($name) -ne $name) { throw "Nom asset non securise : $name" }
    $target = Join-Path $assetsRoot $name
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or (Get-Sha256 $target) -ne [string]$entry.TestHash) {
        throw "Asset actif modifie depuis le test : $target"
    }
    if ([bool]$entry.WasPresent) {
        $backup = Join-Path $backupRoot $name
        if (-not (Test-Path -LiteralPath $backup -PathType Leaf) -or (Get-Sha256 $backup) -ne [string]$entry.OriginalHash) {
            throw "Asset de sauvegarde corrompu : $backup"
        }
    }
}

Copy-Item -LiteralPath $backupRegistry -Destination $targetRegistry -Force
foreach ($entry in @($manifest.Files)) {
    $target = Join-Path $assetsRoot ([string]$entry.Name)
    if ([bool]$entry.WasPresent) {
        Copy-Item -LiteralPath (Join-Path $backupRoot ([string]$entry.Name)) -Destination $target -Force
    } else {
        Remove-Item -LiteralPath $target -Force
    }
}
if ((Get-Sha256 $targetRegistry) -ne [string]$manifest.OriginalRegistryHash) {
    throw "Verification de restauration du registre echouee."
}
Write-Host "Interpolation $($manifest.Resref) restauree depuis : $backupRoot"
