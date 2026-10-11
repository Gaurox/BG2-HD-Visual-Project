$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$taskPlanPath = Join-Path $PSScriptRoot 'operation-plan.json'
$taskPlan = Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
if ($taskPlan.status -ne 'verified') { throw 'Missing verified plan' }
$taskTrashRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot $taskPlan.trash_root))
if (-not $taskTrashRoot.StartsWith($taskRoot + '\corbeille\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Trash outside workspace' }
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'operation-progress.json')) { throw 'Operation already started; inspect journal before resuming' }
function Assert-TaskPath($relative, $expected, $trash) {
    $absolute = [IO.Path]::GetFullPath((Join-Path $taskRoot $relative))
    $prefix = if ($trash) { $taskTrashRoot + '\' } else { $taskRoot + '\animations\' }
    if (-not $absolute.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not $absolute.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) { throw "Unexpected path: $relative" }
    return $absolute
}
function Assert-TaskSource($absolute, $directory) {
    $item = Get-Item -LiteralPath $absolute -Force
    if ($item.PSIsContainer -ne $directory -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Unexpected source: $absolute" }
    if ($directory) {
        if (@(Get-ChildItem -LiteralPath $absolute -Recurse -Force -Attributes ReparsePoint).Count) { throw "Reparse point: $absolute" }
        if (Test-Path -LiteralPath (Join-Path $absolute '.git')) { throw "Embedded Git: $absolute" }
    }
}
foreach ($entry in $taskPlan.deletes) {
    if ($entry.path -notmatch '^animations/(runs|batches)/[^/]+$|^animations/ressources/[^/]+/runs/[^/]+$') { throw 'Not a run root' }
    $absolute = Assert-TaskPath $entry.path $entry.absolute_path $false
    Assert-TaskSource $absolute $true
}
foreach ($entry in @($taskPlan.moves) + @($taskPlan.reservation_moves)) {
    $directory = $entry.source -notlike '*.reservation.json'
    if ($directory -and $entry.source -notmatch '^animations/(runs|batches)/[^/]+$|^animations/ressources/[^/]+/runs/[^/]+$') { throw 'Not a run root' }
    if (-not $directory -and $entry.source -notmatch '^animations/ressources/[^/]+/\.[^/]+\.reservation\.json$') { throw 'Not a reservation' }
    $source = Assert-TaskPath $entry.source $entry.absolute_source $false
    $destination = Assert-TaskPath $entry.destination $entry.absolute_destination $true
    Assert-TaskSource $source $directory
    if (Test-Path -LiteralPath $destination) { throw "Destination exists: $destination" }
    $ancestor = Split-Path -Parent $destination
    while ($ancestor.StartsWith($taskRoot, [StringComparison]::OrdinalIgnoreCase)) {
        if ((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Reparse destination: $ancestor" }
        $ancestor = Split-Path -Parent $ancestor
    }
}
$taskMoved = [Collections.Generic.List[string]]::new()
$taskDeleted = [Collections.Generic.List[string]]::new()
$taskUtf8 = [Text.UTF8Encoding]::new($false)
function Save-TaskProgress($status) {
    $journal = [ordered]@{ status = $status; moved = @($taskMoved); deleted = @($taskDeleted); plan_sha256 = (Get-FileHash -LiteralPath $taskPlanPath -Algorithm SHA256).Hash.ToLowerInvariant() }
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'operation-progress.json'), (($journal | ConvertTo-Json -Depth 5) + "`n"), $taskUtf8)
}
foreach ($entry in @($taskPlan.moves) + @($taskPlan.reservation_moves)) {
    $source = Assert-TaskPath $entry.source $entry.absolute_source $false
    $destination = Assert-TaskPath $entry.destination $entry.absolute_destination $true
    [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    if ((Test-Path -LiteralPath $source) -or -not (Test-Path -LiteralPath $destination)) { throw "Move incomplete: $source" }
    $taskMoved.Add($entry.source); Save-TaskProgress 'moving'
    Write-Output "QUARANTINED $($taskMoved.Count)/51 $($entry.source)"
}
foreach ($entry in $taskPlan.deletes) {
    $absolute = Assert-TaskPath $entry.path $entry.absolute_path $false
    Remove-Item -LiteralPath $absolute -Recurse -Force
    if (Test-Path -LiteralPath $absolute) { throw "Deletion incomplete: $absolute" }
    $taskDeleted.Add($entry.path); Save-TaskProgress 'deleting'
    Write-Output "DELETED $($taskDeleted.Count)/43 $($entry.path)"
}
Save-TaskProgress 'completed'
