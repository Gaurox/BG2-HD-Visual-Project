param(
    [ValidateRange(1, 3)]
    [int]$Workers = 3
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot

$python = 'C:\Users\Adrien\AppData\Roaming\chaiNNer\python\python\python.exe'
$familyRunner = Join-Path $projectRoot 'pipeline\scripts\reboutcx_character_family.py'
$p9Runner = Join-Path $projectRoot 'pipeline\scripts\reboutcx_full_p9.py'
$logs = Join-Path $projectRoot 'sprite\.work\reboutcx-p9-production'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Invoke-P9Verify([string]$Job, [string]$Prefix) {
    $verifyLog = Join-Path $logs ("{0}.verify.log" -f $Prefix.ToLowerInvariant())
    & $python $p9Runner verify $Job *> $verifyLog
    if ($LASTEXITCODE -ne 0) { throw "P9 verify failed: $Prefix; see $verifyLog" }
}

function New-P9Job([string]$P8Job) {
    $result = & $python $p9Runner derive-job $P8Job
    if ($LASTEXITCODE -ne 0) { throw "P9 job derivation failed: $P8Job" }
    return (Join-Path $projectRoot $result.Trim())
}

$catalog = Get-Content -LiteralPath 'sprite\catalogs\creature-x2-nearest\jobs\append-all-playable-characters-v1.json' -Raw | ConvertFrom-Json
$familyJobs = foreach ($sourcePath in $catalog.members) {
    if ($sourcePath -notlike 'sprite/families/playable-characters/*' -or
        $sourcePath -like 'sprite/families/playable-characters/6100-human-male-fighter/*') {
        continue
    }
    $source = Get-Content -LiteralPath $sourcePath -Raw | ConvertFrom-Json
    $stem = $source.job_id -replace '-complete-xn-xbr2x$', ''
    $familyRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $sourcePath)))
    [PSCustomObject]@{
        Animation = $source.animation.id
        P8Job = Join-Path $familyRoot "family-runs\complete-reboutcx-p8-v1\jobs\$stem-complete-reboutcx-p8-v1.json"
    }
}

$completedFamilies = 1 # 0x6200 was fully produced and verified before the P9 migration.
foreach ($family in $familyJobs) {
    if ($family.Animation -eq '0x6200') { continue }
    $p8 = Get-Content -LiteralPath $family.P8Job -Raw | ConvertFrom-Json
    $p8Run = Join-Path $projectRoot $p8.paths.run_dir
    $audit = Join-Path $p8Run 'audit.json'
    if (-not (Test-Path -LiteralPath $audit -PathType Leaf)) {
        & python $familyRunner audit $family.P8Job
        if ($LASTEXITCODE -ne 0) { throw "P8 audit bootstrap failed: $($family.Animation)" }
    }
    & python $familyRunner prepare $family.P8Job
    if ($LASTEXITCODE -ne 0) { throw "P8 prepare bootstrap failed: $($family.Animation)" }
    $prepared = Get-Content -LiteralPath (Join-Path $p8Run 'prepared.json') -Raw | ConvertFrom-Json
    $queue = foreach ($member in $prepared.members) {
        $p9Job = New-P9Job (Join-Path $projectRoot $member.job)
        $p9 = Get-Content -LiteralPath $p9Job -Raw | ConvertFrom-Json
        $p9Manifest = Join-Path $projectRoot (Join-Path $p9.paths.run_dir 'manifest.json')
        [PSCustomObject]@{ Prefix = $member.bam_prefix; Job = $p9Job; Manifest = $p9Manifest }
    }
    Write-Output ("{0} P9 queue {1} components; workers={2}" -f $family.Animation, $queue.Count, $Workers)
    $active = [System.Collections.Generic.List[object]]::new()
    $next = 0
    $verified = 0
    while ($next -lt $queue.Count -or $active.Count -gt 0) {
        while ($next -lt $queue.Count -and $active.Count -lt $Workers) {
            $item = $queue[$next]
            $next++
            if (Test-Path -LiteralPath $item.Manifest -PathType Leaf) {
                Invoke-P9Verify $item.Job $item.Prefix
                $verified++
                Write-Output ("{0} [{1}/{2}] {3} verified-existing" -f $family.Animation, $verified, $queue.Count, $item.Prefix)
                continue
            }
            $stdout = Join-Path $logs ("{0}.{1}.run.log" -f $family.Animation, $item.Prefix.ToLowerInvariant())
            $stderr = Join-Path $logs ("{0}.{1}.err.log" -f $family.Animation, $item.Prefix.ToLowerInvariant())
            $process = Start-Process -FilePath $python -ArgumentList @($p9Runner, '_execute', $item.Job, '--batch-size', '86', '--cpu-workers', '3', '--bucket-quantum', '64') -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
            $active.Add([PSCustomObject]@{ Process = $process; Item = $item; Started = Get-Date; Stdout = $stdout; Stderr = $stderr })
            Write-Output ("{0} [{1}/{2}] {3} start PID={4}" -f $family.Animation, $next, $queue.Count, $item.Prefix, $process.Id)
        }
        $finished = @($active | Where-Object { $_.Process.HasExited })
        if ($finished.Count -eq 0) {
            Start-Sleep -Seconds 1
            continue
        }
        foreach ($record in $finished) {
            $record.Process.Refresh()
            $active.Remove($record)
            if ($record.Process.ExitCode -ne 0) {
                throw "P9 run failed: $($family.Animation) $($record.Item.Prefix); see $($record.Stderr)"
            }
            Invoke-P9Verify $record.Item.Job $record.Item.Prefix
            $verified++
            $elapsed = [math]::Round(((Get-Date) - $record.Started).TotalSeconds, 1)
            Write-Output ("{0} [{1}/{2}] {3} verified {4}s" -f $family.Animation, $verified, $queue.Count, $record.Item.Prefix, $elapsed)
        }
    }
    $completedFamilies++
    Write-Output ("{0} P9 family components complete; families={1}/75" -f $family.Animation, $completedFamilies)
}
