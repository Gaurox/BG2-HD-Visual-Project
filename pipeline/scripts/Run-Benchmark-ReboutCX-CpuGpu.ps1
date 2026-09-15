param(
    [int[]]$CpuWorkers = @(2, 4, 6, 8, 10),
    [ValidateRange(1, 256)]
    [int]$BatchSize = 86
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
$python = 'C:\Users\Adrien\AppData\Roaming\chaiNNer\python\python\python.exe'
$runner = Join-Path $projectRoot 'pipeline\scripts\benchmark_reboutcx_cpu_gpu_pipeline.py'
$job = Join-Path $projectRoot 'sprite\families\playable-characters\6200-human-male-mage\chmw1\jobs\reboutcx-p8-full-v1.json'
$source = Join-Path $projectRoot 'sprite\families\playable-characters\5000-human-male-cleric-low\chmb1\source\manifest.json'
$logs = Join-Path $projectRoot 'sprite\.work\benchmarks\reboutcx-cpu-gpu-5000-chmb1-q64'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

foreach ($workers in $CpuWorkers) {
    $stdout = Join-Path $logs ("cpu-{0}.stdout.json" -f $workers)
    $stderr = Join-Path $logs ("cpu-{0}.stderr.log" -f $workers)
    $arguments = @($runner, $job, $source, '--configured', '--batch-size', $BatchSize, '--cpu-workers', $workers)
    $process = Start-Process -FilePath $python -ArgumentList $arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        throw "CPU/GPU benchmark failed for cpu-workers=$workers; see $stderr"
    }
}
