[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WeiDUExecutable,
    [Parameter(Mandatory)] [string]$ArchivePath,
    [string]$GameRoot = $env:BG2EE_GAME_ROOT,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
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

$ErrorActionPreference='Stop'
$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
$workspace=(Resolve-Path -LiteralPath (Join-Path $release '..\..')).Path
. (Join-Path $release 'tools/Assert-BG2HD-NoActiveAnimationTransaction.ps1')
$animationAuthorityLease = Enter-BG2HDAnimationAuthorityLock -WorkspaceRoot $workspace
$previousTemp=$env:TEMP
$previousTmp=$env:TMP
try {
    # Keep Win32/WeiDU source paths short and all fixtures writable in the workspace.
    $fixtureBase=Join-Path $workspace '.tmp/qa-bg2hd'
    [IO.Directory]::CreateDirectory($fixtureBase) | Out-Null
    $env:TEMP=$fixtureBase
    $env:TMP=$fixtureBase
& (Join-Path $release 'tools/Test-BG2HD-Phase5A-Assets.ps1') -ReleaseRoot $release
& (Join-Path $release 'tools/Test-BG2HD-FutureSaveCompatibility.ps1') -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-ConfigEncoding.ps1') -ReleaseRoot $release
& (Join-Path $release 'tools/Test-BG2HD-SpriteConfig.ps1') -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-Phase5A-Core.ps1') -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-Phase5A-WeiDUUpdate.ps1') -WeiDUExecutable $WeiDUExecutable -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-Phase4Archive.ps1') -ArchivePath $ArchivePath -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-EEexVanillaRestore.ps1') -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-UninstallBootstrap.ps1') -WeiDUExecutable $WeiDUExecutable -GameRoot $GameRoot -ReleaseRoot $release
Write-Output 'PHASE5A_SUITE=PASSED'
}
finally {
    Exit-BG2HDAnimationAuthorityLock -Lease $animationAuthorityLease
    $env:TEMP=$previousTemp
    $env:TMP=$previousTmp
}
