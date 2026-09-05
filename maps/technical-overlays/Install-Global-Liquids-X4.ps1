param(
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$BackupRoot = (Join-Path $PSScriptRoot 'backups\global-liquids-x4-20260823')
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
    if ($running) { throw 'Quittez completement BG2EE et InfinityLoader avant installation.' }
}

Assert-GameClosed
$gameRootPath = (Resolve-Path -LiteralPath $GameRoot).Path
$overridePath = Join-Path $gameRootPath 'override'
$backupPath = [IO.Path]::GetFullPath($BackupRoot)
if (Test-Path -LiteralPath $backupPath) { throw "Sauvegarde deja existante : $backupPath" }

$runName = 'seedvr2-7b-int8-lab-x4-global-overlays'
$sets = @(
    [pscustomobject]@{ Resref='WTLAKA'; Pvrz='WLAKA00.PVRZ' },
    [pscustomobject]@{ Resref='WTLAKB'; Pvrz='WLAKB00.PVRZ' },
    [pscustomobject]@{ Resref='WTLAKC'; Pvrz='WLAKC00.PVRZ' },
    [pscustomobject]@{ Resref='WTLAKD'; Pvrz='WLAKD00.PVRZ' },
    [pscustomobject]@{ Resref='WTLAKE'; Pvrz='WLAKE00.PVRZ' },
    [pscustomobject]@{ Resref='WTPOOL'; Pvrz='WPOOL00.PVRZ' },
    [pscustomobject]@{ Resref='WTSWAM'; Pvrz='WSWAM00.PVRZ' }
)

$resources = foreach ($set in $sets) {
    $build = Join-Path $PSScriptRoot ($set.Resref + '\runs\' + $runName + '\03_build_x4')
    [pscustomobject]@{ Name=($set.Resref + '.TIS'); Source=(Join-Path $build ($set.Resref + '.TIS')) }
    [pscustomobject]@{ Name=$set.Pvrz; Source=(Join-Path $build $set.Pvrz) }
}
foreach ($resource in $resources) {
    if (-not (Test-Path -LiteralPath $resource.Source -PathType Leaf)) { throw "Build absent : $($resource.Source)" }
    $resource | Add-Member -NotePropertyName InstalledHash -NotePropertyValue ((Get-FileHash -LiteralPath $resource.Source -Algorithm SHA256).Hash.ToLowerInvariant())
    $resource | Add-Member -NotePropertyName Destination -NotePropertyValue (Join-Path $overridePath $resource.Name)
    $resource | Add-Member -NotePropertyName WasPresent -NotePropertyValue (Test-Path -LiteralPath $resource.Destination -PathType Leaf)
    $resource | Add-Member -NotePropertyName OriginalHash -NotePropertyValue $null
    if ($resource.WasPresent) { $resource.OriginalHash = (Get-FileHash -LiteralPath $resource.Destination -Algorithm SHA256).Hash.ToLowerInvariant() }
}

New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
foreach ($resource in $resources) {
    if ($resource.WasPresent) { Copy-Item -LiteralPath $resource.Destination -Destination (Join-Path $backupPath $resource.Name) }
}
$manifest = [ordered]@{
    Schema = 'bg2-upscale-global-liquids-x4-install-v1'
    CreatedUtc = [DateTime]::UtcNow.ToString('o')
    GameRoot = $gameRootPath
    Files = @($resources | ForEach-Object { [ordered]@{ Name=$_.Name; WasPresent=[bool]$_.WasPresent; OriginalHash=$_.OriginalHash; InstalledHash=$_.InstalledHash } })
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backupPath 'install-backup.json') -Encoding utf8

try {
    foreach ($resource in $resources) { Copy-Item -LiteralPath $resource.Source -Destination $resource.Destination -Force }
    foreach ($resource in $resources) {
        if ((Get-FileHash -LiteralPath $resource.Destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $resource.InstalledHash) {
            throw "Verification SHA-256 echouee : $($resource.Name)"
        }
    }
} catch {
    $failure = $_
    foreach ($resource in $resources) {
        if ($resource.WasPresent) {
            Copy-Item -LiteralPath (Join-Path $backupPath $resource.Name) -Destination $resource.Destination -Force
        } elseif (Test-Path -LiteralPath $resource.Destination -PathType Leaf) {
            $currentHash = (Get-FileHash -LiteralPath $resource.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($currentHash -eq $resource.InstalledHash) { Remove-Item -LiteralPath $resource.Destination -Force }
        }
    }
    throw "Installation annulee et etat initial restaure : $failure"
}

Write-Host 'Overlays liquides x4 installes : 7 cycles, 14 fichiers verifies.'
Write-Host "Restauration : $PSScriptRoot\Restore-Global-Liquids-X4.ps1"
