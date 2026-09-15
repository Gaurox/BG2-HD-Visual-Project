param(
    [Parameter(Mandatory = $true)] [string]$Queue,
    [switch]$Run,
    [ValidateRange(1, 3)] [int]$Components = 3,
    [ValidateRange(1, 16)] [int]$PreWorkers = 2,
    [ValidateRange(1, 16)] [int]$PostWorkers = 3,
    [ValidateRange(512, 32768)] [int]$MemoryMiB = 2048
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
$python = & python -B -c "import sys; sys.path.insert(0, 'pipeline/scripts'); from workspace_paths import get_path; print(get_path('chainner_python', required=True))"
if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve config://chainner_python' }
$runner = Join-Path $PSScriptRoot 'reboutcx_playable_p10.py'
if ($Run) {
    & $python -B $runner run $Queue --components $Components --pre-workers $PreWorkers --post-workers $PostWorkers --memory-mib $MemoryMiB
} else {
    & $python -B $runner plan $Queue
}
if ($LASTEXITCODE -ne 0) { throw 'P10 command failed' }
