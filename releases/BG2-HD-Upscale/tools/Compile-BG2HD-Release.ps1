[CmdletBinding()]
param([string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path)

$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $ReleaseRoot '..\..'))

& (Join-Path $PSScriptRoot 'New-BG2HD-ContentManifest.ps1') `
    -WorkspaceRoot $workspace -OutputPath (Join-Path $ReleaseRoot 'manifests\content.json')
& (Join-Path $PSScriptRoot 'New-BG2HD-ComponentManifest.ps1') -ReleaseRoot $ReleaseRoot
& (Join-Path $PSScriptRoot 'Generate-BG2HD-Tp2.ps1') -ReleaseRoot $ReleaseRoot
& (Join-Path $PSScriptRoot 'Sync-BG2HD-PackageMetadata.ps1') -ReleaseRoot $ReleaseRoot
