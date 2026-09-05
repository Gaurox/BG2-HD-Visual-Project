param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$GameRoot,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$core = Join-Path (Join-Path (Split-Path -Parent $PSScriptRoot) 'area-animation-area-test') 'area_animation_area_test.py'
if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
    throw "Coeur transactionnel absent : $core"
}

$arguments = @($core, 'restore', '--backup-path', $BackupPath)
if (-not [string]::IsNullOrWhiteSpace($GameRoot)) {
    $arguments += @('--game-root', $GameRoot)
}
if ($VerifyOnly) {
    $arguments += '--verify-only'
}

& python @arguments
exit $LASTEXITCODE
