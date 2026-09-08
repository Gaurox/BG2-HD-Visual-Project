[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$GameRoot,
    [string]$RuntimeBatch = 'icons/batches/item-inventory-xbr2x-aa-runtime-v3'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path.TrimEnd('\')
function Resolve-WorkspacePath([string]$Value) {
    if ([IO.Path]::IsPathRooted($Value)) { return [IO.Path]::GetFullPath($Value) }
    return [IO.Path]::GetFullPath((Join-Path $workspaceRoot $Value))
}
function Get-Sha256([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash }

if (@(Get-Process -Name 'InfinityLoader', 'Baldur', 'BaldurReal' -ErrorAction SilentlyContinue).Count -ne 0) {
    throw 'Le jeu ou InfinityLoader est actif. Ferme-le avant restauration.'
}
$gameFull = (Resolve-Path -LiteralPath (Resolve-WorkspacePath $GameRoot)).Path.TrimEnd('\')
$runRoot = (Resolve-Path -LiteralPath (Resolve-WorkspacePath $RuntimeBatch)).Path
$statePath = Join-Path $runRoot 'ingame-test\active-test.json'
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.schema -notin @('bg2-upscale-item-icon-x2-ingame-test-v1',
                           'bg2-upscale-item-icon-x2-ingame-test-v2') -or
    $state.status -notin @('installed-pending-qa', 'validated-installed', 'qa-failed')) {
    throw "Etat installation non restaurable : $($state.status)"
}
if (-not [string]::Equals([string]$state.game_root, $gameFull, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Le GameRoot differe de etat actif.'
}
foreach ($targetState in $state.targets) {
    $target = [IO.Path]::GetFullPath((Join-Path $gameFull $targetState.relative_path))
    if (-not $target.StartsWith($gameFull + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Cible hors jeu : $target" }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Sha256 $target) -ne [string]$targetState.installed_sha256) {
        throw "Cible absente ou modifiee depuis installation : $($targetState.relative_path)"
    }
    if ($targetState.existed_before -and
        ((-not (Test-Path -LiteralPath $targetState.backup_path -PathType Leaf)) -or
         (Get-Sha256 $targetState.backup_path) -ne [string]$targetState.original_sha256)) {
        throw "Sauvegarde absente ou altérée : $($targetState.relative_path)"
    }
}
foreach ($targetState in $state.targets) {
    $target = [IO.Path]::GetFullPath((Join-Path $gameFull $targetState.relative_path))
    if ($targetState.existed_before) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $targetState.backup_path -Destination $target -Force
    } else {
        Remove-Item -LiteralPath $target -Force
    }
}
$state.status = 'restored'
$state | Add-Member -MemberType NoteProperty -Name restored_at_utc -Value ((Get-Date).ToUniversalTime().ToString('o')) -Force
$state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding utf8
[pscustomobject]@{ Status = $state.status; GameRoot = $gameFull; State = $statePath }
