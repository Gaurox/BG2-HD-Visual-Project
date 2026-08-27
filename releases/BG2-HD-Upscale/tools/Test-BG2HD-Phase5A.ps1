[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WeiDUExecutable,
    [Parameter(Mandatory)] [string]$ArchivePath,
    [string]$GameRoot = 'E:\Steam\steamapps\common\Baldur''s Gate II Enhanced Edition',
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference='Stop'
$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
& (Join-Path $release 'tools/Test-BG2HD-Phase5A-Assets.ps1') -ReleaseRoot $release
& (Join-Path $release 'tools/Test-BG2HD-FutureSaveCompatibility.ps1') -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-Phase5A-Core.ps1') -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-Phase5A-WeiDUUpdate.ps1') -WeiDUExecutable $WeiDUExecutable -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-Phase4Archive.ps1') -ArchivePath $ArchivePath -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-EEexVanillaRestore.ps1') -GameRoot $GameRoot -ReleaseRoot $release
& (Join-Path $release 'tests/Test-BG2HD-UninstallBootstrap.ps1') -WeiDUExecutable $WeiDUExecutable -GameRoot $GameRoot -ReleaseRoot $release
Write-Output 'PHASE5A_SUITE=PASSED'
