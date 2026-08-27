[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference='Stop'
$workspace=(Resolve-Path -LiteralPath $WorkspaceRoot).Path
$release=(Resolve-Path -LiteralPath $ReleaseRoot).Path
& python (Join-Path $release 'tools/Validate-BG2HD-Assets.py') --workspace $workspace --content (Join-Path $release 'manifests/content.json')
if($LASTEXITCODE -ne 0){throw 'Validation structurelle des assets echouee.'}
Write-Output 'PHASE5A_ASSET_STRUCTURE=PASSED'
