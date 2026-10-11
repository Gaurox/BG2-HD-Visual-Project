$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$taskPlanPath = Join-Path $PSScriptRoot 'purge-plan.json'
$taskVerifiedPath = Join-Path $PSScriptRoot 'delete-verified.json'
$taskPlan = Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
$taskVerified = Get-Content -LiteralPath $taskVerifiedPath -Raw | ConvertFrom-Json
if ($taskVerified.status -ne 'verified') { throw 'Missing deletion precheck' }
if ((Get-FileHash -LiteralPath $taskPlanPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskVerified.plan_sha256) {
    throw 'The reviewed plan changed'
}
$taskTargets = [System.Collections.Generic.List[object]]::new()
foreach ($taskEntry in $taskVerified.records) {
    if ($taskEntry.path -notmatch '^animations/(runs|batches)/[^/]+$|^animations/ressources/[^/]+/runs/[^/]+$') {
        throw "Target outside the run-only scope: $($taskEntry.path)"
    }
    $taskAbsolute = [System.IO.Path]::GetFullPath((Join-Path $taskRoot $taskEntry.path))
    $taskAllowed = $taskRoot.TrimEnd('\') + '\animations\'
    if (-not $taskAbsolute.StartsWith($taskAllowed, [System.StringComparison]::OrdinalIgnoreCase) -or
        -not $taskAbsolute.Equals($taskEntry.absolute_path, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Resolved target outside workspace or changed: $taskAbsolute"
    }
    $taskItem = Get-Item -LiteralPath $taskAbsolute -Force
    if (-not $taskItem.PSIsContainer -or ($taskItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Target is not a plain run directory: $taskAbsolute"
    }
    $taskLinks = @(Get-ChildItem -LiteralPath $taskAbsolute -Recurse -Force -Attributes ReparsePoint)
    if ($taskLinks.Count) { throw "Reparse point under deletion target: $taskAbsolute" }
    if (Test-Path -LiteralPath (Join-Path $taskAbsolute '.git')) { throw "Embedded Git repository: $taskAbsolute" }
    $taskTargets.Add([pscustomobject]@{ path = $taskEntry.path; absolute = $taskAbsolute })
}
if ($taskTargets.Count -ne $taskPlan.deletion_count) { throw 'Target count differs from the plan' }
$taskProgress = [System.Collections.Generic.List[string]]::new()
$taskProgressPath = Join-Path $PSScriptRoot 'deletion-progress.json'
$taskUtf8 = [System.Text.UTF8Encoding]::new($false)
foreach ($taskTarget in $taskTargets) {
    # One shell end-to-end; literal validated paths only, never command-string deletion.
    Remove-Item -LiteralPath $taskTarget.absolute -Recurse -Force
    if (Test-Path -LiteralPath $taskTarget.absolute) { throw "Deletion incomplete: $($taskTarget.path)" }
    $taskProgress.Add($taskTarget.path)
    $taskJournal = [ordered]@{ status = 'deleting'; deleted = @($taskProgress); total = $taskTargets.Count }
    [IO.File]::WriteAllText($taskProgressPath, (($taskJournal | ConvertTo-Json -Depth 5) + "`n"), $taskUtf8)
    Write-Output "DELETED $($taskProgress.Count)/$($taskTargets.Count) $($taskTarget.path)"
}
$taskJournal = [ordered]@{ status = 'completed'; deleted = @($taskProgress); total = $taskTargets.Count }
[IO.File]::WriteAllText($taskProgressPath, (($taskJournal | ConvertTo-Json -Depth 5) + "`n"), $taskUtf8)
