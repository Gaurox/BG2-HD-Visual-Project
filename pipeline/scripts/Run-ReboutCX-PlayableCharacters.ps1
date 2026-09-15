param(
    [ValidateRange(1, 64)]
    [int]$Workers = 16
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
$runner = Join-Path $projectRoot 'pipeline\scripts\reboutcx_character_family.py'

while (@(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object {
            $_.CommandLine -match 'reboutcx_full\.py' -and
            $_.CommandLine -match '6200-human-male-mage'
        }).Count -gt 0) {
    Start-Sleep -Seconds 15
}

$catalog = Get-Content `
    'sprite\catalogs\creature-x2-nearest\jobs\append-all-playable-characters-v1.json' `
    -Raw | ConvertFrom-Json
$jobs = foreach ($sourcePath in $catalog.members) {
    if ($sourcePath -notlike 'sprite/families/playable-characters/*' -or
        $sourcePath -like 'sprite/families/playable-characters/6100-human-male-fighter/*') {
        continue
    }
    $source = Get-Content -LiteralPath $sourcePath -Raw | ConvertFrom-Json
    $stem = $source.job_id -replace '-complete-xn-xbr2x$', ''
    $familyRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent `
        (Split-Path -Parent $sourcePath)))
    Join-Path $familyRoot "family-runs\complete-reboutcx-p8-v1\jobs\$stem-complete-reboutcx-p8-v1.json"
}

foreach ($jobPath in $jobs) {
    $job = Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json
    $runDir = Join-Path $projectRoot $job.paths.run_dir
    $audit = Join-Path $runDir 'audit.json'

    Write-Output ("{0} {1}" -f $job.animation_id, $jobPath)
    if (-not (Test-Path -LiteralPath $audit -PathType Leaf)) {
        & python $runner audit $jobPath
        if ($LASTEXITCODE -ne 0) { throw "audit failed: $jobPath" }
    }
    & python $runner prepare $jobPath
    if ($LASTEXITCODE -ne 0) { throw "prepare failed: $jobPath" }
    & python $runner build $jobPath --workers $Workers
    if ($LASTEXITCODE -ne 0) { throw "build failed: $jobPath" }
}
