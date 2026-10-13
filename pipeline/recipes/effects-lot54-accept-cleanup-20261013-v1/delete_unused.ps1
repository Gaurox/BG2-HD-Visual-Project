$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$allowed = [IO.Path]::GetFullPath((Join-Path $workspace 'effects/ressources')) + [IO.Path]::DirectorySeparatorChar
$reportDir = Join-Path $workspace 'effects/batches/lot54-accepted-cleanup-20261013-v1'
$plan = Get-Content -LiteralPath (Join-Path $reportDir 'purge-plan.json') -Raw | ConvertFrom-Json
if (Test-Path -LiteralPath (Join-Path $reportDir 'purge-receipt.json')) { throw 'Historical purge already completed' }
# Verify every absolute root and every byte before the first recursive deletion.
foreach ($target in $plan.targets) {
    $resolved = (Resolve-Path -LiteralPath $target.absolute_path).Path
    $expected = [IO.Path]::GetFullPath((Join-Path $workspace $target.path))
    if ($resolved -ne $expected -or -not $resolved.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw "Out of scope: $resolved" }
    $items = @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)
    if ((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse root: $resolved" }
    if (@($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw "Reparse child: $resolved" }
    if (@($items | Where-Object { -not $_.PSIsContainer }).Count -ne $target.file_count) { throw "Inventory changed: $resolved" }
    foreach ($file in $target.files) {
        $path = Join-Path $resolved $file.path
        if ((Get-Item -LiteralPath $path).Length -ne $file.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $file.sha256) { throw "Trial changed: $path" }
    }
}
$removed = @()
foreach ($target in $plan.targets) {
    Remove-Item -LiteralPath $target.absolute_path -Recurse -Force
    if (Test-Path -LiteralPath $target.absolute_path) { throw "Deletion failed: $($target.absolute_path)" }
    $removed += $target.path
    Write-Output "removed $($target.path)"
}
$receipt = [ordered]@{ schema='bg2-effects-unused-trials-purge-receipt-v1'; status='deleted-verified'; roots=$removed; root_count=$removed.Count; file_count=$plan.file_count; logical_bytes=$plan.logical_bytes; metadata='discarded-trial-metadata/'; free_space_gain_measured=$false }
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $reportDir 'purge-receipt.json') -Encoding utf8
