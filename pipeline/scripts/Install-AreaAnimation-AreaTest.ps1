param(
    [Parameter(Mandatory = $true)]
    [string]$AreaPack,
    [string]$GameRoot,
    [string]$BackupRoot,
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$core = Join-Path (Join-Path (Split-Path -Parent $PSScriptRoot) 'area-animation-area-test') 'area_animation_area_test.py'
if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
    throw "Coeur transactionnel absent : $core"
}

$arguments = @($core, 'install', '--area-pack', $AreaPack)
if (-not [string]::IsNullOrWhiteSpace($GameRoot)) {
    $arguments += @('--game-root', $GameRoot)
}
if (-not [string]::IsNullOrWhiteSpace($BackupRoot)) {
    $arguments += @('--backup-root', $BackupRoot)
}
if ($VerifyOnly) {
    $arguments += '--verify-only'
}

& python @arguments
exit $LASTEXITCODE
