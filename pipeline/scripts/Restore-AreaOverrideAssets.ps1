# Restaure l'override d'une zone a son etat d'avant Install-AreaOverrideAssets.ps1.
#
# Un fichier absent avant l'installation est supprime, un fichier remplace est remis a
# l'identique. La restauration refuse un etat installe divergent plutot que d'ecraser un
# changement qu'elle ne connait pas.

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
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

function Get-Sha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$running = Get-Process -Name Baldur, BaldurReal, InfinityLoader -ErrorAction SilentlyContinue
if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant restauration.' }

$backupPath = (Resolve-Path -LiteralPath $BackupPath).Path
$overrideDir = Join-Path (Resolve-Path -LiteralPath $GameRoot).Path 'override'
$record = Get-Content -LiteralPath (Join-Path $backupPath 'install-backup.json') -Raw | ConvertFrom-Json
if ($record.schema -ne 'bg2-upscale-area-override-install-backup-v1') {
    throw 'Sauvegarde d override incompatible.'
}

$plan = @()
foreach ($file in @($record.Files)) {
    $name = [string]$file.Name
    if ([IO.Path]::GetFileName($name) -ne $name) { throw "Nom de fichier non securise : $name" }
    $target = Join-Path $overrideDir $name
    $current = Get-Sha256 $target
    if ($current -and $current -ne ([string]$file.InstalledSha256).ToLowerInvariant()) {
        throw "Etat installe divergent, restauration refusee : $target"
    }
    if ($file.PresentBefore) {
        $saved = Join-Path $backupPath $name
        if (-not (Test-Path -LiteralPath $saved -PathType Leaf)) { throw "Sauvegarde absente : $saved" }
        if ((Get-Sha256 $saved) -ne ([string]$file.PreviousSha256).ToLowerInvariant()) {
            throw "Fichier de sauvegarde corrompu : $saved"
        }
        $plan += [PSCustomObject]@{ Action = 'remettre'; Target = $target; Source = $saved; Hash = ([string]$file.PreviousSha256).ToLowerInvariant() }
    } else {
        $plan += [PSCustomObject]@{ Action = 'supprimer'; Target = $target; Source = $null; Hash = $null }
    }
}

foreach ($entry in $plan) { Write-Host ("  {0,-10} {1}" -f $entry.Action, $entry.Target) }
if ($VerifyOnly) { Write-Host 'VerifyOnly : aucune ecriture effectuee.'; return }

foreach ($entry in $plan) {
    if ($entry.Action -eq 'remettre') {
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force
        if ((Get-Sha256 $entry.Target) -ne $entry.Hash) { throw "Restauration echouee : $($entry.Target)" }
    } elseif (Test-Path -LiteralPath $entry.Target -PathType Leaf) {
        Remove-Item -LiteralPath $entry.Target -Force
    }
}

Write-Host 'Restauration terminee. Le jeu n a pas ete lance.'
