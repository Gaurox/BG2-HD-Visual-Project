[CmdletBinding()]
param(
    [string]$ReleaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path,
    [string]$WeiDUExecutable = (Join-Path $PSScriptRoot '..\release-inputs\weidu\setup-bg2hd.exe'),
    [string]$PayloadRoot = (Join-Path $PSScriptRoot '..\bg2hd\payload-allvalidated'),
    [string]$OutputName = 'BG2HD-Installer-Windows'
)

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Build-BG2HD-SaveCompatTestPackage.ps1') `
    -ReleaseRoot $ReleaseRoot `
    -WeiDUExecutable $WeiDUExecutable `
    -PayloadRoot $PayloadRoot `
    -OutputName $OutputName
